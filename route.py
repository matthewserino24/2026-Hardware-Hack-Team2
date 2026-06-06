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


def _heading_error(current_deg, target_deg):
    """Shortest signed angular distance current→target, in (-180, 180].

    Positive means the target is clockwise (to the right) of current.
    Wrap-aware so a turn across the ±180° seam takes the short way round.
    """
    diff = (target_deg - current_deg) % 360.0
    if diff > 180.0:
        diff -= 360.0
    return diff


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
        # Wrap-aware signed error: positive → target is to the right (CW).
        error = _heading_error(imu_heading, wp.heading)

        # Proportional steering (clamped).  Deflect toward the target.
        steer = _KP * error
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
