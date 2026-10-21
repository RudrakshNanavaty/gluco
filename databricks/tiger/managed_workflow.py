"""Render a bounded Databricks job; rendering never deploys or starts it."""

import argparse
import json
import re

from replay_config import ReplayConfig


def build_job(
    config, host, port, root, emails, expected_windows, cron=None, sslrootcert=""
):
    if type(expected_windows) is not int or not 1 <= expected_windows <= 15000:
        raise ValueError("Explicit bounded expected window count required")
    if not host or not re.fullmatch(r"[a-zA-Z0-9.-]+", host):
        raise ValueError("Explicit Tiger hostname required")
    if not 1 <= port <= 65535:
        raise ValueError("Invalid Tiger port")
    if not root.startswith("/Workspace/") or ".." in root.split("/"):
        raise ValueError("Explicit absolute Workspace notebook root required")
    if not emails or any(
        not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", e) for e in emails
    ):
        raise ValueError("At least one failure-alert email required")
    common = {
        "session_id": config.session,
        "fixture_id": config.fixture,
        "replay_start": config.anchor,
        "risk_model_version": config.model_version,
        "risk_update_minutes": str(config.cadence),
        "tiger_host": host,
        "tiger_port": str(port),
        "project_root": root,
    }

    def notebook(key, name, params, dependencies=()):
        task = {
            "task_key": key,
            "max_retries": 0,
            "notebook_task": {
                "notebook_path": root + "/" + name,
                "base_parameters": params,
            },
        }
        if dependencies:
            task["depends_on"] = [{"task_key": d} for d in dependencies]
        return task

    from replay_config import instant

    if any(
        instant(value) % 60
        for value in (config.anchor, config.start_at, config.stop_at)
    ):
        raise ValueError("Managed replay times must be minute-aligned")
    # One immutable finite replay batch, never wall-clock advance or retraining.
    from replay_config import instant

    start = 11520 + int((instant(config.start_at) - instant(config.anchor)) // 60)
    stop = 11520 + int((instant(config.stop_at) - instant(config.anchor)) // 60)
    if not 11520 <= start < stop <= 12960 or stop - start > 60:
        raise ValueError(
            "Managed batch must be within the reserved day and at most 60 minutes"
        )
    if start % config.cadence or stop % config.cadence:
        raise ValueError("Batch boundaries must align with scoring cadence")
    batch = {**common, "start_offset": str(start), "end_offset": str(stop)}
    tasks = [
        notebook("prepare", "demo_smoke_test", {**batch, "mode": "prepare"}),
        notebook("emit", "demo_smoke_test", {**batch, "mode": "emit"}, ["prepare"]),
        notebook(
            "bronze",
            "tiger_to_bronze",
            {"tiger_host": host, "tiger_port": str(port), "lookback_minutes": "60"},
            ["emit"],
        ),
        notebook(
            "publish", "demo_smoke_test", {**batch, "mode": "refresh"}, ["bronze"]
        ),
        notebook(
            "verify_publication",
            "verify_publication",
            {
                "session_id": config.session,
                "expected_model": config.model_version,
                "expected_windows": str(expected_windows),
                "sslrootcert": sslrootcert,
                "tiger_host": host,
                "tiger_port": str(port),
                "project_root": root,
            },
            ["publish"],
        ),
    ]
    job = {
        "name": f"Gluco bounded verified replay: {config.session}",
        "max_concurrent_runs": 1,
        "timeout_seconds": 2400,
        "email_notifications": {"on_failure": emails},
        "notification_settings": {
            "no_alert_for_skipped_runs": False,
            "no_alert_for_canceled_runs": False,
        },
        "tasks": tasks,
    }
    if cron:
        job["schedule"] = {
            "quartz_cron_expression": cron,
            "timezone_id": "UTC",
            "pause_status": "PAUSED",
        }
    return job


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="ReplayConfig JSON file")
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, default=5432)
    parser.add_argument("--root", required=True)
    parser.add_argument("--alert-email", action="append", required=True)
    parser.add_argument(
        "--ssl-root-cert",
        default="",
        help="Trusted provider CA path for cloud verification",
    )
    parser.add_argument("--expected-windows", type=int, required=True)
    parser.add_argument(
        "--cron", help="Optional Quartz expression; always rendered PAUSED"
    )
    args = parser.parse_args()
    try:
        with open(args.config) as file:
            config = ReplayConfig(**json.load(file))
        print(
            json.dumps(
                build_job(
                    config,
                    args.host,
                    args.port,
                    args.root,
                    args.alert_email,
                    args.expected_windows,
                    args.cron,
                    args.ssl_root_cert,
                ),
                indent=2,
            )
        )
    except (OSError, ValueError, TypeError):
        parser.error("Invalid workflow configuration")


if __name__ == "__main__":
    main()
