"""Read-only Databricks replay snapshot health; no freshness or Tiger parity claim."""

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

QUERY = Path(__file__).resolve().parents[1] / "sql" / "session_health.sql"
COUNT_FIELDS = (
    "windows",
    "unique_window_keys",
    "participants",
    "invalid_keys",
    "invalid_scores",
    "invalid_features",
    "invalid_window_lengths",
    "unsafe_demo_flags",
    "invalid_synthetic_fractions",
    "pin_rows",
    "release_rows",
    "score_sync_issues",
    "bronze_events",
    "unique_bronze_keys",
)


class HealthError(RuntimeError):
    """Sanitized operational error code suitable for JSON output."""


def evaluate(
    snapshot,
    expected_participants=None,
    expected_windows=None,
    expected_model=None,
    expected_bronze_events=None,
):
    """Fail on data-contract violations, preserving the raw aggregate evidence."""
    try:
        s = dict(snapshot)
        for field in COUNT_FIELDS:
            s[field] = int(s[field])
            if s[field] < 0:
                raise ValueError()
        s["minimum_participants_per_window"] = (
            int(s["minimum_participants_per_window"])
            if s["minimum_participants_per_window"] is not None
            else None
        )
        for field in (
            "pinned_model",
            "feature_version",
            "artifact_path",
            "earliest_event_time",
            "latest_event_time",
        ):
            if field not in s:
                raise ValueError()
    except (KeyError, TypeError, ValueError) as error:
        raise HealthError("invalid_snapshot") from error
    failures = []

    def require(condition, code):
        if not condition:
            failures.append(code)

    require(s["windows"] > 0 and s["participants"] > 0, "empty_session")
    require(s["windows"] == s["unique_window_keys"], "duplicate_dashboard_keys")
    require(s["bronze_events"] == s["unique_bronze_keys"], "duplicate_bronze_keys")
    for field in (
        "invalid_keys",
        "invalid_scores",
        "invalid_features",
        "invalid_window_lengths",
        "unsafe_demo_flags",
        "invalid_synthetic_fractions",
        "score_sync_issues",
    ):
        require(s[field] == 0, field)
    require(
        s["minimum_participants_per_window"] == s["participants"],
        "incomplete_window_roster",
    )
    require(s["pin_rows"] == 1, "missing_or_duplicate_model_pin")
    require(s["release_rows"] == 1, "missing_or_duplicate_model_release")
    model = s["pinned_model"]
    require(
        isinstance(model, str) and re.fullmatch(r"[a-f0-9]{32}", model) is not None,
        "invalid_model_pin",
    )
    require(s["feature_version"] == "wearable-24h-v1", "unexpected_feature_contract")
    require(
        s["artifact_path"]
        == f"/Volumes/workspace/gluco_models/artifacts/{model}/rolling_risk.joblib",
        "unexpected_artifact_path",
    )
    if expected_participants is not None:
        require(
            s["participants"] == expected_participants, "unexpected_participant_count"
        )
    if expected_windows is not None:
        require(s["windows"] == expected_windows, "unexpected_window_count")
    if expected_model is not None:
        require(model == expected_model, "unexpected_model_pin")
    if expected_bronze_events is not None:
        require(
            s["bronze_events"] == expected_bronze_events,
            "unexpected_bronze_event_count",
        )
    return {
        "status": "fail" if failures else "pass",
        "failures": failures,
        "snapshot": s,
        "limitations": [
            "Read-only Databricks snapshot, not a running-service or physical-sensor test",
            "Historical event time is not wall-clock publication freshness",
            "Tiger publication parity and model artifact contents are not checked",
            "An entirely missing time interval requires caller-supplied expected window count to detect",
        ],
    }


def query_snapshot(
    api, warehouse, session, wait_seconds=60, clock=time.monotonic, sleep=time.sleep
):
    def state(response):
        if not isinstance(response, dict) or not isinstance(
            response.get("status"), dict
        ):
            raise HealthError("invalid_statement_response")
        return response["status"].get("state")

    if not re.fullmatch(r"[a-z0-9-]{1,50}", session):
        raise HealthError("invalid_session_id")
    if not re.fullmatch(r"[a-f0-9]{16}", warehouse):
        raise HealthError("invalid_warehouse_id")
    if not 1 <= wait_seconds <= 300:
        raise HealthError("invalid_wait_limit")
    response = api(
        "post",
        "/api/2.0/sql/statements",
        {
            "warehouse_id": warehouse,
            "statement": QUERY.read_text(),
            "wait_timeout": "0s",
            "row_limit": 1,
            "parameters": [{"name": "session_id", "type": "STRING", "value": session}],
        },
    )
    if not isinstance(response, dict):
        raise HealthError("invalid_statement_response")
    statement_id = response.get("statement_id")
    if not isinstance(statement_id, str) or not re.fullmatch(
        r"[a-f0-9-]{36}", statement_id
    ):
        raise HealthError("invalid_statement_response")
    deadline = clock() + wait_seconds
    while state(response) in ("PENDING", "RUNNING"):
        if clock() >= deadline:
            api("post", f"/api/2.0/sql/statements/{statement_id}/cancel", {})
            raise HealthError("statement_timeout")
        sleep(min(2, max(0, deadline - clock())))
        response = api("get", f"/api/2.0/sql/statements/{statement_id}", None)
        if not isinstance(response, dict):
            raise HealthError("invalid_statement_response")
    if state(response) != "SUCCEEDED":
        raise HealthError("statement_failed")
    try:
        manifest = response["manifest"]
        rows = response["result"]["data_array"]
        columns = [c["name"] for c in manifest["schema"]["columns"]]
        if (
            manifest.get("truncated")
            or len(rows) != 1
            or len(rows[0]) != len(columns)
            or len(columns) != len(set(columns))
        ):
            raise ValueError()
        return statement_id, dict(zip(columns, rows[0]))
    except (AttributeError, KeyError, TypeError, ValueError) as error:
        raise HealthError("invalid_statement_result") from error


