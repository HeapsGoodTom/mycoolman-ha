"""Base entity for myCOOLMAN."""

from __future__ import annotations

from homeassistant.helpers.device_info import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MyCoolmanCoordinator


class MyCoolmanEntity(CoordinatorEntity[MyCoolmanCoordinator]):
    """Common base: shares the device registry entry and availability."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: MyCoolmanCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.address)},
            connections={("bluetooth", coordinator.address)},
            manufacturer="myCOOLMAN",
            name="myCOOLMAN Fridge",
        )

    @property
    def available(self) -> bool:
        return super().available and bool(self.coordinator.data)
