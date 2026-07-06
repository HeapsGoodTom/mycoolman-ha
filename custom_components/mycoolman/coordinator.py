"""Connection + data coordinator for a myCOOLMAN fridge over BLE.

Holds a persistent active connection (routed through any in-range ESPHome
Bluetooth Proxy), subscribes to status notifications, and exposes async
command helpers. Reconnection is handled by re-establishing on demand and by
listening for the device becoming available again via the HA Bluetooth stack.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from bleak.exc import BleakError
from bleak_retry_connector import (
    BleakClientWithServiceCache,
    establish_connection,
)

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from . import protocol
from .const import DOMAIN, UPDATE_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)


class MyCoolmanCoordinator(DataUpdateCoordinator[dict]):
    """Manage one fridge connection and its state."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, address: str, pin: str
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{address}",
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )
        self._entry = entry
        self.address = address.upper()
        self._pin = pin
        self._client: BleakClientWithServiceCache | None = None
        self._lock = asyncio.Lock()
        self._notified = asyncio.Event()

    # -- connection management ------------------------------------------------

    async def _get_client(self) -> BleakClientWithServiceCache:
        """Return a connected client, establishing one if needed."""
        if self._client is not None and self._client.is_connected:
            return self._client

        ble_device = bluetooth.async_ble_device_from_address(
            self.hass, self.address, connectable=True
        )
        if ble_device is None:
            raise UpdateFailed(
                f"{self.address} not found by any Bluetooth adapter or proxy"
            )

        client = await establish_connection(
            BleakClientWithServiceCache,
            ble_device,
            self.address,
            disconnected_callback=self._on_disconnect,
        )
        await client.start_notify(protocol.CHAR_UUID, self._on_notify)
        self._client = client
        _LOGGER.debug("Connected to %s", self.address)
        return client

    @callback
    def _on_disconnect(self, _client: BleakClientWithServiceCache) -> None:
        _LOGGER.debug("Disconnected from %s", self.address)
        self._client = None

    @callback
    def _on_notify(self, _char, data: bytearray) -> None:
        parsed = protocol.parse_status(bytes(data))
        if parsed is None:
            return
        self._notified.set()
        self.async_set_updated_data(parsed)

    async def _async_update_data(self) -> dict:
        """Ensure connected and poke a status refresh (keepalive)."""
        try:
            await self.async_send(protocol.CMD_STATUS, 0x00)
        except (BleakError, TimeoutError) as err:
            raise UpdateFailed(f"Error polling {self.address}: {err}") from err
        return self.data or {}

    # -- commands -------------------------------------------------------------

    async def async_send(self, cmd: int, arg: int) -> None:
        """Write one command frame and wait briefly for the reply notify."""
        frame = protocol.build_command(cmd, arg, self._pin)
        async with self._lock:
            client = await self._get_client()
            self._notified.clear()
            await client.write_gatt_char(protocol.CHAR_UUID, frame, response=False)
        try:
            await asyncio.wait_for(self._notified.wait(), timeout=3)
        except TimeoutError:
            _LOGGER.debug("No status notify after command 0x%02x", cmd)

    async def async_set_power(self, on: bool) -> None:
        await self.async_send(protocol.CMD_POWER, 0x01 if on else 0x00)

    async def async_set_turbo(self, on: bool) -> None:
        await self.async_send(protocol.CMD_TURBO, 0x01 if on else 0x00)

    async def async_set_temperature(self, temp: int) -> None:
        await self.async_send(protocol.CMD_SET_TEMP, int(temp) & 0xFF)

    async def async_set_battery(self, level: str) -> None:
        idx = protocol.BATTERY_LEVELS.index(level)
        await self.async_send(protocol.CMD_BATTERY, idx)

    async def async_set_unit(self, celsius: bool) -> None:
        await self.async_send(protocol.CMD_UNIT, 0x00 if celsius else 0x01)

    async def async_show_pin(self) -> None:
        await self.async_send(protocol.CMD_SHOW_PIN, 0x00)

    async def async_shutdown(self) -> None:
        if self._client is not None and self._client.is_connected:
            try:
                await self._client.disconnect()
            except BleakError:
                pass
        self._client = None
