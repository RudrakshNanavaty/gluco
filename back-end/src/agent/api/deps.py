"""Request dependencies: the runtime, who is calling, and shared error handling."""

import logging
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from agent.auth import Authenticator, InvalidTokenError, Principal
from agent.bootstrap import Runtime
from agent.domain.errors import (
    AmbiguousPersonError,
    ForbiddenError,
    PersonNotFoundError,
    QueryError,
)
from agent.query import QueryService

log = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=False)


def get_runtime(request: Request) -> Runtime:
    return request.app.state.runtime


RuntimeDep = Annotated[Runtime, Depends(get_runtime)]

Credentials = Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]


def get_authenticator(request: Request) -> Authenticator:
    return request.app.state.authenticator


def current_principal(
    authenticator: Annotated[Authenticator, Depends(get_authenticator)],
    credentials: Credentials,
) -> Principal:
    if credentials is None:
        raise HTTPException(
            401,
            "Please sign in to continue.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return authenticator.authenticate(credentials.credentials)
    except InvalidTokenError as exc:
        # The client only learns that the session ended; the cause stays here.
        log.warning("Clerk session rejected: %s", exc)
        raise HTTPException(
            401,
            "Your session has ended. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


CurrentPrincipal = Annotated[Principal, Depends(current_principal)]


def query_service(runtime: RuntimeDep, principal: CurrentPrincipal) -> QueryService:
    return runtime.queries(principal)


Queries = Annotated[QueryService, Depends(query_service)]


def install_error_handlers(app: FastAPI) -> None:
    """Domain errors become JSON with a stable `code` the UI can switch on."""

    def body(status: int, code: str, message: str, **extra: object) -> JSONResponse:
        return JSONResponse({"detail": message, "code": code, **extra}, status)

    @app.exception_handler(PersonNotFoundError)
    async def not_found(_: Request, exc: PersonNotFoundError) -> JSONResponse:
        return body(
            404,
            "not_found",
            f"We couldn't find a patient matching {exc.ref!r}.",
            suggestions=exc.suggestions,
        )

    @app.exception_handler(AmbiguousPersonError)
    async def ambiguous(_: Request, exc: AmbiguousPersonError) -> JSONResponse:
        return body(
            409,
            "ambiguous",
            f"{exc.ref!r} matches more than one patient.",
            candidates=exc.candidates,
        )

    @app.exception_handler(ForbiddenError)
    async def forbidden(_: Request, exc: ForbiddenError) -> JSONResponse:
        return body(403, "not_permitted", str(exc))

    @app.exception_handler(QueryError)
    async def bad_query(_: Request, exc: QueryError) -> JSONResponse:
        return body(400, "bad_query", str(exc), **exc.details)
