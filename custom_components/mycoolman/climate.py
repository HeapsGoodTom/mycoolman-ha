"""Climate platform for myCOOLMAN.

Presents the fridge as a thermostat: current temperature, a target-temperature
dial, and power mapped to the HVAC mode (off / cool). Turbo and battery
protection remain as their own entities.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
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
    async_add_entities([MyCoolmanClimate(entry.runtime_data)])


class MyCoolmanClimate(MyCoolmanEntity, ClimateEntity):
    """Thermostat-style control for the fridge."""

    _attr_name = None  # becomes the device's primary entity
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.COOL]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_target_temperature_step = 1
    _attr_min_temp = MIN_TEMP
    _attr_max_temp = MAX_TEMP

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "climate")

    @property
    def current_temperature(self) -> float | None:
        return (self.coordinator.data or {}).get("temperature")

    @property
    def target_temperature(self) -> float | None:
        return (self.coordinator.data or {}).get("setpoint")

    @property
    def hvac_mode(self) -> HVACMode:
        if (self.coordinator.data or {}).get("power"):
            return HVACMode.COOL
        return HVACMode.OFF

    @property
    def hvac_action(self) -> HVACAction:
        if (self.coordinator.data or {}).get("power"):
            return HVACAction.COOLING
        return HVACAction.OFF

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is not None:
            await self.coordinator.async_set_temperature(int(temp))

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        await self.coordinator.async_set_power(hvac_mode == HVACMode.COOL)

    async def async_turn_on(self) -> None:
        await self.coordinator.async_set_power(True)

    async def async_turn_off(self) -> None:
        await self.coordinator.async_set_power(False)
