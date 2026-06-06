# config.py
# Central pin, bus, and address configuration for the STM32G474RE
# MicroPython hardware framework.
#
# Use CPU pin names instead of Arduino header labels because MicroPython on
# STM32 reliably resolves names like 'PA8' and 'PB10'.

# ---------------------------------------------------------------------------
# I2C bus
# ---------------------------------------------------------------------------
I2C_ID = 1
I2C_BUS = I2C_ID
I2C_FREQ = 400_000
I2C_SCL_PIN = "PB8"
I2C_SDA_PIN = "PB9"

# ---------------------------------------------------------------------------
# I2C device addresses (7-bit)
# ---------------------------------------------------------------------------
MPU6050_ADDR = 0x68
MCP9808_ADDR = 0x18
HT16K33_ADDR = 0x70

# ---------------------------------------------------------------------------
# HC-SR04 ultrasonic sensor
# ---------------------------------------------------------------------------
HCSR04_TRIG_PIN = "PA8"
HCSR04_ECHO_PIN = "PA9"
HCSR04_TIMEOUT_US = 30_000
HCSR04_CYCLE_MS = 60
ULTRASONIC_SAMPLE_INTERVAL_MS = 150
SMOOTHING_WINDOW = 5

# ---------------------------------------------------------------------------
# SG90 servo / haptic feedback
# ---------------------------------------------------------------------------
SG90_PWM_PIN = "PB10"
SERVO_PIN = SG90_PWM_PIN
SG90_FREQ_HZ = 50
SERVO_FREQ_HZ = SG90_FREQ_HZ
SG90_MIN_US = 500
SG90_MID_US = 1500
SG90_MAX_US = 2400
SERVO_MIN_US = SG90_MIN_US
SERVO_MID_US = SG90_MID_US
SERVO_MAX_US = SG90_MAX_US
SERVO_NEUTRAL = 90
SERVO_LEFT_TAP = 60
SERVO_RIGHT_TAP = 120
WARNING_TAP_INTERVAL_MS = 400
DANGER_TAP_INTERVAL_MS = 120

# ---------------------------------------------------------------------------
# Speaker
# ---------------------------------------------------------------------------
SPEAKER_PIN = "PB4"

# ---------------------------------------------------------------------------
# IMU
# ---------------------------------------------------------------------------
IMU_GYRO_FS = 250
IMU_CALIBRATION_MS = 2000
IMU_SAMPLE_INTERVAL_MS = 20
CALIBRATION_SAMPLES = IMU_CALIBRATION_MS // IMU_SAMPLE_INTERVAL_MS

# ---------------------------------------------------------------------------
# Route / app
# ---------------------------------------------------------------------------
HEADING_TOLERANCE_DEG = 15
LOOP_PERIOD_MS = 20
FINISH_SUCCESS_PATTERN = False

# Legacy obstacle thresholds kept for compatibility with older code paths.
WARNING_DISTANCE_CM = 75
DANGER_DISTANCE_CM = 40
