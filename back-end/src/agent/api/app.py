"""FastAPI wiring: auth, dashboard, chat (SSE) and health."""

import logging
import threading
from collections.abc import AsyncIterator, Callable, Iterable
from contextlib import asynccontextmanager

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


def _warm_store(runtime: Runtime) -> None:
    """Load the windows now, so the first login doesn't wait for them."""
    try:
        runtime.store.size()
    except Exception:
        log.exception("store warm-up failed; it will load on the first request")


def create_app(runtime: Runtime, authenticator: Authenticator | None = None) -> FastAPI:
    """Build the FastAPI app for a Runtime: CORS, error handlers, the routers and
    `/health`. The window store is warmed on a background thread at startup. Without an
    `authenticator` the Clerk one is built from the settings, which raises ValueError
    when they are missing.
    """

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        # Off the event loop and not awaited: the server accepts requests at once,
        # and one that arrives mid-load waits on the store's refresh lock.
        threading.Thread(
            target=_warm_store, args=(runtime,), name="store-warmup", daemon=True
        ).start()
        yield

    app = FastAPI(title="Gluco API", lifespan=lifespan)
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
        """Whether the database and LLM are ready, and how much data is loaded."""
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
