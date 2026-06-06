# main.py — Top-level integration loop
# Target: STM32G4 Nucleo-64 (NUCLEO-G474RE), MicroPython
#
# Wires together all functional requirements:
#   FR1  imu.py          — MPU-6050 heading via gyro integration
#   FR2  ultrasonic.py   — HC-SR04 distance measurement
#   FR3  obstacle.py     — obstacle detection / zone classification
#   FR4  route.py        — waypoint state machine (STRAIGHT / TURN)
#   FR5  route.py        — heading-based turn completion
#   FR6  servo_feedback.py — SG90 haptic tap feedback
#
# Execution model:
#   Single-threaded 50 Hz main loop (LOOP_PERIOD_MS = 20 ms).
#   No RTOS, no threads.  All modules are polled once per loop iteration.
#   ISR-safe: no shared mutable state between ISR and main loop.

import time
import machine

from config import (
    I2C_BUS,
    HCSR04_TRIG_PIN,
    HCSR04_ECHO_PIN,
    SERVO_PIN,
    LOOP_PERIOD_MS,
    FINISH_SUCCESS_PATTERN,
    ULTRASONIC_SAMPLE_INTERVAL_MS,
)

from imu            import IMU
from ultrasonic     import Ultrasonic
from obstacle       import ObstacleDetector
from servo_feedback import ServoFeedback
from route          import Route, NEUTRAL, TAP_LEFT, TAP_RIGHT, FINISHED


# ---------------------------------------------------------------------------
# Hardware initialisation
# ---------------------------------------------------------------------------

def _init_hardware():
    """Construct and return all peripheral objects.

    Raises RuntimeError if any peripheral fails to initialise so that the
    caller can decide whether to halt or degrade gracefully.
    """
    i2c = machine.I2C(I2C_BUS, freq=400_000)

    imu        = IMU(i2c)
    ultrasonic = Ultrasonic(HCSR04_TRIG_PIN, HCSR04_ECHO_PIN)
    detector   = ObstacleDetector(ultrasonic)
    servo      = ServoFeedback(SERVO_PIN)

    return imu, ultrasonic, detector, servo


# ---------------------------------------------------------------------------
# Startup calibration
# ---------------------------------------------------------------------------

def _calibrate(imu):
    """Run IMU gyro bias calibration.

    The user must hold the device still for ~2 s.  A brief LED blink or
    print statement signals the calibration window.
    """
    print("Calibrating IMU — hold still …")
    imu.calibrate()
    print("Calibration done.")


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def run():
    """Entry point: initialise hardware, calibrate, then run the 50 Hz loop."""

    # ---- hardware init ----
    imu, ultrasonic, detector, servo = _init_hardware()
    _calibrate(imu)

    # ---- route init ----
    route = Route()
    route.reset()

    print("Route started.")

    # ---- 50 Hz control loop ----
    while True:
        loop_start = time.ticks_ms()

        # 1. Update IMU (integrates gyro, updates heading)
        imu.update(loop_start)
        heading = imu.heading()

        # 2. Sample obstacle detector
        blocked = detector.is_blocked()

        # 3. Advance route state machine
        intent = route.tick(heading, loop_start)

        # 4. Drive servo based on intent, with obstacle override
        if intent == FINISHED:
            # Route complete — hold neutral (optionally play success pattern)
            if FINISH_SUCCESS_PATTERN:
                servo.success_sweep()
            else:
                servo.neutral()
            # Stay in finished state; do not break so the device stays alive
        elif blocked:
            # Obstacle override: pause guidance, pulse neutral rapidly to
            # signal the user that forward progress is suspended.
            servo.neutral()
        else:
            # Normal guidance
            if intent == TAP_LEFT:
                servo.tap_left()
            elif intent == TAP_RIGHT:
                servo.tap_right()
            else:
                servo.neutral()

        # 5. Commit servo position for this tick
        servo.tick()

        # 6. Pace the loop to LOOP_PERIOD_MS
        elapsed = time.ticks_diff(time.ticks_ms(), loop_start)
        sleep_ms = LOOP_PERIOD_MS - elapsed
        if sleep_ms > 0:
            time.sleep_ms(sleep_ms)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    run()
