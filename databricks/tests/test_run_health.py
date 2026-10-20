"""Run lifecycle is independent from healthy historical table snapshots."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tiger"))
from session_health import HealthError, evaluate_run, main


def success():
    return {
        "run_id": 10,
        "job_id": 20,
        "end_time": 3600000,
        "state": {"life_cycle_state": "TERMINATED", "result_state": "SUCCESS"},
    }


def test_completed_historical_run_can_pass_without_freshness_claim():
    report = evaluate_run(success(), 10, 20)
    assert report["status"] == "pass"
    assert report["age_hours"] is None


@pytest.mark.parametrize(
    "state",
    [
        {"life_cycle_state": "RUNNING"},
        {"life_cycle_state": "TERMINATED", "result_state": "FAILED"},
        {"life_cycle_state": "TERMINATED", "result_state": "CANCELED"},
    ],
)
def test_active_or_unsuccessful_runs_fail(state):
    run = success()
    run["state"] = state
    assert "run_not_successful" in evaluate_run(run, 10, 20)["failures"]


def test_wrong_run_and_job_are_rejected():
    assert set(evaluate_run(success(), 11, 21)["failures"]) == {
        "unexpected_run_id",
        "unexpected_job_id",
    }


@pytest.mark.parametrize("now", [0, 10801])
def test_future_or_stale_run_fails(now):
    assert (
        "run_outside_freshness_limit"
        in evaluate_run(success(), 10, 20, 1, now=now)["failures"]
    )


def test_recent_run_passes():
    assert evaluate_run(success(), 10, 20, 1, now=7200)["status"] == "pass"


@pytest.mark.parametrize("response", [None, {}, {"state": "secret error"}])
def test_malformed_response_is_sanitized(response):
    with pytest.raises(HealthError, match="^invalid_run_response$"):
        evaluate_run(response, 10, 20)


@pytest.mark.parametrize(
    "options",
    [
        ["--run-id", "10"],
        ["--max-run-age-hours", "1"],
        ["--run-id", "10", "--expected-job-id", "20", "--max-run-age-hours", "nan"],
    ],
)
def test_invalid_cli_contract_fails_before_network(options):
    with pytest.raises(SystemExit) as error:
        main(["--session", "test", "--warehouse", "a" * 16] + options)
    assert error.value.code == 2
