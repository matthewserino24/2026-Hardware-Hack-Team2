# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Firmware for a wrist-mounted navigation aid on a **NUCLEO-G474RE (STM32G4)** running **MicroPython**. A cadence-based main loop reads heading from an MPU-6050 IMU and distance from an HC-SR04 ultrasonic sensor, steers an SG90 servo toward a list of waypoints (proportional control), overrides with obstacle feedback when something is close, and shows status/temperature on an HT16K33 7-segment display. Peripheral datasheets are committed as PDFs in the repo root.

> History note: the repo was once assembled by **concatenating** several `headless/*` agent branches, leaving every source file with two conflicting implementations glued together (and `main.py` not even compiling). That has been resolved — each module now holds a single coherent implementation (the "full demo" / Family A design). If you ever see a file with the same class defined twice, that regression has returned; run the test suite below.

## Running / testing

There is no package manager or third-party test dependency. Two ways to exercise the code:

- **On hardware:** copy the `.py` files to the board and run `main.py`; `main.run()` is the entry point (loops forever). `run(max_iters=N)` runs a bounded number of iterations — used by the host harness.
- **On your laptop (no board):** the firmware imports MicroPython-only APIs (`machine`, `utime`, `const`, `time.ticks_ms`), so it cannot run under CPython directly. [tests/mockhw.py](tests/mockhw.py) fakes those (I2C/Pin/PWM/`time_pulse_us`, the tick clock, and the `const()` builtin) well enough that constructors and the main loop run. Then:

  ```
  python3 tests/test_vet.py     # 14 unit + integration tests (boots main, runs the loop)
  python3 tests/demo_run.py     # smoke demo: boots + runs 400 loop iters, prints display/servo activity
  ```

  The harness mock I2C returns identity bytes that satisfy each driver's self-check (MPU-6050 `WHO_AM_I`, MCP9808 manufacturer/device IDs). `mockhw.set_sim_distance_cm()` injects an obstacle distance; `mockhw.set_auto_advance_ms()` makes the tick clock advance so the cadence loop progresses without real sleeps.

  When adding host-testable logic, keep it free of `machine`/`utime` imports where possible (like [obstacle.py](obstacle.py), which is pure logic) so it can be unit-tested directly.

## Architecture

[main.py](main.py) `startup()` initialises peripherals in dependency order (I2C → display → temp → IMU+calibrate → sonar → servo → zero heading → load `_WAYPOINTS`) and returns the 7 objects. `run()` is a **non-blocking, cadence-based** loop (no `sleep` in the loop body; each task fires on its own `ticks_diff` interval):

- **every iteration** — IMU update (integrate gyro-Z over measured `dt`); route tick (proportional steer toward current waypoint) unless in DANGER.
- **≥60 ms** — HC-SR04 read → `ObstacleDetector.update()`; on a state *transition* fire `servo.warning_pulse()` / `servo.danger_pattern()` (these are short *blocking* sweeps).
- **500 ms** — MCP9808 temperature read + display update (status text overrides temperature: `dAnG` / `WArn` / `donE`, else the temperature).

Modules and their roles:

- **[imu.py](imu.py)** — `IMU`, a thin heading-integration wrapper **over [mpu6050.py](mpu6050.py)**. `calibrate()` measures gyro-Z bias at rest; `update(dt_s)` accumulates an **unbounded** heading (degrees); `heading` is a property; `zero_heading()` re-references. Note `update()` takes an already-differenced `dt_s` (seconds), not an absolute tick count.
- **[mpu6050.py](mpu6050.py)** — low-level MPU-6050 driver (`accel`/`gyro`/`temperature`/`read_all`). `imu.py` builds on it.
- **[ultrasonic.py](ultrasonic.py)** — `HCSR04` driver with a 3-sample median filter; `distance_cm()` returns filtered cm or `None` on timeout.
- **[obstacle.py](obstacle.py)** — `ObstacleDetector`, a **hysteretic** state machine returning the integer constants `CLEAR`/`WARNING`/`DANGER` (0/1/2) with separate entry/exit thresholds so it doesn't chatter at a boundary. A `None` reading **holds** the current state (fail-safe). Pure logic, no hardware imports.
- **[route.py](route.py)** — `Route` over a list of `Waypoint(heading, label)`. `tick(imu_heading, servo)` steers proportionally (`_KP`, clamped to `_MAX_STEER_DEG`) using the **wrap-aware** `_heading_error` (shortest signed arc on the ±180° circle), and advances when the heading holds within `arrival_threshold_deg` for `arrival_hold_ms`. `complete` is a property.
- **[servo_feedback.py](servo_feedback.py)** — `ServoFeedback`: `set_angle`/`neutral`/`steer` plus the blocking `warning_pulse()` and `danger_pattern()` feedback sweeps. `_angle_to_ns` centres on 1500 µs with a symmetric ±950000 ns swing (so ±90° → 550000/2450000 ns, slightly inside the datasheet 500/2400 µs endpoints — fine for the small haptic deflections used).
- **[mcp9808.py](mcp9808.py)** — `MCP9808` temperature sensor (0x18). **[ht16k33.py](ht16k33.py)** — `HT16K33` 4-digit 7-segment display driver (0x70), `print_str`/`print_float`/`show`. Both are wired into `main`.

Data flow is one-directional: sensors → classifier/state machine → servo + display. The three I2C devices (0x68/0x18/0x70) share I2C1 (PB8/PB9) and don't collide.

## config.py — gotcha

[config.py](config.py) holds tunable constants, but it **still contains many duplicated definitions** of the same name (e.g. `SERVO_*`, `WARNING_DISTANCE_CM`, `I2C_BUS`, plus a stray triple-quoted block). Python's last-assignment-wins means the duplicates currently agree on values, but when changing one, search the whole file and edit the **final** occurrence or your edit is silently overwritten. Only `main.py` reads config (pin/address constants); the driver modules take their parameters via constructor args. Consolidating these duplicates is a safe, worthwhile cleanup.

## Hardware constraints to respect in code

- **HC-SR04 Echo is 5 V** — wiring needs a resistor divider down to the 3.3 V STM32 GPIO (see [ultrasonic.py](ultrasonic.py) header). Don't assume a direct connection.
- **SG90 needs the 5 V rail**, not 3.3 V (stalls below ~4.8 V).
- The `warning_pulse()`/`danger_pattern()` sweeps **block** the loop (~300/600 ms) for the duration of the sweep; they only fire on a state transition, so the loop stalls briefly when entering WARNING/DANGER. Keep that in mind before adding latency-sensitive work.
- `imu.heading` is unbounded (never wraps); route arithmetic is made wrap-safe by `route._heading_error`, so reuse it rather than naive subtraction.

## Workflow

Development happened via per-FR `headless/*` branches merged into `main`. After the de-concatenation, the canonical implementation is the single version now on `main`; the old per-FR branch snapshots correspond to the simpler "FR" design (hardcoded route + tap feedback) and are not what `main` runs.
