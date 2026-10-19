from datetime import UTC, datetime, timedelta

from support import SEED, FakeTime, make_settings

from agent.data.factory import build_source
from agent.data.mock import MockSource
from agent.data.postgres import PostgresSource
from agent.data.simulated_live import SimulatedLiveSource
from agent.domain.models import LiveReading

T0 = datetime(2026, 10, 4, 7, tzinfo=UTC)


class FixedLive:
    """A source whose real live row never changes, like a feed that stopped."""

    def __init__(self, readings: list[LiveReading]) -> None:
        self._readings = readings
        self.since_args: list[datetime | None] = []

    def fetch_since(self, published_after):
        self.since_args.append(published_after)
        return []

    def fetch_live(self):
        return self._readings

    def ping(self) -> bool:
        return True


def reading(pid: str, hr: float | None = 70.0) -> LiveReading:
    return LiveReading(
        person_id=pid,
        sensor_time=T0,
        analytics_window_end=T0,
        values={
            "latest_hr_bpm": hr,
            "latest_motion_g": 0.03,
            "latest_skin_temperature_c": 33.0,
        },
    )


def make(*readings: LiveReading):
    time = FakeTime()
    inner = FixedLive(list(readings))
    return SimulatedLiveSource(inner, time), inner, time


def test_sensor_time_advances_with_the_clock_but_analytics_do_not():
    source, _, time = make(reading("a"))
    assert source.fetch_live()[0].sensor_time == T0
    time.now += 42.9
    out = source.fetch_live()[0]
    assert out.sensor_time == T0 + timedelta(seconds=42)
    assert out.analytics_window_end == T0


def test_values_wobble_near_the_real_reading_and_keep_their_precision():
    source, _, time = make(reading("a"))
    seen: set[float | None] = set()
    for _ in range(40):
        time.now += 1
        values = source.fetch_live()[0].values
        hr, motion, temp = (
            values["latest_hr_bpm"],
            values["latest_motion_g"],
            values["latest_skin_temperature_c"],
        )
        assert hr is not None
        assert motion is not None
        assert temp is not None
        assert abs(hr - 70.0) <= 3.0
        assert abs(motion - 0.03) <= 0.03 * 0.3 + 1e-4
        assert abs(temp - 33.0) <= 0.1 + 1e-2
        assert hr == round(hr, 1)
        seen.add(hr)
    assert len(seen) > 5


def test_missing_values_stay_missing():
    source, _, time = make(reading("a", hr=None))
    time.now += 7
    assert source.fetch_live()[0].values["latest_hr_bpm"] is None


def test_people_do_not_move_in_lockstep_and_the_same_time_repeats():
    source, _, time = make(reading("a"), reading("b"))
    time.now += 5
    a, b = source.fetch_live()
    assert a.values != b.values
    assert source.fetch_live() == [a, b]


def test_no_real_live_row_means_no_simulated_one():
    source, _, _ = make()
    assert source.fetch_live() == []


def test_windows_and_ping_pass_through():
    source, inner, _ = make(reading("a"))
    assert source.fetch_since(T0) == []
    assert inner.since_args == [T0]
    assert source.ping() is True


def test_the_factory_wraps_only_when_asked(tmp_path, monkeypatch):
    monkeypatch.setattr(PostgresSource, "check_read_only", lambda self: None)
    database = {"data_backend": "postgres", "pghost": "db.invalid"}
    plain = build_source(make_settings(tmp_path, **database))
    wrapped = build_source(make_settings(tmp_path, simulate_live=True, **database))
    assert isinstance(plain, PostgresSource)
    assert isinstance(wrapped, SimulatedLiveSource)


def test_simulating_over_the_mock_keeps_its_cohort():
    time = FakeTime()
    mock = MockSource(seed=SEED, time_source=time)
    source = SimulatedLiveSource(mock, time)
    time.now += 3
    assert {r.person_id for r in source.fetch_live()} == {
        r.person_id for r in mock.fetch_live()
    }
