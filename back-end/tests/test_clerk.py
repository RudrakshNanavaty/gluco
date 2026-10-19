"""Clerk sign-in: per-request verification, metadata mapping, and the seed script."""

import logging
import re
import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from support import PID, authenticator_for, clerk_token, make_settings

from agent import clerk_seed
from agent.api.app import create_app
from agent.auth import Authenticator, ClerkMetadata, InvalidTokenError
from agent.bootstrap import build_runtime

IDS = [PID, "demo:imu50:00"]
UUID = "0b0b8a9e-4d3c-5f6a-8b7c-9d0e1f2a3b4c"
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def patient_meta(**over: Any) -> dict[str, Any]:
    return {
        "uuid": UUID,
        "role": "patient",
        "participant_id": PID,
        "display_name": "Maria Lopez",
        **over,
    }


@pytest.fixture
def authenticator() -> Authenticator:
    return authenticator_for(lambda: IDS)


def test_patient_session_maps_to_its_participant(authenticator):
    principal = authenticator.authenticate(clerk_token(patient_meta()))
    assert (principal.user_id, principal.role) == (UUID, "patient")
    assert (principal.participant_id, principal.display_name) == (PID, "Maria Lopez")


def test_clinician_session_has_no_participant(authenticator):
    meta = {"uuid": UUID, "role": "clinician", "display_name": "Dr. Priya Shah"}
    principal = authenticator.authenticate(clerk_token(meta))
    assert (principal.role, principal.participant_id) == ("clinician", None)
    assert principal.can_see(PID)


@pytest.mark.parametrize(
    "token",
    [
        pytest.param(clerk_token(None), id="no-metadata"),
        pytest.param(clerk_token("patient"), id="metadata-not-an-object"),
        pytest.param(clerk_token(patient_meta(uuid="nope")), id="bad-uuid"),
        pytest.param(clerk_token(patient_meta(role="admin")), id="unknown-role"),
        pytest.param(
            clerk_token(patient_meta(participant_id="demo:big_ideas:099")),
            id="unknown-participant",
        ),
        pytest.param(clerk_token(patient_meta(), iss="https://evil"), id="issuer"),
        pytest.param(
            clerk_token(patient_meta(), exp=datetime(2020, 1, 1, tzinfo=UTC)),
            id="expired",
        ),
        pytest.param(clerk_token(patient_meta(), key=OTHER_KEY), id="wrong-key"),
        pytest.param("junk", id="not-a-jwt"),
    ],
)
def test_bad_sessions_are_rejected(authenticator, token):
    with pytest.raises(InvalidTokenError):
        authenticator.authenticate(token)


def test_seeded_metadata_signs_its_account_in():
    """The seed script and the Authenticator share one metadata model, so a
    renamed key breaks this test rather than sign-in."""
    patient, doctor = (
        next(a for a in clerk_seed.plan_accounts(IDS, 1) if a.role == role)
        for role in ("patient", "clinician")
    )
    for account in (patient, doctor):
        meta = ClerkMetadata.model_validate(account.metadata)
        principal = meta.principal(IDS)
        assert (principal.user_id, principal.role) == (account.uuid, account.role)
        assert principal.participant_id == account.participant_id
        assert principal.display_name == account.display_name


def test_every_request_is_signed_in_by_its_clerk_session(client):
    assert client.get("/me").status_code == 401
    session = clerk_token(patient_meta())
    me = client.get("/me", headers={"Authorization": f"Bearer {session}"}).json()
    assert (me["user_id"], me["role"], me["participant_id"]) == (UUID, "patient", PID)


def test_username_headers_cannot_pick_a_patient(client):
    """Identity is the session alone, never a header naming an account."""
    response = client.get(
        "/me",
        headers={
            "Authorization": f"Bearer {clerk_token(None)}",
            "X-Clerk-Username": "patient001",
        },
    )
    assert response.status_code == 401


def test_a_rejected_session_logs_why_but_does_not_tell_the_client(client, caplog):
    session = clerk_token(patient_meta(), iss="https://evil")
    with caplog.at_level(logging.WARNING, logger="agent.api.deps"):
        response = client.get("/me", headers={"Authorization": f"Bearer {session}"})
    assert response.status_code == 401
    assert response.json()["detail"] == "Your session has ended. Please sign in again."
    [record] = caplog.records
    reason = record.getMessage().removeprefix("Clerk session rejected: ")
    assert reason
    assert reason not in response.text


