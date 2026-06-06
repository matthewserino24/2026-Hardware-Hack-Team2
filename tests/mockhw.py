"""
mockhw.py — Minimal fakes for MicroPython hardware modules so that the
firmware can be *imported and exercised on a host PC* under CPython.

The firmware targets MicroPython on an STM32G4 and uses APIs that do not
exist in CPython:

    - the `machine` module      (I2C, Pin, PWM, time_pulse_us)
    - the `utime` module        (ticks_ms / ticks_diff / sleep_ms / sleep_us)
    - `time.ticks_ms()` etc.    (MicroPython adds these to `time`)
    - the `const()` builtin     (a MicroPython compile-time hint)

Call `install()` once before importing any firmware module.  It registers
fakes in `sys.modules` and injects `const` into builtins.  The fakes are
*just smart enough* to let constructors succeed (e.g. the MPU-6050 WHO_AM_I
check and the MCP9808 ID checks pass) so we can test logic, not silicon.
"""

import sys
import types
import builtins


# --------------------------------------------------------------------------
# Fake monotonic clock (milliseconds / microseconds), advanced manually.
# --------------------------------------------------------------------------
class _Clock:
    def __init__(self):
        self.ms = 0
        self.auto_step_ms = 0   # if >0, ticks_ms() advances the clock each call

    def ticks_ms(self):
        v = self.ms
        self.ms += self.auto_step_ms
        return v

    def ticks_us(self):
        return self.ms * 1000

    def ticks_diff(self, a, b):
        return a - b

    def sleep_ms(self, n):
        self.ms += int(n)

    def sleep_us(self, n):
        self.ms += int(n) // 1000

    def sleep(self, s):
        self.ms += int(s * 1000)


CLOCK = _Clock()


# --------------------------------------------------------------------------
# Fake machine.Pin
# --------------------------------------------------------------------------
class FakePin:
    OUT = 1
    IN = 0
    PULL_UP = 2
    PULL_DOWN = 3

    def __init__(self, id, mode=-1, pull=-1, value=0):
        self.id = id
        self._value = value

    def value(self, v=None):
        if v is None:
            return self._value
        self._value = v

    def on(self):
        self._value = 1

    def off(self):
        self._value = 0


# --------------------------------------------------------------------------
# Fake machine.PWM
# --------------------------------------------------------------------------
class FakePWM:
    def __init__(self, pin, freq=50):
        self.pin = pin
        self._freq = freq
        self._duty_ns = 0

    def freq(self, f=None):
        if f is None:
            return self._freq
        self._freq = f

    def duty_ns(self, n=None):
        if n is None:
            return self._duty_ns
        self._duty_ns = n

    def deinit(self):
        pass


# --------------------------------------------------------------------------
# Fake machine.I2C
#
# Returns identity bytes that satisfy the driver self-checks:
#   MPU-6050 WHO_AM_I (reg 0x75) -> 0x68
#   MCP9808  MANUFACTURER (0x06) -> 0x0054
#   MCP9808  DEVICE_ID    (0x07) -> 0x0400
#   MCP9808  CONFIG       (0x01) -> 0x0000 (not in shutdown)
#   MCP9808  TA           (0x05) -> ~+23.0 C
# Everything else returns zero bytes.
# --------------------------------------------------------------------------
class FakeI2C:
    def __init__(self, *args, **kwargs):
        self.writes = []

    def _bytes_for(self, reg, n):
        table = {
            0x75: b"\x68",          # MPU-6050 WHO_AM_I
            0x06: b"\x00\x54",      # MCP9808 manufacturer id
            0x07: b"\x04\x00",      # MCP9808 device id
            0x01: b"\x00\x00",      # MCP9808 config (awake)
            0x05: b"\x01\x70",      # MCP9808 ambient temp -> 0x0170/16 = 23.0 C
        }
        data = table.get(reg, b"\x00" * n)
        if len(data) < n:
            data = data + b"\x00" * (n - len(data))
        return data[:n]

    def readfrom_mem(self, addr, reg, n):
        return self._bytes_for(reg, n)

    def readfrom_mem_into(self, addr, reg, buf):
        data = self._bytes_for(reg, len(buf))
        for i in range(len(buf)):
            buf[i] = data[i]

    def writeto_mem(self, addr, reg, data):
        self.writes.append((addr, reg, bytes(data)))

    def writeto(self, addr, data):
        self.writes.append((addr, bytes(data)))

    def scan(self):
        return [0x68, 0x18, 0x70]


# --------------------------------------------------------------------------
# Fake machine.time_pulse_us — simulate an echo for a fixed distance.
# Default: ~100 cm  (pulse_us = 100 * 58 = 5800).
# --------------------------------------------------------------------------
_SIM_DISTANCE_CM = [100.0]


def set_sim_distance_cm(cm):
    """Set the distance the fake HC-SR04 will report (None => timeout)."""
    _SIM_DISTANCE_CM[0] = cm


def set_auto_advance_ms(step):
    """Make utime/time ticks_ms() auto-advance by `step` ms per call so a
    cadence-based main loop progresses in time without real sleeps."""
    CLOCK.auto_step_ms = step


def set_clock_ms(ms):
    CLOCK.ms = ms


def _time_pulse_us(pin, level, timeout_us):
    cm = _SIM_DISTANCE_CM[0]
    if cm is None:
        return -2  # timeout (MicroPython returns negative)
    return int(cm * 58)


# --------------------------------------------------------------------------
# Installer
# --------------------------------------------------------------------------
def install():
    # const() builtin -> identity function
    builtins.const = lambda x: x

    machine = types.ModuleType("machine")
    machine.Pin = FakePin
    machine.PWM = FakePWM
    machine.I2C = FakeI2C
    machine.time_pulse_us = _time_pulse_us
    sys.modules["machine"] = machine

    utime = types.ModuleType("utime")
    utime.ticks_ms = CLOCK.ticks_ms
    utime.ticks_us = CLOCK.ticks_us
    utime.ticks_diff = CLOCK.ticks_diff
    utime.sleep_ms = CLOCK.sleep_ms
    utime.sleep_us = CLOCK.sleep_us
    utime.sleep = CLOCK.sleep
    sys.modules["utime"] = utime

    # The firmware's "version B" modules do `import time` then call
    # time.ticks_ms()/ticks_diff()/sleep_ms() — MicroPython extensions that
    # CPython's real `time` lacks.  Shadow it with a hybrid module.
    import time as _real_time
    fake_time = types.ModuleType("time")
    for name in dir(_real_time):
        if not name.startswith("__"):
            setattr(fake_time, name, getattr(_real_time, name))
    fake_time.ticks_ms = CLOCK.ticks_ms
    fake_time.ticks_us = CLOCK.ticks_us
    fake_time.ticks_diff = CLOCK.ticks_diff
    fake_time.sleep_ms = CLOCK.sleep_ms
    fake_time.sleep_us = CLOCK.sleep_us
    sys.modules["time"] = fake_time

    return machine, utime, fake_time
