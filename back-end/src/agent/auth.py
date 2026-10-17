"""Who is asking: signed tokens, and what each role may see.

Sign-in happens only through Clerk. The server verifies the Clerk session,
reads the role and participant from its server-written metadata, and signs its
own token naming that principal. Every data read is scoped from that token,
never from the UI or the LLM.
"""

import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID

import jwt
from jwt import PyJWKClient, PyJWKClientError

from agent.analysis.ids import display_name

log = logging.getLogger(__name__)

Role = Literal["clinician", "patient"]
ALGORITHM = "HS256"
CLINICIAN_ID = "clinician:demo"
PATIENT_PREFIX = "patient:"
METADATA_CLAIM = "metadata"


@dataclass(frozen=True)
class Principal:
    user_id: str
    role: Role
    display_name: str
    participant_id: str | None = None  # set for patients only

    def can_see(self, person_id: str) -> bool:
        return self.role == "clinician" or person_id == self.participant_id


CLINICIAN = Principal(CLINICIAN_ID, "clinician", "Dr. Demo")


def patient(person_id: str) -> Principal:
    return Principal(
        f"{PATIENT_PREFIX}{person_id}", "patient", display_name(person_id), person_id
    )


class InvalidTokenError(Exception):
    pass


class TokenSigner:
    def __init__(
        self,
        secret: str,
        ttl: timedelta = timedelta(hours=24),
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._secret = secret
        self._ttl = ttl
        self._now = now

    def issue(self, principal: Principal) -> str:
        issued = self._now()
        claims = {
            "sub": principal.user_id,
            "role": principal.role,
            "name": principal.display_name,
            "pid": principal.participant_id,
            "iat": issued,
            "exp": issued + self._ttl,
        }
        return jwt.encode(claims, self._secret, algorithm=ALGORITHM)

    def verify(self, token: str) -> Principal:
        try:
            claims = jwt.decode(
                token,
                self._secret,
                algorithms=[ALGORITHM],
                options={"require": ["sub", "role", "exp"]},
            )
        except jwt.PyJWTError as exc:
            raise InvalidTokenError(str(exc)) from exc
        role = claims["role"]
        if role == "clinician":
            return Principal(
                claims["sub"], "clinician", claims.get("name", "Clinician")
            )
        if role == "patient" and claims.get("pid"):
            return Principal(
                claims["sub"],
                "patient",
                claims.get("name") or display_name(claims["pid"]),
                claims["pid"],
            )
        raise InvalidTokenError("token names no valid role")


class ClerkTokenVerifier:
    """Verify a Clerk session and read who it is from its server-written metadata.

    The seed script stores `{uuid, role, participant_id, display_name}` in each
    Clerk user's `public_metadata`, which only the backend API can write. The
    Clerk dashboard's session token must carry it as the `metadata` claim.
    """

    def __init__(
        self,
        jwks_url: str,
        issuer: str,
        audience: str | None = None,
        timeout: float = 5.0,
    ) -> None:
        self._keys = PyJWKClient(jwks_url, timeout=timeout)
        self._issuer = issuer
        self._audience = audience

    def verify(self, token: str, participant_ids: Iterable[str]) -> Principal:
        claims = self._claims(token)
        meta = claims.get(METADATA_CLAIM)
        if not isinstance(meta, dict):
            raise InvalidTokenError("Clerk session carries no metadata")
        try:
            user_id = str(UUID(str(meta["uuid"])))
        except (KeyError, ValueError) as exc:
            raise InvalidTokenError("Clerk account has no valid uuid") from exc
        name = meta.get("display_name")
        name = name if isinstance(name, str) and name else None
        role = meta.get("role")
        if role == "clinician":
            return Principal(user_id, "clinician", name or "Clinician")
        participant_id = meta.get("participant_id")
        if role == "patient" and participant_id in set(participant_ids):
            return Principal(
                user_id, "patient", name or display_name(participant_id), participant_id
            )
        raise InvalidTokenError("Clerk account is not linked to a patient")

    def _claims(self, token: str) -> dict[str, Any]:
        try:
            key = self._keys.get_signing_key_from_jwt(token).key
            return jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                issuer=self._issuer,
                audience=self._audience,
                options={"require": ["sub", "exp", "iss"]},
            )
        except PyJWKClientError as exc:
            log.warning("Clerk signing keys unavailable or unknown: %s", exc)
            raise InvalidTokenError("Clerk signing key unavailable") from exc
        except jwt.PyJWTError as exc:
            raise InvalidTokenError(f"invalid Clerk session: {exc}") from exc
