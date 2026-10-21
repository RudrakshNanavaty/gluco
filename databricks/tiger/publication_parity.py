"""Bounded read-only comparison of Delta and Tiger dashboard publication."""

import argparse
import json
import math
import os
import re
import subprocess
import time

METRICS = (
    "motion_mean_g",
    "temperature_mean_c_24h",
    "wearable_risk_indicator",
    "synthetic_fraction",
)
LIMIT = 15000


class ParityError(RuntimeError):
    """Sanitized operational failure."""


def compare(delta, tiger, expected_windows, expected_model, tolerance=1e-9):
    """Compare exact microsecond keys/model and finite numeric fields."""

    def index(rows):
        indexed = {}
        if not rows or len(rows) > LIMIT:
            raise ParityError("empty_or_oversized_snapshot")
        for row in rows:
            try:
                person, instant, model, *values = row
                if (
                    not isinstance(person, str)
                    or not person
                    or len(values) != len(METRICS)
                ):
                    raise ValueError()
                instant = int(str(instant))
                values = tuple(float(v) for v in values)
                if not all(math.isfinite(v) for v in values):
                    raise ValueError()
                if not isinstance(model, str) or not re.fullmatch(
                    r"[a-f0-9]{32}", model
                ):
                    raise ValueError()
            except (TypeError, ValueError) as error:
                raise ParityError("invalid_publication_row") from error
            key = (person, instant)
            if key in indexed:
                raise ParityError("duplicate_publication_key")
            indexed[key] = (model, values)
        return indexed

    left, right = index(delta), index(tiger)
    failures = []
    if len(left) != expected_windows or len(right) != expected_windows:
        failures.append("unexpected_window_count")
    missing, extra = left.keys() - right.keys(), right.keys() - left.keys()
    if missing or extra:
        failures.append("publication_key_mismatch")
    wrong_models = sum(
        model != expected_model for model, _ in [*left.values(), *right.values()]
    )
    if wrong_models:
        failures.append("unexpected_model")
    mismatches = {name: 0 for name in METRICS}
    max_errors = {name: 0.0 for name in METRICS}
    for key in left.keys() & right.keys():
        for name, a, b in zip(METRICS, left[key][1], right[key][1]):
            difference = abs(a - b)
            if not math.isfinite(difference):
                raise ParityError("numeric_difference_overflow")
            max_errors[name] = max(max_errors[name], difference)
            mismatches[name] += difference > tolerance
    if any(mismatches.values()):
        failures.append("numeric_publication_mismatch")
    return {
        "status": "fail" if failures else "pass",
        "failures": failures,
        "delta_windows": len(left),
        "tiger_windows": len(right),
        "missing_tiger_keys": len(missing),
        "extra_tiger_keys": len(extra),
        "unexpected_model_rows": wrong_models,
        "mismatched_values": mismatches,
        "max_absolute_errors": max_errors,
    }


def delta_rows(api, warehouse, session):
    columns = ",".join(METRICS)
    sql = f"""SELECT participant_key,unix_micros(window_end),
      (SELECT CASE WHEN count(*)=1 THEN min(model_version) END FROM workspace.gluco_demo.replay_risk_models
       WHERE session_id=:session_id),{columns}
      FROM workspace.gluco_demo.dashboard_windows WHERE session_id=:session_id
      LIMIT {LIMIT + 1}"""
    result = api(
        "post",
        "/api/2.0/sql/statements",
        {
            "warehouse_id": warehouse,
            "statement": sql,
            "wait_timeout": "0s",
            "row_limit": LIMIT + 1,
            "parameters": [{"name": "session_id", "type": "STRING", "value": session}],
        },
    )
    identifier = result.get("statement_id")
    if not isinstance(identifier, str) or not re.fullmatch(
        r"[a-f0-9-]{36}", identifier
    ):
        raise ParityError("invalid_statement_id")
    deadline = time.monotonic() + 120
    while result.get("status", {}).get("state") in ("PENDING", "RUNNING"):
        if time.monotonic() >= deadline:
            api("post", f"/api/2.0/sql/statements/{identifier}/cancel", {})
            raise ParityError("statement_timeout")
        time.sleep(2)
        result = api("get", f"/api/2.0/sql/statements/{identifier}", None)
    manifest = result.get("manifest", {})
    if (
        result.get("status", {}).get("state") != "SUCCEEDED"
        or manifest.get("truncated")
        or manifest.get("total_chunk_count") != 1
    ):
        raise ParityError("failed_or_chunked_statement")
    return identifier, result["result"]["data_array"]


