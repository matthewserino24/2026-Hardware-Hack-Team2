"""
Low-level MPU-6050 MicroPython driver.

This module exposes raw sensor access and simple register helpers.
Heading integration lives in imu.py.
"""

import struct

from config import IMU_GYRO_FS, MPU6050_ADDR

_REG_SMPLRT_DIV = 0x19
_REG_CONFIG = 0x1A
_REG_GYRO_CONFIG = 0x1B
_REG_ACCEL_CONFIG = 0x1C
_REG_ACCEL_XOUT_H = 0x3B
_REG_TEMP_OUT_H = 0x41
_REG_GYRO_XOUT_H = 0x43
_REG_GYRO_ZOUT_H = 0x47
_REG_PWR_MGMT_1 = 0x6B
_REG_WHO_AM_I = 0x75

_FS_SEL_MAP = {
    250: (0x00, 131.0),
    500: (0x08, 65.5),
    1000: (0x10, 32.8),
    2000: (0x18, 16.4),
}

_ACCEL_SCALE = 16384.0


class MPU6050:
    def __init__(self, i2c, addr=MPU6050_ADDR):
        self._i2c = i2c
        self._addr = addr
        self._gyro_cfg, self._gyro_scale = _FS_SEL_MAP.get(IMU_GYRO_FS, _FS_SEL_MAP[250])
        self._buf14 = bytearray(14)

        who = self.who_am_i()
        if who != 0x68:
            raise RuntimeError("MPU-6050 not found (WHO_AM_I=0x{:02X})".format(who))

        self._configure()

    def who_am_i(self):
        return self._read_u8(_REG_WHO_AM_I)

    def accel(self):
        self._read_all()
        return (
            self._s16(0) / _ACCEL_SCALE,
            self._s16(2) / _ACCEL_SCALE,
            self._s16(4) / _ACCEL_SCALE,
        )

    def temperature(self):
        raw = self._read_s16(_REG_TEMP_OUT_H)
        return raw / 340.0 + 36.53

    def gyro(self):
        self._read_all()
        return (
            self._s16(8) / self._gyro_scale,
            self._s16(10) / self._gyro_scale,
            self._s16(12) / self._gyro_scale,
        )

    def read_gyro_z_dps(self):
        return self._read_s16(_REG_GYRO_ZOUT_H) / self._gyro_scale

    def read_all(self):
        self._read_all()
        return (
            self._s16(0) / _ACCEL_SCALE,
            self._s16(2) / _ACCEL_SCALE,
            self._s16(4) / _ACCEL_SCALE,
            self._s16(6) / 340.0 + 36.53,
            self._s16(8) / self._gyro_scale,
            self._s16(10) / self._gyro_scale,
            self._s16(12) / self._gyro_scale,
        )

    def read_raw(self):
        ax, ay, az, temp_c, gx, gy, gz = self.read_all()
        return {
            "ax": ax,
            "ay": ay,
            "az": az,
            "temp_c": temp_c,
            "gx": gx,
            "gy": gy,
            "gz": gz,
        }

    def _configure(self):
        self._write_u8(_REG_PWR_MGMT_1, 0x03)
        self._write_u8(_REG_SMPLRT_DIV, 0x13)
        self._write_u8(_REG_CONFIG, 0x04)
        self._write_u8(_REG_GYRO_CONFIG, self._gyro_cfg)
        self._write_u8(_REG_ACCEL_CONFIG, 0x00)

    def _read_all(self):
        self._i2c.readfrom_mem_into(self._addr, _REG_ACCEL_XOUT_H, self._buf14)

    def _read_s16(self, reg):
        raw = self._i2c.readfrom_mem(self._addr, reg, 2)
        return struct.unpack(">h", raw)[0]

    def _read_u8(self, reg):
        return self._i2c.readfrom_mem(self._addr, reg, 1)[0]

    def _write_u8(self, reg, value):
        self._i2c.writeto_mem(self._addr, reg, bytes([value & 0xFF]))

    def _s16(self, offset):
        value = (self._buf14[offset] << 8) | self._buf14[offset + 1]
        return value if value < 32768 else value - 65536
