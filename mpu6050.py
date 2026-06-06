# mpu6050.py
# MicroPython driver for the InvenSense MPU-6050 6-axis IMU.
# Interface: I2C (400 kHz), address 0x68 (AD0=GND) or 0x69 (AD0=VCC).
#
# Register map (from MPU-6050 datasheet, Rev 3.4):
#   0x6B  PWR_MGMT_1   – wake from sleep, select clock source
#   0x1B  GYRO_CONFIG  – full-scale range
#   0x1C  ACCEL_CONFIG – full-scale range
#   0x3B  ACCEL_XOUT_H – first of 14 consecutive data bytes
#         ACCEL_XOUT_H/L, ACCEL_YOUT_H/L, ACCEL_ZOUT_H/L
#         TEMP_OUT_H/L
#         GYRO_XOUT_H/L, GYRO_YOUT_H/L, GYRO_ZOUT_H/L
#
# Sensitivity (default ±2 g / ±250 °/s):
#   Accel LSB/g  = 16384
#   Gyro  LSB/(°/s) = 131
#   Temp  °C = raw / 340.0 + 36.53

import struct

# Register addresses
_REG_PWR_MGMT_1  = 0x6B
_REG_GYRO_CONFIG = 0x1B
_REG_ACCEL_CONFIG= 0x1C
_REG_ACCEL_XOUT  = 0x3B   # first of 14 bytes (big-endian signed 16-bit pairs)
_REG_WHO_AM_I    = 0x75   # should read 0x68

# Full-scale range selectors
ACCEL_FS_2G  = 0x00   # ±2 g,   16384 LSB/g
ACCEL_FS_4G  = 0x08   # ±4 g,    8192 LSB/g
ACCEL_FS_8G  = 0x10   # ±8 g,    4096 LSB/g
ACCEL_FS_16G = 0x18   # ±16 g,   2048 LSB/g

GYRO_FS_250  = 0x00   # ±250  °/s, 131.0 LSB/(°/s)
GYRO_FS_500  = 0x08   # ±500  °/s,  65.5 LSB/(°/s)
GYRO_FS_1000 = 0x10   # ±1000 °/s,  32.8 LSB/(°/s)
GYRO_FS_2000 = 0x18   # ±2000 °/s,  16.4 LSB/(°/s)

_ACCEL_SCALE = (16384.0, 8192.0, 4096.0, 2048.0)
_GYRO_SCALE  = (131.0,   65.5,   32.8,   16.4)


class MPU6050:
    """
    Minimal MPU-6050 driver.

    Usage::

        from machine import I2C, Pin
        from mpu6050 import MPU6050

        i2c = I2C(1, scl=Pin('PB8'), sda=Pin('PB9'), freq=400_000)
        imu = MPU6050(i2c)
        ax, ay, az = imu.accel()   # g
        gx, gy, gz = imu.gyro()    # °/s
        t = imu.temperature()      # °C
    """

    def __init__(self, i2c, addr=0x68,
                 accel_fs=ACCEL_FS_2G, gyro_fs=GYRO_FS_250):
        self._i2c  = i2c
        self._addr = addr
        self._buf14 = bytearray(14)  # reusable read buffer

        # Verify device identity
        who = self._read_reg(1, _REG_WHO_AM_I)[0]
        if who != 0x68:
            raise RuntimeError(
                "MPU-6050 not found (WHO_AM_I=0x{:02X})".format(who))

        # Wake device: clear SLEEP bit, use internal 8 MHz oscillator
        self._write_reg(_REG_PWR_MGMT_1, 0x00)

        # Configure full-scale ranges
        self._write_reg(_REG_ACCEL_CONFIG, accel_fs)
        self._write_reg(_REG_GYRO_CONFIG,  gyro_fs)

        # Store scale factors
        accel_idx = (accel_fs >> 3) & 0x03
        gyro_idx  = (gyro_fs  >> 3) & 0x03
        self._accel_scale = _ACCEL_SCALE[accel_idx]
        self._gyro_scale  = _GYRO_SCALE[gyro_idx]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def accel(self):
        """Return (ax, ay, az) in g."""
        self._read_all()
        ax = self._s16(0) / self._accel_scale
        ay = self._s16(2) / self._accel_scale
        az = self._s16(4) / self._accel_scale
        return ax, ay, az

    def temperature(self):
        """Return die temperature in °C."""
        self._read_all()
        raw = self._s16(6)
        return raw / 340.0 + 36.53

    def gyro(self):
        """Return (gx, gy, gz) in degrees/second."""
        self._read_all()
        gx = self._s16(8)  / self._gyro_scale
        gy = self._s16(10) / self._gyro_scale
        gz = self._s16(12) / self._gyro_scale
        return gx, gy, gz

    def read_all(self):
        """
        Return (ax, ay, az, temp, gx, gy, gz) in one I2C transaction.
        Units: g, °C, °/s.
        """
        self._read_all()
        ax = self._s16(0)  / self._accel_scale
        ay = self._s16(2)  / self._accel_scale
        az = self._s16(4)  / self._accel_scale
        t  = self._s16(6)  / 340.0 + 36.53
        gx = self._s16(8)  / self._gyro_scale
        gy = self._s16(10) / self._gyro_scale
        gz = self._s16(12) / self._gyro_scale
        return ax, ay, az, t, gx, gy, gz

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _read_all(self):
        """Burst-read all 14 sensor bytes starting at ACCEL_XOUT_H."""
        self._i2c.readfrom_mem_into(self._addr, _REG_ACCEL_XOUT, self._buf14)

    def _s16(self, offset):
        """Interpret two bytes at buf[offset] as a big-endian signed 16-bit int."""
        val = (self._buf14[offset] << 8) | self._buf14[offset + 1]
        return val if val < 32768 else val - 65536

    def _write_reg(self, reg, value):
        self._i2c.writeto_mem(self._addr, reg, bytes([value]))

    def _read_reg(self, n, reg):
        return self._i2c.readfrom_mem(self._addr, reg, n)
