"""The myCOOLMAN integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_ADDRESS, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv

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

SERVICE_SEND_COMMAND = "send_command"
_BYTE = vol.All(vol.Coerce(int), vol.Range(min=0, max=255))
SEND_COMMAND_SCHEMA = vol.Schema(
    {
        vol.Required("command"): _BYTE,
        vol.Required("argument"): _BYTE,
        vol.Optional("address"): cv.string,
    }
)


async def async_setup_entry(hass: HomeAssistant, entry: MyCoolmanConfigEntry) -> bool:
    """Set up myCOOLMAN from a config entry."""
    coordinator = MyCoolmanCoordinator(
        hass, entry, entry.data[CONF_ADDRESS], entry.data[CONF_PIN]
    )
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    _async_register_services(hass)
    return True


def _async_register_services(hass: HomeAssistant) -> None:
    """Register the diagnostic send_command service (once)."""
    if hass.services.has_service(DOMAIN, SERVICE_SEND_COMMAND):
        return

    async def _handle_send_command(call: ServiceCall) -> None:
        address = call.data.get("address")
        loaded = [
            entry
            for entry in hass.config_entries.async_entries(DOMAIN)
            if entry.state is ConfigEntryState.LOADED
        ]
        if address:
            loaded = [
                entry
                for entry in loaded
                if entry.data[CONF_ADDRESS].upper() == address.upper()
            ]
        if not loaded:
            raise ServiceValidationError("No matching myCOOLMAN device is loaded")
        if len(loaded) > 1:
            raise ServiceValidationError(
                "Multiple fridges configured; pass 'address' to choose one"
            )
        coordinator: MyCoolmanCoordinator = loaded[0].runtime_data
        await coordinator.async_send(call.data["command"], call.data["argument"])

    hass.services.async_register(
        DOMAIN, SERVICE_SEND_COMMAND, _handle_send_command, schema=SEND_COMMAND_SCHEMA
    )


async def async_unload_entry(hass: HomeAssistant, entry: MyCoolmanConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.async_shutdown()
    return unload_ok
