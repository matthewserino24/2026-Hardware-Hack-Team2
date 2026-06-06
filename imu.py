# imu.py – MPU-6050 driver with startup calibration and yaw-heading integration.
#
# Target board : NUCLEO-G474RE (STM32G4, MicroPython)
# IMU          : MPU-6050 over I2C1
# I2C pins     : PB8 = SCL  (Arduino D15 / CN10-3)
#                PB9 = SDA  (Arduino D14 / CN10-5)
# I2C address  : 0x68 (AD0 pin tied low, default)
#
# Public API (consumed by route.py and main.py)
# ---------------------------------------------
#   imu = IMU(i2c)        — pass a configured machine.I2C instance
#   imu.calibrate()       — collect gyro-Z bias; hold device still ~2 s
#   imu.update(now_ms)    — integrate gyro-Z; call every LOOP_PERIOD_MS
#   imu.heading()         — current yaw in degrees, wrapped to (-180, 180]
#   imu.zero_heading()    — latch current yaw as 0°
#
# Register references: RM-MPU-6000A-00 Rev 4.0
#   0x1A  CONFIG          – DLPF_CFG (digital low-pass filter)
#   0x1B  GYRO_CONFIG     – FS_SEL (full-scale range)
#   0x1C  ACCEL_CONFIG    – AFS_SEL (full-scale range)
#   0x19  SMPLRT_DIV      – sample-rate divider
#   0x47  GYRO_ZOUT_H     – gyro Z high byte (big-endian signed 16-bit)
#   0x6B  PWR_MGMT_1      – wake device, select clock source
#   0x75  WHO_AM_I        – identity register (expected 0x68)

import struct
import time
from config import (
    MPU6050_ADDR,
    IMU_GYRO_FS,
    IMU_CALIBRATION_MS,
    IMU_SAMPLE_INTERVAL_MS,
    CALIBRATION_SAMPLES,
    LOOP_PERIOD_MS,
)

# ---------------------------------------------------------------------------
# MPU-6050 register addresses
# ---------------------------------------------------------------------------
_REG_SMPLRT_DIV  = const(0x19)
_REG_CONFIG      = const(0x1A)
_REG_GYRO_CONFIG = const(0x1B)
_REG_ACCEL_CONFIG= const(0x1C)
_REG_GYRO_ZOUT_H = const(0x47)
_REG_PWR_MGMT_1  = const(0x6B)
_REG_WHO_AM_I    = const(0x75)

# Gyro full-scale → (GYRO_CONFIG register value, sensitivity in LSB/°/s)
# Source: RM-MPU-6000A-00 §4.4 (Table 1)
_FS_SEL_MAP = {
    250:  (0b00 << 3, 131.0),
    500:  (0b01 << 3,  65.5),
    1000: (0b10 << 3,  32.8),
    2000: (0b11 << 3,  16.4),
}


def _wrap180(angle: float) -> float:
    """Wrap *angle* into the half-open interval (-180, 180].

    Uses only arithmetic (no math module) for compatibility with minimal
    MicroPython builds.
    """
    angle = angle % 360.0
    if angle > 180.0:
        angle -= 360.0
    return angle


