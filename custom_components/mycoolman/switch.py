"""Switch platform for myCOOLMAN (power, turbo)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MyCoolmanConfigEntry
from .entity import MyCoolmanEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MyCoolmanConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        [
            MyCoolmanSwitch(coordinator, "power", "power"),
            MyCoolmanSwitch(coordinator, "turbo", "turbo"),
        ]
    )


class MyCoolmanSwitch(MyCoolmanEntity, SwitchEntity):
    def __init__(self, coordinator, key: str, translation_key: str) -> None:
        super().__init__(coordinator, key)
        self._key = key
        self._attr_translation_key = translation_key

    @property
    def is_on(self) -> bool:
        return bool((self.coordinator.data or {}).get(self._key))

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._set(False)

    async def _set(self, on: bool) -> None:
        if self._key == "power":
            await self.coordinator.async_set_power(on)
        else:
            await self.coordinator.async_set_turbo(on)
