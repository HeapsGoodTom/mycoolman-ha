"""Unit tests for the pure-function BLE wire format in protocol.py.

No Home Assistant install or hardware required. `parse_status` test vectors
are real 22-byte frames captured from a physical MCMR43 during live probing
sessions, not synthesized - each was independently cross-checked against
the fridge's actual state (LED color, buzzer, auto-dim) at capture time.
"""

import protocol
import pytest


class TestCrc16:
    def test_standard_modbus_check_value(self):
        # The well-known CRC-16/MODBUS check value for ASCII "123456789"
        # (poly 0x8005 reflected == 0xA001, init 0xFFFF). Confirms this is a
        # standard, correctly-implemented Modbus CRC16, not just internally
        # self-consistent.
        assert protocol.crc16(b"123456789") == 0x4B37

    def test_empty_input_returns_init_value(self):
        assert protocol.crc16(b"") == 0xFFFF


class TestPinToBytes:
    def test_docstring_example(self):
        assert protocol.pin_to_bytes("ABC") == (0x0A, 0xBC)

    def test_numeric_pin(self):
        assert protocol.pin_to_bytes("822") == (0x08, 0x22)

    def test_strips_whitespace(self):
        assert protocol.pin_to_bytes(" 822 ") == (0x08, 0x22)

    @pytest.mark.parametrize(
        "bad_pin",
        ["82", "8220", "82g", "", "   "],
    )
    def test_rejects_invalid_pin(self, bad_pin):
        with pytest.raises(ValueError):
            protocol.pin_to_bytes(bad_pin)


class TestBuildCommand:
    def test_frame_structure(self):
        frame = protocol.build_command(protocol.CMD_POWER, 0x01, "822")
        assert frame == bytes.fromhex("aa0201082285d755")
        assert frame[0] == 0xAA
        assert frame[-1] == 0x55
        assert len(frame) == 8

    def test_crc_covers_only_cmd_arg_pin_bytes(self):
        frame = protocol.build_command(protocol.CMD_LED, 0x02, "822")
        body = frame[1:5]  # cmd, arg, P3, P4
        expected_crc = protocol.crc16(body)
        actual_crc = (frame[5] << 8) | frame[6]
        assert actual_crc == expected_crc

    def test_arg_is_masked_to_a_byte(self):
        frame = protocol.build_command(protocol.CMD_SET_TEMP, -18 & 0xFF, "822")
        assert frame[2] == 0xEE  # -18 as signed int8, per protocol.py's docstring


class TestParseStatus:
    def test_wrong_length_returns_none(self):
        assert protocol.parse_status(bytes(21)) is None
        assert protocol.parse_status(bytes(23)) is None

    def test_zero_start_byte_returns_none(self):
        assert protocol.parse_status(bytes(22)) is None

    def test_baseline_frame(self):
        # power on, setpoint 4C, temp 7C, battery Medium, 15.4V, LED High
        # White (code1=0), buzzer on, auto-dim on.
        data = bytes.fromhex("55010407ff00000001010100009a0300000000f89eaa")
        parsed = protocol.parse_status(data)
        assert parsed["power"] is True
        assert parsed["setpoint"] == 4
        assert parsed["temperature"] == 7
        assert parsed["turbo"] is False
        assert parsed["battery_protection"] == "Medium"
        assert parsed["unit_celsius"] is True
        assert parsed["voltage"] == pytest.approx(15.4)
        assert parsed["paired"] is True
        assert parsed["code1"] == 0
        assert parsed["led"] == "High White"
        assert parsed["buzzer_on"] is True
        assert parsed["auto_dim_on"] is True

    def test_negative_temperature(self):
        # temperature byte 0xfb == -5C (signed int8)
        data = bytearray.fromhex("55010407ff00000001010100009a0300000000f89eaa")
        data[3] = 0xFB
        assert protocol.parse_status(bytes(data))["temperature"] == -5


class TestCode1Bitmask:
    """code1 (byte 17) bitmask, confirmed by 10 live-hardware captures with
    zero exceptions: bits 0-1 = LED mode index, bit 2 = buzzer off,
    bit 3 = auto-dim off. Each frame below is a real captured status
    notification, cross-checked against the fridge's actual state at
    capture time.
    """

    @pytest.mark.parametrize(
        "raw_hex,expected_led,expected_buzzer_on,expected_auto_dim_on",
        [
            ("55010407ff00000001010100009a0300000000f89eaa", "High White", True, True),
            ("55010407ff00000001010100009a0300000100689faa", "Low White", True, True),
            ("55010407ff0000000101010000990300000200ab9faa", "Orange", True, True),
            ("55010407ff00000001010100009903000006006b9daa", "Orange", False, True),
            ("55010406ff0000000101010000990300000a00fb59aa", "Orange", True, False),
            ("55010407ff0000000101010000990300000e00ab9aaa", "Orange", False, False),
        ],
    )
    def test_confirmed_captures(
        self, raw_hex, expected_led, expected_buzzer_on, expected_auto_dim_on
    ):
        parsed = protocol.parse_status(bytes.fromhex(raw_hex))
        assert parsed["led"] == expected_led
        assert parsed["buzzer_on"] is expected_buzzer_on
        assert parsed["auto_dim_on"] is expected_auto_dim_on

    def test_unused_led_index_decodes_to_none(self):
        # code1 & 0x03 == 3 has never been observed from the fridge, but
        # _LED_BY_CODE1_INDEX has no default - confirm it degrades to None
        # rather than raising, since SelectEntity.current_option expects
        # str | None.
        data = bytearray.fromhex("55010407ff00000001010100009a0300000300f89eaa")
        parsed = protocol.parse_status(bytes(data))
        assert parsed["led"] is None
