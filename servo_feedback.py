"""
SG90 servo feedback driver.

This merged version supports:
- non-blocking warning and danger feedback used by the latest main branch
- non-blocking tap helpers kept from the local framework branch
"""

import utime
from machine import Pin, PWM

import config

_TAP_HOLD_MS = 60


def _angle_to_ns(deg):
    deg = max(0, min(180, int(deg)))
    pulse_us = config.SG90_MIN_US + (
        (config.SG90_MAX_US - config.SG90_MIN_US) * deg
    ) // 180
    return pulse_us * 1000


class ServoFeedback:
    def __init__(self, pin):
        self._pin = Pin(pin) if isinstance(pin, str) else pin
        self._pwm = PWM(self._pin, freq=config.SG90_FREQ_HZ)
        self._angle = float(config.SERVO_NEUTRAL)
        self._state = "IDLE"
        self._phase_start = utime.ticks_ms()
        self._tap_target = config.SERVO_NEUTRAL
        self._danger_side = 0
        self._pulse_count = 0
        self._warn_interval_ms = config.WARNING_TAP_INTERVAL_MS
        self.neutral()

    def set_angle(self, angle_deg):
        self._angle = max(0.0, min(180.0, float(angle_deg)))
        self._pwm.duty_ns(_angle_to_ns(self._angle))

    @property
    def angle(self):
        return self._angle

    def neutral(self):
        self._state = "IDLE"
        self.set_angle(config.SERVO_NEUTRAL)

    def stop(self):
        self.neutral()

    def steer(self, heading_error_deg):
        target = config.SERVO_NEUTRAL + heading_error_deg
        self.set_angle(target)

    def tap_left(self):
        self._tap_target = config.SERVO_LEFT_TAP
        self._start_single_tap()

    def tap_right(self):
        self._tap_target = config.SERVO_RIGHT_TAP
        self._start_single_tap()

    def warning_pulse(self):
        self._danger_side = 0
        self._state = "WARN_PULSE_WAIT"
        self._phase_start = utime.ticks_ms()

    def warning_pattern(self, distance_cm):
        if distance_cm is None:
            self.neutral()
            return

        warn_ms = config.WARNING_TAP_INTERVAL_MS
        danger_ms = config.DANGER_TAP_INTERVAL_MS
        t = (75.0 - float(distance_cm)) / 35.0
        t = max(0.0, min(1.0, t))
        self._warn_interval_ms = int(warn_ms + t * (danger_ms - warn_ms))

        if self._state not in ("WARN_WAIT", "WARN_MOVE", "WARN_HOLD", "WARN_RETURN"):
            self._danger_side = 0
            self._state = "WARN_WAIT"
            self._phase_start = utime.ticks_ms()

    def danger_pattern(self):
        self._danger_side = 0
        self._state = "DANGER_PULSE_MOVE"
        self._phase_start = utime.ticks_ms()
        self._pulse_count = 0
        self.set_angle(config.SERVO_RIGHT_TAP)

    def tick(self, timer=None):
        del timer
        now = utime.ticks_ms()
        elapsed = utime.ticks_diff(now, self._phase_start)

        if self._state == "IDLE":
            return

        if self._state == "TAP_MOVE" and elapsed >= _TAP_HOLD_MS:
            self._state = "TAP_HOLD"
            self._phase_start = now
            return

        if self._state == "TAP_HOLD" and elapsed >= _TAP_HOLD_MS:
            self.set_angle(config.SERVO_NEUTRAL)
            self._state = "TAP_RETURN"
            self._phase_start = now
            return

        if self._state == "TAP_RETURN" and elapsed >= _TAP_HOLD_MS:
            self._state = "IDLE"
            return

        if self._state == "WARN_WAIT" and elapsed >= self._warn_interval_ms:
            if self._danger_side == 0:
                self.set_angle(config.SERVO_LEFT_TAP)
            else:
                self.set_angle(config.SERVO_RIGHT_TAP)
            self._danger_side ^= 1
            self._state = "WARN_MOVE"
            self._phase_start = now
            return

        if self._state == "WARN_MOVE" and elapsed >= _TAP_HOLD_MS:
            self._state = "WARN_HOLD"
            self._phase_start = now
            return

        if self._state == "WARN_HOLD" and elapsed >= _TAP_HOLD_MS:
            self.set_angle(config.SERVO_NEUTRAL)
            self._state = "WARN_RETURN"
            self._phase_start = now
            return

        if self._state == "WARN_RETURN" and elapsed >= _TAP_HOLD_MS:
            self._state = "WARN_WAIT"
            self._phase_start = now

        if self._state == "WARN_PULSE_WAIT" and elapsed >= _TAP_HOLD_MS:
            self.set_angle(config.SERVO_LEFT_TAP)
            self._state = "WARN_PULSE_LEFT"
            self._phase_start = now
            return

        if self._state == "WARN_PULSE_LEFT" and elapsed >= 150:
            self.set_angle(config.SERVO_RIGHT_TAP)
            self._state = "WARN_PULSE_RIGHT"
            self._phase_start = now
            return

        if self._state == "WARN_PULSE_RIGHT" and elapsed >= 150:
            self.neutral()
            return

        if self._state == "DANGER_PULSE_MOVE" and elapsed >= 100:
            self.neutral()
            self._state = "DANGER_PULSE_RETURN"
            self._phase_start = now
            return

        if self._state == "DANGER_PULSE_RETURN" and elapsed >= 100:
            self._pulse_count += 1
            if self._pulse_count >= 3:
                self.neutral()
                return
            self.set_angle(config.SERVO_RIGHT_TAP)
            self._state = "DANGER_PULSE_MOVE"
            self._phase_start = now
            return

    def deinit(self):
        self._pwm.deinit()

    def _start_single_tap(self):
        self.set_angle(self._tap_target)
        self._state = "TAP_MOVE"
        self._phase_start = utime.ticks_ms()
