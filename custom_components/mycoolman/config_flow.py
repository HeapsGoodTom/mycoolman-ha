"""Config flow for myCOOLMAN."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_ADDRESS

from .const import CONF_PIN, DOMAIN
from .protocol import SERVICE_UUID, pin_to_bytes


class MyCoolmanConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for myCOOLMAN."""

    VERSION = 1

    def __init__(self) -> None:
        self._discovered_address: str | None = None
        self._discovered_name: str | None = None
        # address -> label, for the manual picker
        self._discovered: dict[str, str] = {}

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle a device discovered via the Bluetooth stack."""
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()
        self._discovered_address = discovery_info.address
        self._discovered_name = discovery_info.name or "myCOOLMAN"
        self.context["title_placeholders"] = {"name": self._discovered_name}
        return await self.async_step_pin()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manual setup: pick a discovered device."""
        if user_input is not None:
            self._discovered_address = user_input[CONF_ADDRESS]
            await self.async_set_unique_id(
                self._discovered_address, raise_on_progress=False
            )
            self._abort_if_unique_id_configured()
            return await self.async_step_pin()

        current = self._async_current_ids()
        for info in async_discovered_service_info(self.hass, connectable=True):
            if info.address in current:
                continue
            if SERVICE_UUID in info.service_uuids or (
                info.name and "coolman" in info.name.lower()
            ):
                self._discovered[info.address] = f"{info.name} ({info.address})"

        if not self._discovered:
            return self.async_abort(reason="no_devices_found")

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_ADDRESS): vol.In(self._discovered)}
            ),
        )

    async def async_step_pin(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect the 3-digit PIN and finish."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                pin_to_bytes(user_input[CONF_PIN])
            except ValueError:
                errors["base"] = "invalid_pin"
            else:
                return self.async_create_entry(
                    title=self._discovered_name or "myCOOLMAN Fridge",
                    data={
                        CONF_ADDRESS: self._discovered_address,
                        CONF_PIN: user_input[CONF_PIN].strip(),
                    },
                )

        return self.async_show_form(
            step_id="pin",
            data_schema=vol.Schema({vol.Required(CONF_PIN): str}),
            errors=errors,
            description_placeholders={"address": self._discovered_address or ""},
        )
