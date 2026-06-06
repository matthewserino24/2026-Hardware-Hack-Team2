# selftest.py — On-board hardware bring-up checks for the NUCLEO-G474RE.
#
# Run these ON THE BOARD, ONE AT A TIME, from the REPL — NOT all at once, and
# NOT before you have checked the wiring in HARDWARE_BRINGUP.md.
#
# Quick start (in the MicroPython REPL):
#
#     import selftest
#     selftest.scan()          # 1. confirm all 3 I2C devices answer
#     selftest.temp()          # 2. MCP9808 temperature
#     selftest.display()       # 3. HT16K33 shows 8888 then 1234
#     selftest.distance()      # 4. HC-SR04 prints live distance for ~5 s
#     selftest.servo()         # 5. servo: neutral -> LEFT -> RIGHT -> neutral
#     selftest.imu_sign()      # 6. rotate board LEFT; heading should go POSITIVE
#
# Or run the non-moving checks together:
#
#     selftest.passive()       # scan + temp + display + distance (no servo motion)
#
# Each function builds only what it needs, so a failure points at one subsystem.

import utime
from machine import I2C, Pin

import config


def _i2c():
    return I2C(
        config.I2C_ID,
        scl=Pin(config.I2C_SCL_PIN),
        sda=Pin(config.I2C_SDA_PIN),
        freq=config.I2C_FREQ,
    )
    # If the line above raises TypeError on scl/sda, your build wants:
    #   return I2C(config.I2C_ID, freq=config.I2C_FREQ)        # default pins
    # or  from machine import SoftI2C
    #   return SoftI2C(scl=Pin(config.I2C_SCL_PIN), sda=Pin(config.I2C_SDA_PIN),
    #                  freq=config.I2C_FREQ)


# ---------------------------------------------------------------------------
# 1. I2C scan
# ---------------------------------------------------------------------------
def scan():
    """List I2C devices. Expect 0x68 (MPU-6050), 0x18 (MCP9808), 0x70 (HT16K33)."""
    found = _i2c().scan()
    print("I2C devices found:", [hex(a) for a in found])
    expected = {
        config.MPU6050_ADDR: "MPU-6050",
        config.MCP9808_ADDR: "MCP9808",
        config.HT16K33_ADDR: "HT16K33",
    }
    ok = True
    for addr, name in expected.items():
        present = addr in found
        print("  {:<10} {}  {}".format(name, hex(addr), "OK" if present else "MISSING"))
        ok = ok and present
    print("scan:", "PASS" if ok else "FAIL — check wiring / pull-ups / addresses")
    return ok


# ---------------------------------------------------------------------------
# 2. MCP9808 temperature
# ---------------------------------------------------------------------------
def temp():
    """Read and print the MCP9808 temperature (expect roughly room temp)."""
    from mcp9808 import MCP9808
    t = MCP9808(_i2c(), addr=config.MCP9808_ADDR).temperature()
    print("temperature: {:.2f} C".format(t))
    return t


# ---------------------------------------------------------------------------
# 3. HT16K33 display
# ---------------------------------------------------------------------------
def display():
    """Light all segments (8888) then show 1234 so you can read the digits."""
    from ht16k33 import HT16K33
    d = HT16K33(_i2c(), addr=config.HT16K33_ADDR, brightness=8)
    d.print_str("8888"); d.show()
    utime.sleep_ms(1000)
    d.print_str("1234"); d.show()
    print("display: should read 8888 then 1234")


# ---------------------------------------------------------------------------
# 4. HC-SR04 distance
# ---------------------------------------------------------------------------
def distance(seconds=5):
    """Print live filtered distance. Wave your hand to see it change."""
    from ultrasonic import HCSR04
    sonar = HCSR04(config.HCSR04_TRIG_PIN, config.HCSR04_ECHO_PIN)
    end = utime.ticks_add(utime.ticks_ms(), seconds * 1000)
    while utime.ticks_diff(end, utime.ticks_ms()) > 0:
        print("distance: {} cm".format(sonar.distance_cm()))
        utime.sleep_ms(300)
    print("distance: done (None = no echo / out of range / check ECHO divider)")


# ---------------------------------------------------------------------------
# 5. Servo
# ---------------------------------------------------------------------------
def servo():
    """Sweep neutral -> LEFT -> RIGHT -> neutral. Confirm LEFT really goes left."""
    from servo_feedback import ServoFeedback
    s = ServoFeedback(config.SG90_PWM_PIN)
    print("servo: neutral");       s.set_angle(0);   utime.sleep_ms(800)
    print("servo: LEFT (-45)");    s.set_angle(-45); utime.sleep_ms(800)
    print("servo: RIGHT (+45)");   s.set_angle(45);  utime.sleep_ms(800)
    print("servo: neutral");       s.set_angle(0);   utime.sleep_ms(800)
    print("servo: if -45 did NOT move left, your horn/mounting is mirrored")


# ---------------------------------------------------------------------------
# 6. IMU heading sign — THE critical guidance check
# ---------------------------------------------------------------------------
def imu_sign(seconds=6):
    """Calibrate, then integrate heading for a few seconds.

    Hold still during 'calibrating', then ROTATE THE BOARD LEFT (counter-
    clockwise, viewed from above).  Heading should trend POSITIVE.

    If rotating left makes heading go NEGATIVE, set route._STEER_SIGN = +1
    (the IMU is effectively mounted inverted for this code's convention).
    """
    from imu import IMU
    imu = IMU(_i2c(), addr=config.MPU6050_ADDR)
    print("calibrating — hold still ...")
    imu.calibrate()
    imu.zero_heading()
    print("now ROTATE LEFT (CCW). heading should increase (go positive):")
    last = utime.ticks_ms()
    end = utime.ticks_add(last, seconds * 1000)
    while utime.ticks_diff(end, utime.ticks_ms()) > 0:
        now = utime.ticks_ms()
        dt = utime.ticks_diff(now, last)
        if dt > 0:
            last = now
            imu.update(dt / 1000.0)
        print("heading: {:.1f}".format(imu.heading))
        utime.sleep_ms(200)
    print("imu_sign: left rotation -> positive? if not, flip route._STEER_SIGN")


# ---------------------------------------------------------------------------
# Passive bundle (no servo motion)
# ---------------------------------------------------------------------------
def passive():
    """Run the non-moving checks back to back."""
    print("=== scan ===");
    if not scan():
        print("stop: fix I2C before continuing")
        return
    print("=== temp ==="); temp()
    print("=== display ==="); display()
    print("=== distance ==="); distance()
    print("passive checks done")
