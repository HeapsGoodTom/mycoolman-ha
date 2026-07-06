"""Number platform for myCOOLMAN (temperature setpoint)."""

from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MyCoolmanConfigEntry
from .const import MAX_TEMP, MIN_TEMP
from .entity import MyCoolmanEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MyCoolmanConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([MyCoolmanSetpoint(entry.runtime_data)])


class MyCoolmanSetpoint(MyCoolmanEntity, NumberEntity):
    _attr_translation_key = "setpoint"
    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_min_value = MIN_TEMP
    _attr_native_max_value = MAX_TEMP
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "setpoint_control")

    @property
    def native_value(self) -> float | None:
        return (self.coordinator.data or {}).get("setpoint")

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_temperature(int(value))
