"""
HC-SR04 ultrasonic driver.

Exposes both the newer `HCSR04.distance_cm()` API and the simpler
`Ultrasonic.read_cm()` compatibility wrapper.
"""

import utime
from machine import Pin, time_pulse_us

from config import HCSR04_TIMEOUT_US, SMOOTHING_WINDOW

_US_PER_CM = 58.0
_TRIG_US = 10
_MIN_CM = 2.0
_MAX_CM = 400.0


def _median3(a, b, c):
    if a <= b:
        if b <= c:
            return b
        if a <= c:
            return c
        return a
    if a <= c:
        return a
    if b <= c:
        return c
    return b


class HCSR04:
    def __init__(self, trig_pin, echo_pin):
        self._trig = Pin(trig_pin, Pin.OUT, value=0)
        self._echo = Pin(echo_pin, Pin.IN)

        first = self._raw_distance_cm()
        if first is None:
            first = 200.0
        self._median_buf = [first, first, first]
        self._avg_window = [first]

    def distance_cm(self):
        raw = self._raw_distance_cm()
        self._median_buf[2] = self._median_buf[1]
        self._median_buf[1] = self._median_buf[0]
        self._median_buf[0] = raw if raw is not None else self._median_buf[1]
        return _median3(self._median_buf[0], self._median_buf[1], self._median_buf[2])

    def distance_cm_raw(self):
        return self._raw_distance_cm()

    def read_raw_cm(self):
        return self.distance_cm_raw()

    def read_cm(self):
        raw = self._raw_distance_cm()
        if raw is not None:
            self._avg_window.append(raw)
            if len(self._avg_window) > SMOOTHING_WINDOW:
                self._avg_window.pop(0)
        if not self._avg_window:
            return None
        return sum(self._avg_window) / len(self._avg_window)

    def _raw_distance_cm(self):
        self._trig.value(0)
        utime.sleep_us(2)
        self._trig.value(1)
        utime.sleep_us(_TRIG_US)
        self._trig.value(0)

        pulse_us = time_pulse_us(self._echo, 1, HCSR04_TIMEOUT_US)
        if pulse_us < 0:
            return None

        distance = pulse_us / _US_PER_CM
        if distance < _MIN_CM or distance > _MAX_CM:
            return None
        return distance


class Ultrasonic(HCSR04):
    pass
