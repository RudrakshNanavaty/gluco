#!/usr/bin/env python3
"""Configurable, resumable, bounded synthetic replay; no production sensor claims."""

import argparse
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from replay_config import ReplayConfig, instant

CONFIG = ReplayConfig.from_env(os.environ)
ROOT = CONFIG.state_root(Path(__file__).resolve().parents[1] / "local-data")
REMOTE = (
    os.environ.get(
        "DATABRICKS_NOTEBOOK_ROOT", "/Workspace/Shared/gluco/databricks/tiger"
    ).rstrip("/")
    + "/"
)
SESSION = CONFIG.session
ANCHOR = CONFIG.anchor
PREP_AT = instant(CONFIG.prepare_at)
START_AT = instant(CONFIG.start_at)
STOP_AT = instant(CONFIG.stop_at)
CLI = os.environ.get("DATABRICKS_CLI", "databricks")
PROFILE = os.environ.get("DATABRICKS_PROFILE", "se-project-2")
TIGER_HOST = os.environ.get("TIGER_HOST", "")
TIGER_PORT = os.environ.get("TIGER_PORT", "5432")


def api(*arguments):
    result = subprocess.run(
        [CLI, *arguments, "--profile", PROFILE, "--output", "json"],
        check=True,
        capture_output=True,
        text=True,
        timeout=90,
    )
    return json.loads(result.stdout or "{}")


def save(state):
    path = ROOT / "state.json"
    temp = ROOT / "state.json.part"
    temp.write_text(json.dumps(state, indent=2))
    os.replace(temp, path)


def tasks_for(state, mode, start=11520, end=11580):
    CONFIG.validate_state(state, state["fixture_id"])
    if mode not in {"prepare", "advance"}:
        raise ValueError("Unknown replay mode")
    if not 11520 <= start < end <= 12960 or end - start > 60:
        raise ValueError("Replay batch must contain 1–60 reserved minutes")
    if not TIGER_HOST or "REPLACE_WITH" in TIGER_HOST:
        raise ValueError("Set a real TIGER_HOST for all replay phases")
    if not REMOTE.startswith("/Workspace/") or "REPLACE_WITH" in REMOTE:
        raise ValueError("Set an absolute workspace notebook root")
    common = {
        "session_id": SESSION,
        "fixture_id": state["fixture_id"],
        "replay_start": ANCHOR,
        "risk_model_version": CONFIG.model_version,
        "tiger_host": TIGER_HOST,
        "tiger_port": TIGER_PORT,
        "tiger_database": os.environ.get("TIGER_DATABASE", "tsdb"),
        "secret_scope": os.environ.get("DATABRICKS_SECRET_SCOPE", "se-project-2"),
        "risk_update_minutes": str(CONFIG.cadence),
        "start_offset": str(start),
        "end_offset": str(end),
    }

    def notebook(key, name, params, parent=None):
        task = {
            "task_key": key,
            "notebook_task": {
                "notebook_path": REMOTE + name,
                "base_parameters": params,
            },
        }
        if parent:
            task["depends_on"] = [{"task_key": parent}]
        return task

    if mode == "prepare":
        tasks = []
        if os.environ.get("GLUCO_REGISTER_FIXTURE") == "true":
            tasks.append(notebook("register", "register_overnight", {}))
        tasks.append(
            notebook(
                "prepare",
                "demo_smoke_test",
                {**common, "mode": "prepare"},
                "register" if tasks else None,
            )
        )
        return tasks
    return [
        notebook("emit", "demo_smoke_test", {**common, "mode": "emit"}),
        notebook(
            "bronze",
            "tiger_to_bronze",
            {
                "tiger_host": TIGER_HOST,
                "tiger_port": TIGER_PORT,
                "lookback_minutes": "60",
                "tiger_database": common["tiger_database"],
                "secret_scope": common["secret_scope"],
            },
            "emit",
        ),
        notebook("refresh", "demo_smoke_test", {**common, "mode": "refresh"}, "bronze"),
    ]


