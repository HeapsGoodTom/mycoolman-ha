# HANDOFF — myCOOLMAN Home Assistant integration

A working context document for picking this project up in VS Code (with the
Claude Code extension). Read this first, then `README.md`, then the source under
`custom_components/mycoolman/`.

> **Secrets note:** the fridge's Bluetooth MAC and 3-digit PIN are **not** in
> this repo. They live only in Home Assistant's config entry. Never commit real
> MAC/PIN values — this repo is public.

---

## 1. What this project is

An **unofficial Home Assistant custom integration** that monitors and controls a
**myCOOLMAN** portable compressor fridge/freezer over Bluetooth Low Energy.

- No cloud, no vendor account — everything is local.
- The BLE connection is made through Home Assistant's Bluetooth stack, so it runs
  over an **existing ESPHome Bluetooth Proxy** (no dedicated ESP needed).
- Distributed via **HACS** as a custom repository:
  `https://github.com/HeapsGoodTom/mycoolman-ha`.
- The protocol was reverse-engineered from the *myCOOLMAN Recreation* Android app
  (`https://github.com/luoxs/Mycoolman`), then extended by live probing.

**Target device during development:** a single-zone **MCMR43**. The single-zone
**MCMR60** should also work via the same protocol (untested). Dual-zone models
(**MCMR38DZ**, **MCMR55DZ**, **MCMR78DZ**) expose extra freezer fields this
integration does not yet use, and protocol compatibility is unconfirmed —
needs testing.

### Architecture at a glance

- `iot_class: local_push` — a persistent BLE connection with GATT notifications.
- One `DataUpdateCoordinator` per fridge owns the connection, parses 22-byte
  status frames pushed by the device, and exposes async command helpers.
- Connections use `bleak_retry_connector.establish_connection` (required by HA;
  raw `BleakClient.connect` triggers warnings).
- **Connection-slot budget:** an ESP32 proxy allows **3** simultaneous active
  connections. This integration holds one continuously for push updates.

---

## 2. Repository layout

```
mycoolman-ha/
├── README.md
├── HANDOFF.md                     ← this file
├── hacs.json                      ← HACS metadata
├── logo.png                       ← shown in README / HACS description panel
└── custom_components/mycoolman/
    ├── __init__.py                ← setup/unload + `send_command` diagnostic service
    ├── manifest.json              ← domain, bluetooth matcher, requirements, version
    ├── const.py                   ← DOMAIN, CONF_PIN, temp range, update interval
    ├── protocol.py                ← CRC, command builder, status parser  ★ START HERE
    ├── coordinator.py             ← BLE connection + notify parsing + command methods
    ├── config_flow.py             ← Bluetooth discovery + manual setup + PIN entry
    ├── entity.py                  ← shared base entity (device_info, availability)
    ├── climate.py                 ← primary thermostat control (temp + power)
    ├── sensor.py                  ← temperature, setpoint, voltage, error code
    ├── binary_sensor.py           ← turbo, pairing OK
    ├── switch.py                  ← power, turbo
    ├── number.py                  ← setpoint (disabled by default; climate supersedes)
    ├── select.py                  ← battery protection, display unit
    ├── button.py                  ← show pairing code on fridge display
    ├── services.yaml              ← UI schema for the diagnostic service
    ├── strings.json               ← config-flow + entity name strings
    ├── translations/en.json       ← copy of strings.json
    └── brand/
        ├── icon.png               ← 256×256  (HA 2026.3+ local brand image)
        └── icon@2x.png            ← 512×512
```

`protocol.py` is pure functions with no HA dependencies — the best place to read
and unit-test the wire format.

---

## 3. Protocol reference

### GATT

| Item | Value |
|---|---|
| Service UUID | `0000fee0-0000-1000-8000-00805f9b34fb` |
| Characteristic | `0000fee1-0000-1000-8000-00805f9b34fb` (both notify **and** write) |

### PIN encoding

The 3-hex-digit PIN becomes two payload bytes carried in every command:

```
P3 = int(pin[0], 16)
P4 = (int(pin[1], 16) << 4) | int(pin[2], 16)
# example format only:  "ABC" -> P3=0x0A, P4=0xBC
```

The fridge validates the PIN per-command and reports validity in the status
frame (`gc` byte, below). A wrong PIN does **not** stop the fridge replying — it
just returns `gc == 0`. This makes the PIN brute-forceable (≤4096 combos) and is
how `binary_sensor` "Pairing OK" works.

### Command frame (app → fridge), 8 bytes

```
AA  CMD  ARG  P3  P4  CRC_HI  CRC_LO  55
```

- `0xAA` start, `0x55` end.
- CRC = **Modbus CRC16** (poly `0xA001`, init `0xFFFF`) over the 4 bytes
  `CMD ARG P3 P4` only, appended **high byte first**.

### Command opcodes

