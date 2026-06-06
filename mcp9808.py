# mcp9808.py
# MicroPython driver for the Microchip MCP9808 digital temperature sensor.
# Interface: I2C (up to 400 kHz), address 0x18–0x1F (A2:A1:A0 pins).
#
# Register map (MCP9808 datasheet DS20005095B):
#   0x00  CONFIG          – configuration register (16-bit)
#   0x01  TUPPER          – alert upper boundary (16-bit)
#   0x02  TLOWER          – alert lower boundary (16-bit)
#   0x03  TCRIT           – critical temperature (16-bit)
#   0x05  TA              – ambient temperature (16-bit, read-only)
#   0x06  MANUFACTURER_ID – should read 0x0054
#   0x07  DEVICE_ID       – should read 0x0400 (device=0x04, revision=0x00)
#   0x08  RESOLUTION      – resolution register (8-bit)
#
# Temperature register (0x05) format (16-bit big-endian):
#   Bit 15:13  – alert flags (TCRIT, TUPPER, TLOWER)
#   Bit 12     – sign bit (1 = negative)
#   Bits 11:4  – integer part (°C)
#   Bits  3:0  – fractional part (1/16 °C per LSB)
#
# Resolution register (0x08):
#   0x00 → +0.5°C    (30 ms conversion)
#   0x01 → +0.25°C   (65 ms conversion)
#   0x02 → +0.125°C  (130 ms conversion)
#   0x03 → +0.0625°C (250 ms conversion, default)

# Register addresses
_REG_CONFIG       = 0x01
_REG_TA           = 0x05
_REG_MANUFACTURER = 0x06
_REG_DEVICE_ID    = 0x07
_REG_RESOLUTION   = 0x08

# Resolution constants (pass to set_resolution())
RES_0_5    = 0x00   # ±0.5°C,    ~30 ms
RES_0_25   = 0x01   # ±0.25°C,   ~65 ms
RES_0_125  = 0x02   # ±0.125°C,  ~130 ms
RES_0_0625 = 0x03   # ±0.0625°C, ~250 ms (power-on default)

# Expected identity values
_MANUFACTURER_ID = 0x0054
_DEVICE_ID_MASK  = 0xFF00   # upper byte is device ID (0x04); lower is revision
_DEVICE_ID_VAL   = 0x0400


class MCP9808:
    """
    MCP9808 temperature sensor driver.

    Usage::

        from machine import I2C, Pin
        from mcp9808 import MCP9808

        i2c   = I2C(1, scl=Pin('PB8'), sda=Pin('PB9'), freq=400_000)
        sensor = MCP9808(i2c)
        temp   = sensor.temperature()   # float, °C
    """

    def __init__(self, i2c, addr=0x18):
        """
        Parameters
        ----------
        i2c  : machine.I2C instance (already initialised)
        addr : 7-bit I2C address; 0x18 when A2:A1:A0 = 0:0:0 (default)
        """
        self._i2c  = i2c
        self._addr = addr
        self._buf2 = bytearray(2)   # reusable 2-byte read buffer

        # Verify manufacturer and device IDs before use
        mfr = self._read16(_REG_MANUFACTURER)
        if mfr != _MANUFACTURER_ID:
            raise RuntimeError(
                "MCP9808: unexpected manufacturer ID 0x{:04X}".format(mfr))

        dev = self._read16(_REG_DEVICE_ID)
        if (dev & _DEVICE_ID_MASK) != _DEVICE_ID_VAL:
            raise RuntimeError(
                "MCP9808: unexpected device ID 0x{:04X}".format(dev))

        # Ensure the sensor is not in shutdown mode (CONFIG bit 8 = SHDN).
        # Read-modify-write to preserve any other config bits.
        cfg = self._read16(_REG_CONFIG)
        if cfg & 0x0100:                    # SHDN bit set → wake up
            self._write16(_REG_CONFIG, cfg & ~0x0100)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def temperature(self):
        """
        Read and return the ambient temperature in degrees Celsius (float).

        The conversion uses only integer arithmetic until the final division
        so it is efficient on resource-constrained targets.

        Returns
        -------
        float
            Temperature in °C.  Resolution depends on the resolution register
            setting (default ±0.0625°C).
        """
        self._i2c.readfrom_mem_into(self._addr, _REG_TA, self._buf2)
        msb = self._buf2[0]
        lsb = self._buf2[1]

        # Strip the three alert flag bits (bits 15:13 of the 16-bit register)
        msb &= 0x1F

        # Reconstruct the 12-bit two's-complement value.
        # Bit 12 of the original register (now bit 4 of msb after masking)
        # is the sign bit.
        if msb & 0x10:          # negative temperature
            # Two's complement: invert the 13-bit field and add 1
            raw = ((msb & 0x0F) << 8) | lsb
            temp = raw / 16.0 - 256.0
        else:                   # positive temperature
            temp = ((msb << 8) | lsb) / 16.0

        return temp

    def set_resolution(self, resolution=RES_0_0625):
        """
        Set the ADC resolution (and therefore conversion time).

        Parameters
        ----------
        resolution : int
            One of RES_0_5, RES_0_25, RES_0_125, RES_0_0625.
        """
        self._i2c.writeto_mem(self._addr, _REG_RESOLUTION, bytes([resolution & 0x03]))

    def shutdown(self):
        """Put the sensor into low-power shutdown mode (~0.1 µA)."""
        cfg = self._read16(_REG_CONFIG)
        self._write16(_REG_CONFIG, cfg | 0x0100)

    def wake(self):
        """Wake the sensor from shutdown mode."""
        cfg = self._read16(_REG_CONFIG)
        self._write16(_REG_CONFIG, cfg & ~0x0100)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _read16(self, reg):
        """Read a 16-bit big-endian register and return as an int."""
        self._i2c.readfrom_mem_into(self._addr, reg, self._buf2)
        return (self._buf2[0] << 8) | self._buf2[1]

    def _write16(self, reg, value):
        """Write a 16-bit big-endian value to a register."""
        self._i2c.writeto_mem(self._addr, reg,
                              bytes([(value >> 8) & 0xFF, value & 0xFF]))
