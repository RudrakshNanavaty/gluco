"""Adapter logic against a recording stub. Not a live-database test."""

from datetime import UTC, datetime
from decimal import Decimal

from agent.data.postgres import PostgresSource, to_live, to_window
from agent.domain.metrics import GLUCO_CHANGE, GLUCO_SCORE

END = datetime(2026, 10, 4, 7, tzinfo=UTC)
PUBLISHED = datetime(2026, 10, 4, 8, tzinfo=UTC)
PAYLOAD = {
    "source_dataset": "big_ideas",
    "window_minutes": 1440,
    "wearable_risk_indicator": 91.5,
    "risk_change_24h_points": Decimal("87.7"),
    "hr_mean_bpm_24h": 142.9,
    "motion_mean_g": 0.016,
    "temperature_mean_c_24h": "24.2",
    "motion_hr_correlation": None,
    "synthetic_fraction": 0.4,  # provenance: never read
    "demo_only": True,
}


class Recorder(PostgresSource):
    def __init__(self, rows, session_id: str | None = "s1"):
        super().__init__("postgresql://unused", session_id)
        self.rows = rows
        self.queries: list[tuple] = []

    def _query(self, query, params=()):
        self.queries.append(params)
        return self.rows


def test_to_window_inverts_risk_into_gluco_and_keeps_nulls():
    window = to_window("demo:big_ideas:013", END, PAYLOAD)
    assert window.values[GLUCO_SCORE] == 100 - 91.5
    assert window.values[GLUCO_CHANGE] == -87.7
    assert window.values["temperature_mean_c_24h"] == 24.2
    assert window.values["motion_hr_correlation"] is None
    assert window.values["motion_std_g"] is None  # absent, not zero
    assert "synthetic_fraction" not in window.values
    assert (END - window.window_start).total_seconds() == 24 * 3600
    assert window.source_dataset == "big_ideas"


def test_to_window_with_no_prediction():
    window = to_window("p", END, {"wearable_risk_indicator": True})
    assert window.values[GLUCO_SCORE] is None
    assert window.source_dataset == "unknown"


def test_fetch_since_maps_rows_to_published_windows():
    row = {
        "person_id": "demo:big_ideas:013",
        "window_end": END,
        "payload": PAYLOAD,
        "published_at": PUBLISHED,
    }
    [published] = Recorder([row]).fetch_since(PUBLISHED)
    assert published.published_at == PUBLISHED
    assert published.window.person_id == "demo:big_ideas:013"
    assert published.window.values[GLUCO_SCORE] == 100 - 91.5


def test_session_defaults_to_the_most_recently_published():
    source = Recorder([{"session": "latest-run"}], session_id=None)
    assert source.session_id() == "latest-run"
    source.session_id()
    assert len(source.queries) == 1  # cached


def test_no_session_means_no_rows():
    assert Recorder([], session_id=None).fetch_since(None) == []


def test_write_check_reports_a_read_only_role():
    assert Recorder([{"writable": False}]).can_write() is False


LIVE_PAYLOAD = {
    **PAYLOAD,
    "window_end": "2026-10-04T13:45:00+00:00",
    "latest_sensor_time": "2026-10-04T14:06:53+00:00",
    "latest_hr_bpm": None,  # IMU: no heart-rate sensor
    "latest_motion_g": 0.0188,
    "latest_skin_temperature_c": "34.45",
}


def test_to_live_reads_sensor_time_and_keeps_missing_heart_rate():
    reading = to_live("demo:imu50:13", LIVE_PAYLOAD, PUBLISHED)
    assert reading.sensor_time == datetime(2026, 10, 4, 14, 6, 53, tzinfo=UTC)
    assert reading.analytics_window_end == datetime(2026, 10, 4, 13, 45, tzinfo=UTC)
    assert reading.values == {
        "latest_hr_bpm": None,
        "latest_motion_g": 0.0188,
        "latest_skin_temperature_c": 34.45,
    }
    fallback = to_live("p", {}, PUBLISHED)
    assert (fallback.sensor_time, fallback.analytics_window_end) == (PUBLISHED, None)


def test_windows_carry_the_live_snapshot_too():
    window = to_window("p", END, LIVE_PAYLOAD)
    assert window.values["latest_motion_g"] == 0.0188


def test_fetch_live_maps_rows_to_readings():
    row = {
        "person_id": "demo:imu50:13",
        "payload": LIVE_PAYLOAD,
        "sensor_published_at": PUBLISHED,
    }
    [reading] = Recorder([row]).fetch_live()
    assert reading.person_id == "demo:imu50:13"
    assert reading.values["latest_motion_g"] == 0.0188
