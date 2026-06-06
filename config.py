# config.py — Project-wide configuration constants
# Target: STM32G4 Nucleo-64 (NUCLEO-G474RE), MicroPython
#
# Each subsystem owner adds their own section here so that merge conflicts
# are localised to the relevant lines.

# ---------------------------------------------------------------------------
# Obstacle-detection thresholds  (FR3 — obstacle.py)
# ---------------------------------------------------------------------------
# §3 of the requirements document:
#   distance_cm > WARNING_DISTANCE_CM  →  CLEAR   (follow waypoint guidance)
#   DANGER_DISTANCE_CM < distance_cm
#                      ≤ WARNING_DISTANCE_CM  →  WARNING  (warning_pattern)
#   distance_cm ≤ DANGER_DISTANCE_CM   →  DANGER  (danger_pattern, overrides)
WARNING_DISTANCE_CM = 75   # cm — upper edge of the WARNING band
DANGER_DISTANCE_CM  = 40   # cm — DANGER threshold (inclusive)
# ---------------------------------------------------------------------------
# config.py — Project-wide tunable constants
# ---------------------------------------------------------------------------
# All servo angles are in degrees (0–180).  Adjust SERVO_* values on the
# body without touching servo_feedback.py.

# --- Servo haptic feedback (FR6) -------------------------------------------
SERVO_NEUTRAL        = 90   # Centre position; no haptic stimulus
SERVO_LEFT_TAP       = 60   # Left-wrist tap excursion  (tune on body)
SERVO_RIGHT_TAP      = 120  # Right-wrist tap excursion (tune on body)

WARNING_TAP_INTERVAL_MS = 400   # Tap cadence at the warning boundary (75 cm)
DANGER_TAP_INTERVAL_MS  = 120   # Tap cadence at the danger boundary  (40 cm)
"""
config.py — Project-wide configuration constants for the wrist-mounted
navigation prototype (STM32G4 / MicroPython).

Add new constants here rather than scattering magic numbers through modules.
"""

# ---------------------------------------------------------------------------
# Ultrasonic distance sensor (HC-SR04)  — FR2
# ---------------------------------------------------------------------------

# Minimum time between successive distance measurements (milliseconds).
# The HC-SR04 datasheet recommends ≥ 60 ms per cycle to prevent the outgoing
# trigger pulse from interfering with the returning echo.  150 ms gives
# comfortable headroom and a ~6 Hz update rate suitable for navigation.
ULTRASONIC_SAMPLE_INTERVAL_MS: int = 150

# Number of valid (non-None) readings kept in the rolling average window.
# Larger values smooth out more noise but increase latency to step changes.
# 5 readings × 150 ms/reading = 750 ms worst-case lag on a sudden change.
SMOOTHING_WINDOW: int = 5
