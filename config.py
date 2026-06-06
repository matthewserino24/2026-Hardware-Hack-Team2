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
