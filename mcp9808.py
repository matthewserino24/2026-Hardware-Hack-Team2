"""
Low-level MCP9808 MicroPython driver.
"""

from config import MCP9808_ADDR

_REG_CONFIG = 0x01
_REG_AMBIENT_TEMP = 0x05
_REG_MANUFACTURER_ID = 0x06
_REG_DEVICE_ID = 0x07
_REG_RESOLUTION = 0x08

_EXPECTED_MANUFACTURER_ID = 0x0054
_EXPECTED_DEVICE_ID = 0x0400


class MCP9808:
    def __init__(self, i2c, addr=MCP9808_ADDR):
        self._i2c = i2c
        self._addr = addr

        if self.manufacturer_id() != _EXPECTED_MANUFACTURER_ID:
            raise RuntimeError("MCP9808 manufacturer ID mismatch")

        if (self.device_id() & 0xFFF0) != _EXPECTED_DEVICE_ID:
            raise RuntimeError("MCP9808 device ID mismatch")

    def manufacturer_id(self):
        return self._read_u16(_REG_MANUFACTURER_ID)

    def device_id(self):
        return self._read_u16(_REG_DEVICE_ID)

    def temperature(self):
        raw = self._read_u16(_REG_AMBIENT_TEMP)
        temp = (raw & 0x0FFF) / 16.0
        if raw & 0x1000:
            temp -= 256.0
        return temp

    def configure(self, value=0x0000):
        self._write_u16(_REG_CONFIG, value)

    def set_resolution(self, value=0x03):
        self._i2c.writeto_mem(self._addr, _REG_RESOLUTION, bytes([value & 0x03]))

    def _read_u16(self, reg):
        data = self._i2c.readfrom_mem(self._addr, reg, 2)
        return (data[0] << 8) | data[1]

    def _write_u16(self, reg, value):
        self._i2c.writeto_mem(
            self._addr,
            reg,
            bytes([(value >> 8) & 0xFF, value & 0xFF]),
        )
