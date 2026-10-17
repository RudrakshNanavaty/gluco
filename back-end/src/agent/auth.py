"""Who is asking: demo personas, signed tokens, and what each role may see.

There are no passwords. A persona picker logs in as the clinician or as any
participant, and the server signs a token naming that persona. Every data read
is scoped from the token, never from the UI or the LLM.
"""

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from jwt import PyJWKClient

from agent.analysis.ids import display_name
from agent.domain.errors import PersonNotFoundError

Role = Literal["clinician", "patient"]
ALGORITHM = "HS256"
CLINICIAN_ID = "clinician:demo"
PATIENT_PREFIX = "patient:"


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


def personas(participant_ids: Iterable[str]) -> list[Principal]:
    return [CLINICIAN, *(patient(pid) for pid in participant_ids)]


def persona(user_id: str, participant_ids: Iterable[str]) -> Principal:
    """The persona a login names; raises PersonNotFoundError if there is none."""
    if user_id == CLINICIAN_ID:
        return CLINICIAN
    person_id = user_id.removeprefix(PATIENT_PREFIX)
    if user_id.startswith(PATIENT_PREFIX) and person_id in set(participant_ids):
        return patient(person_id)
    raise PersonNotFoundError(user_id)


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
            return patient(claims["pid"])
        raise InvalidTokenError("token names no valid role")


class ClerkTokenVerifier:
    """Verify Clerk sessions and bind them to the in-memory patient directory."""

    def __init__(
        self,
        jwks_url: str,
        issuer: str | None = None,
        audience: str | None = None,
        user_map: dict[str, str] | None = None,
        username_map: dict[str, str] | None = None,
    ) -> None:
        self._keys = PyJWKClient(jwks_url)
        self._issuer = issuer
        self._audience = audience
        self._user_map = user_map or {}
        self._username_map = {key.lower(): value for key, value in (username_map or {}).items()}

    def verify(
        self,
        token: str,
        participant_ids: Iterable[str],
        username_hint: str | None = None,
    ) -> Principal:
        try:
            signing_key = self._keys.get_signing_key_from_jwt(token).key
            options: dict[str, Any] = {"require": ["sub", "exp"]}
            claims = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                issuer=self._issuer,
                audience=self._audience,
                options=options,
            )
        except Exception as exc:
            raise InvalidTokenError("invalid Clerk session") from exc

        participant_ids = set(participant_ids)
        user_id = str(claims["sub"])
        participant_id = self._user_map.get(user_id)
        username = (
            claims.get("username")
            or claims.get("preferred_username")
            or username_hint
        )
        if participant_id is None and isinstance(username, str):
            participant_id = self._username_map.get(username.lower())
        if participant_id not in participant_ids:
            raise InvalidTokenError("Clerk account is not linked to a patient")
        return patient(participant_id)
