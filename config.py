# config.py
# Central pin / bus / address configuration for the 2026 Hardware Hack Team2
# wrist-navigation prototype.  Target: NUCLEO-G474RE running MicroPython.
#
# IMPORTANT — pin names:
#   The MicroPython STM32 port resolves *CPU* pin names ('PA8', 'PB10', ...).
#   It does NOT reliably resolve Arduino-header labels ('D6', 'D7', ...) unless
#   the board build defines them, so machine.Pin('D7') typically raises
#   ValueError.  All pins below therefore use CPU names; the Arduino label is
#   kept in the comment for wiring reference only.
#
# Pin map (NUCLEO-G474RE):
#   I2C1 SCL      PB8   (Arduino D15 / CN10-3)   shared by all 3 I2C devices
#   I2C1 SDA      PB9   (Arduino D14 / CN10-5)
#   HC-SR04 TRIG  PA8   (Arduino D7)  GPIO out, 10 us trigger pulse
#   HC-SR04 ECHO  PA9   (Arduino D8)  GPIO in,  via 5V->3.3V divider (see ultrasonic.py)
#   SG90 PWM      PB10  (Arduino D6)  TIM2_CH3, 50 Hz
#
# I2C device addresses (7-bit):
#   MPU-6050  0x68  (AD0 tied low)
#   MCP9808   0x18  (A2=A1=A0=0)
#   HT16K33   0x70  (A2=A1=A0=0)

# ---------------------------------------------------------------------------
# I2C bus
# ---------------------------------------------------------------------------
I2C_ID   = 1          # STM32 I2C peripheral index -> I2C1 (PB8/PB9)
I2C_FREQ = 400_000    # 400 kHz Fast-mode (all three devices support it)
I2C_SCL_PIN = 'PB8'
I2C_SDA_PIN = 'PB9'

# ---------------------------------------------------------------------------
# I2C device addresses (7-bit)
# ---------------------------------------------------------------------------
MPU6050_ADDR = 0x68
MCP9808_ADDR = 0x18
HT16K33_ADDR = 0x70

# ---------------------------------------------------------------------------
# HC-SR04 ultrasonic sensor
# ---------------------------------------------------------------------------
HCSR04_TRIG_PIN = 'PA8'   # GPIO output, 10 us trigger pulse
HCSR04_ECHO_PIN = 'PA9'   # GPIO input, echo width proportional to distance

# ---------------------------------------------------------------------------
# SG90 servo (haptic feedback)
# ---------------------------------------------------------------------------
# 50 Hz PWM (20 ms period); pulse width 500 us (-90) .. 1500 us (0) .. 2400 us (+90).
# Must be a timer-channel-capable pin; PB10 = TIM2_CH3 on the G474.
SG90_PWM_PIN = 'PB10'

# NOTE on obstacle thresholds: the CLEAR/WARNING/DANGER distances and their
# hysteresis live as constructor defaults in obstacle.ObstacleDetector
# (danger 20/25 cm, warning 60/65 cm).  Tune them there, or pass explicit
# values when constructing the detector in main.startup().