def verify_receipt(metadata, output, run_id, session, model, windows):
    """Link an API-selected successful publisher task to its notebook receipt."""
    try:
        state = metadata["state"]
        notebook = output["notebook_output"]
        receipt = json.loads(notebook["result"])
        if (
            metadata["run_id"] != run_id
            or state["life_cycle_state"] != "TERMINATED"
            or state.get("result_state") != "SUCCESS"
            or notebook.get("truncated", False)
            or receipt["session_id"] != session
            or receipt["mode"] not in ("prepare", "refresh", "score_existing")
            or receipt["risk_model_version"] != model
            or receipt["dashboard_rows"] != windows
            or receipt["scored_windows"] != windows
        ):
            raise ValueError()
    except (KeyError, TypeError, ValueError) as error:
        raise ParityError("invalid_publisher_receipt") from error
    return {
        "task_run_id": run_id,
        "session": session,
        "model": model,
        "windows": windows,
        "status": "pass",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", required=True)
    parser.add_argument("--warehouse", required=True)
    parser.add_argument("--expected-windows", type=int, required=True)
    parser.add_argument("--expected-model", required=True)
    parser.add_argument("--profile", default="se-project-2")
    parser.add_argument("--cli", default="databricks")
    parser.add_argument("--publication-task-run-id", type=int)
    args = parser.parse_args()
    if args.publication_task_run_id is not None and args.publication_task_run_id <= 0:
        parser.error("Publication task run ID must be positive")
    if not re.fullmatch(r"[a-z0-9-]{1,50}", args.session):
        parser.error("Invalid session")
    if not re.fullmatch(r"[a-f0-9]{16}", args.warehouse):
        parser.error("Invalid warehouse")
    if not re.fullmatch(r"[a-f0-9]{32}", args.expected_model):
        parser.error("Invalid model")
    if not 1 <= args.expected_windows <= LIMIT:
        parser.error("Expected windows must be within 1..15000")

    def api(method, path, payload):
        command = [args.cli, "api", method, path, "--profile", args.profile]
        if payload is not None:
            command += ["--json", json.dumps(payload)]
        completed = subprocess.run(
            command, capture_output=True, text=True, check=True, timeout=30
        )
        return json.loads(completed.stdout)

    try:
        import psycopg

        conninfo = os.environ["GLUCO_TIGER_CONNINFO"]
        statement, delta = delta_rows(api, args.warehouse, args.session)
        expressions = ",".join(
            f"(payload->>'{name}')::double precision" for name in METRICS
        )
        with psycopg.connect(
            conninfo,
            connect_timeout=15,
            options="-c default_transaction_read_only=on -c statement_timeout=30000",
        ) as connection:
            tiger = connection.execute(
                f"""SELECT participant_key,
                (extract(epoch FROM window_end)*1000000)::bigint,
                payload->>'risk_model_version',{expressions}
                FROM gold.dashboard_windows WHERE session_id=%s LIMIT {LIMIT + 1}""",
                (args.session,),
            ).fetchall()
        report = compare(delta, tiger, args.expected_windows, args.expected_model)
        if args.publication_task_run_id is not None:
            run_id = args.publication_task_run_id
            report["publisher_receipt"] = verify_receipt(
                api("get", f"/api/2.1/jobs/runs/get?run_id={run_id}", None),
                api("get", f"/api/2.1/jobs/runs/get-output?run_id={run_id}", None),
                run_id,
                args.session,
                args.expected_model,
                args.expected_windows,
            )
        report.update(
            session=args.session,
            statement_id=statement,
            limitations=[
                "Separate snapshots; pause replay to avoid concurrent-publication races",
                "Compares four metrics and keys/model, not all payload fields or an immutable audit",
            ],
        )
    except Exception as error:  # noqa: BLE001 - CLI boundary must redact DB/CLI secrets
        # Never expose connection strings, SQL API bodies or source rows.
        code = (
            str(error) if isinstance(error, ParityError) else "publication_check_error"
        )
        print(json.dumps({"status": "error", "error": code}))
        return 2
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
