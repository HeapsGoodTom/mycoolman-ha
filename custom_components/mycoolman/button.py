"""Button platform for myCOOLMAN."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MyCoolmanConfigEntry
from .entity import MyCoolmanEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MyCoolmanConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    async_add_entities([MyCoolmanShowPinButton(entry.runtime_data)])


class MyCoolmanShowPinButton(MyCoolmanEntity, ButtonEntity):
    """Ask the fridge to show its 3-digit pairing code on its own display."""

    _attr_translation_key = "show_pin"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "show_pin")

    async def async_press(self) -> None:
        await self.coordinator.async_show_pin()
