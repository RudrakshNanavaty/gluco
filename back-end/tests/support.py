"""Shared constants and helpers for tests (fixtures live in conftest.py)."""

import uuid
from collections.abc import Callable, Iterable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from agent.auth import Authenticator, Principal
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
        "replay_enabled": False,
        "session_db_path": tmp / "sessions.sqlite",
        "trace_path": tmp / "trace.jsonl",
        **overrides,
    }
    return Settings(_env_file=None, **values)  # pyright: ignore[reportCallIssue]


# --- Clerk sessions -------------------------------------------------------------

ISSUER = "https://clerk.example.test"
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def clerk_token(meta: Any = None, *, key: Any = KEY, **claims: Any) -> str:
    """A Clerk-shaped session token, signed with the test key."""
    body: dict[str, Any] = {
        "sub": "user_1",
        "iss": ISSUER,
        "exp": datetime.now(UTC) + timedelta(hours=1),
        "metadata": meta,
        **claims,
    }
    body = {k: v for k, v in body.items() if v is not None}
    return jwt.encode(body, key, algorithm="RS256")


def authenticator_for(participants: Callable[[], Iterable[str]]) -> Authenticator:
    """The real Authenticator, trusting the test key instead of Clerk's."""
    return Authenticator(lambda _token: KEY.public_key(), ISSUER, participants)


def clerk_user_id(principal: Principal) -> str:
    """The user id `bearer(principal)` signs in as (Clerk accounts have UUIDs)."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, principal.user_id))


def bearer(principal: Principal) -> dict[str, str]:
    """Headers carrying a Clerk session for `principal`."""
    meta = {
        "uuid": clerk_user_id(principal),
        "role": principal.role,
        "participant_id": principal.participant_id,
        "display_name": principal.display_name,
    }
    return {"Authorization": f"Bearer {clerk_token(meta)}"}
