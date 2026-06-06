# obstacle.py
# Obstacle classification layer for the HC-SR04 ultrasonic sensor.
#
# Converts a filtered distance reading into one of three states:
#
#   CLEAR   – path is free; no action required
#   WARNING – obstacle detected within warning zone; slow down / alert
#   DANGER  – obstacle within danger zone; stop / emergency response
#
# Hysteresis prevents rapid state toggling near threshold boundaries.
# Each threshold has a separate entry and exit distance so the state
# only changes when the reading crosses the hysteresis band.
#
# Default thresholds (configurable at construction):
#
#   DANGER  zone: distance ≤ 20 cm  (entry), ≥ 25 cm (exit)
#   WARNING zone: distance ≤ 60 cm  (entry), ≥ 65 cm (exit)
#   CLEAR   zone: distance >  65 cm
#
# Usage::
#
#     from obstacle import ObstacleDetector, CLEAR, WARNING, DANGER
#     from ultrasonic import HCSR04
#
#     sonar    = HCSR04('PA8', 'PA9')
#     detector = ObstacleDetector()
#
#     dist  = sonar.distance_cm()
#     state = detector.update(dist)
#     if state == DANGER:
#         stop_motors()

# State constants (use these for comparisons, not raw integers)
CLEAR   = 0
WARNING = 1
DANGER  = 2

_STATE_NAMES = {CLEAR: "CLEAR", WARNING: "WARNING", DANGER: "DANGER"}


class ObstacleDetector:
    """
    Hysteretic obstacle state machine.

    Parameters
    ----------
    danger_entry_cm  : float  Distance at which state enters DANGER (default 20)
    danger_exit_cm   : float  Distance at which state exits  DANGER (default 25)
    warning_entry_cm : float  Distance at which state enters WARNING (default 60)
    warning_exit_cm  : float  Distance at which state exits  WARNING (default 65)
    """

    def __init__(
        self,
        danger_entry_cm  = 20.0,
        danger_exit_cm   = 25.0,
        warning_entry_cm = 60.0,
        warning_exit_cm  = 65.0,
    ):
        if danger_exit_cm <= danger_entry_cm:
            raise ValueError("danger_exit_cm must be > danger_entry_cm")
        if warning_exit_cm <= warning_entry_cm:
            raise ValueError("warning_exit_cm must be > warning_entry_cm")
        if warning_entry_cm <= danger_exit_cm:
            raise ValueError("warning_entry_cm must be > danger_exit_cm")

        self._d_entry  = danger_entry_cm
        self._d_exit   = danger_exit_cm
        self._w_entry  = warning_entry_cm
        self._w_exit   = warning_exit_cm

        self._state    = CLEAR
        self._distance = None   # last valid distance reading

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(self, distance_cm):
        """
        Feed a new distance reading and return the current obstacle state.

        Parameters
        ----------
        distance_cm : float or None
            Filtered distance from HCSR04.distance_cm().
            None is treated as sensor timeout → state held unchanged.

        Returns
        -------
        int : CLEAR, WARNING, or DANGER
        """
        if distance_cm is None:
            # Sensor timeout: hold current state (fail-safe: do not clear)
            return self._state

        self._distance = distance_cm
        state = self._state

        if state == CLEAR:
            if distance_cm <= self._w_entry:
                state = WARNING
            # (no direct CLEAR→DANGER jump; WARNING is the intermediate)

        if state == WARNING:
            if distance_cm <= self._d_entry:
                state = DANGER
            elif distance_cm >= self._w_exit:
                state = CLEAR

        if state == DANGER:
            if distance_cm >= self._d_exit:
                state = WARNING

        self._state = state
        return state

    @property
    def state(self):
        """Current obstacle state (CLEAR, WARNING, or DANGER)."""
        return self._state

    @property
    def state_name(self):
        """Human-readable state string."""
        return _STATE_NAMES.get(self._state, "UNKNOWN")

    @property
    def last_distance(self):
        """Last valid distance reading in cm, or None if never updated."""
        return self._distance
