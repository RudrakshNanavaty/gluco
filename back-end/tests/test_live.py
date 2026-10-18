from datetime import datetime, timedelta

from support import PID, SEED, FakeTime

from agent.auth import CLINICIAN, patient
from agent.clock import ReplayClock
from agent.data.mock import MockSource
from agent.domain.metrics import LIVE_METRICS
from agent.domain.models import LiveReading
from agent.domain.ports import PublishedWindow
from agent.live import LiveStore
from agent.query import QueryService, QuerySpec
from agent.store import WindowStore


class CountingSource(MockSource):
    def __init__(self, time: FakeTime) -> None:
        super().__init__(seed=SEED, time_source=time)
        self.live_calls = 0
        self.window_calls = 0
        self.fail = False
        self.analytics_ahead = False

    def fetch_since(self, published_after: datetime | None) -> list[PublishedWindow]:
        self.window_calls += 1
        return super().fetch_since(published_after)

    def fetch_live(self) -> list[LiveReading]:
        self.live_calls += 1
        if self.fail:
            raise RuntimeError("database down")
        readings = super().fetch_live()
        if self.analytics_ahead:
            readings = [
                r.model_copy(
                    update={"analytics_window_end": r.sensor_time + timedelta(hours=1)}
                )
                for r in readings
            ]
        return readings


def make_live_stores(time: FakeTime) -> tuple[CountingSource, WindowStore, LiveStore]:
    source = CountingSource(time)
    windows = WindowStore(source, refresh_s=1e9, time_source=time)
    return source, windows, LiveStore(source, windows, 1.0, time_source=time)


def test_readings_refresh_at_most_once_per_period():
    time = FakeTime()
    source, _, live = make_live_stores(time)
    first = live.reading(PID)
    assert first is not None
    live.reading(PID)
    assert source.live_calls == 1
    time.now += 5
    later = live.reading(PID)
    assert source.live_calls == 2
    assert later is not None
    assert later.sensor_time - first.sensor_time == timedelta(seconds=5)


def test_a_failed_refresh_keeps_the_previous_readings():
    time = FakeTime()
    source, _, live = make_live_stores(time)
    before = live.reading(PID)
    source.fail = True
    time.now += 2
    assert live.reading(PID) == before
    assert live.reading(PID) == before  # backs off rather than retrying at once
    assert source.live_calls == 2


def test_newer_analytics_make_the_window_store_refresh():
    time = FakeTime()
    source, windows, live = make_live_stores(time)
    live.reading(PID)
    windows.participants()
    loads = source.window_calls
    source.analytics_ahead = True
    time.now += 2
    live.reading(PID)
    windows.participants()  # well inside its own refresh period
    assert source.window_calls > loads


def test_rows_and_queries_carry_the_live_readings():
    time = FakeTime()
    _, windows, live = make_live_stores(time)
    clock = ReplayClock(windows.data_range, enabled=False)
    svc = QueryService(windows, clock, CLINICIAN, live)
    time.now += 3
    reading = live.reading(PID)
    assert reading is not None

    row = svc.participant(PID)
    assert row.live_at == reading.sensor_time
    for metric in LIVE_METRICS:
        assert row.values[metric] == reading.values[metric]
    listed = next(r for r in svc.participants() if r.person_id == PID)
    assert listed == row  # every read sees the same live view
    assert len(svc.live_readings()) == 17
    assert [
        r.person_id
        for r in QueryService(windows, clock, patient(PID), live).live_readings()
    ] == [PID]

    result = svc.query(
        QuerySpec(metrics=["latest_hr_bpm"], participants=[PID], bucket="raw", hours=3)
    )
    last = result.series[0].points[-1]
    assert (last["t"], last["latest_hr_bpm"]) == (
        reading.sensor_time,
        reading.values["latest_hr_bpm"],
    )
    # A query that doesn't ask for live metrics gains no extra point.
    plain = svc.query(QuerySpec(participants=[PID], bucket="raw", hours=3))
    assert plain.series[0].points[-1]["t"] == row.window_end


def test_no_live_readings_while_the_replay_is_behind():
    time = FakeTime()
    _, windows, live = make_live_stores(time)
    clock = ReplayClock(windows.data_range, seconds_per_hour=10, time_source=time)
    svc = QueryService(windows, clock, CLINICIAN, live)
    row = svc.participant(PID)
    assert row.live_at is None
    assert svc.live_readings() == []
