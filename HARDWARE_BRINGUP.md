# Hardware bring-up checklist — NUCLEO-G474RE

Audit date: 2026-06-06. Run through this before and during the first on-board test.
The host test suite (`python3 tests/test_vet.py`) cannot catch any of these — they
depend on the physical board, wiring, and MicroPython build.

## Fixed in code during the audit
These were corrected; listed so you know what changed:

1. **Pin names** — `config.py` now uses CPU names (`PA8`/`PA9`/`PB10`), not Arduino
   labels (`D7`/`D8`/`D6`). `machine.Pin('D7')` raises `ValueError` on the STM32
   port, which would have stopped boot at `startup()`.
2. **Steering direction** — `route.py` cued the servo the *wrong way* relative to
   the codebase's own conventions (IMU +heading = CCW/left; servo +angle = right).
   Now a left waypoint cues a left deflection. Controlled by `route._STEER_SIGN`.
3. **Tick wraparound** — `main.py` cadence timers used plain subtraction on
   `ticks_ms()`; replaced with `ticks_add`, which is defined across the wrap.

## Must verify on the bench (electrical / safety)
- [ ] **HC-SR04 ECHO divider.** ECHO idles/drives 5 V. Put a divider (~1 kΩ series +
      2 kΩ to GND, or 10 k/20 k) between ECHO (PA9) and the MCU pin **before powering**.
      Driving 5 V into a 3.3 V GPIO can damage the pin.
- [ ] **SG90 power.** Servo VCC on a **separate 5 V rail** (not the MCU 3.3 V), with a
      **common ground** to the Nucleo. Stall current ~500 mA will brown out the board
      if taken from a logic pin/rail.
- [ ] **TRIG level.** PA8 drives 3.3 V into HC-SR04 TRIG — accepted as logic-high, no
      shifter needed. Confirm wiring TRIG↔PA8, ECHO↔PA9 (via divider).
- [ ] **I2C pull-ups.** PB8/PB9 need pull-ups to 3.3 V (most breakout boards include
      them; if all three share a bus, don't stack too many — ~2.2–4.7 kΩ total).

## Must verify on the bench (firmware / build)
- [ ] **MicroPython version.** `ServoFeedback` uses `PWM(...).duty_ns()`, which needs
      MicroPython **≥ 1.20**. Check `import sys; sys.implementation` on the board.
- [ ] **PB10 is PWM-capable** on your build. `machine.PWM(Pin('PB10'), freq=50)` then
      `duty_ns()` should not raise. PB10 = TIM2_CH3 on the G474; if your build doesn't
      route PWM there, move the servo to another timer pin and update `config.SG90_PWM_PIN`.
- [ ] **I2C constructor signature.** `main.startup()` calls
      `machine.I2C(1, scl=Pin('PB8'), sda=Pin('PB9'), freq=...)`. If your build rejects
      the `scl`/`sda` keywords for hardware I2C, fall back to `machine.I2C(1, freq=...)`
      (default I2C1 pins) or `machine.SoftI2C(scl=Pin('PB8'), sda=Pin('PB9'), freq=...)`.
- [ ] **Device scan.** Before running `main`, confirm all three devices answer:
      `machine.I2C(1).scan()` should list `0x68` (MPU-6050), `0x18` (MCP9808),
      `0x70` (HT16K33). A missing address means wiring/address-strap/pull-up issue and
      `startup()` will raise `RuntimeError` (no recovery — it drops to the REPL).

## Must verify on the bench (behavioural / calibration)
- [ ] **Gyro sign / steer direction.** Rotate the device **left (CCW)** and confirm
      `imu.heading` *increases*. Then walk a left waypoint and confirm the servo cues
      **left**. If either is backwards (e.g. IMU mounted inverted), flip
      `route._STEER_SIGN` from `-1` to `+1`. This is the single most likely
      "it guides the wrong way" issue.
- [ ] **Gyro bias / drift.** `startup()` calibrates ~1 s — hold **completely still**
      during the `CAL` splash. Gyro-only heading drifts over minutes (no mag/accel
      fusion); re-run / re-zero between route attempts for a fair test.
- [ ] **Obstacle thresholds.** DANGER/WARNING distances (20/25 cm and 60/65 cm with
      hysteresis) are constructor defaults in `obstacle.ObstacleDetector`, **not**
      `config.py`. Tune them for wrist range by passing explicit values in
      `main.startup()` if 20 cm is too close.
- [ ] **Servo travel.** `_angle_to_ns` centres on 1500 µs with a symmetric ±950 000 ns
      swing, so ±90° → 550/2450 µs (slightly inside the 500/2400 µs datasheet endpoints).
      Confirm the horn doesn't bind at the extremes; the nav code only uses ±60°.

## Known design limitations (not bugs — decide if they matter for your demo)
- **Blocking feedback sweeps.** `warning_pulse()` (~300 ms) and `danger_pattern()`
  (~600 ms) use `sleep_ms` and **block the main loop** while running. They fire once on
  entering WARNING/DANGER; during the sweep the IMU isn't updated, so the next `dt` is
  large. Acceptable for a short demo; revisit if you need continuous danger haptics or
  tight timing.
- **DANGER haptic fires once.** While DANGER persists the loop holds the servo neutral
  and pauses the route; it does not keep buzzing. The display still shows `dAnG`.
- **Clear-path ping stall.** When nothing is within ~4 m, `time_pulse_us` blocks the
  full ~23 ms timeout each ping, lowering the effective loop/IMU rate. Fine indoors.
- **Tight, unpaced loop.** No `sleep` in the loop body (by design); it polls as fast as
  possible, generating heavy I2C traffic. If you want a steadier ~50 Hz and lower bus
  load, add a small `utime.sleep_ms()` at the bottom of the loop.
