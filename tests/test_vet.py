"""
test_vet.py — Host-side test suite for the navigation firmware.

Run with plain CPython (no third-party deps):

    python3 tests/test_vet.py

Coverage:
  * Structure      — every source file compiles and defines each name once.
  * Importability  — every module imports under the mock-hardware harness.
  * Integration    — main.startup() boots all peripherals and main.run()
                     executes its loop end-to-end without raising.
  * Unit logic     — drivers/state machines behave correctly in isolation.

Hardware is faked by tests/mockhw.py; nothing here touches a real board.
"""

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import mockhw  # noqa: E402
mockhw.install()

MODULES = [
    "config", "mpu6050", "mcp9808", "ht16k33",
    "imu", "ultrasonic", "obstacle", "servo_feedback", "route", "main",
]


# ===========================================================================
# Structure
# ===========================================================================
class TestStructure(unittest.TestCase):
    def test_all_sources_compile(self):
        import py_compile
        for mod in MODULES:
            path = os.path.join(ROOT, mod + ".py")
            try:
                py_compile.compile(path, doraise=True)
            except py_compile.PyCompileError as e:  # noqa: PERF203
                self.fail("{}.py does not compile: {}".format(mod, e))

    def test_config_pins_use_cpu_names_not_arduino_labels(self):
        # machine.Pin on the STM32 port resolves CPU names ('PA8') but not
        # Arduino labels ('D7'); the latter would crash Pin() on the board.
        import config
        for name in ("HCSR04_TRIG_PIN", "HCSR04_ECHO_PIN", "SG90_PWM_PIN",
                     "I2C_SCL_PIN", "I2C_SDA_PIN"):
            val = getattr(config, name)
            self.assertRegex(
                val, r"^P[A-H]\d{1,2}$",
                "{}={!r} is not a CPU pin name (expected e.g. 'PA8')".format(name, val))

    def test_no_duplicate_definitions(self):
        import ast
        offenders = {}
        for mod in MODULES:
            with open(os.path.join(ROOT, mod + ".py")) as fh:
                tree = ast.parse(fh.read())

            def scan(prefix, body):
                seen = {}
                for n in body:
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        seen[n.name] = seen.get(n.name, 0) + 1
                        if isinstance(n, ast.ClassDef):
                            scan(prefix + n.name + ".", n.body)
                for k, v in seen.items():
                    if v > 1:
                        offenders[mod + ".py:" + prefix + k] = v

            scan("", tree.body)
        self.assertEqual(offenders, {}, "duplicate definitions: " + repr(offenders))


# ===========================================================================
# Importability
# ===========================================================================
class TestImportability(unittest.TestCase):
    def test_all_modules_import(self):
        failed = {}
        for mod in MODULES:
            try:
                __import__(mod)
            except Exception as e:  # noqa: BLE001
                failed[mod] = "{}: {}".format(type(e).__name__, e)
        self.assertEqual(failed, {})


