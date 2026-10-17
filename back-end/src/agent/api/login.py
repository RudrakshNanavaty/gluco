"""Persona picker and demo login. No passwords: the signed token is the identity."""

from fastapi import APIRouter, HTTPException

from agent.api.deps import ClerkCredentialsDep, CurrentPrincipal, RuntimeDep
from agent.api.schemas import LoginRequest, LoginResponse, PrincipalOut
from agent.auth import CLINICIAN, InvalidTokenError, persona
from agent.domain.errors import PersonNotFoundError

router = APIRouter(tags=["auth"])


@router.post("/auth/clerk-login")
def clerk_login(credentials: ClerkCredentialsDep, runtime: RuntimeDep) -> LoginResponse:
    if runtime.clerk is None:
        raise HTTPException(503, "Clerk authentication is not configured.")
    if credentials is None:
        raise HTTPException(401, "A Clerk session is required.")
    try:
        principal = runtime.clerk.verify(
            credentials.credentials,
            runtime.store.participants(),
            username_hint=credentials.username_hint,
        )
    except InvalidTokenError as exc:
        raise HTTPException(401, "This Clerk account is not linked to a patient.") from exc
    return LoginResponse(
        token=runtime.signer.issue(principal),
        expires_in=int(runtime.settings.token_ttl_hours * 3600),
        principal=PrincipalOut.of(principal),
    )


@router.get("/personas")
def list_personas(runtime: RuntimeDep) -> list[PrincipalOut]:
    # Never expose the patient directory before authentication.
    return [PrincipalOut.of(CLINICIAN)]


@router.post("/auth/login")
def login(request: LoginRequest, runtime: RuntimeDep) -> LoginResponse:
    try:
        principal = persona(request.persona_id, runtime.store.participants())
    except PersonNotFoundError as exc:
        raise HTTPException(
            404, f"We couldn't find a profile called {request.persona_id!r}."
        ) from exc
    return LoginResponse(
        token=runtime.signer.issue(principal),
        expires_in=int(runtime.settings.token_ttl_hours * 3600),
        principal=PrincipalOut.of(principal),
    )


@router.get("/me")
def me(principal: CurrentPrincipal) -> PrincipalOut:
    return PrincipalOut.of(principal)
