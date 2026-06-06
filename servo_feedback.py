# servo_feedback.py
# SG90 micro-servo driver with haptic-style feedback patterns.
#
# Hardware notes (SG90 datasheet):
#   - Signal: 50 Hz PWM (20 ms period)
#   - Pulse width: 500 µs (−90°) … 1500 µs (0°) … 2400 µs (+90°)
#   - Dead-band: 10 µs — do not update faster than the servo can respond
#   - Operating voltage: 4.8 V (use a separate 5 V rail, not MCU 3.3 V)
#   - Current: up to 500 mA stall — must NOT be powered from MCU pin
#
# STM32G4 PWM:
#   machine.PWM(pin, freq=50) uses a hardware timer channel.
#   duty_ns() sets the on-time in nanoseconds (MicroPython ≥1.20).
#
# Angle convention:
#   0°   → centre (1500 µs)
#   +90° → full right (2400 µs)
#   −90° → full left  ( 500 µs)
#
# Feedback patterns:
#   warning_pulse()  – single 20° sweep left/right (non-blocking via state)
#   danger_pattern() – rapid 3× centre→right→centre sweep
#   neutral()        – return to 0° and hold
#
# Usage::
#
#     from machine import Pin
#     from servo_feedback import ServoFeedback
#
#     servo = ServoFeedback('PA0')
#     servo.set_angle(45)
#     servo.neutral()

import utime
from machine import Pin, PWM

# SG90 pulse width limits (nanoseconds)
_PULSE_MIN_NS  =  500_000   # −90°  (500 µs)
_PULSE_MID_NS  = 1_500_000  #   0°  (1500 µs)
_PULSE_MAX_NS  = 2_400_000  # +90°  (2400 µs)
_PWM_FREQ_HZ   = 50         # 20 ms period

# Derived: ns per degree
_NS_PER_DEG    = (_PULSE_MAX_NS - _PULSE_MIN_NS) / 180.0   # ≈ 10 555 ns/°


def _angle_to_ns(angle_deg):
    """Convert angle (−90 … +90) to pulse width in nanoseconds."""
    angle_deg = max(-90.0, min(90.0, float(angle_deg)))
    return int(_PULSE_MID_NS + angle_deg * _NS_PER_DEG)


class ServoFeedback:
    """
    SG90 servo driver with blocking feedback sweep patterns.

    Parameters
    ----------
    pin : str or int
        PWM-capable pin name (e.g. 'PA0', 'D3').
    """

    def __init__(self, pin):
        self._pwm = PWM(Pin(pin), freq=_PWM_FREQ_HZ)
        self._angle = 0.0
        self.neutral()

    # ------------------------------------------------------------------
    # Basic control
    # ------------------------------------------------------------------

    def set_angle(self, angle_deg):
        """
        Move servo to angle_deg (−90 … +90).

        Parameters
        ----------
        angle_deg : float  Target angle in degrees.
        """
        self._angle = max(-90.0, min(90.0, float(angle_deg)))
        self._pwm.duty_ns(_angle_to_ns(self._angle))

    def neutral(self):
        """Return servo to centre position (0°)."""
        self.set_angle(0.0)

    @property
    def angle(self):
        """Current commanded angle in degrees."""
        return self._angle

    # ------------------------------------------------------------------
    # Feedback patterns (blocking — keep durations short)
    # ------------------------------------------------------------------

    def warning_pulse(self):
        """
        Single left/right sweep to signal a WARNING condition.
        Total duration: ~300 ms.
        """
        self.set_angle(-20.0)
        utime.sleep_ms(150)
        self.set_angle(20.0)
        utime.sleep_ms(150)
        self.neutral()

    def danger_pattern(self):
        """
        Rapid 3× centre→right→centre sweep to signal DANGER.
        Total duration: ~600 ms.
        """
        for _ in range(3):
            self.set_angle(45.0)
            utime.sleep_ms(100)
            self.neutral()
            utime.sleep_ms(100)

    def steer(self, heading_error_deg):
        """
        Proportional steering: map heading error to servo angle.

        A positive heading_error means the target is to the right;
        the servo deflects right to steer toward it.

        Parameters
        ----------
        heading_error_deg : float
            Signed heading error in degrees (target − current).
            Clamped to ±90° servo range.
        """
        self.set_angle(heading_error_deg)

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def deinit(self):
        """Release the PWM timer channel."""
        self._pwm.deinit()
