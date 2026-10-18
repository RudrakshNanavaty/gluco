"""Validated replay identity and schedule shared by controller and sensor sender."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re

LEGACY_SESSION = "continuous-oct4-v1"


def instant(value):
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Replay times must include a timezone offset")
    return parsed.timestamp()


@dataclass(frozen=True)
class ReplayConfig:
    session: str
    anchor: str
    prepare_at: str
    start_at: str
    stop_at: str
    model_version: str
    fixture: str = "overnight-v1"
    cadence: int = 15

    def __post_init__(self):
        for name in [self.session, self.fixture]:
            if not re.fullmatch(r"[a-z0-9-]{1,50}", name):
                raise ValueError(
                    "Replay identifiers require 1–50 lowercase letters, digits or hyphens"
                )
        if not re.fullmatch(r"[a-f0-9]{32}", self.model_version):
            raise ValueError("An explicit 32-hex model release is required")
        anchor, prepare, start, stop = map(
            instant, [self.anchor, self.prepare_at, self.start_at, self.stop_at]
        )
        if not anchor <= prepare <= start < stop:
            raise ValueError("Require anchor <= prepare <= start < stop")
        if stop - anchor > 1440 * 60:
            raise ValueError(
                "Prepared replay bank supports at most one day after the anchor"
            )
        if self.cadence not in {5, 15, 60}:
            raise ValueError("Analytics cadence must be 5, 15 or 60 minutes")

    @classmethod
    def from_env(cls, env):
        session = env.get("GLUCO_REPLAY_SESSION", LEGACY_SESSION)
        defaults = {
            "ANCHOR": "2026-10-04T07:00:00-04:00",
            "PREPARE_AT": "2026-10-04T08:00:00-04:00",
            "START_AT": "2026-10-04T12:00:00-04:00",
            "STOP_AT": "2026-10-04T15:00:00-04:00",
            "MODEL_VERSION": "0006be934ae7480d922f248ddd25a17d",
        }
        values = {}
        for key, default in defaults.items():
            value = env.get("GLUCO_REPLAY_" + key)
            if value is None:
                if session != LEGACY_SESSION:
                    raise ValueError("New sessions require GLUCO_REPLAY_" + key)
                value = default
            values[key] = value
        return cls(
            session,
            values["ANCHOR"],
            values["PREPARE_AT"],
            values["START_AT"],
            values["STOP_AT"],
            values["MODEL_VERSION"],
            env.get("GLUCO_REPLAY_FIXTURE", "overnight-v1"),
            int(env.get("GLUCO_REPLAY_CADENCE", "15")),
        )

    def state_root(self, base):
        base = Path(base)
        return (
            base / "continuous-demo"
            if self.session == LEGACY_SESSION
            else base / "replay" / self.session
        )

    def identity(self, fixture=None):
        return {
            "session_id": self.session,
            "anchor": self.anchor,
            "fixture_id": fixture or self.fixture,
            "model_version": self.model_version,
            "prepare_at": self.prepare_at,
            "start_at": self.start_at,
            "stop_at": self.stop_at,
            "cadence": self.cadence,
        }

    def validate_state(self, state, fixture=None):
        if state["session_id"] != self.session or state["anchor"] != self.anchor:
            raise ValueError("Stored timeline differs; use a new session")
        if (
            not isinstance(state.get("cursor"), int)
            or not 11520 <= state["cursor"] <= 12960
        ):
            raise ValueError("Stored cursor is outside the reserved replay day")
        if state.get("configuration") != self.identity(fixture):
            raise ValueError(
                "Stored replay configuration differs or is legacy; explicitly migrate before resuming"
            )

    def target(self, now):
        return max(11520, min(12960, 11520 + int((now - instant(self.anchor)) // 60)))
