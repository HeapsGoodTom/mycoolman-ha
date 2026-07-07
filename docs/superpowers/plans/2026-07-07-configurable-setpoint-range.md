# Configurable Setpoint Range Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a user set their fridge's min/max setpoint range at setup and later via the integration's Configure screen, instead of hardcoding `-20`/`20` in `const.py`.

**Architecture:** The range lives in `entry.options` under two new keys (`min_temp`, `max_temp`), written by both the config flow (a new step after PIN entry) and a new options flow. `MyCoolmanCoordinator` (which already holds a reference to the config entry) exposes `min_temp`/`max_temp` properties that read from options with a `-20`/`20` fallback; `climate.py` and `number.py` read the live value from the coordinator instead of a fixed class attribute. An update listener reloads the entry automatically when options change, so edits apply immediately.

**Tech Stack:** Home Assistant custom integration (Python), `voluptuous` for config-flow schemas, `ruff` for lint/format.

**Testing approach:** This repo has no automated test harness for the Home Assistant platform layer (config flow / entities) — see `HANDOFF.md` §5, §8 item 7, which lists a `pytest` suite as a separate, not-yet-done piece of future work, scoped only to `protocol.py` (pure functions, no HA dependency). Building out `pytest-homeassistant-custom-component` scaffolding is out of scope for this feature. Each task below is instead verified with `ruff check` / `ruff format --check` / `python -m compileall` (catching syntax/import errors) plus a manual verification pass against a real Home Assistant instance in the final task, matching the spec's "Testing" section.

---

### Task 1: Core range plumbing (`const.py`, `coordinator.py`, `climate.py`, `number.py`)

**Files:**
- Modify: `custom_components/mycoolman/const.py`
- Modify: `custom_components/mycoolman/coordinator.py`
- Modify: `custom_components/mycoolman/climate.py`
- Modify: `custom_components/mycoolman/number.py`

- [ ] **Step 1: Update `const.py` — add option keys, rename the fixed constants to defaults**

Replace the file's contents with:

```python
"""Constants for the myCOOLMAN integration."""

DOMAIN = "mycoolman"

CONF_PIN = "pin"
CONF_MIN_TEMP = "min_temp"
CONF_MAX_TEMP = "max_temp"

# How often to poke the fridge for a fresh frame (also acts as a keepalive /
# reconnect trigger). Status also arrives asynchronously via notifications.
UPDATE_INTERVAL_SECONDS = 30

# Default setpoint range, confirmed for the single-zone 43. Other models may
# support a different range; the config/options flow lets a user override it
# per entry. These are only the fallback when an entry has no override set.
DEFAULT_MIN_TEMP = -20
DEFAULT_MAX_TEMP = 20
```

- [ ] **Step 2: Add range properties to `coordinator.py`**

In `custom_components/mycoolman/coordinator.py`, change the import line:

```python
from .const import DOMAIN, UPDATE_INTERVAL_SECONDS
```

to:

```python
from .const import (
    CONF_MAX_TEMP,
    CONF_MIN_TEMP,
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
    DOMAIN,
    UPDATE_INTERVAL_SECONDS,
)
```

Then add these two properties right after `__init__` (before the `# -- connection management` comment):

```python
    @property
    def min_temp(self) -> int:
        """Minimum settable temperature, from entry options or the default."""
        return self._entry.options.get(CONF_MIN_TEMP, DEFAULT_MIN_TEMP)

    @property
    def max_temp(self) -> int:
        """Maximum settable temperature, from entry options or the default."""
        return self._entry.options.get(CONF_MAX_TEMP, DEFAULT_MAX_TEMP)
```

- [ ] **Step 3: Point `climate.py` at the coordinator's live range**

In `custom_components/mycoolman/climate.py`, remove the constants import:

```python
from .const import MAX_TEMP, MIN_TEMP
```

Remove these two class attributes:

```python
    _attr_min_temp = MIN_TEMP
    _attr_max_temp = MAX_TEMP
```

Add these properties to `MyCoolmanClimate` (right after `__init__`, before `current_temperature`):

```python
    @property
    def min_temp(self) -> float:
        return self.coordinator.min_temp

    @property
    def max_temp(self) -> float:
        return self.coordinator.max_temp
```