def evaluate_run(response, run_id, expected_job_id, max_age_hours=None, now=None):
    """Check one completed run; expose no cloud error bodies or parameters."""
    if not isinstance(response, dict):
        raise HealthError("invalid_run_response")
    try:
        actual_run = response["run_id"]
        job = response["job_id"]
        state = response["state"]
        lifecycle = state["life_cycle_state"]
        result = state.get("result_state")
        end = response.get("end_time", 0)
        if (
            type(actual_run) is not int
            or type(job) is not int
            or not isinstance(lifecycle, str)
            or type(end) is not int
            or end < 0
        ):
            raise ValueError()
    except (KeyError, TypeError, ValueError) as error:
        raise HealthError("invalid_run_response") from error
    failures = []
    if actual_run != run_id:
        failures.append("unexpected_run_id")
    if job != expected_job_id:
        failures.append("unexpected_job_id")
    if lifecycle != "TERMINATED" or result != "SUCCESS":
        failures.append("run_not_successful")
    if not end:
        failures.append("missing_run_end_time")
    age = None
    if max_age_hours is not None:
        now = time.time() if now is None else now
        age = (now - end / 1000) / 3600
        if age < 0 or age > max_age_hours:
            failures.append("run_outside_freshness_limit")
    return {
        "status": "fail" if failures else "pass",
        "failures": failures,
        "run_id": actual_run,
        "job_id": job,
        "life_cycle_state": lifecycle,
        "result_state": result,
        "end_time_ms": end,
        "age_hours": age,
        "limitations": [
            "Selected run only; does not establish recurrence or absence of newer failures",
            "Caller supplies run/session association; not verified publication lineage",
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", required=True)
    parser.add_argument("--warehouse", required=True)
    parser.add_argument("--profile", default="se-project-2")
    parser.add_argument("--cli", default="databricks")
    parser.add_argument("--wait-seconds", type=int, default=60)
    parser.add_argument("--expected-participants", type=int)
    parser.add_argument("--expected-windows", type=int)
    parser.add_argument("--expected-model")
    parser.add_argument("--expected-bronze-events", type=int)
    parser.add_argument("--run-id", type=int)
    parser.add_argument("--expected-job-id", type=int)
    parser.add_argument("--max-run-age-hours", type=float)
    args = parser.parse_args(argv)
    if (args.run_id is None) != (args.expected_job_id is None):
        parser.error("Supply run ID and expected job ID together")
    if any(v is not None and v <= 0 for v in (args.run_id, args.expected_job_id)):
        parser.error("Run and job IDs must be positive")
    if args.max_run_age_hours is not None and (
        args.run_id is None or not 0 < args.max_run_age_hours < float("inf")
    ):
        parser.error("A finite positive run age requires run and job IDs")
    if any(
        v is not None and v <= 0
        for v in (args.expected_participants, args.expected_windows)
    ):
        parser.error("Expected counts must be positive")
    if args.expected_bronze_events is not None and args.expected_bronze_events < 0:
        parser.error("Expected Bronze event count must be nonnegative")
    if args.expected_model is not None and not re.fullmatch(
        r"[a-f0-9]{32}", args.expected_model
    ):
        parser.error("Expected model must be a 32-character lowercase hex release")

    def api(method, path, payload):
        command = [args.cli, "api", method, path, "--profile", args.profile]
        if payload is not None:
            command += ["--json", json.dumps(payload)]
        try:
            result = subprocess.run(
                command, check=True, capture_output=True, text=True, timeout=30
            )
            return json.loads(result.stdout)
        except (subprocess.SubprocessError, OSError, ValueError) as error:
            raise HealthError("cli_request_failed") from error

    try:
        statement_id, snapshot = query_snapshot(
            api, args.warehouse, args.session, args.wait_seconds
        )
        report = evaluate(
            snapshot,
            args.expected_participants,
            args.expected_windows,
            args.expected_model,
            args.expected_bronze_events,
        )
        report.update(session=args.session, statement_id=statement_id)
        if args.run_id is not None:
            run = evaluate_run(
                api("get", f"/api/2.1/jobs/runs/get?run_id={args.run_id}", None),
                args.run_id,
                args.expected_job_id,
                args.max_run_age_hours,
            )
            report["run"] = run
            if run["status"] != "pass":
                report["status"] = "fail"
                report["failures"].extend(run["failures"])
    except HealthError as error:
        print(json.dumps({"status": "error", "error": str(error)}))
        return 2
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    sys.exit(main())
