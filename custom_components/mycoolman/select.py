"""Select platform for myCOOLMAN (battery protection level)."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MyCoolmanConfigEntry
from .entity import MyCoolmanEntity
from .protocol import BATTERY_LEVELS


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MyCoolmanConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        [
            MyCoolmanBatterySelect(coordinator),
            MyCoolmanUnitSelect(coordinator),
        ]
    )


class MyCoolmanBatterySelect(MyCoolmanEntity, SelectEntity):
    _attr_translation_key = "battery_protection"
    _attr_options = BATTERY_LEVELS

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "battery_protection")

    @property
    def current_option(self) -> str | None:
        return (self.coordinator.data or {}).get("battery_protection")

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_battery(option)


class MyCoolmanUnitSelect(MyCoolmanEntity, SelectEntity):
    """Fridge display unit (does not affect values reported to HA)."""

    _attr_translation_key = "display_unit"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = ["Celsius", "Fahrenheit"]

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "display_unit")

    @property
    def current_option(self) -> str | None:
        data = self.coordinator.data or {}
        if "unit_celsius" not in data:
            return None
        return "Celsius" if data["unit_celsius"] else "Fahrenheit"

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_unit(option == "Celsius")