- [ ] **Step 4: Point `number.py` at the coordinator's live range**

In `custom_components/mycoolman/number.py`, remove the constants import:

```python
from .const import MAX_TEMP, MIN_TEMP
```

Remove these two class attributes:

```python
    _attr_native_min_value = MIN_TEMP
    _attr_native_max_value = MAX_TEMP
```

Add these properties to `MyCoolmanSetpoint` (right after `__init__`, before `native_value`):

```python
    @property
    def native_min_value(self) -> float:
        return self.coordinator.min_temp

    @property
    def native_max_value(self) -> float:
        return self.coordinator.max_temp
```

- [ ] **Step 5: Lint and compile-check**

Run:

```bash
ruff check custom_components/mycoolman
ruff format --check custom_components/mycoolman
python -m compileall custom_components/mycoolman
```

Expected: all three report no errors. (If `ruff`/`homeassistant` aren't installed yet, follow `HANDOFF.md` §5a to set up the venv first.)

- [ ] **Step 6: Commit**

```bash
git add custom_components/mycoolman/const.py custom_components/mycoolman/coordinator.py custom_components/mycoolman/climate.py custom_components/mycoolman/number.py
git commit -m "Read setpoint range from the coordinator instead of a fixed constant"
```

---

### Task 2: Config flow — collect the range at setup

**Files:**
- Modify: `custom_components/mycoolman/config_flow.py`
- Modify: `custom_components/mycoolman/strings.json`
- Modify: `custom_components/mycoolman/translations/en.json`

- [ ] **Step 1: Update imports and `__init__` in `config_flow.py`**

Change:

```python
from .const import CONF_PIN, DOMAIN
```

to:

```python
from .const import (
    CONF_MAX_TEMP,
    CONF_MIN_TEMP,
    CONF_PIN,
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
    DOMAIN,
)
```

Change:

```python
    def __init__(self) -> None:
        self._discovered_address: str | None = None
        self._discovered_name: str | None = None
        # address -> label, for the manual picker
        self._discovered: dict[str, str] = {}
```

to:

```python
    def __init__(self) -> None:
        self._discovered_address: str | None = None
        self._discovered_name: str | None = None
        self._pin: str | None = None
        # address -> label, for the manual picker
        self._discovered: dict[str, str] = {}
```

- [ ] **Step 2: Make `async_step_pin` hand off to a new range step**

Change the body of `async_step_pin` from:

```python
    async def async_step_pin(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect the 3-digit PIN and finish."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                pin_to_bytes(user_input[CONF_PIN])
            except ValueError:
                errors["base"] = "invalid_pin"
            else:
                return self.async_create_entry(
                    title=self._discovered_name or "myCOOLMAN Fridge",
                    data={
                        CONF_ADDRESS: self._discovered_address,
                        CONF_PIN: user_input[CONF_PIN].strip(),
                    },
                )

        return self.async_show_form(
            step_id="pin",
            data_schema=vol.Schema({vol.Required(CONF_PIN): str}),
            errors=errors,
            description_placeholders={"address": self._discovered_address or ""},
        )
```

to:

```python
    async def async_step_pin(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect the 3-digit PIN, then move on to the setpoint range."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                pin_to_bytes(user_input[CONF_PIN])
            except ValueError:
                errors["base"] = "invalid_pin"
            else:
                self._pin = user_input[CONF_PIN].strip()
                return await self.async_step_range()

        return self.async_show_form(
            step_id="pin",
            data_schema=vol.Schema({vol.Required(CONF_PIN): str}),
            errors=errors,
            description_placeholders={"address": self._discovered_address or ""},
        )

    async def async_step_range(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect the fridge's setpoint range and create the entry."""
        errors: dict[str, str] = {}
        if user_input is not None:
            min_temp = user_input[CONF_MIN_TEMP]
            max_temp = user_input[CONF_MAX_TEMP]
            if min_temp >= max_temp:
                errors["base"] = "min_max_invalid"
            else:
                return self.async_create_entry(
                    title=self._discovered_name or "myCOOLMAN Fridge",
                    data={
                        CONF_ADDRESS: self._discovered_address,
                        CONF_PIN: self._pin,
                    },
                    options={
                        CONF_MIN_TEMP: min_temp,
                        CONF_MAX_TEMP: max_temp,
                    },
                )

        return self.async_show_form(
            step_id="range",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MIN_TEMP, default=DEFAULT_MIN_TEMP): vol.Coerce(
                        int
                    ),
                    vol.Required(CONF_MAX_TEMP, default=DEFAULT_MAX_TEMP): vol.Coerce(
                        int
                    ),
                }
            ),
            errors=errors,
        )
```

- [ ] **Step 3: Add the new strings to `strings.json`**

In `custom_components/mycoolman/strings.json`, add a `"range"` step under `config.step` (after `"pin"`):

```json
      "range": {
        "title": "Setpoint range",
        "description": "Set the minimum and maximum temperature your fridge supports. Defaults are confirmed for the single-zone myCOOLMAN 43; adjust if yours differs.",
        "data": {
          "min_temp": "Minimum temperature (°C)",
          "max_temp": "Maximum temperature (°C)"
        }
      }
```

And add `min_max_invalid` under `config.error` (after `"invalid_pin"`):

```json
      "min_max_invalid": "Maximum temperature must be greater than the minimum."
```

The full `config` block should now read:

```json
  "config": {
    "flow_title": "{name}",
    "step": {
      "user": {
        "title": "myCOOLMAN",
        "description": "Select your fridge.",
        "data": {
          "address": "Device"
        }
      },
      "pin": {
        "title": "Pairing PIN",
        "description": "Enter the 3-digit pairing PIN for {address} (shown on the fridge display during pairing).",
        "data": {
          "pin": "PIN"
        }
      },
      "range": {
        "title": "Setpoint range",
        "description": "Set the minimum and maximum temperature your fridge supports. Defaults are confirmed for the single-zone myCOOLMAN 43; adjust if yours differs.",
        "data": {
          "min_temp": "Minimum temperature (°C)",
          "max_temp": "Maximum temperature (°C)"
        }
      }
    },
    "error": {
      "invalid_pin": "The PIN must be exactly 3 hex digits (e.g. 822).",
      "min_max_invalid": "Maximum temperature must be greater than the minimum."
    },
    "abort": {
      "already_configured": "This fridge is already configured.",
      "no_devices_found": "No myCOOLMAN fridge was found. Make sure it is powered on and in range of a Bluetooth adapter or proxy."
    }
  },
```

- [ ] **Step 4: Apply the identical change to `translations/en.json`**

`custom_components/mycoolman/translations/en.json` is a copy of `strings.json`.
Add the same `"range"` step under `config.step` (after `"pin"`):

```json
      "range": {
        "title": "Setpoint range",
        "description": "Set the minimum and maximum temperature your fridge supports. Defaults are confirmed for the single-zone myCOOLMAN 43; adjust if yours differs.",
        "data": {
          "min_temp": "Minimum temperature (°C)",
          "max_temp": "Maximum temperature (°C)"
        }
      }
```

And the same `min_max_invalid` entry under `config.error` (after `"invalid_pin"`):

```json
      "min_max_invalid": "Maximum temperature must be greater than the minimum."
```

- [ ] **Step 5: Lint and compile-check**

Run:

```bash
ruff check custom_components/mycoolman
ruff format --check custom_components/mycoolman
python -m compileall custom_components/mycoolman
python -c "import json; json.load(open('custom_components/mycoolman/strings.json')); json.load(open('custom_components/mycoolman/translations/en.json'))"
```

Expected: no errors from any command (the last one fails loudly with a `json.decoder.JSONDecodeError` if either JSON file is malformed).

- [ ] **Step 6: Commit**

```bash
git add custom_components/mycoolman/config_flow.py custom_components/mycoolman/strings.json custom_components/mycoolman/translations/en.json
git commit -m "Ask for the setpoint range during config flow setup"
```

---

### Task 3: Options flow — edit the range after setup

**Files:**
- Modify: `custom_components/mycoolman/config_flow.py`
- Modify: `custom_components/mycoolman/strings.json`
- Modify: `custom_components/mycoolman/translations/en.json`

- [ ] **Step 1: Import `OptionsFlow` and `ConfigEntry`**

In `custom_components/mycoolman/config_flow.py`, change:

```python
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
```

to:

```python
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
```

- [ ] **Step 2: Add `async_get_options_flow` to `MyCoolmanConfigFlow`**

Add this static method to `MyCoolmanConfigFlow`, right after the `VERSION = 1` line:

```python
    @staticmethod
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> MyCoolmanOptionsFlow:
        return MyCoolmanOptionsFlow()
```

- [ ] **Step 3: Add the `MyCoolmanOptionsFlow` class**

Append this class at the end of `custom_components/mycoolman/config_flow.py`:

```python
class MyCoolmanOptionsFlow(OptionsFlow):
    """Let the user adjust the setpoint range after setup."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            min_temp = user_input[CONF_MIN_TEMP]
            max_temp = user_input[CONF_MAX_TEMP]
            if min_temp >= max_temp:
                errors["base"] = "min_max_invalid"
            else:
                return self.async_create_entry(data=user_input)

        current_min = self.config_entry.options.get(CONF_MIN_TEMP, DEFAULT_MIN_TEMP)
        current_max = self.config_entry.options.get(CONF_MAX_TEMP, DEFAULT_MAX_TEMP)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_MIN_TEMP, default=current_min): vol.Coerce(int),
                    vol.Required(CONF_MAX_TEMP, default=current_max): vol.Coerce(int),
                }
            ),
            errors=errors,
        )
```

- [ ] **Step 4: Add the options-flow strings to `strings.json`**

Add a top-level `"options"` key in `custom_components/mycoolman/strings.json`, as a sibling of `"config"` and `"entity"`:

```json
  "options": {
    "step": {
      "init": {
        "title": "Setpoint range",
        "description": "Set the minimum and maximum temperature your fridge supports.",
        "data": {
          "min_temp": "Minimum temperature (°C)",
          "max_temp": "Maximum temperature (°C)"
        }
      }
    },
    "error": {
      "min_max_invalid": "Maximum temperature must be greater than the minimum."
    }
  },
```

- [ ] **Step 5: Apply the identical change to `translations/en.json`**

Add the same top-level `"options"` key to
`custom_components/mycoolman/translations/en.json`, as a sibling of
`"config"` and `"entity"`:

```json
  "options": {
    "step": {
      "init": {
        "title": "Setpoint range",
        "description": "Set the minimum and maximum temperature your fridge supports.",
        "data": {
          "min_temp": "Minimum temperature (°C)",
          "max_temp": "Maximum temperature (°C)"
        }
      }
    },
    "error": {
      "min_max_invalid": "Maximum temperature must be greater than the minimum."
    }
  },
```

- [ ] **Step 6: Lint and compile-check**

Run:

```bash
ruff check custom_components/mycoolman
ruff format --check custom_components/mycoolman
python -m compileall custom_components/mycoolman
python -c "import json; json.load(open('custom_components/mycoolman/strings.json')); json.load(open('custom_components/mycoolman/translations/en.json'))"
```

Expected: no errors from any command.

- [ ] **Step 7: Commit**

```bash
git add custom_components/mycoolman/config_flow.py custom_components/mycoolman/strings.json custom_components/mycoolman/translations/en.json
git commit -m "Add an options flow to edit the setpoint range after setup"
```

---

### Task 4: Reload the entry automatically when options change

**Files:**
- Modify: `custom_components/mycoolman/__init__.py`

- [ ] **Step 1: Register an update listener in `async_setup_entry`**

Change:

```python
async def async_setup_entry(hass: HomeAssistant, entry: MyCoolmanConfigEntry) -> bool:
    """Set up myCOOLMAN from a config entry."""
    coordinator = MyCoolmanCoordinator(
        hass, entry, entry.data[CONF_ADDRESS], entry.data[CONF_PIN]
    )
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _async_register_services(hass)
    return True
```

to:

```python
async def async_setup_entry(hass: HomeAssistant, entry: MyCoolmanConfigEntry) -> bool:
    """Set up myCOOLMAN from a config entry."""
    coordinator = MyCoolmanCoordinator(
        hass, entry, entry.data[CONF_ADDRESS], entry.data[CONF_PIN]
    )
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    _async_register_services(hass)
    return True


async def _async_update_listener(
    hass: HomeAssistant, entry: MyCoolmanConfigEntry
) -> None:
    """Reload the entry when its options change (e.g. setpoint range edited)."""
    await hass.config_entries.async_reload(entry.entry_id)
```

- [ ] **Step 2: Lint and compile-check**

Run:

```bash
ruff check custom_components/mycoolman
ruff format --check custom_components/mycoolman
python -m compileall custom_components/mycoolman
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add custom_components/mycoolman/__init__.py
git commit -m "Reload the config entry automatically when options change"
```

---

### Task 5: Update documentation

**Files:**
- Modify: `README.md`
- Modify: `HANDOFF.md`

- [ ] **Step 1: Update `README.md`'s install steps and range note**

Change (around line 43):

```markdown
5. Enter the 3-digit PIN when prompted.
```

to:

```markdown
5. Enter the 3-digit PIN when prompted, then set the fridge's setpoint range
   (defaults to −20…20 °C, confirmed for the single-zone 43 — adjust if your
   model differs).
```

Change (around lines 56-57):

```markdown
- Setpoint range defaults to −20…20 °C; adjust `MIN_TEMP`/`MAX_TEMP` in
  `const.py` for your model.
```

to:

```markdown
- Setpoint range defaults to −20…20 °C (confirmed for the single-zone 43). Set
  it during setup, or change it later via **Settings → Devices & Services →
  myCOOLMAN → Configure**.
```

- [ ] **Step 2: Update `HANDOFF.md`'s roadmap item and entities section**

Change item 5 under §8 "Polish" from:

```markdown
5. ~~Confirm the real setpoint range for the 43~~ — confirmed −20…20°C, matches
   `MIN_TEMP`/`MAX_TEMP` in `const.py` already.
```

to:

```markdown
5. ~~Confirm the real setpoint range for the 43~~ — confirmed −20…20°C. Now
   user-configurable per entry via the config flow (setup) and options flow
   (Configure button); `DEFAULT_MIN_TEMP`/`DEFAULT_MAX_TEMP` in `const.py` are
   just the fallback for entries with no override.
```

Also update §4 "Entities & service currently implemented" — add a line after the `select` bullet noting the options flow:

```markdown
- **options flow** — adjust the fridge's setpoint range (min/max °C) after
  setup, via **Configure** on the integration's device card.
```

- [ ] **Step 3: Commit**

```bash
git add README.md HANDOFF.md
git commit -m "Document the configurable setpoint range"
```

---

### Task 6: Manual end-to-end verification

**Files:** none (verification only)

**Result: user confirmed the setpoint range functionality works on real hardware.**

- [x] **Step 1: Deploy to a real Home Assistant instance**

Follow `HANDOFF.md` §6: copy `custom_components/mycoolman/` to
`/config/custom_components/mycoolman/` on the test HA instance, then fully
restart Home Assistant (custom-component code changes require a restart, not
just a reload).

- [x] **Step 2: Verify the new config-flow step**

Remove any existing myCOOLMAN config entry for the test fridge, then re-add it
via **Settings → Devices & Services → + Add Integration → myCOOLMAN** (or let
Bluetooth discovery prompt it). Confirm:
- After entering the PIN, a "Setpoint range" form appears, prefilled with
  `-20` / `20`.
- Submitting `min_temp = 25`, `max_temp = 10` shows the "Maximum temperature
  must be greater than the minimum" error and does not proceed.
- Submitting `min_temp = -20`, `max_temp = 20` creates the entry successfully.

- [x] **Step 3: Verify the options flow applies immediately**

On the newly created entry, go to **Settings → Devices & Services →
myCOOLMAN → Configure**. Confirm:
- The form is prefilled with the range chosen in Step 2.
- Changing `max_temp` to a different value (e.g. `15`) and submitting updates
  the climate card's target-temperature slider and the (disabled-by-default,
  re-enable it to check) setpoint number entity's max bound immediately,
  with no manual reload or HA restart.

- [x] **Step 4: Verify backward compatibility with pre-existing entries**

If a config entry from before this feature exists (no `min_temp`/`max_temp` in
its options), confirm its climate card still shows a `-20`…`20` range until
edited via Configure.

- [ ] **Step 5: Final commit if any fixups were needed**

If manual verification surfaced any bugs, fix them, re-run the lint/compile
commands from the relevant task, and commit:

```bash
git add -A
git commit -m "Fix issues found during manual verification"
```

(Skip this step if no fixes were needed.)
