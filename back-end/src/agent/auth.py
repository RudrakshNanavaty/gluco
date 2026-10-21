"""Who is asking: the Clerk session behind each request, and what each role may see.

Sign-in happens only through Clerk. Every request carries the user's Clerk
session token. The Authenticator verifies it, reads the role and participant
from its server-written metadata, and returns the Principal. Every data read is
scoped from that Principal, never from the UI or the LLM (ADR 0001).
"""

import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any, Literal
from uuid import UUID

import jwt
from jwt import PyJWKClient, PyJWKClientError
from pydantic import BaseModel, ConfigDict, ValidationError

from agent.analysis.ids import display_name

log = logging.getLogger(__name__)

Role = Literal["clinician", "patient"]
CLINICIAN_ID = "clinician:demo"
PATIENT_PREFIX = "patient:"
METADATA_CLAIM = "metadata"


@dataclass(frozen=True)
class Principal:
    """The signed-in user: id, role, display name and, for patients, the participant
    they are. Every data read is scoped from it.
    """

    user_id: str
    role: Role
    display_name: str
    participant_id: str | None = None  # set for patients only

    def can_see(self, person_id: str) -> bool:
        return self.role == "clinician" or person_id == self.participant_id


CLINICIAN = Principal(CLINICIAN_ID, "clinician", "Dr. Demo")


def patient(person_id: str) -> Principal:
    """The Principal of the patient who is participant `person_id`."""
    return Principal(
        f"{PATIENT_PREFIX}{person_id}", "patient", display_name(person_id), person_id
    )


class InvalidTokenError(Exception):
    """A Clerk session token that cannot be accepted: bad or expired, no valid metadata,
    an unknown signing key, or an account not linked to a known participant.
    """

    pass


class ClerkMetadata(BaseModel):
    """What a Clerk user's `public_metadata` holds.

    `clerk_seed` writes it and the Authenticator reads it, so the two can never
    disagree on a key. Only the backend API can write public_metadata; the Clerk
    dashboard's session token must carry it as the `metadata` claim.
    """

    model_config = ConfigDict(frozen=True)

    uuid: UUID
    role: Role
    participant_id: str | None = None
    display_name: str | None = None

    def principal(self, participant_ids: Iterable[str]) -> Principal:
        """Who this account is; a patient must be linked to a known participant."""
        user_id = str(self.uuid)
        if self.role == "clinician":
            return Principal(user_id, "clinician", self.display_name or "Clinician")
        pid = self.participant_id
        if pid is None or pid not in set(participant_ids):
            raise InvalidTokenError("Clerk account is not linked to a patient")
        return Principal(
            user_id, "patient", self.display_name or display_name(pid), pid
        )


# The key that signed a token. Clerk's JWKS in production, a fixed key in tests.
KeyResolver = Callable[[str], Any]


def jwks_keys(url: str, timeout: float = 5.0) -> KeyResolver:
    """Clerk's signing keys, fetched from its JWKS endpoint and cached."""
    client = PyJWKClient(url, timeout=timeout)

    def key(token: str) -> Any:
        try:
            return client.get_signing_key_from_jwt(token).key
        except PyJWKClientError as exc:
            log.warning("Clerk signing keys unavailable or unknown: %s", exc)
            raise InvalidTokenError("Clerk signing key unavailable") from exc

    return key


class Authenticator:
    """Turns a request's Clerk session token into a Principal."""

    def __init__(
        self,
        keys: KeyResolver,
        issuer: str,
        participants: Callable[[], Iterable[str]],
        audience: str | None = None,
    ) -> None:
        self._keys = keys
        self._issuer = issuer
        self._participants = participants
        self._audience = audience

    def authenticate(self, bearer: str) -> Principal:
        try:
            claims = jwt.decode(
                bearer,
                self._keys(bearer),
                algorithms=["RS256"],
                issuer=self._issuer,
                audience=self._audience,
                options={"require": ["sub", "exp", "iss"]},
            )
        except jwt.PyJWTError as exc:
            raise InvalidTokenError(f"invalid Clerk session: {exc}") from exc
        try:
            meta = ClerkMetadata.model_validate(claims.get(METADATA_CLAIM))
        except ValidationError as exc:
            raise InvalidTokenError("Clerk session carries no valid metadata") from exc
        return meta.principal(self._participants())
