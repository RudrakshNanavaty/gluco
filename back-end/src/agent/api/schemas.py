"""HTTP request and response models that are not domain or query models."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints

from agent.auth import Principal, Role
from agent.clock import ClockState

SessionId = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{1,128}$")]
Message = Annotated[str, StringConstraints(min_length=1, max_length=4000)]


class PrincipalOut(BaseModel):
    """The caller as `GET /me` returns them."""

    user_id: str
    role: Role
    display_name: str
    participant_id: str | None

    @classmethod
    def of(cls, principal: Principal) -> "PrincipalOut":
        return cls(
            user_id=principal.user_id,
            role=principal.role,
            display_name=principal.display_name,
            participant_id=principal.participant_id,
        )


class ClockCommand(BaseModel):
    """A request to move the replay clock. `speed` needs `seconds_per_hour`; `seek`
    needs `to`.
    """

    action: Literal["play", "pause", "speed", "seek"]
    seconds_per_hour: float | None = Field(default=None, gt=0)  # for "speed"
    to: datetime | None = None  # for "seek"


class ChatRequest(BaseModel):
    """One chat message and the thread (session id) it belongs to."""

    session_id: SessionId
    message: Message


class Health(BaseModel):
    """Service status for `GET /health`: database and LLM readiness, how many windows
    and participants are loaded, and the replay clock.
    """

    db: bool
    llm: bool
    windows: int
    participants: int
    clock: ClockState | None
