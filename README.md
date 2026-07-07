<img src="logo.png" alt="myCOOLMAN" width="240" align="right" />

# myCOOLMAN for Home Assistant

Control and monitor a **myCOOLMAN** portable fridge/freezer (single-zone models
such as the CTP/CTG 43) over Bluetooth LE from Home Assistant — using your
existing **ESPHome Bluetooth Proxy**, no dedicated ESP required.

The protocol was reverse-engineered from the *myCOOLMAN Recreation* Android app
([github.com/luoxs/Mycoolman](https://github.com/luoxs/Mycoolman)). No cloud, no
account — everything is local.

## Entities

| Entity | Type | Notes |
|---|---|---|
| Temperature | sensor | Cabinet temperature (°C) |
| Setpoint | sensor + number | Read-back and control |
| Input voltage | sensor | Scaling is a best guess — verify (see below) |
| Error code | sensor | Raw status/error byte |
| Power | switch | On/off |
| Turbo | switch / binary_sensor | Turbo mode |
| Battery protection | select | Low / Medium / High |
| Pairing OK | binary_sensor | Reflects the fridge's PIN-valid flag |

## Requirements

- Home Assistant with the **Bluetooth** integration set up.
- A Bluetooth adapter **or an ESPHome Bluetooth Proxy with active connections**
  (the default proxy build). The fridge uses one of the ESP32's **3** active
  connection slots.
- Your fridge's **3-digit pairing PIN** (shown on the fridge display during
  pairing; if you've lost it, remove the fridge in the official app or clear the
  app's storage to make it display again).

## Install via HACS

1. HACS → three-dot menu → **Custom repositories**.
2. Add this repository's URL, category **Integration**.
3. Install **myCOOLMAN**, then restart Home Assistant.
4. The fridge should be auto-discovered under **Settings → Devices & Services**.
   Otherwise add it manually via **+ Add Integration → myCOOLMAN**.
5. Enter the 3-digit PIN when prompted, then set the fridge's setpoint range
   (defaults to −20…20 °C, confirmed for the single-zone 43 — adjust if your
   model differs).

## Verifying the voltage scaling

Bytes 12–13 of the status frame are assumed to be voltage in tenths of a volt.
Compare the "Input voltage" sensor against the fridge's own display; if it's off
by a constant factor, adjust the divisor in `protocol.py` (`parse_status`).

## Notes / limitations

- The integration holds a persistent connection (for push updates), so it
  occupies one proxy connection slot continuously.
- The fridge must stay within range of a proxy/adapter.
- Setpoint range defaults to −20…20 °C (confirmed for the single-zone 43). Set
  it during setup, or change it later via **Settings → Devices & Services →
  myCOOLMAN → Configure**.

## Disclaimer

Unofficial, not affiliated with or endorsed by myCOOLMAN. Use at your own risk.
