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
# Target: STM32G4 Nucleo-64 (NUCLEO-G474RE) running MicroPython
#
# Pin mapping reference (NUCLEO-G474RE Arduino header):
#   I2C_SDA  → D14 → PB9
#   I2C_SCL  → D15 → PB8
#   HC-SR04 TRIG → D7  → PA8
#   HC-SR04 ECHO → D8  → PA9
#   SG90 PWM     → D6  → PB10  (TIM2_CH3)
#   Speaker      → D5  → PB4
#
# I2C device addresses (7-bit):
#   MPU-6050  : 0x68  (AD0 tied low)
#   MCP9808   : 0x18  (A2=A1=A0=0)
#   HT16K33   : 0x70  (A2=A1=A0=0)
#
# All tunable values live here. Modules import only the names they need.

# ---------------------------------------------------------------------------
# I2C bus (shared by MPU-6050, MCP9808, HT16K33)
# ---------------------------------------------------------------------------
I2C_ID      = 1          # STM32G4 I2C peripheral index → I2C1
I2C_BUS     = 1          # alias used by some modules
I2C_SCL_PIN = 'PB8'     # Arduino D15 / morpho CN10-3
I2C_SDA_PIN = 'PB9'     # Arduino D14 / morpho CN10-5
I2C_FREQ    = 400_000   # 400 kHz Fast-mode (all devices support it)

# ---------------------------------------------------------------------------
# I2C device addresses (7-bit)
# ---------------------------------------------------------------------------
MPU6050_ADDR = 0x68   # AD0 tied low (default)
MCP9808_ADDR = 0x18   # A2=A1=A0=0
HT16K33_ADDR = 0x70   # A2=A1=A0=0

# ---------------------------------------------------------------------------
# MPU-6050 (IMU) — FR1
# ---------------------------------------------------------------------------
IMU_GYRO_FS         = 250    # Full-scale ±250 °/s  (register FS_SEL = 0)
IMU_CALIBRATION_MS  = 2000   # Stationary calibration window at startup (ms)

# Derived: sample interval used by calibrate() inner loop and main loop tick.
# 50 Hz → 20 ms.  Must match SMPLRT_DIV setting in imu.py (_configure).
IMU_SAMPLE_INTERVAL_MS = 20

# Number of calibration samples collected during calibrate().
# IMU_CALIBRATION_MS / IMU_SAMPLE_INTERVAL_MS = 2000 / 20 = 100 samples.
CALIBRATION_SAMPLES = IMU_CALIBRATION_MS // IMU_SAMPLE_INTERVAL_MS

# ---------------------------------------------------------------------------
# HC-SR04 (Ultrasonic distance) — FR2 / FR3
# ---------------------------------------------------------------------------
HCSR04_TRIG_PIN           = 'D7'    # PA8 – GPIO output, 10 µs trigger pulse
HCSR04_ECHO_PIN           = 'D8'    # PA9 – GPIO input, echo pulse width ∝ distance
HCSR04_TIMEOUT_US         = 30_000  # 30 ms → ~510 cm max; avoids blocking
HCSR04_CYCLE_MS           = 60      # Minimum inter-measurement interval (datasheet)
TRIG_PIN                  = 'PA8'   # alternate alias (board pin name)
ECHO_PIN                  = 'PA9'   # alternate alias (board pin name)
OBSTACLE_DIST_CM          = 40      # Closer than this → OBSTACLE state
WARNING_DISTANCE_CM       = 75      # > this → CLEAR; ≤ this and > DANGER → WARNING
DANGER_DISTANCE_CM        = 40      # ≤ this → DANGER (overrides waypoint guidance)
ULTRASONIC_SAMPLE_INTERVAL_MS = 150 # Main-loop ultrasonic poll period (ms)
SMOOTHING_WINDOW          = 5       # Rolling-average window size (readings)

# ---------------------------------------------------------------------------
# SG90 Servo (haptic feedback) — FR6
# ---------------------------------------------------------------------------
SG90_PWM_PIN         = 'D6'    # PB10 – TIM2_CH3
SG90_FREQ_HZ         = 50      # 20 ms period (standard RC servo)
SG90_MIN_US          = 500     # Pulse width for −90° (full left)
SG90_MID_US          = 1500    # Pulse width for   0° (centre / neutral)
SG90_MAX_US          = 2400    # Pulse width for +90° (full right)
SERVO_PIN            = 'D6'    # alias used by servo_feedback.py
SERVO_FREQ_HZ        = 50      # alias
SERVO_NEUTRAL        = 90      # Centre position in degrees
SERVO_LEFT_TAP       = 60      # Left-wrist tap excursion (degrees)
SERVO_RIGHT_TAP      = 120     # Right-wrist tap excursion (degrees)
SERVO_NEUTRAL_US     = 1500    # Centre pulse width (µs)
SERVO_LEFT_US        = 2000    # ~+90° pulse width (µs)
SERVO_RIGHT_US       = 1000    # ~-90° pulse width (µs)
SERVO_TAP_MS         = 200     # Duration of each haptic tap pulse (ms)
SERVO_TAP_PERIOD_MS  = 600     # Time between tap pulses (ms)
WARNING_TAP_INTERVAL_MS = 400  # Tap cadence at warning boundary ~75 cm (ms)
DANGER_TAP_INTERVAL_MS  = 120  # Tap cadence at danger boundary ~40 cm (ms)

# ---------------------------------------------------------------------------
# STEMMA speaker (PAM8302A class-D amp)
# ---------------------------------------------------------------------------
SPEAKER_PIN = 'D5'   # PB4 – PWM tone output

# ---------------------------------------------------------------------------
# Route / waypoint state machine — FR4 / FR5
# ---------------------------------------------------------------------------
HEADING_TOLERANCE_DEG = 15     # ±15° band to consider a turn complete

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
LOOP_PERIOD_MS = 20            # 50 Hz control loop (matches IMU_SAMPLE_INTERVAL_MS)

# ---------------------------------------------------------------------------
# Optional finish pattern
# ---------------------------------------------------------------------------
FINISH_SUCCESS_PATTERN = False  # Set True to enable celebratory servo sweep
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
