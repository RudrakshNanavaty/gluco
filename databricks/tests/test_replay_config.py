"""Replay configuration, task contracts and cursor recovery without cloud calls."""

import copy
import json
import sys
from dataclasses import replace
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tiger"))
from replay_config import ReplayConfig, instant
import continuous_demo as controller


@pytest.fixture
def config():
    return ReplayConfig(
        "test-replay",
        "2026-10-17T10:00:00-04:00",
        "2026-10-17T10:00:00-04:00",
        "2026-10-17T10:05:00-04:00",
        "2026-10-17T11:00:00-04:00",
        "a" * 32,
        cadence=5,
    )


def state_for(config):
    return {
        "session_id": config.session,
        "fixture_id": config.fixture,
        "anchor": config.anchor,
        "cursor": 11520,
        "ready": True,
        "configuration": config.identity(),
    }


def test_new_session_requires_explicit_times_and_model():
    with pytest.raises(ValueError, match="require"):
        ReplayConfig.from_env({"GLUCO_REPLAY_SESSION": "new-session"})


@pytest.mark.parametrize(
    "field,value",
    [
        ("session", "../escape"),
        ("model_version", "latest"),
        ("anchor", "2026-10-17T10:00:00"),
        ("cadence", 7),
        ("stop_at", "2026-10-17T09:00:00-04:00"),
        ("stop_at", "2026-10-19T11:00:00-04:00"),
    ],
)
def test_invalid_config_rejected(config, field, value):
    with pytest.raises(ValueError):
        replace(config, **{field: value})


def test_state_directories_are_session_specific(config, tmp_path):
    assert config.state_root(tmp_path) != replace(config, session="another").state_root(
        tmp_path
    )
    assert config.state_root(tmp_path) == tmp_path / "replay" / config.session


@pytest.mark.parametrize(
    "field,value",
    [
        ("model_version", "b" * 32),
        ("cadence", 15),
        ("fixture", "nine-day-v1"),
        ("stop_at", "2026-10-17T12:00:00-04:00"),
    ],
)
def test_resume_cannot_silently_change_pinned_config(config, field, value):
    with pytest.raises(ValueError, match="differs"):
        replace(config, **{field: value}).validate_state(state_for(config))


def test_unversioned_legacy_state_requires_explicit_migration(config):
    state = state_for(config)
    state.pop("configuration")
    with pytest.raises(ValueError, match="legacy"):
        config.validate_state(state)


def test_target_clamps_to_reserved_day(config):
    assert config.target(instant(config.anchor) - 60) == 11520
    assert config.target(instant(config.anchor) + 300) == 11525
    assert config.target(instant(config.anchor) + 90000) == 12960


@pytest.fixture
def configured_controller(config, monkeypatch):
    monkeypatch.setattr(controller, "CONFIG", config)
    monkeypatch.setattr(controller, "SESSION", config.session)
    monkeypatch.setattr(controller, "ANCHOR", config.anchor)
    monkeypatch.setattr(controller, "TIGER_HOST", "db.example.invalid")
    monkeypatch.setattr(controller, "REMOTE", "/Workspace/Users/test/replay/")
    monkeypatch.delenv("GLUCO_REGISTER_FIXTURE", raising=False)
    return state_for(config)


def test_all_replay_phases_receive_connection_and_pin(configured_controller, config):
    state = configured_controller
    prepared = controller.tasks_for(state, "prepare")
    assert [t["task_key"] for t in prepared] == ["prepare"]
    tasks = controller.tasks_for(state, "advance", 11520, 11525)
    assert [t["task_key"] for t in tasks] == ["emit", "bronze", "refresh"]
    assert tasks[1]["depends_on"] == [{"task_key": "emit"}]
    assert tasks[2]["depends_on"] == [{"task_key": "bronze"}]
    for task in prepared + tasks:
        params = task["notebook_task"]["base_parameters"]
        assert params["tiger_host"] == "db.example.invalid"
        assert "secret_scope" in params
        if task["task_key"] != "bronze":
            assert params["session_id"] == config.session
            assert params["risk_model_version"] == config.model_version
            assert params["risk_update_minutes"] == "5"
    assert "REPLACE_WITH" not in json.dumps(tasks)


@pytest.mark.parametrize(
    "start,end", [(11519, 11525), (11520, 11520), (11520, 11581), (12959, 12961)]
)
def test_batch_bounds_rejected(configured_controller, start, end):
    with pytest.raises(ValueError, match="batch"):
        controller.tasks_for(configured_controller, "advance", start, end)


