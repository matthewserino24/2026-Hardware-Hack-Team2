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
