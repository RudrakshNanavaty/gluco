"""Who is signed in. Sign-in itself happens in Clerk; see `agent.auth`."""

from fastapi import APIRouter

from agent.api.deps import CurrentPrincipal
from agent.api.schemas import PrincipalOut

router = APIRouter(tags=["auth"])


@router.get("/me")
def me(principal: CurrentPrincipal) -> PrincipalOut:
    """The signed-in user's id, role, display name and participant (`GET /me`)."""
    return PrincipalOut.of(principal)
