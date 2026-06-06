# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Firmware for a wrist-mounted navigation aid built on a **NUCLEO-G474RE (STM32G4)** running **MicroPython**. A 50 Hz control loop reads heading from an MPU-6050 IMU and distance from an HC-SR04 ultrasonic sensor, advances a hardcoded waypoint route, and delivers turn-by-turn and obstacle guidance as haptic taps through an SG90 servo. The datasheets for every peripheral are committed as PDFs in the repo root.

## Running / testing

There is **no build system, package manager, linter, or test suite** in this repo. Code runs directly on-device.

- **On hardware:** copy the `.py` files to the board's filesystem (e.g. via `mpremote`/`rshell`/Thonny) and run `main.py`. `main.run()` is the entry point.
- **On a host machine:** several modules import MicroPython-only built-ins (`machine`, `utime`, `const`, `PWM`, `time.ticks_ms`/`sleep_ms`) and will **not** import under CPython. [obstacle.py](obstacle.py) is intentionally pure-logic and is the cleanest to unit-test on the host (a `.pyc` for it already exists in `__pycache__/`). The standalone drivers `mpu6050.py`, `mcp9808.py`, and `ht16k33.py` import only `struct`/stdlib at module level, so they *import* under CPython, but exercising them needs a mock `machine.I2C` object.

When adding host-testable logic, keep it free of `machine`/`utime` imports like `obstacle.py` does.

## Architecture

Single-threaded, no RTOS, no interrupts sharing state. [main.py](main.py) `run()` does: init hardware → calibrate IMU (hold still ~2 s) → `Route().reset()` → loop forever at `LOOP_PERIOD_MS` (20 ms). Each tick: `imu.update()` → `detector.is_blocked()` → `route.tick(heading, now)` → drive servo from the returned intent → `servo.tick()` → pace to 20 ms.

The pipeline of modules, each mapped to a functional requirement (FR):

- **[imu.py](imu.py)** (FR1) — `IMU` class. MPU-6050 over I2C1. `calibrate()` measures gyro-Z bias while stationary; `update(now_ms)` integrates bias-corrected gyro-Z into a yaw heading wrapped to `(-180, 180]`; `heading()` returns it. Positive = clockwise/right turn. Verifies `WHO_AM_I == 0x68` on construction.
- **[ultrasonic.py](ultrasonic.py)** (FR2) — `Ultrasonic` class. HC-SR04 driver. `read_raw_cm()` fires one ping; `read_cm()` returns a rolling average over `SMOOTHING_WINDOW` valid readings. Invalid/timeout reads return `None` and are dropped, never zeroed.
- **[obstacle.py](obstacle.py)** (FR3) — pure function `obstacle_state(distance_cm)` → `CLEAR` / `WARNING` / `DANGER` by distance thresholds. `None` (missed echo) maps to `CLEAR` to avoid false alarms. `DANGER` is checked first so the boundary value resolves to the more urgent state.
- **[route.py](route.py)** (FR4/FR5) — `Route` state machine over the hardcoded `route` list of waypoints (`STRAIGHT` advances on elapsed time; `TURN_LEFT`/`TURN_RIGHT` tap until heading is within `HEADING_TOLERANCE_DEG` of target; `FINISH` is terminal). `tick()` returns a servo *intent*: `NEUTRAL` / `TAP_LEFT` / `TAP_RIGHT` / `FINISHED`. The route is hardcoded here — edit the `route` list to change the path.
- **[servo_feedback.py](servo_feedback.py)** (FR6) — `ServoFeedback` class. Non-blocking 12-state machine driving the SG90 via `duty_ns` PWM. Methods (`tap_left/right`, `warning_pattern`, `danger_pattern`, `neutral`) only update state and return immediately; **`tick()` is the only method that moves the servo** and must be polled at least every ~60 ms. No `sleep` anywhere — safe to call from a timer ISR.

Data flow is one-directional: sensors → classifiers/state machine → intent → servo. Modules communicate through plain return values and string constants; there is no shared mutable state between them.

### Standalone peripheral drivers (not wired into the main loop)

Three generic I2C drivers exist but are **not imported by `main.py`** — they are reusable building blocks / for additional peripherals, with their own `__init__(i2c, ...)` signatures and `WHO_AM_I`/ID checks:

- **[mpu6050.py](mpu6050.py)** — generic `MPU6050` driver exposing raw `accel()` / `gyro()` / `temperature()` / `read_all()`. **Do not confuse this with [imu.py](imu.py).** `imu.py`'s `IMU` class is the navigation-specific driver actually used by the main loop: it adds gyro-bias calibration and integrates gyro-Z into a wrapped yaw `heading()`. `mpu6050.py` is a lower-level, stateless driver. If asked to change "the IMU," confirm which one — heading/route behavior lives in `imu.py`.
- **[mcp9808.py](mcp9808.py)** — `MCP9808` temperature sensor (address 0x18), with `temperature()`, resolution control, and shutdown/wake.
- **[ht16k33.py](ht16k33.py)** — `HT16K33` driver for an Adafruit 4-digit 7-segment backpack (address 0x70): `print_str` / `print_int` / `print_float` / raw `set_digit`, with a shadow RAM buffer pushed on `show()`.

These three take an externally-constructed `machine.I2C` and would share I2C1 (0x68 / 0x18 / 0x70 don't collide) if integrated. Unlike `imu.py`/`ultrasonic.py`/`servo_feedback.py`, they read their config from constructor arguments rather than `config.py`.

## config.py — important gotcha

[config.py](config.py) is the single source of tunable constants — modules import only the names they need and avoid magic numbers. **However, the file currently contains several duplicated/conflicting definitions** of the same constant (e.g. `SERVO_PIN`, `WARNING_DISTANCE_CM`, `I2C_BUS`, the various `SERVO_*` and tap-interval constants appear multiple times, and there is a stray triple-quoted docstring partway through). In Python the **last assignment wins**, so when changing a value, search the whole file and edit the *final* occurrence — or you'll edit a line that gets overwritten lower down. Consolidating these duplicates is a reasonable cleanup if asked.

Pin/address reference lives in the comments of `config.py` (Arduino-header pin names like `D7`/`PA8`, I2C addresses `0x68`/`0x18`/`0x70`).

## Hardware constraints to respect in code

- **HC-SR04 Echo is 5 V** — the wiring requires a resistor divider to the 3.3 V STM32 GPIO (noted in `ultrasonic.py`). Don't assume direct connection.
- **SG90 needs the 5 V rail**, not 3.3 V (stalls below ~4.8 V).
- Heading and turn-completion math is **wrap-aware** on `(-180, 180]`; reuse `_wrap180` / `_heading_error` rather than naive subtraction.
- Loop timing is interdependent: `LOOP_PERIOD_MS` (20 ms) matches `IMU_SAMPLE_INTERVAL_MS` and the MPU-6050 `SMPLRT_DIV` (50 Hz) set in `imu._configure()`. Changing one may require changing the others.

## Workflow

Development happens via per-FR feature branches that merge into `main` (see git history: `headless/<id>/implement-the-<feature>`). Each module is owned independently and depends only on the documented public API of the others, not their internals.