def settle(state, deadline):
    pending = state.get("pending")
    if not pending:
        return
    run_id = pending["run_id"]
    while True:
        if time.time() >= deadline or (ROOT / "STOP").exists():
            api("jobs", "cancel-run", str(run_id))
            state["status"] = "stop_requested"
            save(state)
            raise SystemExit(
                "Stopped; partial batch will be retried idempotently on an authorized resume"
            )
        run = api("jobs", "get-run", str(run_id))
        lifecycle = run["state"]["life_cycle_state"]
        if lifecycle in {"TERMINATED", "SKIPPED", "INTERNAL_ERROR"}:
            if run["state"].get("result_state") != "SUCCESS":
                state["status"] = "needs_attention"
                state["error"] = run["state"]
                save(state)
                raise RuntimeError(
                    f"Databricks run {run_id} did not succeed; cursor not advanced"
                )
            wanted = "prepare" if pending["mode"] == "prepare" else "refresh"
            task = next(t for t in run["tasks"] if t["task_key"] == wanted)
            output = api("jobs", "get-run-output", str(task["run_id"]))
            data = json.loads(output["notebook_output"]["result"])
            if (
                data.get("session_id") != SESSION
                or not isinstance(data.get("participants"), int)
                or data["participants"] < 1
            ):
                raise ValueError("Replay output does not match the requested session")
            (ROOT / "latest_dashboard.json").write_text(json.dumps(data, indent=2))
            if pending["mode"] == "prepare":
                state["ready"] = True
            else:
                state["cursor"] = pending["end"]
            state.update(
                participants=data["participants"],
                last_successful_run=run_id,
                status="ready",
            )
            state.pop("pending", None)
            state.pop("error", None)
            save(state)
            print(
                json.dumps(
                    {
                        "run_id": run_id,
                        "cursor": state["cursor"],
                        "participants": state["participants"],
                    }
                ),
                flush=True,
            )
            return
        time.sleep(15)


def submit(state, mode, end, deadline):
    tasks = tasks_for(state, mode, state["cursor"], end)
    run = api(
        "jobs",
        "submit",
        "--json",
        json.dumps(
            {
                "run_name": f"Gluco {SESSION}: {mode} through {end}",
                "timeout_seconds": min(1800, max(60, int(deadline - time.time()))),
                "tasks": tasks,
            }
        ),
        "--no-wait",
    )
    state["pending"] = {"run_id": run["run_id"], "mode": mode, "end": end}
    state["status"] = "running"
    save(state)
    settle(state, deadline)