| Opcode | Meaning | Argument | Status |
|---|---|---|---|
| `0x01` | Request/refresh status | `0x00` | confirmed |
| `0x02` | Power | `0x01` on / `0x00` off | confirmed |
| `0x03` | Set temperature | target °C as signed int8 (`-18` → `0xEE`) | confirmed |
| `0x05` | Turbo | `0x01` on / `0x00` off | confirmed |
| `0x07` | Battery protection | `0x00` Low / `0x01` Medium / `0x02` High | confirmed |
| `0x08` | Display unit | `0x00` °C / `0x01` °F (fridge display only) | confirmed by probing |
| `0x09` | Show pairing code on display | `0x00` | confirmed by probing |
| `0x0C` | LED | `0x00` High White / `0x01` Low White / `0x02` Orange | confirmed by probing |
| `0x0D` | Buzzer | `0x00` on / `0x01` off | confirmed by probing |
| `0x0E` | Auto-dim (fridge display) | `0x00` on / `0x01` off | confirmed by probing |
| `0x04`, `0x06`, `0x0A`, `0x0B` | — | tried args 0/1/2, no observed effect | dead? |

### Status frame (fridge → app), 22 bytes

| Idx | Field | Notes |
|---|---|---|
| 0 | start | frame marker |
| 1 | power | 0/1 |
| 2 | setpoint | signed int8 °C (cool zone) |
| 3 | temperature | signed int8 °C (real, cool zone) |
| 4 | freezer setpoint | dual-zone only, unused |
| 5 | freezer real | dual-zone only, unused |
| 6 | turbo | 0/1 |
| 7 | heat | unused |
| 8 | battery protection | 0 Low / 1 Medium / 2 High |
| 9 | unit | 1 = °C |
| 10 | status | meaning unknown — candidate for compressor state |
| 11 | error code | raw |
| 12–13 | voltage hi/lo | scaling **unconfirmed** (assumed ÷10 → volts) |
| 14 | `gc` | 0 = PIN rejected |
| 15 | heat setpoint | unused |
| 16 | timer | unused |
| 17 | `code1` | bits 0-1 = LED mode index (0=High White/1=Low White/2=Orange); bit 2 = buzzer off; bit 3 = auto-dim off. Confirmed by live probing. |
| 18 | `code2` | **unknown** — confirmed flat/uninformative across every capture so far |
| 19–21 | CRC hi, CRC lo, `0x55` | |

Temperatures decode as `value - 256 if value > 128 else value` (signed int8, °C).
The fridge always transmits Celsius; the unit setting only affects its own screen.

---

## 4. Entities & service currently implemented

- **climate** — primary control: current temp, target-temp dial, power mapped to
  off/cool. Temperature unit fixed to Celsius (data integrity).
- **sensor** — temperature, setpoint (read-back), input voltage, error code.
- **binary_sensor** — turbo, pairing OK.
- **switch** — power, turbo, buzzer, auto-dim.
- **number** — setpoint (disabled by default; the climate entity supersedes it).
- **select** — battery protection; display unit (°C/°F); LED mode (High
  White/Low White/Orange).
- **options flow** — adjust the fridge's setpoint range (min/max °C) after
  setup, via **Configure** on the integration's device card.
- **button** — show pairing code on the fridge display.
- **service** `mycoolman.send_command` — diagnostic; sends a raw
  `command`/`argument` with correct PIN + CRC. Optional `address` to target a
  specific fridge. This is the probing tool for undiscovered opcodes.

---

## 5. Dev environment setup (VS Code)

You do **not** need a full HA source checkout. Pick the level that suits you.

### 5a. Minimal (lint + compile locally, test on real HA)

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install ruff                   # HA's linter/formatter
ruff check .
ruff format --check .
python -m compileall custom_components/mycoolman
```

Match your HA's Python version if you can (recent HA runs 3.13/3.14).

### 5b. Fuller (import HA APIs, run hassfest-style checks)

```bash
pip install homeassistant ruff
```

Installing `homeassistant` lets your editor resolve the `homeassistant.*`
imports for autocomplete and type checking. It's a large install; skip it if you
only need lint + on-device testing.

### 5c. Suggested repo dev files to add

`.github/workflows/validate.yml` (standard HACS validation in CI):

```yaml
name: Validate
on:
  push:
  pull_request:
  schedule:
    - cron: "0 0 * * *"
jobs:
  hacs:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: hacs/action@main
        with:
          category: integration
  hassfest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: home-assistant/actions/hassfest@master
