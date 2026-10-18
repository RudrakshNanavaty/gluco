"""Shared constants and helpers for tests (fixtures live in conftest.py)."""

from pathlib import Path
from typing import Any

from agent.config import Settings

PID = "demo:big_ideas:013"  # the pinned sharp drop in the mock data
OTHER = "demo:big_ideas:002"
SEED = 7  # the mock data every test runs against


class FakeTime:
    """A controllable monotonic clock, in seconds."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def make_settings(tmp: Path, **overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "agent_model": "test-model",
        "data_backend": "mock",
        "allow_dev_auth_secret": True,
        "replay_enabled": False,
        "session_db_path": tmp / "sessions.sqlite",
        "trace_path": tmp / "trace.jsonl",
        **overrides,
    }
    return Settings(_env_file=None, **values)  # pyright: ignore[reportCallIssue]
