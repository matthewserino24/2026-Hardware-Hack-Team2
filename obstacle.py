# obstacle.py — Obstacle-detection state classifier (FR3)
# Target: STM32G4 Nucleo-64 (NUCLEO-G474RE), MicroPython
#
# Implements §3 of the requirements document:
#
#   distance_cm > WARNING_DISTANCE_CM  →  'CLEAR'
#   DANGER_DISTANCE_CM < distance_cm
#                      ≤ WARNING_DISTANCE_CM  →  'WARNING'
#   distance_cm ≤ DANGER_DISTANCE_CM   →  'DANGER'
#
# A None reading (missed echo / sensor timeout) is treated as CLEAR so that
# transient dropouts do not trigger false obstacle alerts (§3 note).
#
# This module is intentionally pure-logic with no hardware dependencies so
# that it can be unit-tested on the host without a connected board.

from config import WARNING_DISTANCE_CM, DANGER_DISTANCE_CM

# Public state constants – use these instead of bare strings so callers can
# do identity comparisons (``state is CLEAR``) as well as equality checks.
CLEAR   = 'CLEAR'
WARNING = 'WARNING'
DANGER  = 'DANGER'


def obstacle_state(distance_cm):
    """Classify a distance reading into one of CLEAR / WARNING / DANGER.

    Parameters
    ----------
    distance_cm : float | int | None
        Distance returned by the ultrasonic driver.  Pass None when the
        sensor did not produce a valid echo (timeout / out-of-range); this
        is treated as CLEAR to avoid false alarms on missed readings.

    Returns
    -------
    str
        One of the module-level constants ``CLEAR``, ``WARNING``, or
        ``DANGER``.

    Boundary rules (closed/open intervals matching §3):
        distance_cm is None          → CLEAR
        distance_cm > 75 cm          → CLEAR
        40 cm < distance_cm ≤ 75 cm  → WARNING
        distance_cm ≤ 40 cm          → DANGER
    """
    # Missed echo → treat as no obstacle (do not false-alarm)
    if distance_cm is None:
        return CLEAR

    # DANGER takes priority over WARNING; check it first so the boundary
    # value (exactly DANGER_DISTANCE_CM) maps to DANGER, not WARNING.
    if distance_cm <= DANGER_DISTANCE_CM:
        return DANGER

    if distance_cm <= WARNING_DISTANCE_CM:
        return WARNING

    return CLEAR
