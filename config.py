# config.py
# Central pin and bus configuration for the 2026 Hardware Hack Team2 project.
# Target: STM32 Nucleo-G474RE running MicroPython v1.28+
#
# Pin mapping reference (from NUCLEO_G474RE/pins.csv):
#   I2C_SDA -> D14 -> PB9
#   I2C_SCL -> D15 -> PB8
#   HC-SR04 TRIG -> D7  -> PA8
#   HC-SR04 ECHO -> D8  -> PA9
#   SG90 PWM     -> D6  -> PB10  (TIM2_CH3 capable)
#   STEMMA audio -> D5  -> PB4   (PWM / DAC-routed analog signal)
#
# All I2C devices share the single hardware I2C bus (I2C1 on PB8/PB9).
# I2C addresses (7-bit):
#   MPU-6050  : 0x68  (AD0 pin tied low)
#   MCP9808   : 0x18  (A2=A1=A0=0)
#   HT16K33   : 0x70  (A2=A1=A0=0, 28-pin package base addr 0b1110_000)

# ---------------------------------------------------------------------------
# I2C bus
# ---------------------------------------------------------------------------
I2C_ID  = 1        # pyb.I2C(1) -> SCL=PB8, SDA=PB9
I2C_FREQ = 400_000  # 400 kHz Fast-mode (all three devices support it)

# ---------------------------------------------------------------------------
# HC-SR04 ultrasonic sensor
# ---------------------------------------------------------------------------
HCSR04_TRIG_PIN = 'D7'   # PA8 – GPIO output, 10 µs pulse
HCSR04_ECHO_PIN = 'D8'   # PA9 – GPIO input, measure high-pulse duration

# ---------------------------------------------------------------------------
# SG90 servo motor
# ---------------------------------------------------------------------------
# 50 Hz PWM (20 ms period).  Pulse width: 500 µs (−90°) … 2400 µs (+90°)
SG90_PWM_PIN    = 'D6'   # PB10 – TIM2 CH3
SG90_FREQ_HZ    = 50
SG90_MIN_US     = 500    # pulse width for −90°
SG90_MID_US     = 1500   # pulse width for   0° (centre)
SG90_MAX_US     = 2400   # pulse width for +90°

# ---------------------------------------------------------------------------
# STEMMA speaker (PAM8302A class-D amp, AC-coupled input)
# ---------------------------------------------------------------------------
# Drive with PWM tone on D5 (PB4).  The amp accepts 0–3 V signal; the
# STM32 GPIO high level is 3.3 V which is within spec.
SPEAKER_PIN     = 'D5'   # PB4

# ---------------------------------------------------------------------------
# I2C device addresses (7-bit)
# ---------------------------------------------------------------------------
MPU6050_ADDR  = 0x68
MCP9808_ADDR  = 0x18
HT16K33_ADDR  = 0x70