class IMU:
    """MPU-6050 driver providing gyro-integrated yaw heading.

    Parameters
    ----------
    i2c : machine.I2C
        A fully configured I2C bus instance.  The caller is responsible for
        constructing it with the correct pins and frequency.  Example::

            from machine import I2C, Pin
            i2c = I2C(1, scl=Pin('PB8'), sda=Pin('PB9'), freq=400_000)
            imu = IMU(i2c)

    Typical startup sequence
    ------------------------
    ::

        imu = IMU(i2c)
        imu.calibrate()       # hold device still for ~2 s
        imu.zero_heading()    # optional: re-zero after calibration
        # move servo to neutral, then enter main loop:
        while True:
            now = time.ticks_ms()
            imu.update(now)
            print(imu.heading())
            time.sleep_ms(LOOP_PERIOD_MS)
    """

    def __init__(self, i2c):
        self._i2c = i2c
        self._addr = MPU6050_ADDR

        # Resolve gyro sensitivity from config
        fs_reg, self._sensitivity = _FS_SEL_MAP.get(
            IMU_GYRO_FS, _FS_SEL_MAP[250]
        )
        self._fs_reg = fs_reg

        # Verify device identity before touching any other register.
        who = self._read_byte(_REG_WHO_AM_I)
        if who != 0x68:
            raise RuntimeError(
                "MPU-6050 not found (WHO_AM_I=0x{:02X}, expected 0x68)".format(who)
            )

        self._configure()

        # Runtime state
        self._bias: float    = 0.0    # gyro-Z zero-rate offset in °/s
        self._hdg: float     = 0.0    # integrated heading in degrees
        self._last_ms: int   = time.ticks_ms()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def calibrate(self) -> None:
        """Collect gyro-Z readings while stationary and store the mean bias.

        Samples CALIBRATION_SAMPLES readings spaced IMU_SAMPLE_INTERVAL_MS
        apart (total ≈ IMU_CALIBRATION_MS ms ≈ 2 s at defaults).  The device
        must be held completely still for the full duration.

        Resets the integrated heading to 0° and re-latches the timestamp so
        stale drift does not carry forward.
        """
        accumulator: float = 0.0
        for _ in range(CALIBRATION_SAMPLES):
            accumulator += self._read_gyro_z_dps()
            time.sleep_ms(IMU_SAMPLE_INTERVAL_MS)

        self._bias = accumulator / CALIBRATION_SAMPLES
        self._hdg  = 0.0
        self._last_ms = time.ticks_ms()

    def zero_heading(self) -> None:
        """Latch the current yaw as 0°.

        Call after calibrate() and before entering the navigation loop if
        the device was moved during calibration teardown.
        """
        self._hdg = 0.0
        self._last_ms = time.ticks_ms()

    def update(self, now_ms: int) -> None:
        """Integrate the bias-corrected gyro-Z rate into the heading.

        Parameters
        ----------
        now_ms : int
            Current value of ``time.ticks_ms()``.  Passing it in (rather
            than reading it internally) lets the caller use a single
            consistent timestamp across all sensors in the main loop.

        Must be called at approximately LOOP_PERIOD_MS intervals.  Uses the
        actual elapsed time so occasional scheduling jitter does not
        accumulate as a systematic error.
        """
        dt_s = time.ticks_diff(now_ms, self._last_ms) / 1000.0
        self._last_ms = now_ms

        rate_dps = self._read_gyro_z_dps() - self._bias
        self._hdg = _wrap180(self._hdg + rate_dps * dt_s)

    def heading(self) -> float:
        """Return the current yaw heading in degrees, wrapped to (-180, 180].

        Positive = clockwise rotation (right turn), negative = counter-clockwise
        (left turn), assuming the MPU-6050 Z-axis points upward.
        """
        return self._hdg

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _configure(self) -> None:
        """Wake the MPU-6050 and apply sensor configuration.

        Register writes (verified against RM-MPU-6000A-00 §4):

        PWR_MGMT_1  = 0x03  – clear SLEEP; CLKSEL=3 (PLL with Z gyro ref,
                               recommended over internal 8 MHz oscillator)
        SMPLRT_DIV  = 0x13  – divider=19; gyro output rate with DLPF=1 kHz,
                               so sample rate = 1000/(1+19) = 50 Hz = 20 ms ✓
        CONFIG      = 0x04  – DLPF_CFG=4: accel BW≈21 Hz, gyro BW≈20 Hz,
                               appropriate for 50 Hz sampling of walking motion
        GYRO_CONFIG = self._fs_reg  – FS_SEL from IMU_GYRO_FS in config.py
        ACCEL_CONFIG= 0x00  – AFS_SEL=0 → ±2 g (not used for heading, but
                               left at a safe default)
        """
        # 1. Wake device (reset value of PWR_MGMT_1 is 0x40 = SLEEP set)
        self._write_byte(_REG_PWR_MGMT_1, 0x03)
        time.sleep_ms(100)  # allow PLL to stabilise (datasheet: ≥50 ms)

        # 2. Sample rate: 50 Hz (20 ms period)
        self._write_byte(_REG_SMPLRT_DIV, 0x13)   # 19 decimal

        # 3. DLPF: ~21 Hz bandwidth (DLPF_CFG = 4)
        self._write_byte(_REG_CONFIG, 0x04)

        # 4. Gyro full-scale range (from config)
        self._write_byte(_REG_GYRO_CONFIG, self._fs_reg)

        # 5. Accel full-scale: ±2 g (safe default)
        self._write_byte(_REG_ACCEL_CONFIG, 0x00)

    def _read_gyro_z_dps(self) -> float:
        """Read GYRO_ZOUT (registers 0x47–0x48) and return °/s.

        The two bytes are big-endian signed 16-bit (two's complement).
        struct.unpack('>h', ...) handles sign extension correctly.
        Sensitivity at ±250 °/s = 131 LSB/°/s  (datasheet §4.20).
        """
        raw = self._i2c.readfrom_mem(self._addr, _REG_GYRO_ZOUT_H, 2)
        z_raw = struct.unpack('>h', raw)[0]   # signed 16-bit big-endian
        return z_raw / self._sensitivity

    def _write_byte(self, reg: int, value: int) -> None:
        self._i2c.writeto_mem(self._addr, reg, bytes([value]))

    def _read_byte(self, reg: int) -> int:
        return self._i2c.readfrom_mem(self._addr, reg, 1)[0]
