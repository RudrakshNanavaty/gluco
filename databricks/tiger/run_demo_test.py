#!/usr/bin/env python3
"""Submit a finite recording phase. Uses existing CLI authentication, never DB secrets."""

import argparse
import json
from pathlib import Path
import re
import subprocess


def build_run(session: str, phase: str, overrides: dict[str, str] | None = None) -> dict:
    """`overrides` are notebook parameters (fixture_id, replay_start, tiger_host, ...)
    applied to every task that takes them; the committed JSON keeps its placeholders."""
    if not re.fullmatch(r"[a-z0-9-]{1,50}", session):
        raise ValueError("Session must use 1–50 lowercase letters, digits, or hyphens")
    overrides = overrides or {}
    run = json.loads(Path(__file__).with_name("demo_smoke_test.run.json").read_text())
    phases = {
        "prepare": {"prepare_history"},
        "hour1": {"emit_hour_one", "bronze_hour_one", "dashboard_hour_one"},
        "hour2": {"emit_hour_two", "bronze_hour_two", "dashboard_hour_two"},
    }
    if phase != "all":
        run["tasks"] = [task for task in run["tasks"] if task["task_key"] in phases[phase]]
    selected = {task["task_key"] for task in run["tasks"]}
    for task in run["tasks"]:
        dependencies = [d for d in task.get("depends_on", []) if d["task_key"] in selected]
        if dependencies:
            task["depends_on"] = dependencies
        else:
            task.pop("depends_on", None)
        params = task["notebook_task"]["base_parameters"]
        if task["notebook_task"]["notebook_path"].endswith("/demo_smoke_test"):
            params["session_id"] = session
            params.update(overrides)
        elif "tiger_host" in overrides:
            params["tiger_host"] = overrides["tiger_host"]
            params["tiger_port"] = overrides.get("tiger_port", params["tiger_port"])
    run["run_name"] = f"Gluco demo {session}: {phase}"
    return run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", required=True, help="Use one new ID for all phases of a recording")
    parser.add_argument("--phase", choices=["prepare", "hour1", "hour2", "all"], default="all")
    parser.add_argument("--profile", default="se-project-2")
    parser.add_argument("--fixture", help="e.g. overnight-v1 for the 66-person cohort")
    parser.add_argument("--replay-start", help="ISO time with offset; must match a saved session")
    parser.add_argument("--tiger-host", help="Tiger hostname; also sent to the prepare/emit/refresh notebooks")
    parser.add_argument("--tiger-port", default="5432")
    parser.add_argument("--risk-model-version", help="32-hex release to pin, if the session has none")
    parser.add_argument("--dry-run", action="store_true", help="Print configuration without submitting")
    args = parser.parse_args()
    overrides = {
        key: value
        for key, value in {
            "fixture_id": args.fixture,
            "replay_start": args.replay_start,
            "tiger_host": args.tiger_host,
            "tiger_port": args.tiger_port if args.tiger_host else None,
            "risk_model_version": args.risk_model_version,
        }.items()
        if value
    }
    run = build_run(args.session, args.phase, overrides)
    if args.dry_run:
        print(json.dumps(run, indent=2))
        return
    print("Finite simulated replay; wait for each phase to succeed before starting the next.", flush=True)
    subprocess.run(["databricks", "jobs", "submit", "--profile", args.profile,
                    "--json", json.dumps(run), "--no-wait", "--output", "json"], check=True)


if __name__ == "__main__":
    main()
