# route.py
# Waypoint route state machine.
#
# Manages an ordered list of waypoints, each defined by a target heading
# (degrees relative to the zeroed IMU heading) and an optional label.
# The state machine advances to the next waypoint when the heading error
# falls within ARRIVAL_THRESHOLD_DEG for at least ARRIVAL_HOLD_MS ms.
#
# Integration:
#   - Call route.tick(imu_heading, servo) every loop iteration.
#   - The servo is steered proportionally toward the current waypoint heading.
#   - When all waypoints are visited, route.complete is True.
#
# Usage::
#
#     from route import Route, Waypoint
#     from imu import IMU
#     from servo_feedback import ServoFeedback
#
#     waypoints = [
#         Waypoint(heading=0.0,   label="Start"),
#         Waypoint(heading=45.0,  label="Turn right 45"),
#         Waypoint(heading=-30.0, label="Turn left 30"),
#     ]
#     route = Route(waypoints)
#
#     # in loop:
#     route.tick(imu.heading, servo)
#     if route.complete:
#         print("Route finished")

import utime

# Heading error below which we consider the waypoint "reached"
_ARRIVAL_THRESHOLD_DEG = 5.0
# Must hold within threshold for this long before advancing
_ARRIVAL_HOLD_MS       = 500
# Maximum servo deflection for proportional steering (degrees)
_MAX_STEER_DEG         = 60.0
# Proportional gain: servo_angle = Kp × heading_error (clamped to ±MAX_STEER)
_KP                    = 0.8


class Waypoint:
    """
    A single navigation waypoint.

    Parameters
    ----------
    heading : float
        Target heading in degrees relative to the IMU zero reference.
        Positive = counter-clockwise (right-hand rule, Z-up).
    label   : str
        Human-readable name for logging/display.
    """

    def __init__(self, heading, label=""):
        self.heading = float(heading)
        self.label   = label

    def __repr__(self):
        return "Waypoint(heading={:.1f}, label={!r})".format(
            self.heading, self.label
        )


class Route:
    """
    Ordered waypoint route state machine.

    Parameters
    ----------
    waypoints : list of Waypoint
        Ordered list of waypoints to visit.
    arrival_threshold_deg : float
        Heading error (degrees) within which a waypoint is considered reached.
    arrival_hold_ms : int
        Time (ms) the heading must stay within threshold before advancing.
    """

    def __init__(
        self,
        waypoints,
        arrival_threshold_deg = _ARRIVAL_THRESHOLD_DEG,
        arrival_hold_ms       = _ARRIVAL_HOLD_MS,
    ):
        if not waypoints:
            raise ValueError("waypoints list must not be empty")

        self._waypoints  = list(waypoints)
        self._index      = 0
        self._threshold  = arrival_threshold_deg
        self._hold_ms    = arrival_hold_ms
        self._hold_start = None   # ticks_ms() when we entered the hold window
        self._complete   = False
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

    def tick(self, imu_heading, servo):
        """
        Update the route state machine.

        Parameters
        ----------
        imu_heading : float
            Current heading from IMU.heading (degrees, zeroed at route start).
        servo : ServoFeedback
            Servo instance to steer.  Will be commanded each call.
        """
        if self._complete:
            servo.neutral()
            return

        wp = self._waypoints[self._index]
        error = wp.heading - imu_heading   # positive → need to turn CCW

        # Proportional steering (clamped)
        steer = -_KP * error
        if steer >  _MAX_STEER_DEG:
            steer =  _MAX_STEER_DEG
        elif steer < -_MAX_STEER_DEG:
            steer = -_MAX_STEER_DEG
        servo.steer(steer)

        # Arrival detection with hold timer
        now = utime.ticks_ms()
        if abs(error) <= self._threshold:
            if self._hold_start is None:
                self._hold_start = now
            elif utime.ticks_diff(now, self._hold_start) >= self._hold_ms:
                self._advance()
        else:
            self._hold_start = None   # reset hold timer if we drift out

    @property
    def complete(self):
        """True when all waypoints have been visited."""
        return self._complete

    @property
    def current_waypoint(self):
        """The active Waypoint, or None if the route is complete."""
        if self._complete:
            return None
        return self._waypoints[self._index]

    @property
    def index(self):
        """Zero-based index of the current waypoint."""
        return self._index

    @property
    def total(self):
        """Total number of waypoints in the route."""
        return len(self._waypoints)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _advance(self):
        """Move to the next waypoint, or mark route complete."""
        self._hold_start = None
        self._index += 1
        if self._index >= len(self._waypoints):
            self._complete = True
        # else: next tick() will steer toward the new waypoint
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
