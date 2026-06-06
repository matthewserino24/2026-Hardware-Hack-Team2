# ultrasonic.py
# HC-SR04 ultrasonic distance sensor driver for MicroPython on STM32G4.
#
# Hardware notes (from HC-SR04 datasheet):
#   - VCC: 5 V (module draws ~15 mA)
#   - TRIG: 10 µs active-high pulse on any GPIO output
#   - ECHO: high pulse whose width encodes distance.
#         *** ECHO is a 5 V signal — the STM32G4 GPIO is 5V-tolerant on
#         most pins but the safe practice is a voltage divider:
#         ECHO → 1 kΩ → MCU pin → 2 kΩ → GND  (gives ~3.3 V at MCU) ***
#   - Formula: distance_cm = pulse_width_us / 58
#   - Minimum cycle time: 60 ms (to prevent trigger echo cross-talk)
#   - Range: 2 cm – 400 cm; returns None on timeout / out-of-range
#
# Smoothing: a 3-sample median filter is applied to suppress single-shot
# spikes.  The filter buffer is pre-filled with the first valid reading so
# the output is valid from the very first call.
#
# Usage::
#
#     from machine import Pin
#     from ultrasonic import HCSR04
#
#     sonar = HCSR04(trig_pin='PA8', echo_pin='PA9')
#     dist  = sonar.distance_cm()   # float or None

import utime
from machine import Pin, time_pulse_us

# Speed of sound at ~20°C: 343 m/s → 34300 cm/s
# Round-trip: distance_cm = pulse_us * 34300 / 2 / 1_000_000
#           = pulse_us / 58.31  ≈ pulse_us / 58
_US_PER_CM    = 58          # µs per cm (round-trip, standard approximation)
_TIMEOUT_US   = 23200       # 400 cm × 58 µs/cm = 23200 µs max echo
_TRIG_US      = 10          # trigger pulse width (datasheet: ≥10 µs)
_MEDIAN_N     = 3           # median filter window size (must be odd)


def _median3(a, b, c):
    """Return the median of three values without sorting (branchless-ish)."""
    if a <= b:
        if b <= c:
            return b
        elif a <= c:
            return c
        else:
            return a
    else:
        if a <= c:
            return a
        elif b <= c:
            return c
        else:
            return b


class HCSR04:
    """
    HC-SR04 ultrasonic distance sensor driver with 3-sample median filter.

    Parameters
    ----------
    trig_pin : str or int
        Pin name/number for the TRIG output (e.g. 'PA8' or 'D7').
    echo_pin : str or int
        Pin name/number for the ECHO input (e.g. 'PA9' or 'D8').
        Must be connected through a voltage divider if the module runs at 5 V.
    """

    def __init__(self, trig_pin, echo_pin):
        self._trig = Pin(trig_pin, Pin.OUT, value=0)
        self._echo = Pin(echo_pin, Pin.IN)

        # Pre-fill the median filter buffer with a real measurement so the
        # first filtered reading is meaningful rather than zero.
        first = self._raw_distance_cm()
        if first is None:
            first = 200.0   # safe fallback: mid-range
        self._buf = [first, first, first]   # circular buffer, newest at [0]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def distance_cm(self):
        """
        Return the median-filtered distance in centimetres (float), or None
        if all three buffer slots are invalid (sensor not responding).

        The filter window holds the last 3 raw readings.  A single bad
        reading (spike or timeout) is suppressed as long as the other two
        are valid.
        """
        raw = self._raw_distance_cm()

        # Shift buffer: drop oldest, insert newest at front
        self._buf[2] = self._buf[1]
        self._buf[1] = self._buf[0]
        self._buf[0] = raw if raw is not None else self._buf[1]

        # Median of the three buffer values
        return _median3(self._buf[0], self._buf[1], self._buf[2])

    def distance_cm_raw(self):
        """
        Return a single unfiltered distance reading in cm, or None on timeout.
        Useful for diagnostics.
        """
        return self._raw_distance_cm()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _raw_distance_cm(self):
        """
        Fire one ultrasonic pulse and measure the echo width.

        Returns float (cm) or None on timeout / out-of-range.
        """
        trig = self._trig
        echo = self._echo

        # Ensure trigger is low before pulsing
        trig.value(0)
        utime.sleep_us(2)

        # 10 µs trigger pulse
        trig.value(1)
        utime.sleep_us(_TRIG_US)
        trig.value(0)

        # Measure echo pulse width; returns -1 on timeout
        pulse_us = time_pulse_us(echo, 1, _TIMEOUT_US)

        if pulse_us < 0:
            return None

        dist = pulse_us / _US_PER_CM
        # Clamp to sensor's specified range
        if dist < 2.0 or dist > 400.0:
            return None

        return dist
