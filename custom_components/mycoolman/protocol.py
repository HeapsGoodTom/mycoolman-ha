"""myCOOLMAN BLE protocol.

Reverse-engineered from the myCOOLMAN Recreation Android app
(github.com/luoxs/Mycoolman). Single FEE0/FEE1 characteristic is used for
both status notifications and command writes. No encryption; every command
carries a 3-hex-digit PIN split across two bytes, plus a Modbus CRC16.
"""

from __future__ import annotations

# BLE GATT identifiers
SERVICE_UUID = "0000fee0-0000-1000-8000-00805f9b34fb"
CHAR_UUID = "0000fee1-0000-1000-8000-00805f9b34fb"

# Command opcodes (byte 1 of the frame)
CMD_STATUS = 0x01  # request/refresh status (also validates the PIN)
CMD_POWER = 0x02  # arg 0x01 on / 0x00 off
CMD_SET_TEMP = 0x03  # arg = target temperature as signed int8
CMD_TURBO = 0x05  # arg 0x01 on / 0x00 off
CMD_BATTERY = 0x07  # arg 0x00 low / 0x01 medium / 0x02 high
CMD_UNIT = 0x08  # arg 0x00 Celsius / 0x01 Fahrenheit (fridge display only)
CMD_SHOW_PIN = 0x09  # arg 0x00 - show the pairing code on the fridge display
CMD_LED = 0x0C  # arg 0x00 High White / 0x01 Low White / 0x02 Orange
CMD_BUZZER = 0x0D  # arg 0x00 on / 0x01 off
CMD_AUTO_DIM = 0x0E  # arg 0x00 on / 0x01 off

BATTERY_LEVELS = ["Low", "Medium", "High"]
_BATTERY_BY_INDEX = {0: "Low", 1: "Medium", 2: "High"}


def pin_to_bytes(pin: str) -> tuple[int, int]:
    """Split a 3-hex-digit PIN into the two payload bytes (P3, P4)."""
    pin = pin.strip()
    if len(pin) != 3 or any(c not in "0123456789abcdefABCDEF" for c in pin):
        raise ValueError("PIN must be exactly 3 hex digits, e.g. 822")
    p_hi = int(pin[0], 16)
    p_lo = (int(pin[1], 16) << 4) | int(pin[2], 16)
    return p_hi, p_lo


def crc16(data: bytes) -> int:
    """Modbus CRC16 (poly 0xA001, init 0xFFFF)."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


def build_command(cmd: int, arg: int, pin: str) -> bytes:
    """Build an 8-byte command frame: AA CMD ARG P3 P4 CRChi CRClo 55."""
    p_hi, p_lo = pin_to_bytes(pin)
    body = bytes([cmd, arg & 0xFF, p_hi, p_lo])
    crc = crc16(body)
    return bytes([0xAA, *body, (crc >> 8) & 0xFF, crc & 0xFF, 0x55])


def _s8(value: int) -> int:
    """Interpret a byte as a signed 8-bit integer (temperatures in degC)."""
    return value - 256 if value > 128 else value


def parse_status(data: bytes) -> dict | None:
    """Parse a 22-byte status notification into a state dict, or None."""
    if len(data) != 22 or data[0] == 0x00:
        return None
    return {
        "power": data[1] != 0,
        "setpoint": _s8(data[2]),
        "temperature": _s8(data[3]),
        "turbo": data[6] != 0,
        "battery_protection": _BATTERY_BY_INDEX.get(data[8], "Low"),
        "unit_celsius": data[9] == 0x01,
        "status": data[10],
        "error": data[11],
        # Voltage scaling is a best guess (tenths of a volt) - verify against
        # the fridge's own display and adjust VOLTAGE_DIVISOR if needed.
        "voltage": ((data[12] << 8) | data[13]) / 10.0,
        "paired": data[14] != 0,  # 'gc' byte: 0 == wrong PIN
        "code1": data[17],
        "code2": data[18],
    }
