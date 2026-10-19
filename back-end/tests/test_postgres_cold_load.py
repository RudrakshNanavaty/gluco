"""Regression guard: the first load must stay small enough for the statement timeout.

A real session once had ~33k windows (~49 MB with their JSON payloads). One
`SELECT` over all of them was cancelled by `statement_timeout`, which also covers
sending the rows, so `/me` failed with a 500 and the dashboard never loaded.

The fake table below stands in for that session. Like the real database it
cancels any statement that would return too many rows, so reintroducing an
unbounded or un-trimmed cold-path query fails here without needing Tiger.
"""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import psycopg.errors
import pytest
from fastapi.testclient import TestClient
from psycopg import sql
from support import PID, authenticator_for, bearer, make_settings

from agent.api.app import create_app
from agent.auth import patient
from agent.bootstrap import build_runtime
from agent.data.postgres import WINDOW_PAYLOAD_KEYS, PostgresSource
from agent.store import WindowStore

PEOPLE = [f"demo:big_ideas:{n:03d}" for n in range(1, 18)]  # includes PID
HOURS = 1_900  # 17 people x 1,900 hours ~ 32k rows, like the real session
FIRST_END = datetime(2026, 9, 1, tzinfo=UTC)
BATCH = 500
# What one statement may return before the (simulated) timeout cancels it.
MAX_ROWS_PER_STATEMENT = 5 * BATCH
MAX_PAYLOAD_BYTES_PER_ROW = 1_500
PROVENANCE = {f"provenance_{n}": "x" * 200 for n in range(40)}


def _payload(person: int, hour: int) -> dict[str, Any]:
    return {
        "source_dataset": "big_ideas",
        "window_minutes": 1440,
        "window_end": (FIRST_END + timedelta(hours=hour)).isoformat(),
        "wearable_risk_indicator": 50.0 + (person + hour) % 40,
        "risk_change_24h_points": 1.5,
        "hr_mean_bpm_24h": 70.0 + person,
        "motion_mean_g": 0.02,
        **PROVENANCE,
    }


class ColdTable(PostgresSource):
    """A recording stand-in for gold.dashboard_windows."""

    def __init__(self, batch_size: int = BATCH) -> None:
        super().__init__("postgresql://unused", "s1", batch_size=batch_size)
        # Everyone publishes each hour at the same instant, so keyset paging
        # has to cope with ties on published_at.
        self.table = sorted(
            [
                (
                    FIRST_END + timedelta(hours=hour, minutes=5),
                    person_id,
                    FIRST_END + timedelta(hours=hour),
                    _payload(person, hour),
                )
                for hour in range(HOURS)
                for person, person_id in enumerate(PEOPLE)
            ],
            key=lambda r: r[:3],
        )
        self.statements: list[str] = []
        self.rows_returned: list[int] = []
        self.payload_bytes: list[int] = []

    def _query(self, query, params=()):
        text = query.as_string()
        self.statements.append(text)
        rows = self.table
        if len(params) == 5:  # session, cursor (3), limit
            cursor = tuple(params[1:4])
            rows = [r for r in rows if (r[0], r[1], r[2]) > cursor]
        elif len(params) == 3:  # session, published_after, limit
            rows = [r for r in rows if r[0] >= params[1]]
        if "LIMIT" in text:
            rows = rows[: params[-1]]
        if len(rows) > MAX_ROWS_PER_STATEMENT:
            raise psycopg.errors.QueryCanceled(
                "canceling statement due to statement timeout"
            )
        # The database only sends the keys the statement asked for.
        out = [
            {
                "person_id": person_id,
                "window_end": end,
                "published_at": published,
                "payload": {k: v for k, v in payload.items() if f"'{k}'" in text},
            }
            for published, person_id, end, payload in rows
        ]
        self.rows_returned.append(len(out))
        self.payload_bytes.extend(len(json.dumps(r["payload"])) for r in out)
        return out


def test_the_table_is_as_big_as_the_session_that_broke():
    assert len(ColdTable().table) > 30_000


def test_cold_load_reads_everything_in_bounded_statements():
    source = ColdTable()
    published = source.fetch_since(None)

    assert len(published) == len(source.table)
    assert all("LIMIT" in s for s in source.statements)
    assert max(source.rows_returned) <= BATCH
    assert len(source.statements) > len(source.table) // BATCH


def test_cold_load_leaves_the_provenance_payload_in_the_database():
    source = ColdTable()
    source.fetch_since(None)

    assert max(source.payload_bytes) <= MAX_PAYLOAD_BYTES_PER_ROW
    selected = " ".join(source.statements)
    assert "provenance_" not in selected
    assert all(f"'{key}'" in selected for key in WINDOW_PAYLOAD_KEYS)


def test_paging_neither_skips_nor_repeats_rows_that_share_a_timestamp():
    source = ColdTable()
    keys = [(p.window.person_id, p.window.window_end) for p in source.fetch_since(None)]

    assert keys == [(person_id, end) for _, person_id, end, _ in source.table]


def test_an_incremental_refresh_rereads_only_the_last_timestamp_onward():
    source = ColdTable()
    last = source.table[-1][0]
    refreshed = source.fetch_since(last)

    assert len(refreshed) == len(PEOPLE)
    assert {p.published_at for p in refreshed} == {last}
    assert len(source.statements) == 1


def test_an_unbounded_cold_query_is_cancelled_like_the_real_timeout(monkeypatch):
    """Proves the guard bites: the original single SELECT fails this table."""
    source = ColdTable()
    monkeypatch.setattr(
        source,
        "_window_batch",
        lambda *_: (
            sql.SQL("SELECT payload FROM gold.dashboard_windows WHERE session_id = %s"),
            ("s1",),
        ),
    )
    with pytest.raises(psycopg.errors.QueryCanceled):
        source.fetch_since(None)


def test_first_login_succeeds_on_a_cold_store(tmp_path: Path):
    """The path that broke: /me forces the first load of the whole store."""
    source = ColdTable()
    runtime = build_runtime(make_settings(tmp_path), source=source)
    client = TestClient(
        create_app(runtime, authenticator_for(runtime.store.participants))
    )

    response = client.get("/me", headers=bearer(patient(PID)))

    assert response.status_code == 200
    assert response.json()["participant_id"] == PID
    assert runtime.store.size() == len(source.table)


def test_a_cold_store_survives_many_batches():
    source = ColdTable()
    store = WindowStore(source)

    assert len(store.participants()) == len(PEOPLE)
    assert store.size() == len(source.table)
