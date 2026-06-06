"""
HT16K33 display driver.

Supports the 4-digit 7-segment backpack API used by main.py and also keeps
the lighter matrix-style helpers added in the local framework.
"""

from config import HT16K33_ADDR

_CMD_OSC_ON = 0x21
_CMD_DISP_ON = 0x81
_CMD_DIM_BASE = 0xE0
_COLON_OFFSET = 4
_DIGIT_OFFSET = (0, 2, 6, 8)

_FONT = {
    "0": 0x3F, "1": 0x06, "2": 0x5B, "3": 0x4F,
    "4": 0x66, "5": 0x6D, "6": 0x7D, "7": 0x07,
    "8": 0x7F, "9": 0x6F,
    "A": 0x77, "b": 0x7C, "C": 0x39, "d": 0x5E,
    "E": 0x79, "F": 0x71, "G": 0x3D, "H": 0x76,
    "h": 0x74, "I": 0x06, "J": 0x1E, "L": 0x38,
    "n": 0x54, "o": 0x5C, "P": 0x73, "r": 0x50,
    "S": 0x6D, "t": 0x78, "U": 0x3E, "u": 0x1C,
    "y": 0x6E, "-": 0x40, "_": 0x08, " ": 0x00,
}

_DIGIT_GLYPHS_3X5 = {
    "0": [0x7, 0x5, 0x5, 0x5, 0x7],
    "1": [0x2, 0x6, 0x2, 0x2, 0x7],
    "2": [0x7, 0x1, 0x7, 0x4, 0x7],
    "3": [0x7, 0x1, 0x7, 0x1, 0x7],
    "4": [0x5, 0x5, 0x7, 0x1, 0x1],
    "5": [0x7, 0x4, 0x7, 0x1, 0x7],
    "6": [0x7, 0x4, 0x7, 0x5, 0x7],
    "7": [0x7, 0x1, 0x2, 0x2, 0x2],
    "8": [0x7, 0x5, 0x7, 0x5, 0x7],
    "9": [0x7, 0x5, 0x7, 0x1, 0x7],
    "-": [0x0, 0x0, 0x7, 0x0, 0x0],
}


class HT16K33:
    def __init__(self, i2c, addr=HT16K33_ADDR, brightness=15):
        self._i2c = i2c
        self._addr = addr
        self._buf = bytearray(17)
        self._buf[0] = 0x00
        self._cmd(_CMD_OSC_ON)
        self._cmd(_CMD_DISP_ON)
        self.set_brightness(brightness)
        self.clear()
        self.show()

    def set_brightness(self, level):
        level = max(0, min(15, int(level)))
        self._cmd(_CMD_DIM_BASE | level)

    def clear(self):
        for i in range(1, 17):
            self._buf[i] = 0x00

    def show(self):
        self._i2c.writeto(self._addr, self._buf)

    def set_pixel(self, x, y, on=True):
        if not (0 <= x < 8 and 0 <= y < 8):
            return
        index = 1 + y * 2
        mask = 1 << x
        if on:
            self._buf[index] |= mask
        else:
            self._buf[index] &= ~mask & 0xFF

    def set_digit(self, pos, segments, dot=False):
        if not 0 <= pos <= 3:
            raise ValueError("pos must be 0-3")
        value = segments & 0x7F
        if dot:
            value |= 0x80
        self._buf[1 + _DIGIT_OFFSET[pos]] = value

    def set_colon(self, on=True):
        self._buf[1 + _COLON_OFFSET] = 0x02 if on else 0x00

    def print_str(self, text, colon=False):
        self.clear()
        pos = 0
        i = 0
        while pos < 4 and i < len(text):
            ch = text[i]
            i += 1
            if ch == ".":
                if pos > 0:
                    prev_offset = 1 + _DIGIT_OFFSET[pos - 1]
                    self._buf[prev_offset] |= 0x80
                continue
            self.set_digit(pos, _FONT.get(ch, 0x00))
            pos += 1
        self.set_colon(colon)

    def print_int(self, value, pad=True):
        if value < -999 or value > 9999:
            self.print_str("----")
            return
        if pad:
            self.print_str("{:>4d}".format(int(value)))
        else:
            self.print_str("{:04d}".format(int(value)))

    def print_float(self, value, decimal_places=1):
        formatted = "{:.{}f}".format(value, decimal_places)
        if sum(1 for ch in formatted if ch != ".") > 4:
            self.print_str("----")
            return
        self.print_str(formatted)

    def display_number(self, number):
        self.clear()
        text = str(int(number))
        if len(text) == 1:
            self._draw_digit_glyph(text, 2, 1)
        else:
            self._draw_digit_glyph(text[-2], 0, 1)
            self._draw_digit_glyph(text[-1], 4, 1)
        self.show()

    def _draw_digit_glyph(self, ch, x_off, y_off):
        glyph = _DIGIT_GLYPHS_3X5.get(ch, _DIGIT_GLYPHS_3X5["-"])
        for row in range(5):
            for col in range(3):
                if glyph[row] & (1 << (2 - col)):
                    self.set_pixel(x_off + col, y_off + row, True)

    def _cmd(self, byte):
        self._i2c.writeto(self._addr, bytes([byte]))
