# route.py — Waypoint route state machine (FR4 + FR5)
# Target: STM32G4 Nucleo-64 (NUCLEO-G474RE), MicroPython
#
# Implements a time/heading-driven state machine that advances through a
# hardcoded list of navigation waypoints and returns a servo intent on
# every tick.
#
# Dependencies (do NOT modify those modules):
#   imu.py          — imu.heading() → float degrees, wrapped (-180, 180]
#   servo_feedback.py — ServoFeedback.tap_left() / tap_right() / neutral()
#
# Servo intents returned by tick():
#   'NEUTRAL'    — hold servo at centre; no haptic stimulus
#   'TAP_LEFT'   — fire one left tap (caller drives servo_feedback)
#   'TAP_RIGHT'  — fire one right tap
#   'FINISHED'   — route complete; hold neutral indefinitely
#
# Heading arithmetic is wrap-aware: the shortest angular distance between
# two headings on the (-180, 180] circle is used for turn completion checks.
#
# §6 example route (hardcoded):
#   Walk straight for 4 s → turn left to -90° → walk straight for 3 s
#   → turn right back to 0° → finish.

import time
from config import HEADING_TOLERANCE_DEG

# ---------------------------------------------------------------------------
# Hardcoded route  (§6 of requirements)
# ---------------------------------------------------------------------------
route = [
    {'action': 'STRAIGHT',    'duration_ms': 4000},
    {'action': 'TURN_LEFT',   'target_heading': -90},
    {'action': 'STRAIGHT',    'duration_ms': 3000},
    {'action': 'TURN_RIGHT',  'target_heading': 0},
    {'action': 'FINISH'},
]

# ---------------------------------------------------------------------------
# Servo intent constants
# ---------------------------------------------------------------------------
NEUTRAL   = 'NEUTRAL'
TAP_LEFT  = 'TAP_LEFT'
TAP_RIGHT = 'TAP_RIGHT'
FINISHED  = 'FINISHED'


# ---------------------------------------------------------------------------
# Heading utility
# ---------------------------------------------------------------------------

def _heading_error(current_deg, target_deg):
    """Return the shortest signed angular distance from current to target.

    Result is in (-180, 180].  Positive means target is clockwise of current.
    Uses only arithmetic — no math module required.
    """
    diff = (target_deg - current_deg) % 360.0
    if diff > 180.0:
        diff -= 360.0
    return diff


# ---------------------------------------------------------------------------
# Route class
# ---------------------------------------------------------------------------

class Route:
    """Waypoint route state machine.

    Typical usage::

        r = Route()
        r.reset()                          # start from waypoint 0

        while True:
            now = time.ticks_ms()
            imu.update(now)
            intent = r.tick(imu.heading(), now)

            if intent == 'TAP_LEFT':
                servo.tap_left()
            elif intent == 'TAP_RIGHT':
                servo.tap_right()
            else:
                servo.neutral()

            servo.tick()
            time.sleep_ms(LOOP_PERIOD_MS)
    """

    def __init__(self):
        self._index     = 0              # current waypoint index into route[]
        self._seg_start = None           # ticks_ms() when this segment began

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def reset(self):
        """Restart from waypoint 0 and reset the segment timer."""
        self._index     = 0
        self._seg_start = time.ticks_ms()

    def current_action(self):
        """Return the action string of the current waypoint, e.g. 'STRAIGHT'."""
        if self._index >= len(route):
            return 'FINISH'
        return route[self._index]['action']

    def tick(self, heading_deg, now_ms):
        """Evaluate the current waypoint and return a servo intent string.

        Parameters
        ----------
        heading_deg : float
            Current heading from imu.heading(), wrapped to (-180, 180].
        now_ms : int
            Current time from time.ticks_ms().

        Returns
        -------
        str
            One of: 'NEUTRAL' | 'TAP_LEFT' | 'TAP_RIGHT' | 'FINISHED'

        Side effects
        ------------
        Advances self._index when the current waypoint's completion
        condition is met, and resets self._seg_start for the next segment.
        """
        # Guard: past end of route
        if self._index >= len(route):
            return FINISHED

        # Initialise segment timer on first tick (or after reset)
        if self._seg_start is None:
            self._seg_start = now_ms

        wp = route[self._index]
        action = wp['action']

        # ------------------------------------------------------------------
        # FINISH — terminal state; never advance further
        # ------------------------------------------------------------------
        if action == 'FINISH':
            return FINISHED

        # ------------------------------------------------------------------
        # STRAIGHT — advance when elapsed time >= duration_ms
        # ------------------------------------------------------------------
        if action == 'STRAIGHT':
            elapsed = time.ticks_diff(now_ms, self._seg_start)
            if elapsed >= wp['duration_ms']:
                self._advance(now_ms)
            return NEUTRAL

        # ------------------------------------------------------------------
        # TURN_LEFT — tap left until |heading - target| <= tolerance
        # ------------------------------------------------------------------
        if action == 'TURN_LEFT':
            target = wp['target_heading']
            if abs(_heading_error(heading_deg, target)) <= HEADING_TOLERANCE_DEG:
                self._advance(now_ms)
                return NEUTRAL
            return TAP_LEFT

        # ------------------------------------------------------------------
        # TURN_RIGHT — tap right until |heading - target| <= tolerance
        # ------------------------------------------------------------------
        if action == 'TURN_RIGHT':
            target = wp['target_heading']
            if abs(_heading_error(heading_deg, target)) <= HEADING_TOLERANCE_DEG:
                self._advance(now_ms)
                return NEUTRAL
            return TAP_RIGHT

        # Unknown action — treat as neutral (defensive)
        return NEUTRAL

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _advance(self, now_ms):
        """Move to the next waypoint and reset the segment start time."""
        self._index    += 1
        self._seg_start = now_ms
