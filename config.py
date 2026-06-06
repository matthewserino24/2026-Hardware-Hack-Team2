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
