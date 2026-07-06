"""The myCOOLMAN integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ADDRESS, Platform
from homeassistant.core import HomeAssistant

from .const import CONF_PIN, DOMAIN
from .coordinator import MyCoolmanCoordinator

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]

type MyCoolmanConfigEntry = ConfigEntry[MyCoolmanCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: MyCoolmanConfigEntry) -> bool:
    """Set up myCOOLMAN from a config entry."""
    coordinator = MyCoolmanCoordinator(
        hass, entry, entry.data[CONF_ADDRESS], entry.data[CONF_PIN]
    )
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MyCoolmanConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.async_shutdown()
    return unload_ok
