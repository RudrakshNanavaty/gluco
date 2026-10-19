"""Synthetic live readings over a real source, for when nothing publishes any.

The windows (and the real live row, as a baseline) still come from the wrapped
source; only the per-second sensor readings are made up. They are simulated, not
measured: a gentle wobble around each participant's last real reading.
"""

import math
import time
import zlib
from collections.abc import Callable
from datetime import datetime, timedelta

from agent.domain.models import LiveReading
from agent.domain.ports import PublishedWindow, WindowSource

# metric -> (relative swing, absolute swing, decimals); the larger swing applies.
_WOBBLE: dict[str, tuple[float, float, int]] = {
    "latest_hr_bpm": (0.0, 3.0, 1),
    "latest_motion_g": (0.3, 0.0, 4),
    "latest_skin_temperature_c": (0.0, 0.1, 2),
}
_PERIOD_S = 10.0 * 2 * math.pi  # one wobble cycle, as in the mock


class SimulatedLiveSource:
    """Implements WindowSource; windows pass through, live readings are simulated."""

    def __init__(
        self,
        inner: WindowSource,
        time_source: Callable[[], float] = time.monotonic,
    ) -> None:
        self._inner = inner
        self._time = time_source
        self._started = time_source()

    def fetch_since(self, published_after: datetime | None) -> list[PublishedWindow]:
        return self._inner.fetch_since(published_after)

    def ping(self) -> bool:
        return self._inner.ping()

    def fetch_live(self) -> list[LiveReading]:
        """The real readings, a second per second on and wobbling."""
        elapsed = int(self._time() - self._started)
        return [self._simulate(r, elapsed) for r in self._inner.fetch_live()]

    @staticmethod
    def _simulate(reading: LiveReading, elapsed: int) -> LiveReading:
        # A stable per-person phase, so participants don't move in lockstep.
        phase = zlib.crc32(reading.person_id.encode()) % 628 / 100
        wobble = math.sin(elapsed * 2 * math.pi / _PERIOD_S + phase)
        values: dict[str, float | None] = {}
        for name, value in reading.values.items():
            relative, absolute, places = _WOBBLE.get(name, (0.0, 0.0, 4))
            if value is None:
                values[name] = None
                continue
            swing = max(abs(value) * relative, absolute)
            values[name] = round(max(value + swing * wobble, 0.0), places)
        return reading.model_copy(
            update={
                "sensor_time": reading.sensor_time + timedelta(seconds=elapsed),
                "values": values,
            }
        )
