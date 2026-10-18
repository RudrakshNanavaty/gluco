"""Composition root: wires settings, data, clock, agents and chat."""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass

from agents import Agent, FunctionTool

from agent.api.chat_service import ChatService
from agent.api.sessions import ChatSessions
from agent.api.widget_store import WidgetStore
from agent.auth import Principal
from agent.clock import ReplayClock
from agent.config import Settings
from agent.data.factory import build_source
from agent.domain.ports import WindowSource
from agent.factory import build_agent
from agent.guardrails import build_input_guardrails
from agent.live import LiveStore
from agent.llm import LlmConnection
from agent.observability.trace import JsonlTracer
from agent.query import QueryService
from agent.store import WindowStore
from agent.tools.registry import build_tools

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Runtime:
    settings: Settings
    llm: LlmConnection
    source: WindowSource
    store: WindowStore
    live: LiveStore
    clock: ReplayClock
    sessions: ChatSessions
    widgets: WidgetStore
    chat: ChatService

    def queries(self, principal: Principal) -> QueryService:
        return QueryService(self.store, self.clock, principal, self.live)

    def tools_for(self, principal: Principal) -> list[FunctionTool]:
        return build_tools(self.queries(principal))


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
    guardrails = {
        role: build_input_guardrails(settings.effective_guardrail_model, role)
        for role in ("clinician", "patient")
    }
    sessions = ChatSessions(settings.session_db_path)

    def agent_for(principal: Principal) -> Agent:
        return build_agent(
            principal=principal,
            now=clock.now(),
            model=settings.agent_model,
            tools=build_tools(QueryService(store, clock, principal, live)),
            input_guardrails=guardrails[principal.role],
        )

    chat = ChatService(
        agents=agent_for,
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
        sessions=sessions,
        widgets=WidgetStore(settings.session_db_path),
        chat=chat,
    )
