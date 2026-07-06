"""Number platform for myCOOLMAN (temperature setpoint)."""

from __future__ import annotations

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MyCoolmanConfigEntry
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
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX
    # The climate entity now provides the primary setpoint control; keep this
    # for automations but hidden by default to avoid duplication.
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "setpoint_control")

    @property
    def native_min_value(self) -> float:
        return self.coordinator.min_temp

    @property
    def native_max_value(self) -> float:
        return self.coordinator.max_temp

    @property
    def native_value(self) -> float | None:
        return (self.coordinator.data or {}).get("setpoint")

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_temperature(int(value))
