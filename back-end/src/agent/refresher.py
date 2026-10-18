"""Refresh in-memory data at most once per period, without blocking readers."""

import logging
import threading
from collections.abc import Callable

log = logging.getLogger(__name__)


class Refresher:
    """Runs `pull` when the data is older than `period_s`, one thread at a time."""

    def __init__(
        self,
        pull: Callable[[], None],
        period_s: float,
        time_source: Callable[[], float],
        what: str,
    ) -> None:
        self._pull = pull
        self._period_s = period_s
        self._time = time_source
        self._what = what
        self._lock = threading.Lock()
        self._at: float | None = None

    def invalidate(self) -> None:
        """Refresh on the next read rather than waiting out the period."""
        self._at = None

    def run(self) -> None:
        """Refresh now, waiting for any refresh in progress; raises on failure."""
        with self._lock:
            self._pull()
            self._at = self._time()

    def run_if_stale(self) -> None:
        """Refresh if the period has passed. Best effort: when another thread is
        already refreshing, or this refresh fails, readers keep the previous data."""
        stale = self._at is None or self._time() - self._at >= self._period_s
        if not stale or not self._lock.acquire(blocking=False):
            return
        try:
            self._pull()
        except Exception:
            log.exception("%s refresh failed; serving the previous data", self._what)
        finally:
            self._at = self._time()  # after a failure, back off until the next period
            self._lock.release()
