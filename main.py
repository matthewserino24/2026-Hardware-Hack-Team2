# main.py
# Top-level entry point for the 2026 Hardware Hack Team2 navigation demo.
# Target: STM32 Nucleo-G474RE running MicroPython v1.28+
#
# ── Architecture ────────────────────────────────────────────────────────────
#
#  Startup sequence (§5.1):
#    1. Initialise I2C bus (PB8/PB9, 400 kHz)
#    2. Initialise HT16K33 display → show "boot" splash
#    3. Initialise MCP9808 temperature sensor
#    4. Initialise MPU-6050 via IMU wrapper → calibrate gyro bias (~1 s)
#    5. Initialise HC-SR04 ultrasonic sensor
#    6. Initialise SG90 servo → centre
#    7. Zero IMU heading
#    8. Load waypoint route
#    9. Show "rdy" on display, enter main loop
#
#  Main event loop (§10) — non-blocking, cadence-based:
#
#    Cadence    Task
#    ─────────  ──────────────────────────────────────────────────────────
#    Every loop IMU update (integrate gyro-Z, dt measured with ticks_ms)
#    60 ms      HC-SR04 read (datasheet: ≥60 ms between pings)
#    500 ms     MCP9808 temperature read + display update
#    Every loop Route tick (servo steering toward current waypoint)
#    Every loop Obstacle state update → servo feedback on state change
#
#  All timing uses utime.ticks_ms() / ticks_diff() — no blocking sleeps
#  in the main loop.  The HC-SR04 _raw_distance_cm() call itself takes
#  up to ~23 ms (echo timeout); this is acceptable because the 60 ms
#  cadence guard prevents back-to-back pings.
#
# ── Pin map (from config.py) ─────────────────────────────────────────────
#
#   I2C1 SCL  PB8  (D15)   → MPU-6050, MCP9808, HT16K33
#   I2C1 SDA  PB9  (D14)
#   HC-SR04 TRIG  PA8 (D7)
#   HC-SR04 ECHO  PA9 (D8)  ← via 1kΩ/2kΩ voltage divider (5 V → 3.3 V)
#   SG90 PWM      PB10 (D6) ← TIM2_CH3, 50 Hz
#
# ── Obstacle state → servo feedback mapping ──────────────────────────────
#
#   CLEAR   → servo steers toward current waypoint (normal operation)
#   WARNING → single warning_pulse() then resume steering
#   DANGER  → danger_pattern() then hold neutral until DANGER clears
#
# ── Display content ──────────────────────────────────────────────────────
#
#   Normal:  temperature in °C (e.g. "23.5")
#   DANGER:  "dAnG"
#   WARNING: "WArn"
#   Route complete: "donE"

import utime
from machine import I2C, Pin

import config
from ht16k33       import HT16K33
from mcp9808       import MCP9808
from imu           import IMU
from ultrasonic    import HCSR04
from obstacle      import ObstacleDetector, CLEAR, WARNING, DANGER
from servo_feedback import ServoFeedback
from route         import Route, Waypoint

# ── Timing cadences (milliseconds) ───────────────────────────────────────
_SONAR_CADENCE_MS = 60    # HC-SR04: ≥60 ms between pings (datasheet)
_TEMP_CADENCE_MS  = 500   # MCP9808: update display twice per second

# ── Demo waypoint route ───────────────────────────────────────────────────
# Headings are relative to the zeroed IMU heading at startup.
# Positive = counter-clockwise (right-hand rule, Z-up).
_WAYPOINTS = [
    Waypoint(heading=  0.0, label="Fwd"),
    Waypoint(heading= 45.0, label="Left 45"),
    Waypoint(heading=  0.0, label="Fwd again"),
    Waypoint(heading=-45.0, label="Right 45"),
    Waypoint(heading=  0.0, label="Home"),
]


# ── Startup sequence ─────────────────────────────────────────────────────

