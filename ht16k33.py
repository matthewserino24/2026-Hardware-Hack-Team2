# ht16k33.py
# MicroPython driver for the Holtek HT16K33 LED matrix/segment controller.
# Interface: I2C (up to 400 kHz), address 0x70–0x77 (A2:A1:A0 pins).
#
# Command bytes (HT16K33 datasheet, Table 1):
#   0x20        – System oscillator OFF (standby)
#   0x21        – System oscillator ON
#   0x80        – Display OFF, no blink
#   0x81        – Display ON,  no blink
#   0x83        – Display ON,  blink 2 Hz
#   0x85        – Display ON,  blink 1 Hz
#   0x87        – Display ON,  blink 0.5 Hz
#   0xE0–0xEF   – Dimming: 0xE0 = 1/16 (min), 0xEF = 16/16 (max)
#
# Display RAM: 16 bytes (8 × 16-bit rows), written starting at address 0x00.
# For a 4-digit 7-segment display (e.g. Adafruit 0.56" backpack):
#   RAM[0]  → digit 0 (leftmost)
#   RAM[2]  → digit 1
#   RAM[4]  → colon / special (bit 1 of RAM[4] = colon on Adafruit backpack)
#   RAM[6]  → digit 2
#   RAM[8]  → digit 3 (rightmost)
#
# 7-segment bit mapping (Adafruit backpack wiring):
#   Bit 0 = segment A (top)
#   Bit 1 = segment B (top-right)
#   Bit 2 = segment C (bottom-right)
#   Bit 3 = segment D (bottom)
#   Bit 4 = segment E (bottom-left)
#   Bit 5 = segment F (top-left)
#   Bit 6 = segment G (middle)
#   Bit 7 = decimal point

# HT16K33 command bytes
_CMD_OSC_ON    = 0x21   # turn on system oscillator
_CMD_OSC_OFF   = 0x20   # standby (oscillator off)
_CMD_DISP_ON   = 0x81   # display on, no blink
_CMD_DISP_OFF  = 0x80   # display off
_CMD_BLINK_2HZ = 0x83
_CMD_BLINK_1HZ = 0x85
_CMD_BLINK_HALF= 0x87
_CMD_DIM_BASE  = 0xE0   # add 0–15 for 1/16 … 16/16 brightness

# 7-segment font: digits 0–9 and a small set of letters/symbols.
# Each entry is the bitmask for segments A–G (bit 0 = A … bit 6 = G).
_FONT = {
    '0': 0x3F, '1': 0x06, '2': 0x5B, '3': 0x4F,
    '4': 0x66, '5': 0x6D, '6': 0x7D, '7': 0x07,
    '8': 0x7F, '9': 0x6F,
    'A': 0x77, 'b': 0x7C, 'C': 0x39, 'd': 0x5E,
    'E': 0x79, 'F': 0x71, 'G': 0x3D, 'H': 0x76,
    'h': 0x74, 'I': 0x06, 'J': 0x1E, 'L': 0x38,
    'n': 0x54, 'o': 0x5C, 'P': 0x73, 'r': 0x50,
    'S': 0x6D, 't': 0x78, 'U': 0x3E, 'u': 0x1C,
    'y': 0x6E,
    '-': 0x40,   # minus / dash
    '_': 0x08,   # underscore
    ' ': 0x00,   # blank
}

# Adafruit 4-digit 7-segment backpack RAM byte offsets for each digit position.
# The display RAM is 16 bytes; each digit occupies 2 bytes (low byte used).
_DIGIT_OFFSET = (0, 2, 6, 8)   # positions 0–3 (position 4 = colon at offset 4)
_COLON_OFFSET = 4


