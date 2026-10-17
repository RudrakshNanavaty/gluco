from datetime import UTC, datetime, timedelta

import jwt
import pytest
from support import PID

from agent.auth import CLINICIAN, InvalidTokenError, Principal, TokenSigner, patient

SECRET = "test-secret-that-is-at-least-32-bytes"
OTHER_SECRET = "another-secret-that-is-at-least-32-b"


def test_tokens_round_trip_per_role():
    signer = TokenSigner(SECRET)
    assert signer.verify(signer.issue(CLINICIAN)) == CLINICIAN
    assert signer.verify(signer.issue(patient(PID))) == patient(PID)


def test_tokens_keep_the_clerk_uuid_and_display_name():
    signer = TokenSigner(SECRET)
    ident = "0b0b8a9e-4d3c-5f6a-8b7c-9d0e1f2a3b4c"
    named = Principal(ident, "patient", "Maria Lopez", PID)
    assert signer.verify(signer.issue(named)) == named


def test_tampered_foreign_and_expired_tokens_are_rejected():
    signer = TokenSigner(SECRET)
    token = signer.issue(patient(PID))
    with pytest.raises(InvalidTokenError):
        signer.verify(token[:-2] + ("AA" if token[-2:] != "AA" else "BB"))
    with pytest.raises(InvalidTokenError):
        TokenSigner(OTHER_SECRET).verify(token)
    forged = jwt.encode(
        {
            "sub": "x",
            "role": "clinician",
            "exp": datetime.now(UTC) + timedelta(hours=1),
        },
        OTHER_SECRET,
        algorithm="HS256",
    )
    with pytest.raises(InvalidTokenError):
        signer.verify(forged)
    old = TokenSigner(
        SECRET, ttl=timedelta(hours=1), now=lambda: datetime(2020, 1, 1, tzinfo=UTC)
    )
    with pytest.raises(InvalidTokenError):
        signer.verify(old.issue(CLINICIAN))


def test_patient_token_without_participant_is_rejected():
    token = jwt.encode(
        {"sub": "p", "role": "patient", "exp": datetime.now(UTC) + timedelta(hours=1)},
        SECRET,
        algorithm="HS256",
    )
    with pytest.raises(InvalidTokenError):
        TokenSigner(SECRET).verify(token)