```

`ruff.toml` (light, HA-flavoured):

```toml
target-version = "py313"
[lint]
select = ["E", "F", "I", "UP", "B", "SIM"]
```

`.gitignore`:

```
.venv/
__pycache__/
*.pyc
```

---

## 6. Test loop against your real Home Assistant

Because the integration needs the actual fridge + proxy, real testing happens on
your HA instance.

1. Get the code onto HA. On Home Assistant OS, install the **Samba share** or
   **Advanced SSH & Web Terminal** add-on and copy the folder to
   `/config/custom_components/mycoolman/`. (Or edit in place with the **Studio
   Code Server** add-on.)
2. **Restart Home Assistant** — custom-component *code* changes require a full
   restart (reloading the entry alone won't re-import changed modules).
3. Watch **Settings → System → Logs**, or enable debug logging in
   `configuration.yaml`:

   ```yaml
   logger:
     default: warning
     logs:
       custom_components.mycoolman: debug
   ```

   Debug logs print each parsed status dict (temperature, voltage, `code1`,
   `code2`, `paired`, …) — useful for the open questions below.
4. Probe unknown opcodes via **Developer Tools → Actions →
   myCOOLMAN: Send raw command**.

---

## 7. Release / HACS workflow

1. Bump `version` in `manifest.json` (semver). `0.1.0` was the baseline;
   `0.2.0` added display-unit + show-pin + diagnostic-service, plus the
   configurable setpoint range; `0.3.0` added the LED/buzzer/auto-dim
   entities and the myCOOLMAN MCMR Fridge/Freezer rename.
2. Commit and push. Optionally tag a GitHub release — HACS can track either the
   default branch or releases.
3. Users update through HACS. `brand/icon.png` shows inside HA on 2026.3+; the
   HACS store tile currently still reads from the HACS CDN, so it may look blank
   there (known HACS limitation) — the README `logo.png` covers the description.

---

## 8. Open tasks / roadmap

**High-value, unblocked:**

1. **Verify voltage scaling.** The 43 has no on-device display option for input
   voltage (checked the menu and manual — not present), so the sensor can't be
   confirmed against the fridge itself. A multimeter reading at the DC input
   barrel plug, compared against the "Input voltage" sensor, is the only
   remaining way to confirm/adjust the divisor in `protocol.parse_status`
   (bytes 12–13). Still open.
2. ~~Test the `code1`/`code2` = PIN echo theory.~~ — **Refuted.** Captured a debug
   status frame: `code1=8`, `code2=0`. `P3` happened to match (`8`), but `P4`
   (`34`) did not — `code1`/`code2` are not the PIN echoed back. Self-discovering
   PINs is not possible via these bytes; their actual meaning is still unknown.

**Needs data capture:**

3. ~~LED, buzzer, auto-dim opcodes.~~ — **Confirmed by live probing** against a
   real MCMR43: `0x0C` = LED (`select`: High White/Low White/Orange), `0x0D` =
   buzzer (`switch`), `0x0E` = auto-dim (`switch`). `0x0A`/`0x0B` remain dead
   (tried, no observed effect). Implemented.
4. ~~Once LED/buzzer/dim state is known, check whether any unknown status
   byte changes when you toggle them.~~ — **Confirmed and implemented.**
   `code1` (byte 17) is a bitmask: bits 0-1 = LED mode index, bit 2 = buzzer
   off, bit 3 = auto-dim off (10 live captures, zero exceptions; every other
   byte in the frame stayed flat). LED/buzzer/auto-dim are now real read-back
   entities, not optimistic — `protocol.parse_status` decodes them directly.

**Polish:**

5. ~~Confirm the real setpoint range for the 43~~ — confirmed −20…20°C. Now
   user-configurable per entry via the config flow (setup) and options flow
   (Configure button); `DEFAULT_MIN_TEMP`/`DEFAULT_MAX_TEMP` in `const.py` are
   just the fallback for entries with no override.
6. Optional: transparent, trimmed `brand/icon.png` for a cleaner in-HA icon.
7. Optional: add `tests/` with `pytest` unit tests for `protocol.py`
   (CRC vectors, frame build, status parse) — no hardware needed.

---

## 9. Gotchas learned the hard way

- `DeviceInfo` imports from `homeassistant.helpers.device_registry`, **not**
  `homeassistant.helpers.device_info` (that module doesn't exist). A wrong import
  in `entity.py` takes down every platform that imports it.
- The CRC in the *received* frames is high-byte-first followed by the `0x55` end
  byte; the *sent* frames also append CRC high-byte-first. Keep them consistent.
- A "scanner only" Bluetooth Proxy build can't hold active connections — the
  fridge needs a proxy with active connections enabled (the default build).
- Don't exceed the ESP32's 3 active-connection limit on the chosen proxy.

---

## 10. Working with Claude Code

- Point the assistant at this file first (`Read HANDOFF.md`), then `protocol.py`.
- Claude Code auto-loads a `CLAUDE.md` at the repo root as project memory. If you
  want that, add a short `CLAUDE.md` that says "See HANDOFF.md for full context"
  plus the one-line build/lint commands from §5a.
- Good first prompts: "Add pytest unit tests for protocol.py using the CRC
  vectors in HANDOFF.md" or "Implement LED select + buzzer switch given these
  captured opcodes: …".
