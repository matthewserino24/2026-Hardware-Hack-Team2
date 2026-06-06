# imu.py
# High-level IMU wrapper for the MPU-6050.
# Provides gyro-Z heading integration with bias calibration.
#
# Coordinate convention:
#   Positive gyro-Z → counter-clockwise yaw when the board is flat (Z-up).
#   Heading is accumulated in degrees; zero_heading() resets the reference.
#
# Calibration:
#   calibrate() collects CALIBRATION_SAMPLES gyro-Z readings at rest and
#   stores the mean as a bias offset.  The device must be stationary during
#   calibration.  Typical bias is a few °/s; without correction it would
#   accumulate ~10° of drift per minute.
#
# Usage::
#
#     from machine import I2C, Pin
#     from imu import IMU
#
#     i2c = I2C(1, scl=Pin('PB8'), sda=Pin('PB9'), freq=400_000)
#     imu = IMU(i2c)
#     imu.calibrate()      # hold still ~1 s
#     imu.zero_heading()
#     # in loop:
#     imu.update(dt_s)
#     print(imu.heading)   # degrees, unbounded accumulation

import utime
from mpu6050 import MPU6050

# Number of samples averaged during calibration (~50 ms each → ~1 s total)
_CALIBRATION_SAMPLES  = 20
_CALIBRATION_DELAY_MS = 50   # ms between calibration samples


class IMU:
    """
    Heading-integration wrapper around the MPU-6050.

    Parameters
    ----------
    i2c  : machine.I2C (already initialised)
    addr : 7-bit I2C address (default 0x68, AD0=GND)
    """

    def __init__(self, i2c, addr=0x68):
        self._mpu     = MPU6050(i2c, addr=addr)
        self._bias_z  = 0.0    # gyro-Z bias in °/s
        self._heading = 0.0    # accumulated heading in degrees
        self._ref     = 0.0    # heading at last zero_heading() call

    # ------------------------------------------------------------------
    # Calibration
    # ------------------------------------------------------------------

    def calibrate(self):
        """
        Collect gyro-Z readings at rest and compute the static bias.

        The device must be completely stationary during this call.
        Takes approximately CALIBRATION_SAMPLES × CALIBRATION_DELAY_MS ms.
        """
        total = 0.0
        for _ in range(_CALIBRATION_SAMPLES):
            _, _, gz = self._mpu.gyro()
            total += gz
            utime.sleep_ms(_CALIBRATION_DELAY_MS)
        self._bias_z = total / _CALIBRATION_SAMPLES

    def zero_heading(self):
        """
        Reset the heading reference to the current accumulated heading.
        After this call, imu.heading returns 0.0 until the device rotates.
        """
        self._ref = self._heading

    # ------------------------------------------------------------------
    # Update (call once per loop iteration with elapsed time)
    # ------------------------------------------------------------------

    def update(self, dt_s):
        """
        Integrate gyro-Z over dt_s seconds and accumulate into heading.

        Parameters
        ----------
        dt_s : float
            Elapsed time since the last call, in seconds.
            Caller is responsible for measuring this with ticks_ms/ticks_diff.
        """
        _, _, gz = self._mpu.gyro()
        gz_corrected = gz - self._bias_z
        # Dead-band: ignore noise below 0.5 °/s to suppress micro-drift
        if abs(gz_corrected) < 0.5:
            gz_corrected = 0.0
        self._heading += gz_corrected * dt_s

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def heading(self):
        """
        Current heading relative to the last zero_heading() call, in degrees.
        Positive = counter-clockwise (right-hand rule, Z-up).
        Unbounded — does not wrap at ±180°.
        """
        return self._heading - self._ref

    @property
    def raw_heading(self):
        """Accumulated heading since power-on (not zeroed), in degrees."""
        return self._heading

    @property
    def bias(self):
        """Gyro-Z bias measured during the last calibrate() call (°/s)."""
        return self._bias_z
