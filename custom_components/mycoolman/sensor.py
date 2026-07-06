"""Sensor platform for myCOOLMAN."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import UnitOfElectricPotential, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import MyCoolmanConfigEntry
from .entity import MyCoolmanEntity


@dataclass(frozen=True, kw_only=True)
class MyCoolmanSensorDescription(SensorEntityDescription):
    """Describes a myCOOLMAN sensor."""

    value_fn: Callable[[dict], float | int | str | None]


SENSORS: tuple[MyCoolmanSensorDescription, ...] = (
    MyCoolmanSensorDescription(
        key="temperature",
        translation_key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("temperature"),
    ),
    MyCoolmanSensorDescription(
        key="setpoint",
        translation_key="setpoint",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        value_fn=lambda d: d.get("setpoint"),
    ),
    MyCoolmanSensorDescription(
        key="voltage",
        translation_key="voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("voltage"),
    ),
    MyCoolmanSensorDescription(
        key="error",
        translation_key="error",
        value_fn=lambda d: d.get("error"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MyCoolmanConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        MyCoolmanSensor(coordinator, description) for description in SENSORS
    )


class MyCoolmanSensor(MyCoolmanEntity, SensorEntity):
    """A myCOOLMAN sensor."""

    entity_description: MyCoolmanSensorDescription

    def __init__(self, coordinator, description: MyCoolmanSensorDescription) -> None:
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | int | str | None:
        return self.entity_description.value_fn(self.coordinator.data or {})