class HT16K33:
    """
    Driver for the HT16K33 LED controller, targeting the Adafruit 4-digit
    7-segment backpack (product #878 / #879).

    Usage::

        from machine import I2C, Pin
        from ht16k33 import HT16K33

        i2c     = I2C(1, scl=Pin('PB8'), sda=Pin('PB9'), freq=400_000)
        display = HT16K33(i2c)
        display.print_str("1234")
        display.show()

        # Show a floating-point number with one decimal place:
        display.print_float(23.5)
        display.show()

        # Raw segment control:
        display.set_digit(0, 0x79)   # 'E' on digit 0
        display.show()
    """

    def __init__(self, i2c, addr=0x70, brightness=15):
        """
        Parameters
        ----------
        i2c        : machine.I2C instance (already initialised)
        addr       : 7-bit I2C address; 0x70 when A2:A1:A0 = 0:0:0 (default)
        brightness : 0–15 (0 = 1/16 duty, 15 = full brightness)
        """
        self._i2c   = i2c
        self._addr  = addr
        # 17-byte buffer: byte 0 = RAM start address (0x00), bytes 1–16 = RAM
        self._buf   = bytearray(17)
        self._buf[0] = 0x00   # RAM write address pointer

        # Power on oscillator
        self._cmd(_CMD_OSC_ON)
        # Display on, no blink
        self._cmd(_CMD_DISP_ON)
        # Set brightness
        self.set_brightness(brightness)
        # Clear all segments
        self.clear()
        self.show()

    # ------------------------------------------------------------------
    # Public API — display control
    # ------------------------------------------------------------------

    def set_brightness(self, level):
        """
        Set display brightness.

        Parameters
        ----------
        level : int, 0–15
            0 = minimum (1/16 duty cycle), 15 = maximum (16/16).
        """
        level = max(0, min(15, level))
        self._cmd(_CMD_DIM_BASE | level)

    def blink(self, rate=0):
        """
        Set blink rate.

        Parameters
        ----------
        rate : int
            0 = no blink, 1 = 2 Hz, 2 = 1 Hz, 3 = 0.5 Hz
        """
        cmds = (_CMD_DISP_ON, _CMD_BLINK_2HZ, _CMD_BLINK_1HZ, _CMD_BLINK_HALF)
        self._cmd(cmds[rate & 0x03])

    def clear(self):
        """Clear the shadow RAM buffer (does not update display until show())."""
        for i in range(1, 17):
            self._buf[i] = 0x00

    def show(self):
        """Push the shadow RAM buffer to the HT16K33 display RAM over I2C."""
        self._i2c.writeto(self._addr, self._buf)

    # ------------------------------------------------------------------
    # Public API — digit/segment control
    # ------------------------------------------------------------------

    def set_digit(self, pos, segments, dot=False):
        """
        Write raw segment bits to one digit position.

        Parameters
        ----------
        pos      : int, 0–3 (left to right)
        segments : int, 0x00–0x7F  (bits 0–6 = segments A–G)
        dot      : bool, True to light the decimal point (bit 7)
        """
        if not 0 <= pos <= 3:
            raise ValueError("pos must be 0–3")
        offset = _DIGIT_OFFSET[pos]
        val = segments & 0x7F
        if dot:
            val |= 0x80
        self._buf[1 + offset] = val

    def set_colon(self, on=True):
        """
        Enable or disable the centre colon (Adafruit backpack only).

        Parameters
        ----------
        on : bool
        """
        self._buf[1 + _COLON_OFFSET] = 0x02 if on else 0x00

    def print_str(self, text, colon=False):
        """
        Write up to 4 characters from *text* to the display buffer.

        Characters not in the font table are rendered as blanks.
        A '.' immediately following a digit character lights that digit's
        decimal point and does not consume a digit position.

        Parameters
        ----------
        text   : str  (up to 4 printable characters, optionally with '.')
        colon  : bool – set the colon segment
        """
        self.clear()
        pos = 0
        i   = 0
        while pos < 4 and i < len(text):
            ch = text[i]
            i += 1
            if ch == '.':
                # Decimal point belongs to the previous digit
                if pos > 0:
                    prev_offset = _DIGIT_OFFSET[pos - 1]
                    self._buf[1 + prev_offset] |= 0x80
                continue
            self.set_digit(pos, _FONT.get(ch, 0x00))
            pos += 1

        self.set_colon(colon)

    def print_int(self, value, pad=True):
        """
        Display a signed integer (−999 to 9999).

        Parameters
        ----------
        value : int
        pad   : bool – if True, left-pad with spaces; if False, left-pad with '0'
        """
        if value < -999 or value > 9999:
            self.print_str("----")
            return

        negative = value < 0
        value = abs(value)
        if negative:
            if not pad:
                digits = "-{:03d}".format(value)
            else:
                digits = list("{:>4d}".format(value))
                for k in range(4):
                    if digits[k] != ' ':
                        digits[k - 1] = '-'
                        break
                digits = ''.join(digits)
        else:
            digits = "{:04d}".format(value) if not pad else "{:>4d}".format(value)

        self.print_str(digits)

    def print_float(self, value, decimal_places=1):
        """
        Display a floating-point number with a decimal point.

        Supports values that fit in 4 significant digits (e.g. −9.9 to 999.9
        with decimal_places=1).  Out-of-range values show "----".

        The formatted string (e.g. "23.5") is passed directly to print_str,
        which handles the '.' character by setting the decimal-point bit on
        the preceding digit without consuming a digit position.

        Parameters
        ----------
        value          : float
        decimal_places : int, 1 or 2
        """
        fmt = "{:.{}f}".format(value, decimal_places)

        # Count significant digit characters (excluding '-' and '.') to check
        # whether the value fits on a 4-digit display.
        sig_digits = sum(1 for c in fmt if c.isdigit())
        if sig_digits > 4:
            self.print_str("----")
            return

        self.print_str(fmt)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _cmd(self, byte):
        """Send a single command byte to the HT16K33."""
        self._i2c.writeto(self._addr, bytes([byte]))
