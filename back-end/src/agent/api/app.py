"""FastAPI wiring: auth, dashboard, chat (SSE) and health."""

import logging
from collections.abc import Callable, Iterable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agent.api import chat, dashboard, me, widgets
from agent.api.deps import install_error_handlers
from agent.api.schemas import Health
from agent.auth import Authenticator, jwks_keys
from agent.bootstrap import Runtime, build_runtime
from agent.config import Settings

log = logging.getLogger(__name__)


def clerk_authenticator(
    settings: Settings, participants: Callable[[], Iterable[str]]
) -> Authenticator:
    """The production Authenticator: Clerk's keys, from the settings."""
    if not settings.clerk_jwks_url or not settings.clerk_issuer:
        raise ValueError(
            "CLERK_JWKS_URL and CLERK_ISSUER are required to serve the API; "
            "see .env.example."
        )
    return Authenticator(
        jwks_keys(settings.clerk_jwks_url),
        issuer=settings.clerk_issuer,
        participants=participants,
        audience=settings.clerk_audience,
    )


def create_app(runtime: Runtime, authenticator: Authenticator | None = None) -> FastAPI:
    app = FastAPI(title="Gluco API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=runtime.settings.allowed_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.runtime = runtime
    app.state.authenticator = authenticator or clerk_authenticator(
        runtime.settings, runtime.store.participants
    )
    install_error_handlers(app)
    for module in (me, dashboard, chat, widgets):
        app.include_router(module.router)

    @app.get("/health", tags=["health"])
    def health() -> Health:
        db = runtime.source.ping()
        try:
            windows, people = runtime.store.size(), len(runtime.store.participants())
            clock = runtime.clock.state()
        except Exception:
            log.exception("store unavailable")
            windows, people, clock = 0, 0, None
        return Health(
            db=db,
            llm=runtime.llm.is_ready(),
            windows=windows,
            participants=people,
            clock=clock,
        )

    return app


def create_default_app() -> FastAPI:
    """Factory for uvicorn: `uvicorn agent.api.app:create_default_app --factory`."""
    return create_app(build_runtime())