def retry_pending(state, deadline, resume_stopped=False):
    """Explicit recovery only after the old cloud run has stopped."""
    pending = state.get("pending")
    if not pending:
        raise ValueError("No pending batch to retry")
    stopped = (ROOT / "STOP").exists()
    if stopped and not resume_stopped:
        raise ValueError("Use --resume-stopped to explicitly clear the STOP marker")
    run = api("jobs", "get-run", str(pending["run_id"]))
    status = run["state"]
    if status["life_cycle_state"] not in {"TERMINATED", "SKIPPED", "INTERNAL_ERROR"}:
        raise ValueError(
            "Pending run is still active; wait for termination before retrying"
        )
    if stopped:
        (ROOT / "STOP").unlink()
    if status.get("result_state") == "SUCCESS":
        settle(state, deadline)
        return
    state.setdefault("retry_history", []).append(
        {**pending, "result_state": status.get("result_state")}
    )
    save(state)
    # Keep the old pending record until submission succeeds; submit replaces it.
    submit(state, pending["mode"], pending["end"], deadline)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=[
            "prepare",
            "advance",
            "live",
            "judge",
            "status",
            "stop",
            "dry-run",
            "retry",
        ],
    )
    parser.add_argument(
        "--fallback",
        action="store_true",
        help="Use the proven 17-person fixture when first preparing",
    )
    parser.add_argument(
        "--background",
        action="store_true",
        help="Detach the live/scheduled controller with a log and sleep prevention",
    )
    parser.add_argument("--batch-minutes", type=int, default=CONFIG.cadence)
    parser.add_argument(
        "--through-offset",
        type=int,
        help="Bound advance/dry-run to a reserved minute offset (11520–12960)",
    )
    parser.add_argument(
        "--resume-stopped",
        action="store_true",
        help="Explicitly clear STOP when retrying a terminated run",
    )
    args = parser.parse_args()
    if args.resume_stopped and args.action != "retry":
        raise ValueError("resume-stopped is only supported for retry")
    if args.through_offset is not None:
        if (
            args.action not in {"advance", "dry-run"}
            or not 11520 <= args.through_offset <= 12960
        ):
            raise ValueError(
                "through-offset requires advance/dry-run and a reserved offset"
            )
    ROOT.mkdir(parents=True, exist_ok=True)
    path = ROOT / "state.json"
    state = (
        json.loads(path.read_text())
        if path.exists()
        else {
            "session_id": SESSION,
            "fixture_id": "nine-day-v1" if args.fallback else CONFIG.fixture,
            "anchor": ANCHOR,
            "cursor": 11520,
            "ready": False,
            "status": "not_started",
            "configuration": CONFIG.identity(
                "nine-day-v1" if args.fallback else CONFIG.fixture
            ),
        }
    )
    if args.fallback and state["fixture_id"] != "nine-day-v1":
        raise ValueError("Cannot switch an established session to a different roster")
    if args.action == "status":
        print(json.dumps(state, indent=2))
        return
    if args.action not in {"status", "stop"}:
        CONFIG.validate_state(state, "nine-day-v1" if args.fallback else CONFIG.fixture)
    if not 1 <= args.batch_minutes <= 60:
        raise ValueError("batch-minutes must be 1–60")
    if args.action == "dry-run":
        print(
            json.dumps(
                tasks_for(
                    state,
                    "advance",
                    state["cursor"],
                    min(
                        args.through_offset or 12960,
                        state["cursor"] + args.batch_minutes,
                    ),
                ),
                indent=2,
            )
        )
        return
    if args.action == "stop":
        (ROOT / "STOP").touch()
        state["status"] = "stop_requested"
        save(state)
        if state.get("pending"):
            api("jobs", "cancel-run", str(state["pending"]["run_id"]))
        print("Stopped new replay batches; dashboard history is preserved")
        return
    if args.background:
        earliest = START_AT if args.action == "judge" else PREP_AT
        if (
            args.action not in {"live", "judge"}
            or not earliest <= time.time() < STOP_AT
        ):
            raise ValueError("Replay is outside its configured execution window")
        # A scheduled noon start must not duplicate an explicitly started feed.
        with (ROOT / "controller.lock").open("a") as probe:
            try:
                fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                print(json.dumps({"already_running": True, "session_id": SESSION}))
                return
        if not state["ready"] or (ROOT / "STOP").exists():
            raise ValueError("Replay must be prepared and not explicitly stopped")
        with (ROOT / "controller.log").open("a") as log:
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-u",
                    str(Path(__file__).resolve()),
                    args.action,
                    "--batch-minutes",
                    str(args.batch_minutes),
                ],
                stdout=log,
                stderr=log,
                start_new_session=True,
            )
            subprocess.Popen(
                ["/usr/bin/caffeinate", "-i", "-s", "-w", str(process.pid)],
                stdout=log,
                stderr=log,
                start_new_session=True,
            )
        (ROOT / "controller_launch.json").write_text(
            json.dumps(
                {
                    "pid": process.pid,
                    "action": args.action,
                    "session_id": SESSION,
                    "started_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        )
        print(json.dumps({"controller_pid": process.pid, "stop_at": CONFIG.stop_at}))
        return
    lock = (ROOT / "controller.lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    if not PREP_AT <= time.time() < STOP_AT:
        raise ValueError("Outside configured prepare/stop window")
    if args.action == "judge" and not START_AT <= time.time() < STOP_AT:
        raise ValueError("Outside configured scheduled replay window")
    if args.action == "live" and not PREP_AT <= time.time() < STOP_AT:
        raise ValueError("Outside configured live replay window")
    if not 1 <= args.batch_minutes <= 60:
        raise ValueError("batch-minutes must be 1–60")
    if args.action == "retry":
        retry_pending(state, min(STOP_AT, time.time() + 2400), args.resume_stopped)
        return
    if (ROOT / "STOP").exists():
        raise ValueError(
            "STOP marker is present; request an explicit resume before clearing it"
        )
    save(state)
    continuous = args.action in {"live", "judge"}
    deadline = STOP_AT if continuous else min(STOP_AT, time.time() + 2400)
    if state.get("pending"):
        settle(state, deadline)
    if args.action == "prepare":
        if not state["ready"]:
            submit(state, "prepare", 11580, deadline)
        print(json.dumps(state, indent=2))
        return
    if not state["ready"]:
        raise ValueError("Run prepare and verify it before replay")
    fixed_target = (
        args.through_offset
        if args.through_offset is not None
        else CONFIG.target(time.time())
    )
    while time.time() < deadline and not (ROOT / "STOP").exists():
        cadence = args.batch_minutes
        target = CONFIG.target(time.time()) if continuous else fixed_target
        backlog = target - state["cursor"]
        if backlog > 0 and (args.action == "advance" or backlog >= cadence):
            submit(
                state,
                "advance",
                state["cursor"] + min(args.batch_minutes, backlog),
                deadline,
            )
        elif args.action == "advance" or state["cursor"] >= 12960:
            break
        else:
            time.sleep(10)
    state["status"] = "stopped" if continuous else "ready"
    save(state)
    print(json.dumps(state, indent=2))


if __name__ == "__main__":
    main()
