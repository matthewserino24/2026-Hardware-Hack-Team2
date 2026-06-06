"""
demo_run.py — Boot the firmware on the host and watch the main loop run.

    python3 tests/demo_run.py

Installs the mock hardware, instruments the servo + display so their commands
are visible, simulates a moving obstacle, and runs a bounded number of loop
iterations.  This is a smoke demo, not a test — it just shows the integrated
system executing end to end without a board.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

import mockhw
mockhw.install()
mockhw.set_clock_ms(0)
mockhw.set_auto_advance_ms(20)   # ~50 Hz loop

import main          # noqa: E402
import servo_feedback  # noqa: E402
import ht16k33         # noqa: E402

# --- instrument the servo so we can see steering / feedback commands -------
_real_set_angle = servo_feedback.ServoFeedback.set_angle
servo_log = []


def _logged_set_angle(self, angle):
    servo_log.append(round(angle, 1))
    return _real_set_angle(self, angle)


servo_feedback.ServoFeedback.set_angle = _logged_set_angle

# --- instrument the display ------------------------------------------------
display_log = []
_real_print_str = ht16k33.HT16K33.print_str
_real_print_float = ht16k33.HT16K33.print_float


def _logged_print_str(self, text, colon=False):
    display_log.append(text)
    return _real_print_str(self, text, colon)


def _logged_print_float(self, value, decimal_places=1):
    display_log.append("{:.{}f}".format(value, decimal_places))
    return _real_print_float(self, value, decimal_places)


ht16k33.HT16K33.print_str = _logged_print_str
ht16k33.HT16K33.print_float = _logged_print_float

print("Booting firmware (mock hardware)...")
mockhw.set_sim_distance_cm(100.0)   # start with a clear path
print("Running main loop, clear path...")
main.run(max_iters=200)

print("Injecting an obstacle at 15 cm (DANGER)...")
mockhw.set_sim_distance_cm(15.0)
main.run(max_iters=200)

print()
print("display showed (in order, deduped): ", end="")
deduped = []
for d in display_log:
    if not deduped or deduped[-1] != d:
        deduped.append(d)
print(deduped)
print("servo angle commands seen        : {} commands, range [{}, {}]".format(
    len(servo_log), min(servo_log), max(servo_log)))
print()
print("OK — booted, ran 400 loop iterations across CLEAR and DANGER states, "
      "no exceptions.")
