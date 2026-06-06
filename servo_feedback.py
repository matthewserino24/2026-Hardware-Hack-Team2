# ---------------------------------------------------------------------------
# servo_feedback.py — SG90 haptic feedback layer
# Target: STM32G4 Nucleo-64 (NUCLEO-G474RE) running MicroPython
# ---------------------------------------------------------------------------
#
# HARDWARE
# --------
#   SG90 servo:  50 Hz PWM, pulse width 500 µs – 2 400 µs
#     500 µs  →   0°  (full clockwise)
#    1500 µs  →  90°  (neutral / centre)
#    2400 µs  → 180°  (full counter-clockwise)
#   Signal wire (orange) → any timer-capable GPIO (e.g. PA0 / D1 on Nucleo)
#   Power (red)  → 5 V rail (NOT 3.3 V — servo stalls below 4.8 V)
#   Ground (brown) → GND
#
# API OVERVIEW
# ------------
#   fb = ServoFeedback(machine.Pin("PA0"))
#   fb.neutral()                    # hold centre, no motion
#   fb.tap_left()                   # single left tap then return to neutral
#   fb.tap_right()                  # single right tap then return to neutral
#   fb.warning_pattern(distance_cm) # scaled tap cadence, 75 cm → 40 cm
#   fb.danger_pattern()             # rapid alternating left↔right taps
#   fb.stop()                       # cancel any running pattern, go neutral
#
#   Call fb.tick() from a periodic timer ISR or a tight main-loop poll.
#   tick() is the only function that actually moves the servo; all other
#   methods just update the state machine and return immediately (non-blocking).
#
# TICK CADENCE
# ------------
#   tick() must be called at least as often as DANGER_TAP_INTERVAL_MS / 2
#   (i.e. ≥ every 60 ms for the default 120 ms danger interval).
#   A 10 ms timer is recommended — it gives smooth timing without busy-waiting.
#
#   Example wiring with machine.Timer:
#       import machine
#       timer = machine.Timer()
#       timer.init(period=10, mode=machine.Timer.PERIODIC,
#                  callback=fb.tick)
#
# NON-BLOCKING DESIGN
# -------------------
#   The class implements a flat state machine with nine states.  Each call to
#   tick() checks elapsed time (utime.ticks_ms) and advances the state when
#   the current phase has run long enough.  No utime.sleep() calls are used
#   anywhere inside the class so the caller's thread / main loop is never
#   blocked.
#
#   State diagram:
#
#   IDLE ──tap_left/right──► TAP_MOVE ──► TAP_HOLD ──► TAP_RETURN ──► IDLE
#
#   IDLE ──warning_pattern──► WARN_WAIT ──► WARN_MOVE ──► WARN_HOLD
#                                 ▲                              │
#                                 └──────── WARN_RETURN ◄────────┘
#
#   IDLE ──danger_pattern──► DANGER_MOVE ──► DANGER_HOLD ──► DANGER_RETURN
#                                 ▲                                  │
#                                 └──────── DANGER_WAIT ◄────────────┘
#
# ---------------------------------------------------------------------------

import utime
from machine import PWM

import config

# ---------------------------------------------------------------------------
# SG90 pulse-width constants (nanoseconds)
# ---------------------------------------------------------------------------
_PULSE_MIN_NS   = 500_000    #  500 µs →   0°
_PULSE_MAX_NS   = 2_400_000  # 2400 µs → 180°
_PULSE_RANGE_NS = _PULSE_MAX_NS - _PULSE_MIN_NS  # 1 900 000 ns across 180°

# How long the servo dwells at the tap position before returning (ms).
# 60 ms is long enough for the wrist to register the tap but short enough
# not to dominate the inter-tap interval even at DANGER_TAP_INTERVAL_MS=120.
_TAP_HOLD_MS = 60

# ---------------------------------------------------------------------------
# State-machine states  (module-level constants; const() folds to int)
# ---------------------------------------------------------------------------
_ST_IDLE         = const(0)   # Neutral, no pattern running
_ST_TAP_MOVE     = const(1)   # Single tap: moving to tap position
_ST_TAP_HOLD     = const(2)   # Single tap: dwelling at tap position
_ST_TAP_RETURN   = const(3)   # Single tap: returning to neutral → IDLE
_ST_WARN_WAIT    = const(4)   # Warning:    waiting between taps
_ST_WARN_MOVE    = const(5)   # Warning:    moving to tap position
_ST_WARN_HOLD    = const(6)   # Warning:    dwelling at tap position
_ST_WARN_RETURN  = const(7)   # Warning:    returning to neutral → WARN_WAIT
_ST_DANGER_MOVE  = const(8)   # Danger:     moving to tap position
_ST_DANGER_HOLD  = const(9)   # Danger:     dwelling at tap position
_ST_DANGER_RETURN= const(10)  # Danger:     returning to neutral
_ST_DANGER_WAIT  = const(11)  # Danger:     waiting between taps → DANGER_MOVE