def test_missing_host_blocks_prepare_too(configured_controller, monkeypatch):
    monkeypatch.setattr(controller, "TIGER_HOST", "")
    with pytest.raises(ValueError, match="TIGER_HOST"):
        controller.tasks_for(configured_controller, "prepare")


def test_failed_run_does_not_advance_cursor(
    configured_controller, monkeypatch, tmp_path
):
    state = copy.deepcopy(configured_controller)
    state["pending"] = {"run_id": 123, "mode": "advance", "end": 11525}
    monkeypatch.setattr(controller, "ROOT", tmp_path)
    monkeypatch.setattr(controller.time, "time", lambda: 100)
    monkeypatch.setattr(
        controller,
        "api",
        lambda *args: {
            "state": {"life_cycle_state": "TERMINATED", "result_state": "FAILED"}
        },
    )
    with pytest.raises(RuntimeError, match="cursor not advanced"):
        controller.settle(state, 200)
    assert state["cursor"] == 11520
    assert state["pending"]["run_id"] == 123


def test_successful_refresh_advances_once(configured_controller, monkeypatch, tmp_path):
    state = copy.deepcopy(configured_controller)
    state["pending"] = {"run_id": 123, "mode": "advance", "end": 11525}
    monkeypatch.setattr(controller, "ROOT", tmp_path)
    monkeypatch.setattr(controller.time, "time", lambda: 100)

    def api(*args):
        if args[1] == "get-run":
            return {
                "state": {"life_cycle_state": "TERMINATED", "result_state": "SUCCESS"},
                "tasks": [{"task_key": "refresh", "run_id": 456}],
            }
        return {
            "notebook_output": {
                "result": json.dumps(
                    {"participants": 66, "session_id": state["session_id"]}
                )
            }
        }

    monkeypatch.setattr(controller, "api", api)
    controller.settle(state, 200)
    assert state["cursor"] == 11525
    assert "pending" not in state
    controller.settle(state, 200)
    assert state["cursor"] == 11525


def test_stop_cancels_pending_run_without_advancing(
    configured_controller, monkeypatch, tmp_path
):
    state = copy.deepcopy(configured_controller)
    state["pending"] = {"run_id": 123, "mode": "advance", "end": 11525}
    (tmp_path / "STOP").touch()
    monkeypatch.setattr(controller, "ROOT", tmp_path)
    monkeypatch.setattr(controller.time, "time", lambda: 100)
    calls = []
    monkeypatch.setattr(controller, "api", lambda *args: calls.append(args))
    with pytest.raises(SystemExit, match="partial batch"):
        controller.settle(state, 200)
    assert calls == [("jobs", "cancel-run", "123")]
    assert state["cursor"] == 11520
    assert state["pending"]["run_id"] == 123


def test_invalid_saved_cursor_rejected(config):
    state = state_for(config)
    state["cursor"] = 12961
    with pytest.raises(ValueError, match="cursor"):
        config.validate_state(state)


def test_dry_run_honors_explicit_short_endpoint(
    configured_controller, monkeypatch, tmp_path, capsys
):
    monkeypatch.setattr(controller, "ROOT", tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "continuous_demo.py",
            "dry-run",
            "--batch-minutes",
            "5",
            "--through-offset",
            "11523",
        ],
    )
    controller.main()
    tasks = json.loads(capsys.readouterr().out)
    assert tasks[0]["notebook_task"]["base_parameters"]["end_offset"] == "11523"
    assert not (tmp_path / "state.json").exists()


def test_retry_event_identity_is_stable_and_session_scoped(config):
    from demo_replay_payload import event_for_minute

    row = {
        "demo_only": True,
        "training_eligible": False,
        "minute_offset": 11520,
        "fixture_id": config.fixture,
        "demo_participant_key": "demo:big_ideas:001",
        "source_participant_key": "big_ideas:001",
        "enmo_mean_g": 0.1,
        "temperature_mean_c": 32,
        "is_synthetic": True,
        "provenance": "test",
        "donor_source_clock": "test",
        "intended_source_clock": "test",
        "unit_status": "test",
        "generation_policy": "test",
    }
    anchor = datetime.fromisoformat(config.anchor)
    first = event_for_minute(row, config.session, anchor)
    assert event_for_minute(row, config.session, anchor) == first
    assert (
        event_for_minute(row, "different-session", anchor)["event_id"]
        != first["event_id"]
    )
    assert first["measurements"]["demo"]["training_eligible"] is False
