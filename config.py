# config.py — Project-wide configuration constants
# Target: STM32G4 Nucleo-64 (NUCLEO-G474RE), MicroPython
#
# Each FR adds its own section here.  Do not scatter magic numbers in modules.

# ---------------------------------------------------------------------------
# Obstacle-detection thresholds (FR3)
# ---------------------------------------------------------------------------
WARNING_DISTANCE_CM = 75   # > this → CLEAR; ≤ this and > DANGER → WARNING
DANGER_DISTANCE_CM  = 40   # ≤ this → DANGER (overrides waypoint guidance)

# ---------------------------------------------------------------------------
# HC-SR04 ultrasonic sensor (FR2)
# ---------------------------------------------------------------------------
HCSR04_TRIG_PIN          = "D7"    # GPIO output – 10 µs trigger pulse
HCSR04_ECHO_PIN          = "D8"    # GPIO input  – echo pulse width ∝ distance
HCSR04_TIMEOUT_US        = 30_000  # 30 ms → ~510 cm max; avoids blocking
HCSR04_CYCLE_MS          = 60      # Minimum inter-measurement interval (datasheet)
ULTRASONIC_SAMPLE_INTERVAL_MS = 150  # Main-loop ultrasonic poll period (ms)
SMOOTHING_WINDOW         = 5       # Rolling-average window for distance readings

# ---------------------------------------------------------------------------
# SG90 servo / haptic feedback (FR6)
# ---------------------------------------------------------------------------
SERVO_PIN            = "D9"    # PWM-capable pin (TIM1_CH1 on PA8 / Arduino D9)
SERVO_FREQ_HZ        = 50      # 20 ms period – standard servo PWM
SERVO_MIN_US         = 500     # Pulse width for −90° (full left)
SERVO_MID_US         = 1500    # Pulse width for   0° (centre / neutral)
SERVO_MAX_US         = 2400    # Pulse width for +90° (full right)
SERVO_NEUTRAL        = 90      # Centre angle (degrees)
SERVO_LEFT_TAP       = 60      # Left-wrist tap excursion  (tune on body)
SERVO_RIGHT_TAP      = 120     # Right-wrist tap excursion (tune on body)
WARNING_TAP_INTERVAL_MS = 400  # Tap cadence at the warning boundary (75 cm)
DANGER_TAP_INTERVAL_MS  = 120  # Tap cadence at the danger boundary  (40 cm)

# ---------------------------------------------------------------------------
# MPU-6050 IMU (FR1) — I²C, AD0 pin = GND → address 0x68
# ---------------------------------------------------------------------------
MPU6050_ADDR           = 0x68
I2C_BUS                = 1     # I²C1 on Arduino header (PB8=SCL, PB9=SDA)
I2C_ID                 = I2C_BUS   # alias used by imu.py
I2C_FREQ               = 400_000   # 400 kHz Fast-mode
IMU_GYRO_FS            = 250       # Full-scale ±250 °/s (FS_SEL = 0)
IMU_CALIBRATION_MS     = 2000      # Stationary calibration window (ms)
IMU_SAMPLE_INTERVAL_MS = 20    # Gyro integration period (ms); matches SMPLRT_DIV
CALIBRATION_SAMPLES    = IMU_CALIBRATION_MS // IMU_SAMPLE_INTERVAL_MS  # 100

# ---------------------------------------------------------------------------
# Route / waypoint state machine (FR4 + FR5)
# ---------------------------------------------------------------------------
HEADING_TOLERANCE_DEG = 15     # ±15° band to consider a TURN waypoint complete

# ---------------------------------------------------------------------------
# Main-loop timing
# ---------------------------------------------------------------------------
LOOP_PERIOD_MS = 20            # 50 Hz control loop (matches IMU_SAMPLE_INTERVAL_MS)

# ---------------------------------------------------------------------------
# Optional: play a success pattern on FINISH instead of plain neutral
# ---------------------------------------------------------------------------
FINISH_SUCCESS_PATTERN = False  # set True to enable celebratory servo sweep