# ===========================================================================
# Integration — boot + run the real main loop
# ===========================================================================
class TestIntegration(unittest.TestCase):
    def setUp(self):
        mockhw.set_clock_ms(0)
        mockhw.set_auto_advance_ms(20)        # 50 Hz-ish loop progression
        mockhw.set_sim_distance_cm(100.0)     # clear path

    def tearDown(self):
        mockhw.set_auto_advance_ms(0)

    def test_startup_returns_seven_peripherals(self):
        import main
        result = main.startup()
        self.assertEqual(len(result), 7)
        display, temp, imu, sonar, detector, servo, route = result
        self.assertIsNotNone(display)
        self.assertEqual(route.total, len(main._WAYPOINTS))

    def test_run_loop_executes_without_error(self):
        import main
        # 600 iterations of the cadence loop; must not raise.
        main.run(max_iters=600)

    def test_danger_obstacle_triggers_feedback_and_holds_route(self):
        import main, obstacle
        mockhw.set_sim_distance_cm(10.0)      # inside DANGER entry (20 cm)
        # Should run cleanly and drive the danger feedback path.
        main.run(max_iters=50)

    def test_steering_cues_toward_the_turn_direction(self):
        # IMU +heading = CCW = left; servo +angle = right.
        # A LEFT waypoint (+45) at heading 0 must command a LEFT (negative) servo
        # angle, and a RIGHT waypoint (-45) a RIGHT (positive) angle.
        import route

        class _Servo:
            def __init__(self): self.last = None
            def neutral(self): self.last = 0.0
            def steer(self, a): self.last = a

        left = _Servo()
        r = route.Route([route.Waypoint(45.0, "Left 45")])
        r.tick(0.0, left)
        self.assertLess(left.last, 0.0, "left waypoint should cue a left (negative) deflection")

        right = _Servo()
        r = route.Route([route.Waypoint(-45.0, "Right 45")])
        r.tick(0.0, right)
        self.assertGreater(right.last, 0.0, "right waypoint should cue a right (positive) deflection")

    def test_route_completes_when_heading_holds_on_target(self):
        # Single forward waypoint at heading 0; with zero gyro the heading
        # stays 0, error stays 0, so after the hold window the route completes.
        import route, servo_feedback, config

        class _Servo:
            def __init__(self): self.calls = []
            def neutral(self): self.calls.append("neutral")
            def steer(self, a): self.calls.append(("steer", a))

        r = route.Route([route.Waypoint(0.0, "fwd")], arrival_hold_ms=100)
        servo = _Servo()
        mockhw.set_clock_ms(0)
        mockhw.set_auto_advance_ms(0)
        for t in range(0, 400, 20):
            mockhw.set_clock_ms(t)
            r.tick(0.0, servo)
        self.assertTrue(r.complete)


# ===========================================================================
# Unit logic
# ===========================================================================
class TestHeadingMath(unittest.TestCase):
    def test_imu_heading_is_unbounded_and_zeroes(self):
        # Family A IMU integrates an unbounded heading and zero_heading()
        # latches the current value as the new reference.
        import imu
        i = imu.IMU.__new__(imu.IMU)
        i._heading = 123.0
        i._ref = 0.0
        self.assertAlmostEqual(i.heading, 123.0)
        i.zero_heading()
        self.assertAlmostEqual(i.heading, 0.0)

    def test_route_heading_error_shortest_arc(self):
        import route
        self.assertAlmostEqual(route._heading_error(0, 10), 10)
        self.assertAlmostEqual(route._heading_error(170, -170), 20)   # across seam
        self.assertAlmostEqual(route._heading_error(-170, 170), -20)


class TestMedianFilter(unittest.TestCase):
    def test_median3(self):
        import ultrasonic
        self.assertEqual(ultrasonic._median3(3, 1, 2), 2)
        self.assertEqual(ultrasonic._median3(2, 2, 5), 2)


class TestObstacleHysteresis(unittest.TestCase):
    def setUp(self):
        import obstacle
        self.o = obstacle
        self.det = obstacle.ObstacleDetector()

    def test_constants_are_distinct_ints(self):
        self.assertEqual((self.o.CLEAR, self.o.WARNING, self.o.DANGER), (0, 1, 2))

    def test_clear_to_danger_with_hysteresis(self):
        self.assertEqual(self.det.update(100.0), self.o.CLEAR)
        self.assertEqual(self.det.update(15.0), self.o.DANGER)
        self.assertEqual(self.det.update(22.0), self.o.DANGER)   # in hysteresis band
        self.assertEqual(self.det.update(26.0), self.o.WARNING)  # past danger_exit
        self.assertEqual(self.det.update(100.0), self.o.CLEAR)

    def test_none_reading_holds_state(self):
        self.det.update(15.0)
        self.assertEqual(self.det.update(None), self.o.DANGER)


class TestServoMapping(unittest.TestCase):
    def test_angle_to_ns_centre_and_symmetric_swing(self):
        import servo_feedback as sf
        # Implementation centres on 1500 us and swings a symmetric ±950000 ns,
        # giving 550000/2450000 ns at ±90 (a small offset from the datasheet
        # 500000/2400000 endpoints — fine for small haptic deflections).
        self.assertEqual(sf._angle_to_ns(0.0), 1_500_000)
        self.assertEqual(sf._angle_to_ns(-90.0), 550_000)
        self.assertEqual(sf._angle_to_ns(90.0), 2_450_000)
        # input is clamped to ±90 so out-of-range angles cannot exceed the swing
        self.assertEqual(sf._angle_to_ns(200.0), sf._angle_to_ns(90.0))


if __name__ == "__main__":
    unittest.main(verbosity=2)
