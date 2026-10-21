"""Chat endpoints: one streamed turn, and the caller's own threads."""

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from agent.api.dashboard import SSE_HEADERS
from agent.api.deps import CurrentPrincipal, RuntimeDep
from agent.api.schemas import ChatRequest, SessionId
from agent.api.sessions import ChatThread, TranscriptMessage
from agent.api.sse import sse_frame

router = APIRouter(tags=["chat"])


@router.post("/chat")
async def chat_turn(
    request: ChatRequest, runtime: RuntimeDep, principal: CurrentPrincipal
) -> EventSourceResponse:
    """Stream one assistant turn as server-sent events (`POST /chat`), in the caller's
    scope.
    """

    async def events():
        async for event in runtime.chat.stream(
            runtime.for_principal(principal), request.session_id, request.message
        ):
            yield sse_frame(event)

    return EventSourceResponse(events(), headers=SSE_HEADERS)


@router.get("/chat/sessions")
def threads(runtime: RuntimeDep, principal: CurrentPrincipal) -> list[ChatThread]:
    """The caller's chat threads, most recently active first (`GET /chat/sessions`)."""
    return runtime.sessions.threads(principal.user_id)


@router.get("/chat/sessions/{session_id}")
async def thread(
    session_id: SessionId, runtime: RuntimeDep, principal: CurrentPrincipal
) -> list[TranscriptMessage]:
    """One of the caller's threads as stored messages (`GET
    /chat/sessions/{session_id}`). 404 when the thread is not theirs.
    """
    if not runtime.sessions.owns(principal.user_id, session_id):
        raise HTTPException(404, "We couldn't find that conversation.")
    return await runtime.sessions.transcript(principal.user_id, session_id)
