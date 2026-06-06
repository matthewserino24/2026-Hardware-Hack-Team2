"""
ultrasonic.py — HC-SR04 distance measurement for the wrist-mounted navigation prototype.

Hardware note (§8 of requirements):
    The HC-SR04 Echo pin outputs a 5 V signal.  The STM32G4 GPIO is 3.3 V-tolerant
    only up to VDD+0.3 V ≈ 3.6 V.  A resistor voltage divider (e.g. 10 kΩ / 20 kΩ)
    MUST be placed between the sensor Echo pin and the MCU GPIO before powering the
    board.  The Trig pin is driven by the MCU at 3.3 V; the HC-SR04 accepts this as
    a valid TTL high level, so no level-shifting is needed on that line.

Timing (from datasheet):
    - Send ≥ 10 µs high pulse on TRIG.
    - Module fires 8 × 40 kHz bursts and raises ECHO high.
    - ECHO pulse width (µs) / 58 = distance in centimetres.
    - Recommended measurement cycle: ≥ 60 ms (config uses 150 ms).
    - Valid range: 2 cm – 400 cm.
"""

import machine
import utime
from config import SMOOTHING_WINDOW

# Physical limits of the HC-SR04 (datasheet §1)
_MIN_CM: float = 2.0
_MAX_CM: float = 400.0

# 30 ms timeout covers a ~5 m round-trip — well beyond the 4 m sensor maximum.
# time_pulse_us() returns a negative value when the timeout expires.
_ECHO_TIMEOUT_US: int = 30_000

# µs-per-cm conversion factor from the HC-SR04 datasheet
_US_PER_CM: float = 58.0


class Ultrasonic:
    """Non-blocking HC-SR04 driver with rolling-average smoothing.

    Usage::

        sensor = Ultrasonic(trig_pin="A1", echo_pin="A0")

        # In the main loop (call every ULTRASONIC_SAMPLE_INTERVAL_MS):
        distance = sensor.read_cm()   # smoothed, or None if no valid data yet
    """

    def __init__(self, trig_pin, echo_pin) -> None:
        """Initialise GPIO pins.

        Args:
            trig_pin: Pin identifier accepted by ``machine.Pin`` (e.g. ``"A1"``
                      or an integer board pin number).
            echo_pin: Pin identifier for the Echo line.  Connect through a
                      voltage divider — see module-level hardware note.
        """
        self._trig = machine.Pin(trig_pin, machine.Pin.OUT, value=0)
        self._echo = machine.Pin(echo_pin, machine.Pin.IN)

        # Rolling window: list of up to SMOOTHING_WINDOW valid cm readings.
        # We use a plain list and manage the window manually so this module
        # stays compatible with MicroPython builds that omit collections.deque.
        self._window: list = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def read_raw_cm(self):
        """Fire one ultrasonic pulse and return the raw distance in cm.

        Returns:
            float: Distance in centimetres (2.0 – 400.0), or
            None:  If the echo timed out (no target in range) or the
                   returned value is outside the sensor's valid range.
        """
        # Ensure TRIG is low before the pulse (≥ 2 µs settling time).
        self._trig.value(0)
        utime.sleep_us(2)

        # Raise TRIG for exactly 10 µs to start ranging.
        self._trig.value(1)
        utime.sleep_us(10)
        self._trig.value(0)

        # Measure the ECHO pulse width.
        # time_pulse_us(pin, level, timeout_us) returns the pulse width in µs,
        # or a *negative* value if the timeout expires before the pulse ends.
        pulse_us = machine.time_pulse_us(self._echo, 1, _ECHO_TIMEOUT_US)

        # Timeout: no echo received within 30 ms.
        if pulse_us < 0:
            return None

        distance_cm = pulse_us / _US_PER_CM

        # Reject readings outside the sensor's specified operating range.
        if distance_cm < _MIN_CM or distance_cm > _MAX_CM:
            return None

        return distance_cm

    def read_cm(self):
        """Return a smoothed distance reading using a rolling average.

        Calls ``read_raw_cm()`` once, appends valid results to the internal
        window, and returns the mean of the last ``SMOOTHING_WINDOW`` valid
        readings.  Invalid readings (None) are silently dropped — they are
        never zeroed or substituted — so the smoothed value reflects only
        real echoes.

        Returns:
            float: Smoothed distance in centimetres, or
            None:  If the window contains no valid readings yet.
        """
        raw = self.read_raw_cm()

        if raw is not None:
            self._window.append(raw)
            # Keep only the most recent SMOOTHING_WINDOW entries.
            if len(self._window) > SMOOTHING_WINDOW:
                # Remove the oldest reading from the front.
                self._window.pop(0)

        if not self._window:
            return None

        return sum(self._window) / len(self._window)
