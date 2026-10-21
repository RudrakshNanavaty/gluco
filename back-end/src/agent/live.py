"""In-memory copy of everyone's newest sensor readings, refreshed every second.

The live readings are one small row per participant, so the store re-reads all of it
whenever a reader finds it older than `refresh_s`; polling never triggers any
computation upstream. When the readings show analytics newer than the window
store holds, the window store is told to refresh on its next read, so new
windows appear within about a second instead of waiting out its own period.
"""

import time
from collections.abc import Callable

from agent.domain.models import LiveReading
from agent.domain.ports import WindowSource
from agent.refresher import Refresher
from agent.store import WindowStore


class LiveStore:
    """In-memory copy of each participant's newest live readings, re-read when a reader
    finds it older than `refresh_s`. When the readings show analytics newer than the
    window store holds, that store is told to refresh.
    """

    def __init__(
        self,
        source: WindowSource,
        windows: WindowStore,
        refresh_s: float = 1.0,
        time_source: Callable[[], float] = time.monotonic,
    ) -> None:
        self._source = source
        self._windows = windows
        self._readings: dict[str, LiveReading] = {}
        self._refresher = Refresher(self._pull, refresh_s, time_source, "live")

    def _pull(self) -> None:
        readings = {r.person_id: r for r in self._source.fetch_live()}
        self._readings = readings
        newest = max(
            (
                r.analytics_window_end
                for r in readings.values()
                if r.analytics_window_end
            ),
            default=None,
        )
        bounds = self._windows.data_range()
        if newest is not None and (bounds is None or newest > bounds[1]):
            self._windows.invalidate()

    def reading(self, person_id: str) -> LiveReading | None:
        """The person's newest readings; a failed refresh keeps the old ones."""
        self._refresher.run_if_stale()
        return self._readings.get(person_id)
