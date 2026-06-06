"""
Top-level MicroPython entry point for the ZH base hardware framework.

This keeps the latest main-branch startup and loop behavior while remaining
compatible with the framework driver layout in this branch.
"""

import utime
from machine import I2C, Pin

import config
from ht16k33 import HT16K33
from imu import IMU
from mcp9808 import MCP9808
from obstacle import CLEAR, DANGER, WARNING, ObstacleDetector
from route import Route, Waypoint
from servo_feedback import ServoFeedback
from ultrasonic import HCSR04

_SONAR_CADENCE_MS = 60
_TEMP_CADENCE_MS = 500

_WAYPOINTS = [
    Waypoint(heading=0.0, label="Fwd"),
    Waypoint(heading=45.0, label="Left 45"),
    Waypoint(heading=0.0, label="Fwd again"),
    Waypoint(heading=-45.0, label="Right 45"),
    Waypoint(heading=0.0, label="Home"),
]


def startup():
    i2c = I2C(
        config.I2C_ID,
        scl=Pin(config.I2C_SCL_PIN),
        sda=Pin(config.I2C_SDA_PIN),
        freq=config.I2C_FREQ,
    )

    display = HT16K33(i2c, addr=config.HT16K33_ADDR, brightness=8)
    display.print_str("boot")
    display.show()

    temp_sensor = MCP9808(i2c, addr=config.MCP9808_ADDR)

    display.print_str("CAL ")
    display.show()
    imu = IMU(i2c, addr=config.MPU6050_ADDR)
    imu.calibrate()

    sonar = HCSR04(
        trig_pin=config.HCSR04_TRIG_PIN,
        echo_pin=config.HCSR04_ECHO_PIN,
    )

    servo = ServoFeedback(config.SG90_PWM_PIN)
    servo.neutral()

    imu.zero_heading()
    nav_route = Route(_WAYPOINTS)

    display.print_str(" rdy")
    display.show()
    utime.sleep_ms(500)

    return display, temp_sensor, imu, sonar, ObstacleDetector(), servo, nav_route


def run(max_iters=None):
    """
    Run the main loop.

    Parameters
    ----------
    max_iters : int or None
        Run forever when None. When set, stop after the requested number of
        loop iterations. Useful for host-side testing.
    """
    display, temp_sensor, imu, sonar, detector, servo, nav_route = startup()

    last_sonar_ms = utime.ticks_add(utime.ticks_ms(), -_SONAR_CADENCE_MS)
    last_temp_ms = utime.ticks_add(utime.ticks_ms(), -_TEMP_CADENCE_MS)
    last_imu_ms = utime.ticks_ms()

    obstacle_state = CLEAR
    last_temp_c = 0.0

    iters = 0
    while max_iters is None or iters < max_iters:
        iters += 1
        now = utime.ticks_ms()

        dt_ms = utime.ticks_diff(now, last_imu_ms)
        if dt_ms > 0:
            last_imu_ms = now
            imu.update(dt_ms / 1000.0)

        if utime.ticks_diff(now, last_sonar_ms) >= _SONAR_CADENCE_MS:
            last_sonar_ms = now
            prev_obstacle = obstacle_state
            obstacle_state = detector.update(sonar.distance_cm())

            if obstacle_state != prev_obstacle:
                if obstacle_state == DANGER:
                    servo.danger_pattern()
                elif obstacle_state == WARNING:
                    servo.warning_pulse()

        if obstacle_state == DANGER:
            pass
        elif obstacle_state != WARNING and not nav_route.complete:
            nav_route.tick(imu.heading, servo)

        servo.tick()

        if utime.ticks_diff(now, last_temp_ms) >= _TEMP_CADENCE_MS:
            last_temp_ms = now
            last_temp_c = temp_sensor.temperature()

            if nav_route.complete:
                display.print_str("donE")
            elif obstacle_state == DANGER:
                display.print_str("dAnG")
            elif obstacle_state == WARNING:
                display.print_str("WArn")
            else:
                display.print_float(last_temp_c, decimal_places=1)
            display.show()


if __name__ == "__main__":
    run()
