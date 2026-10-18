"""The WindowSource contract, run against every adapter.

The mock adapter always runs. The Postgres adapter runs with LIVE_DB=1 and a
database configured in .env (`just test-live`), so `just test` stays offline.
"""

import os
from collections.abc import Callable

import pytest
from support import SEED

from agent.config import Settings
from agent.data.mock import MockSource
from agent.data.postgres import PostgresSource
from agent.domain.metrics import GLUCO_SCORE, LIVE_METRICS, METRICS
from agent.domain.ports import WindowSource


def mock() -> WindowSource:
    return MockSource(seed=SEED)


def postgres() -> WindowSource:
    if not os.environ.get("LIVE_DB"):
        pytest.skip("the Postgres adapter runs with LIVE_DB=1")
    # Built here, not at import, so the normal run never reads .env.
    settings = Settings(agent_model="unused")  # pyright: ignore[reportCallIssue]
    conninfo = settings.database_conninfo
    if conninfo is None:
        pytest.skip("no database configured in .env")
    return PostgresSource(conninfo, settings.dashboard_session_id)


@pytest.fixture(scope="module", params=[mock, postgres], ids=["mock", "postgres"])
def source(request: pytest.FixtureRequest) -> WindowSource:
    build: Callable[[], WindowSource] = request.param
    return build()


def test_it_answers_a_ping(source: WindowSource):
    assert source.ping()


def test_windows_carry_known_metrics_and_a_bounded_score(source: WindowSource):
    published = source.fetch_since(None)
    assert published
    for row in published:
        window = row.window
        assert set(window.values) <= set(METRICS)
        assert window.window_start < window.window_end
        score = window.value(GLUCO_SCORE)
        assert score is None or 0 <= score <= 100


def test_fetch_since_returns_only_rows_published_at_or_after(source: WindowSource):
    every = source.fetch_since(None)
    times = sorted({row.published_at for row in every})
    cutoff = times[len(times) // 2]
    later = source.fetch_since(cutoff)
    assert later
    assert all(row.published_at >= cutoff for row in later)
    assert {(r.window.person_id, r.window.window_end) for r in later} <= {
        (r.window.person_id, r.window.window_end) for r in every
    }


def test_live_readings_are_one_per_known_participant(source: WindowSource):
    participants = {row.window.person_id for row in source.fetch_since(None)}
    readings = source.fetch_live()
    people = [r.person_id for r in readings]
    assert len(people) == len(set(people))
    assert set(people) <= participants
    for reading in readings:
        assert set(reading.values) == set(LIVE_METRICS)