def test_serving_the_api_needs_clerk_settings(tmp_path, source):
    runtime = build_runtime(make_settings(tmp_path), source=source)
    with pytest.raises(ValueError, match="CLERK_JWKS_URL and CLERK_ISSUER"):
        create_app(runtime)
    issuer_only = make_settings(tmp_path, clerk_issuer="https://clerk.example.test")
    with pytest.raises(ValueError, match="CLERK_JWKS_URL and CLERK_ISSUER"):
        create_app(build_runtime(issuer_only, source=source))


# --- seed script ----------------------------------------------------------------


def test_plan_is_deterministic_and_collision_free():
    ids = [f"demo:big_ideas:{n:03d}" for n in range(1, 40)]
    first = clerk_seed.plan_accounts(ids, doctors=3)
    again = clerk_seed.plan_accounts(list(reversed(ids)), doctors=3)
    assert first == again
    assert len({a.username for a in first}) == len(first) == 42
    assert len({a.uuid for a in first}) == 42
    assert [a.role for a in first[:3]] == ["clinician"] * 3
    assert all(a.username.startswith("dr-") for a in first[:3])
    assert first[3].uuid == str(uuid.uuid5(clerk_seed.NAMESPACE, f"patient:{ids[0]}"))


def test_existing_accounts_keep_their_username():
    ids = [PID]
    fresh = clerk_seed.plan_accounts(ids, doctors=0)[0]
    kept = clerk_seed.plan_accounts(
        ids, doctors=0, taken_usernames=["taken"], known={fresh.uuid: "renamed"}
    )[0]
    assert kept.username == "renamed"
    clash = clerk_seed.plan_accounts(ids, doctors=0, taken_usernames=[fresh.username])
    assert clash[0].username == f"{fresh.username}2"


class FakeClerk:
    def __init__(self, users: list[dict[str, Any]] | None = None) -> None:
        self.stored = users or []
        self.created: list[clerk_seed.Account] = []
        self.patched: list[str] = []

    def users(self) -> list[dict[str, Any]]:
        return self.stored

    def create(self, account: clerk_seed.Account, password: str) -> None:
        assert password == "pw"
        self.created.append(account)

    def update_metadata(self, clerk_id: str, account: clerk_seed.Account) -> None:
        self.patched.append(clerk_id)


def run_sync(clerk: FakeClerk, *, dry_run: bool = False):
    return clerk_seed.sync(
        clerk,  # pyright: ignore[reportArgumentType]
        lambda taken, known: clerk_seed.plan_accounts(IDS, 1, taken, known),
        "pw",
        dry_run,
    )


def test_sync_creates_once_and_a_rerun_changes_nothing():
    clerk = FakeClerk()
    accounts = run_sync(clerk)
    assert len(clerk.created) == len(accounts) == 3
    clerk.stored = [
        {"id": f"user_{i}", "username": a.username, "public_metadata": a.metadata}
        for i, a in enumerate(clerk.created)
    ]
    clerk.created.clear()
    run_sync(clerk)
    assert clerk.created == []
    assert clerk.patched == []


def test_sync_repairs_drifted_metadata_and_dry_run_writes_nothing():
    account = clerk_seed.plan_accounts(IDS, 0)[0]
    stale = {
        "id": "user_9",
        "username": account.username,
        "public_metadata": {**account.metadata, "role": "clinician"},
    }
    clerk = FakeClerk([stale])
    run_sync(clerk, dry_run=True)
    assert clerk.created == []
    assert clerk.patched == []
    run_sync(clerk)
    assert clerk.patched == ["user_9"]


def test_usernames_use_only_what_clerk_allows():
    ids = [f"demo:big_ideas:{n:03d}" for n in range(1, 40)]
    for account in clerk_seed.plan_accounts(ids, doctors=3):
        assert re.fullmatch(r"[a-z0-9_-]+", account.username), account.username


def test_full_roster_is_the_66_person_cohort():
    roster = clerk_seed.full_roster()
    assert len(roster) == len(set(roster)) == 66
    assert roster[0] == "demo:big_ideas:001"
    assert roster[-1] == "demo:imu50:49"
    assert PID in roster