def startup():
    """
    Initialise all peripherals in dependency order.
    Returns a tuple: (display, temp_sensor, imu, sonar, detector, servo, route)
    Raises RuntimeError on any hardware fault.
    """
    # 1. I2C bus ─────────────────────────────────────────────────────────
    i2c = I2C(
        config.I2C_ID,
        scl=Pin('PB8'),
        sda=Pin('PB9'),
        freq=config.I2C_FREQ,
    )

    # 2. HT16K33 display ─────────────────────────────────────────────────
    display = HT16K33(i2c, addr=config.HT16K33_ADDR, brightness=8)
    display.print_str("boot")
    display.show()

    # 3. MCP9808 temperature sensor ───────────────────────────────────────
    temp_sensor = MCP9808(i2c, addr=config.MCP9808_ADDR)

    # 4. MPU-6050 IMU + gyro calibration (~1 s, device must be still) ────
    display.print_str("CAL ")
    display.show()
    imu = IMU(i2c, addr=config.MPU6050_ADDR)
    imu.calibrate()   # blocks ~1 s; collects 20 samples at 50 ms each

    # 5. HC-SR04 ultrasonic sensor ────────────────────────────────────────
    sonar = HCSR04(
        trig_pin=config.HCSR04_TRIG_PIN,
        echo_pin=config.HCSR04_ECHO_PIN,
    )

    # 6. SG90 servo → centre ─────────────────────────────────────────────
    servo = ServoFeedback(config.SG90_PWM_PIN)
    servo.neutral()

    # 7. Zero IMU heading ─────────────────────────────────────────────────
    imu.zero_heading()

    # 8. Waypoint route ───────────────────────────────────────────────────
    nav_route = Route(_WAYPOINTS)

    # 9. Ready ────────────────────────────────────────────────────────────
    display.print_str(" rdy")
    display.show()
    utime.sleep_ms(500)   # brief splash before loop starts

    return display, temp_sensor, imu, sonar, ObstacleDetector(), servo, nav_route


# ── Main event loop ───────────────────────────────────────────────────────

def run():
    """
    Main non-blocking event loop.

    Timing strategy:
      - Record ticks_ms() at the top of every iteration as `now`.
      - Each cadenced task compares ticks_diff(now, last_X_ms) against its
        interval.  No utime.sleep() calls inside the loop.
      - IMU update uses ticks_diff from the previous iteration to compute dt.
    """
    display, temp_sensor, imu, sonar, detector, servo, nav_route = startup()

    # Cadence timestamps (initialised to trigger immediately on first pass)
    last_sonar_ms = utime.ticks_ms() - _SONAR_CADENCE_MS
    last_temp_ms  = utime.ticks_ms() - _TEMP_CADENCE_MS

    # IMU dt tracking
    last_imu_ms   = utime.ticks_ms()

    # Obstacle state tracking (detect transitions for feedback)
    prev_obstacle  = CLEAR
    obstacle_state = CLEAR

    # Cached temperature for display
    last_temp_c    = 0.0

    # ── Loop ─────────────────────────────────────────────────────────────
    while True:
        now = utime.ticks_ms()

        # ── IMU update (every iteration) ─────────────────────────────────
        dt_ms = utime.ticks_diff(now, last_imu_ms)
        last_imu_ms = now
        dt_s = dt_ms / 1000.0
        imu.update(dt_s)

        # ── HC-SR04 read (≥60 ms cadence) ────────────────────────────────
        if utime.ticks_diff(now, last_sonar_ms) >= _SONAR_CADENCE_MS:
            last_sonar_ms = now
            dist = sonar.distance_cm()
            prev_obstacle  = obstacle_state
            obstacle_state = detector.update(dist)

            # Trigger servo feedback on state transitions
            if obstacle_state != prev_obstacle:
                if obstacle_state == DANGER:
                    servo.danger_pattern()   # ~600 ms blocking sweep
                elif obstacle_state == WARNING:
                    servo.warning_pulse()    # ~300 ms blocking sweep

        # ── Route tick + servo steering ───────────────────────────────────
        if obstacle_state == DANGER:
            # Hold neutral while in danger; do not advance route
            servo.neutral()
        elif not nav_route.complete:
            nav_route.tick(imu.heading, servo)

        # ── MCP9808 temperature read + display update (500 ms cadence) ───
        if utime.ticks_diff(now, last_temp_ms) >= _TEMP_CADENCE_MS:
            last_temp_ms = now
            last_temp_c  = temp_sensor.temperature()

            # Display: obstacle state overrides temperature readout
            if nav_route.complete:
                display.print_str("donE")
            elif obstacle_state == DANGER:
                display.print_str("dAnG")
            elif obstacle_state == WARNING:
                display.print_str("WArn")
            else:
                display.print_float(last_temp_c, decimal_places=1)
            display.show()


# ── Entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    run()
