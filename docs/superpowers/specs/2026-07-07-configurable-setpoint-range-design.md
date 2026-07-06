# Configurable setpoint range — design

## Problem

`MIN_TEMP`/`MAX_TEMP` in `const.py` are hardcoded to `-20`/`20`°C, confirmed
correct for the single-zone myCOOLMAN 43. Other models in the same product
line (37, DZ variants, etc.) are believed to speak the same protocol but may
support a different setpoint range. Users running those models need a way to
adjust the range without editing the source.

## Goals

- Let a user set the fridge's min/max setpoint range for their specific model.
- Offer it both at initial setup (so it's not an easily-missed feature) and
  later via the integration's Configure screen (so it can be corrected without
  removing and re-adding the device).
- Changes apply immediately — no manual reload or HA restart required.
- Existing config entries (created before this feature) keep working with the
  current `-20`/`20` default, no migration step required.

## Non-goals

- No validation beyond `min < max` — we don't know the real limits of other
  models, so no hardcoded outer bound is enforced.
- No per-zone (dual-zone freezer) range; out of scope until dual-zone support
  itself is built.

## Design

### Storage: `entry.options`, single source of truth

Both the initial config flow and the later options flow write to
`entry.options` under two new keys (defined in `const.py`):

```python
CONF_MIN_TEMP = "min_temp"
CONF_MAX_TEMP = "max_temp"
DEFAULT_MIN_TEMP = -20  # renamed from MIN_TEMP; also the fallback for entries
DEFAULT_MAX_TEMP = 20   # created before this feature existed
```

Rejected alternative: storing the range in `entry.data`. HA convention treats
`data` as set-once at entry creation; mixing a later-editable options-flow
write into it fights the framework and forfeits the automatic-reload-on-change
behavior `OptionsFlow` + an update listener gives us for free.

### `coordinator.py`

`MyCoolmanCoordinator` already holds `self._entry`. Add two read-only
properties that are the single place every entity reads the range from:

```python
@property
def min_temp(self) -> int:
    return self._entry.options.get(CONF_MIN_TEMP, DEFAULT_MIN_TEMP)

@property
def max_temp(self) -> int:
    return self._entry.options.get(CONF_MAX_TEMP, DEFAULT_MAX_TEMP)
```

### `config_flow.py`

- New step `async_step_range`, entered after `async_step_pin` completes.
  Shows a form with `min_temp`/`max_temp` prefilled with
  `DEFAULT_MIN_TEMP`/`DEFAULT_MAX_TEMP`. On submit, validates `min < max`
  (error key `min_max_invalid` on failure); on success calls:

  ```python
  self.async_create_entry(
      title=...,
      data={CONF_ADDRESS: ..., CONF_PIN: ...},
      options={CONF_MIN_TEMP: min_temp, CONF_MAX_TEMP: max_temp},
  )
  ```

- New `MyCoolmanOptionsFlow(OptionsFlow)` with `async_step_init`: the same
  form, prefilled from the *current* entry options (falling back to the
  defaults for entries that predate this feature), same `min < max`
  validation, `self.async_create_entry(data=user_input)` on success.

- `MyCoolmanConfigFlow.async_get_options_flow` static method returns
  `MyCoolmanOptionsFlow()`, wiring the Configure button to it.

### `__init__.py`

In `async_setup_entry`, register a reload-on-change listener so options-flow
edits apply immediately without a manual reload:

```python
entry.async_on_unload(entry.add_update_listener(_async_update_listener))

async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
```

### `climate.py` / `number.py`

Remove the class-level `_attr_min_temp`/`_attr_max_temp`
(`_attr_native_min_value`/`_attr_native_max_value` for `number.py`). Replace
with properties reading from the coordinator, so each entity always reflects
the live entry options:

```python
@property
def min_temp(self) -> float:
    return self.coordinator.min_temp

@property
def max_temp(self) -> float:
    return self.coordinator.max_temp
```

(`number.py` overrides `native_min_value`/`native_max_value` the same way.)

### `strings.json` / `translations/en.json`

- New `config.step.range` entry (title/description/data labels for
  `min_temp`/`max_temp`).
- New `config.error.min_max_invalid` string, shared with the options flow.
- New `options.step.init` entry mirroring the range form's labels.

## Documentation

`README.md:56` currently tells users to edit `MIN_TEMP`/`MAX_TEMP` in
`const.py` directly — update it to describe the Configure-screen setting
instead. `HANDOFF.md` §8 item 5 (setpoint range) should note the range is now
user-configurable rather than a fixed constant.

## Testing

- Manual: run through config flow on a real HA instance, confirm the range
  step appears, defaults are prefilled, `min >= max` shows the error.
- Manual: open Configure on an already-configured entry, change the range,
  confirm the climate card's temperature dial updates immediately without a
  manual reload.
- Manual: confirm an entry created before this feature shipped (no
  `min_temp`/`max_temp` in its options) still shows `-20`/`20` until edited.
- No hardware interaction needed for any of the above — this only touches
  config-flow/entity range plumbing, not the BLE protocol.
