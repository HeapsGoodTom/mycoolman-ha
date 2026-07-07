<img src="logo.png" alt="myCOOLMAN" width="240" align="right" />

# myCOOLMAN MCMR Fridge/Freezer for Home Assistant

<a href="https://www.buymeacoffee.com/heapsgoodtom"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" height="40" /></a>

Control and monitor a **myCOOLMAN MCMR** portable fridge/freezer over
Bluetooth LE from Home Assistant — using your existing **ESPHome Bluetooth
Proxy**, no dedicated ESP needed. Confirmed working on the single-zone
**MCMR43**; the single-zone **MCMR60** should also work via the same protocol
(untested). Dual-zone models — **MCMR38DZ**, **MCMR55DZ**, **MCMR78DZ** — are
untested and expose extra freezer fields this integration does not yet use.

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
| LED | select | High White / Low White / Orange (write-only) |
| Buzzer | switch | Write-only |
| Auto-dim | switch | Display auto-dim, write-only |

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
3. Install **myCOOLMAN MCMR Fridge/Freezer**, then restart Home Assistant.
4. The fridge should be auto-discovered under **Settings → Devices & Services**.
   Otherwise add it manually via **+ Add Integration → myCOOLMAN MCMR Fridge/Freezer**.
5. Enter the 3-digit PIN when prompted, then set the fridge's setpoint range
   (defaults to −20…20 °C, confirmed for the single-zone MCMR43 — adjust if your
   model differs).

## Verifying the voltage scaling

Bytes 12–13 of the status frame are assumed to be voltage in tenths of a volt.
Compare the "Input voltage" sensor against the fridge's own display; if it's off
by a constant factor, adjust the divisor in `protocol.py` (`parse_status`).

## Next steps

- **MCMR60 / dual-zone owners** — if you can install this and report back (or
  open an issue) with what works and what doesn't, that would help a lot; only
  a single-zone MCMR43 has been tested against so far.
- **Input voltage scaling** — see [Verifying the voltage scaling](#verifying-the-voltage-scaling)
  above; a multimeter reading at the DC input barrel plug compared against the
  sensor would confirm or correct the divisor.
- **Bugs, feature ideas, or other models** — issues and PRs are welcome on the
  repo.

## Notes / limitations

- The integration holds a persistent connection (for push updates), so it
  occupies one proxy connection slot continuously.
- The fridge must stay within range of a proxy/adapter.
- Setpoint range defaults to −20…20 °C (confirmed for the single-zone MCMR43). Set
  it during setup, or change it later via **Settings → Devices & Services →
  myCOOLMAN MCMR Fridge/Freezer → Configure**.

## Disclaimer

Unofficial, not affiliated with or endorsed by myCOOLMAN. Use at your own risk.

This integration was built with the assistance of Claude (Anthropic's AI
coding assistant) — the author is an enthusiast, not a professional
programmer. Review the code yourself before relying on it, especially around
Bluetooth connection handling.

The BLE protocol was learned by observing and analyzing the behavior of the
*myCOOLMAN Recreation* Android app (github.com/luoxs/Mycoolman) as a
reference; no source code from that project is included here. That project's
repository does not clearly state a license, so if you plan to reuse protocol
details beyond what's documented in this README, verify your own rights to do
so independently.

## License

MIT — see [LICENSE](LICENSE).
