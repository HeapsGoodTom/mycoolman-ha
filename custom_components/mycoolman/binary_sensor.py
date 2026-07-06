"""Binary sensor platform for myCOOLMAN."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MyCoolmanConfigEntry
from .entity import MyCoolmanEntity


@dataclass(frozen=True, kw_only=True)
class MyCoolmanBinaryDescription(BinarySensorEntityDescription):
    value_fn: Callable[[dict], bool]


BINARY_SENSORS: tuple[MyCoolmanBinaryDescription, ...] = (
    MyCoolmanBinaryDescription(
        key="turbo",
        translation_key="turbo",
        value_fn=lambda d: bool(d.get("turbo")),
    ),
    MyCoolmanBinaryDescription(
        key="paired",
        translation_key="paired",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda d: bool(d.get("paired")),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MyCoolmanConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        MyCoolmanBinarySensor(coordinator, description)
        for description in BINARY_SENSORS
    )


class MyCoolmanBinarySensor(MyCoolmanEntity, BinarySensorEntity):
    entity_description: MyCoolmanBinaryDescription

    def __init__(self, coordinator, description: MyCoolmanBinaryDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool:
        return self.entity_description.value_fn(self.coordinator.data or {})
