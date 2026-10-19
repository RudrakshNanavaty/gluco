"""Against the real Tiger database: `just test-live` (needs the database in .env).

Skipped in the normal run so `just test` stays offline. What every adapter must
do is in test_window_source.py; these check the real panel's data.
"""

import os

import pytest

from agent.config import Settings
from agent.data.postgres import PostgresSource
from agent.domain.metrics import LIVE_METRICS
from agent.store import WindowStore

pytestmark = pytest.mark.skipif(
    not os.environ.get("LIVE_DB"),
    reason="live database tests run with LIVE_DB=1 and a configured database",
)


@pytest.fixture(scope="module")
def source() -> PostgresSource:
    # Built here, not at import, so the normal run never reads .env.
    settings = Settings(agent_model="unused")  # pyright: ignore[reportCallIssue]
    conninfo = settings.database_conninfo
    if conninfo is None:
        pytest.skip("no database configured in .env")
    return PostgresSource(conninfo, settings.dashboard_session_id)


def test_live_readings_cover_the_panel(source):
    store = WindowStore(source)
    participants = set(store.participants())
    assert len(participants) >= 60
    readings = source.fetch_live()
    assert {r.person_id for r in readings} == participants
    for reading in readings:
        assert set(reading.values) == set(LIVE_METRICS)
        if ":imu50:" in reading.person_id:
            assert reading.values["latest_hr_bpm"] is None


def test_imu_device_has_no_heart_rate(source):
    store = WindowStore(source)
    imu = [pid for pid in store.participants() if ":imu50:" in pid]
    for pid in imu:
        assert all(w.value("hr_mean_bpm_24h") is None for w in store.history(pid))