def _angle_to_ns(deg):
    """Map 0–180° to SG90 pulse width in nanoseconds.

    Uses integer arithmetic throughout; clamps input to [0, 180] so
    out-of-range angles never damage the servo mechanically.

    Mapping:
        0°   → 500 000 ns  (500 µs)
        90°  → 1 450 000 ns (≈1.45 ms, close to the 1.5 ms centre)
        180° → 2 400 000 ns (2400 µs)
    """
    deg = max(0, min(180, deg))
    return _PULSE_MIN_NS + (_PULSE_RANGE_NS * deg) // 180


class ServoFeedback:
    """Non-blocking SG90 haptic feedback driver for wrist navigation.

    Parameters
    ----------
    pwm_pin : machine.Pin
        A Pin object for the servo signal line.  The pin must be connected
        to a timer channel capable of PWM output on the STM32G4 (e.g. PA0,
        which maps to TIM2_CH1 — a 32-bit timer, giving fine ns resolution
        at 50 Hz).
    """

    def __init__(self, pwm_pin):
        # Initialise PWM at 50 Hz.  duty_ns is used throughout because it
        # maps directly to servo pulse width without floating-point arithmetic.
        self._pwm = PWM(pwm_pin, freq=50)
        self._write_duty_ns = self._pwm.duty_ns

        # State machine
        self._state           = _ST_IDLE
        self._phase_start     = 0     # utime.ticks_ms() when current phase began
        self._tap_target      = config.SERVO_NEUTRAL
        self._danger_side     = 0     # 0 = left next, 1 = right next
        self._warn_interval_ms = config.WARNING_TAP_INTERVAL_MS

        # Drive to neutral immediately on construction so the servo does not
        # twitch to an unknown position on power-up.
        self._write_angle(config.SERVO_NEUTRAL)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def neutral(self):
        """Hold the servo at SERVO_NEUTRAL.  Cancels any running pattern."""
        self._state = _ST_IDLE
        self._write_angle(config.SERVO_NEUTRAL)

    def stop(self):
        """Alias for neutral() — cancel pattern and centre the servo."""
        self.neutral()

    def tap_left(self):
        """Execute a single left tap then return to neutral (non-blocking).

        Immediately writes the tap angle; tick() drives the hold and return.
        """
        self._tap_target = config.SERVO_LEFT_TAP
        self._start_single_tap()

    def tap_right(self):
        """Execute a single right tap then return to neutral (non-blocking).

        Immediately writes the tap angle; tick() drives the hold and return.
        """
        self._tap_target = config.SERVO_RIGHT_TAP
        self._start_single_tap()

    def warning_pattern(self, distance_cm):
        """Start a repeating bilateral tap pattern whose cadence scales with distance.

        Cadence interpolation:
            75 cm → WARNING_TAP_INTERVAL_MS  (slow)
            40 cm → DANGER_TAP_INTERVAL_MS   (fast)
            Outside this range the interval is clamped.

        If the warning pattern is already running, only the interval is
        updated so the pattern continues smoothly without a restart.

        Parameters
        ----------
        distance_cm : float | int
            Current obstacle distance in centimetres.
        """
        warn_ms   = config.WARNING_TAP_INTERVAL_MS
        danger_ms = config.DANGER_TAP_INTERVAL_MS

        # Linear interpolation: t=0 at 75 cm (slow), t=1 at 40 cm (fast).
        t = (75.0 - float(distance_cm)) / (75.0 - 40.0)
        t = max(0.0, min(1.0, t))
        interval_ms = int(warn_ms + t * (danger_ms - warn_ms))

        # If already in warning mode, update interval and return — no restart.
        if self._state in (_ST_WARN_WAIT, _ST_WARN_MOVE,
                           _ST_WARN_HOLD, _ST_WARN_RETURN):
            self._warn_interval_ms = interval_ms
            return

        # Start fresh warning pattern from the wait state.
        self._warn_interval_ms = interval_ms
        self._danger_side = 0
        self._state = _ST_WARN_WAIT
        self._phase_start = utime.ticks_ms()

    def danger_pattern(self):
        """Start rapid alternating left↔right taps at DANGER_TAP_INTERVAL_MS.

        Idempotent: calling while already in danger mode is a no-op so the
        pattern is not reset mid-cycle.
        """
        if self._state in (_ST_DANGER_MOVE, _ST_DANGER_HOLD,
                           _ST_DANGER_RETURN, _ST_DANGER_WAIT):
            return  # already running — do not restart

        self._danger_side = 0
        self._write_angle(config.SERVO_LEFT_TAP)
        self._state = _ST_DANGER_MOVE
        self._phase_start = utime.ticks_ms()

    def tick(self, timer=None):
        """Advance the state machine.  Call this periodically (≤ 60 ms apart).

        Safe to call from a MicroPython timer ISR on STM32 — no heap
        allocation, no blocking calls, no floating-point in the hot path.
        """
        now     = utime.ticks_ms()
        elapsed = utime.ticks_diff(now, self._phase_start)
        state   = self._state

        # ---- IDLE --------------------------------------------------------
        if state == _ST_IDLE:
            return

        # ---- Single-tap sequence -----------------------------------------
        # TAP_MOVE: servo is moving toward tap position; wait for travel time.
        elif state == _ST_TAP_MOVE:
            if elapsed >= _TAP_HOLD_MS:
                self._state = _ST_TAP_HOLD
                self._phase_start = now

        # TAP_HOLD: servo is at tap position; dwell then return to neutral.
        elif state == _ST_TAP_HOLD:
            if elapsed >= _TAP_HOLD_MS:
                self._write_angle(config.SERVO_NEUTRAL)
                self._state = _ST_TAP_RETURN
                self._phase_start = now

        # TAP_RETURN: servo is returning to neutral; then go IDLE.
        elif state == _ST_TAP_RETURN:
            if elapsed >= _TAP_HOLD_MS:
                self._state = _ST_IDLE

        # ---- Warning pattern sequence ------------------------------------
        # WARN_WAIT: inter-tap pause; fire next tap when interval expires.
        elif state == _ST_WARN_WAIT:
            if elapsed >= self._warn_interval_ms:
                if self._danger_side == 0:
                    self._write_angle(config.SERVO_LEFT_TAP)
                    self._danger_side = 1
                else:
                    self._write_angle(config.SERVO_RIGHT_TAP)
                    self._danger_side = 0
                self._state = _ST_WARN_MOVE
                self._phase_start = now

        # WARN_MOVE: servo is moving to tap position.
        elif state == _ST_WARN_MOVE:
            if elapsed >= _TAP_HOLD_MS:
                self._state = _ST_WARN_HOLD
                self._phase_start = now

        # WARN_HOLD: servo is at tap position; dwell then return.
        elif state == _ST_WARN_HOLD:
            if elapsed >= _TAP_HOLD_MS:
                self._write_angle(config.SERVO_NEUTRAL)
                self._state = _ST_WARN_RETURN
                self._phase_start = now

        # WARN_RETURN: servo returning to neutral; loop back to WARN_WAIT.
        elif state == _ST_WARN_RETURN:
            if elapsed >= _TAP_HOLD_MS:
                self._state = _ST_WARN_WAIT
                self._phase_start = now

        # ---- Danger pattern sequence -------------------------------------
        # DANGER_MOVE: servo is moving to tap position.
        elif state == _ST_DANGER_MOVE:
            if elapsed >= _TAP_HOLD_MS:
                self._state = _ST_DANGER_HOLD
                self._phase_start = now

        # DANGER_HOLD: servo is at tap position; dwell then return.
        elif state == _ST_DANGER_HOLD:
            if elapsed >= _TAP_HOLD_MS:
                self._write_angle(config.SERVO_NEUTRAL)
                self._state = _ST_DANGER_RETURN
                self._phase_start = now

        # DANGER_RETURN: servo returning to neutral; then wait.
        elif state == _ST_DANGER_RETURN:
            if elapsed >= _TAP_HOLD_MS:
                self._state = _ST_DANGER_WAIT
                self._phase_start = now

        # DANGER_WAIT: inter-tap pause; fire next tap when interval expires.
        elif state == _ST_DANGER_WAIT:
            if elapsed >= config.DANGER_TAP_INTERVAL_MS:
                if self._danger_side == 0:
                    self._write_angle(config.SERVO_LEFT_TAP)
                    self._danger_side = 1
                else:
                    self._write_angle(config.SERVO_RIGHT_TAP)
                    self._danger_side = 0
                self._state = _ST_DANGER_MOVE
                self._phase_start = now

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _write_angle(self, deg):
        """Write a servo angle (0–180°) via duty_ns.  No allocation."""
        self._write_duty_ns(_angle_to_ns(deg))

    def _start_single_tap(self):
        """Begin the single-tap sub-sequence (move → hold → return → idle)."""
        self._write_angle(self._tap_target)
        self._state = _ST_TAP_MOVE
        self._phase_start = utime.ticks_ms()
