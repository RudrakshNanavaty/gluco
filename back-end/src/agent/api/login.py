"""Clerk sign-in: a verified Clerk session is exchanged for the app's own token."""

import logging

from fastapi import APIRouter, HTTPException

from agent.api.deps import Credentials, CurrentPrincipal, RuntimeDep
from agent.api.schemas import LoginResponse, PrincipalOut
from agent.auth import InvalidTokenError

log = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])


@router.post("/auth/clerk-login")
def clerk_login(credentials: Credentials, runtime: RuntimeDep) -> LoginResponse:
    if runtime.clerk is None:
        raise HTTPException(503, "Clerk authentication is not configured.")
    if credentials is None:
        raise HTTPException(
            401, "A Clerk session is required.", headers={"WWW-Authenticate": "Bearer"}
        )
    try:
        principal = runtime.clerk.verify(
            credentials.credentials, runtime.store.participants()
        )
    except InvalidTokenError as exc:
        # The client only learns "could not be signed in"; the cause stays here.
        log.warning("Clerk sign-in rejected: %s", exc)
        raise HTTPException(
            401,
            "This account could not be signed in.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return LoginResponse(
        token=runtime.signer.issue(principal),
        expires_in=int(runtime.settings.token_ttl_hours * 3600),
        principal=PrincipalOut.of(principal),
    )


@router.get("/me")
def me(principal: CurrentPrincipal) -> PrincipalOut:
    return PrincipalOut.of(principal)
