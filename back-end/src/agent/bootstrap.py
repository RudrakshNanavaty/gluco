"""Composition root: wires settings, data, clock, agents and chat."""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from functools import cached_property

from agents import Agent, FunctionTool, InputGuardrail

from agent.api.chat_service import ChatService
from agent.api.sessions import ChatSessions
from agent.api.widget_store import WidgetStore
from agent.auth import Principal, Role
from agent.clock import ReplayClock
from agent.config import Settings
from agent.data.factory import build_source
from agent.domain.errors import ForbiddenError
from agent.domain.ports import WindowSource
from agent.factory import build_agent
from agent.guardrails import build_input_guardrails
from agent.live import LiveStore
from agent.llm import LlmConnection
from agent.observability.trace import JsonlTracer
from agent.query import QueryService
from agent.store import WindowStore
from agent.tools import TOOLS

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Runtime:
    settings: Settings
    llm: LlmConnection
    source: WindowSource
    store: WindowStore
    live: LiveStore
    clock: ReplayClock
    guardrails: dict[Role, list[InputGuardrail]]
    sessions: ChatSessions
    widgets: WidgetStore
    chat: ChatService

    def for_principal(self, principal: Principal) -> "Scope":
        return Scope(self, principal)


class Scope:
    """Everything one Principal's requests get, bound to their scope.

    The one place per-user wiring happens, so the REST API, the tools and chat
    always read through the same store and clock.
    """

    def __init__(self, runtime: Runtime, principal: Principal) -> None:
        self._runtime = runtime
        self.principal = principal
        self.queries = QueryService(
            runtime.store, runtime.clock, principal, runtime.live
        )

    @cached_property
    def tools(self) -> list[FunctionTool]:
        return TOOLS[self.principal.role](self.queries)

    def agent(self) -> Agent:
        runtime = self._runtime
        return build_agent(
            principal=self.principal,
            now=runtime.clock.now(),
            model=runtime.settings.agent_model,
            model_settings=runtime.llm.model_settings(),
            tools=self.tools,
            input_guardrails=runtime.guardrails[self.principal.role],
        )

    def clock(self) -> ReplayClock:
        """The shared replay clock, to move it. Clinicians only (ADR 0002)."""
        if self.principal.role != "clinician":
            raise ForbiddenError("Only clinicians can change the demo time.")
        return self._runtime.clock


def build_runtime(
    settings: Settings | None = None,
    source: WindowSource | None = None,
    time_source: Callable[[], float] = time.monotonic,
) -> Runtime:
    settings = settings or Settings()  # pyright: ignore[reportCallIssue]
    llm = LlmConnection.from_settings(settings)
    llm.configure()
    source = source or build_source(settings)
    store = WindowStore(source, settings.store_refresh_s, time_source)
    live = LiveStore(source, store, settings.live_refresh_s, time_source)
    clock = ReplayClock(
        store.data_range,
        start=settings.replay_start,
        seconds_per_hour=settings.replay_seconds_per_hour,
        enabled=settings.replay_enabled,
        time_source=time_source,
    )
    guardrails: dict[Role, list[InputGuardrail]] = {
        role: build_input_guardrails(
            settings.effective_guardrail_model, role, llm.model_settings()
        )
        for role in ("clinician", "patient")
    }
    sessions = ChatSessions(settings.session_db_path)
    chat = ChatService(
        sessions=sessions,
        tracer=JsonlTracer(settings.trace_path),
        max_turns=settings.max_turns,
    )
    return Runtime(
        settings=settings,
        llm=llm,
        source=source,
        store=store,
        live=live,
        clock=clock,
        guardrails=guardrails,
        sessions=sessions,
        widgets=WidgetStore(settings.session_db_path),
        chat=chat,
    )
