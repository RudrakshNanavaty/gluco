"""Read-only snapshot invariants and bounded Statement API failure handling."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tiger"))
from session_health import HealthError, evaluate, query_snapshot

MODEL = "a" * 32
STATEMENT = "a" * 8 + "-" + "b" * 4 + "-" + "c" * 4 + "-" + "d" * 4 + "-" + "e" * 12


def healthy():
    return {
        "windows": "132",
        "unique_window_keys": "132",
        "participants": "66",
        "invalid_keys": "0",
        "invalid_scores": "0",
        "invalid_features": "0",
        "invalid_window_lengths": "0",
        "unsafe_demo_flags": "0",
        "invalid_synthetic_fractions": "0",
        "pin_rows": "1",
        "release_rows": "1",
        "score_sync_issues": "0",
        "bronze_events": "330",
        "unique_bronze_keys": "330",
        "minimum_participants_per_window": "66",
        "pinned_model": MODEL,
        "feature_version": "wearable-24h-v1",
        "artifact_path": f"/Volumes/workspace/gluco_models/artifacts/{MODEL}/rolling_risk.joblib",
        "earliest_event_time": "2020-01-01",
        "latest_event_time": "2020-01-02",
    }


def test_historical_event_time_is_not_a_freshness_failure():
    report = evaluate(healthy(), 66, 132, MODEL)
    assert report["status"] == "pass" and report["failures"] == []
    assert any("Historical" in s for s in report["limitations"])


@pytest.mark.parametrize(
    "field,value,code",
    [
        ("unique_window_keys", "131", "duplicate_dashboard_keys"),
        ("unique_bronze_keys", "329", "duplicate_bronze_keys"),
        ("invalid_scores", "1", "invalid_scores"),
        ("invalid_features", "1", "invalid_features"),
        ("unsafe_demo_flags", "1", "unsafe_demo_flags"),
        ("score_sync_issues", "1", "score_sync_issues"),
        ("minimum_participants_per_window", "65", "incomplete_window_roster"),
        ("pin_rows", "2", "missing_or_duplicate_model_pin"),
        ("release_rows", "0", "missing_or_duplicate_model_release"),
        ("artifact_path", "/tmp/other.joblib", "unexpected_artifact_path"),
    ],
)
def test_contract_violation_is_reported(field, value, code):
    s = healthy()
    s[field] = value
    report = evaluate(s)
    assert report["status"] == "fail" and code in report["failures"]


def test_explicit_expected_counts_and_model_detect_complete_missing_intervals():
    r = evaluate(healthy(), 67, 198, "b" * 32)
    assert set(r["failures"]) == {
        "unexpected_participant_count",
        "unexpected_window_count",
        "unexpected_model_pin",
    }


def test_unknown_session_with_zero_rows_is_not_a_pass():
    s = healthy()
    s.update(
        windows="0",
        unique_window_keys="0",
        participants="0",
        minimum_participants_per_window=None,
        pin_rows="0",
        release_rows="0",
        pinned_model=None,
        feature_version=None,
        artifact_path=None,
    )
    assert "empty_session" in evaluate(s)["failures"]


def test_missing_or_malformed_aggregate_is_operational_error():
    s = healthy()
    s.pop("invalid_scores")
    with pytest.raises(HealthError, match="invalid_snapshot"):
        evaluate(s)


def result(truncated=False):
    return {
        "statement_id": STATEMENT,
        "status": {"state": "SUCCEEDED"},
        "manifest": {
            "truncated": truncated,
            "schema": {"columns": [{"name": "windows"}]},
        },
        "result": {"data_array": [["132"]]},
    }


def test_statement_uses_bound_session_and_polls_pending_result():
    calls = []

    def api(method, path, payload):
        calls.append((method, path, payload))
        return (
            {"statement_id": STATEMENT, "status": {"state": "PENDING"}}
            if method == "post"
            else result()
        )

    statement, row = query_snapshot(api, "a" * 16, "demo-session", sleep=lambda _: None)
    assert statement == STATEMENT and row == {"windows": "132"}
    assert calls[0][2]["parameters"] == [
        {"name": "session_id", "type": "STRING", "value": "demo-session"}
    ]
    assert calls[1][0] == "get"


def test_invalid_session_is_rejected_before_network():
    def api(*args):
        pytest.fail("Unexpected network request")

    with pytest.raises(HealthError, match="invalid_session_id"):
        query_snapshot(api, "a" * 16, "x'; DROP TABLE t")


def test_own_running_statement_is_canceled_on_timeout():
    now = [0]
    calls = []

    def api(method, path, payload):
        calls.append((method, path))
        return {"statement_id": STATEMENT, "status": {"state": "RUNNING"}}

    def sleep(seconds):
        now[0] += seconds

    with pytest.raises(HealthError, match="statement_timeout"):
        query_snapshot(
            api, "a" * 16, "demo", wait_seconds=1, clock=lambda: now[0], sleep=sleep
        )
    assert calls[-1] == ("post", f"/api/2.0/sql/statements/{STATEMENT}/cancel")


def test_truncated_success_is_rejected():
    with pytest.raises(HealthError, match="invalid_statement_result"):
        query_snapshot(lambda *args: result(True), "a" * 16, "demo")


def test_cloud_error_details_are_not_exposed():
    def api(*args):
        return {
            "statement_id": STATEMENT,
            "status": {"state": "FAILED", "error": {"message": "private data"}},
        }

    with pytest.raises(HealthError, match="^statement_failed$"):
        query_snapshot(api, "a" * 16, "demo")


def test_expected_bronze_events_detects_missing_ingestion():
    r = evaluate(healthy(), expected_bronze_events=396)
    assert r["failures"] == ["unexpected_bronze_event_count"]


def test_cli_passes_expected_bronze_events_to_evaluation(monkeypatch, capsys):
    import json

    import session_health

    monkeypatch.setattr(
        session_health, "query_snapshot", lambda *args: (STATEMENT, healthy())
    )
    assert (
        session_health.main(
            [
                "--session",
                "demo",
                "--warehouse",
                "a" * 16,
                "--expected-bronze-events",
                "396",
            ]
        )
        == 1
    )
    report = json.loads(capsys.readouterr().out)
    assert report["failures"] == ["unexpected_bronze_event_count"]


def test_malformed_api_envelope_is_sanitized():
    with pytest.raises(HealthError, match="^invalid_statement_response$"):
        query_snapshot(lambda *args: [], "a" * 16, "demo")


def test_malformed_status_is_not_a_success_or_traceback():
    response = {"statement_id": STATEMENT, "status": None}
    with pytest.raises(HealthError, match="^invalid_statement_response$"):
        query_snapshot(lambda *args: response, "a" * 16, "demo")
