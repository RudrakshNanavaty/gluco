"""Widgets: refresh one built in chat, pin it, list pins, refresh one, unpin it."""

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from agent import widgets
from agent.api.deps import CurrentPrincipal, Queries, RuntimeDep
from agent.api.widget_store import PinnedWidget
from agent.query import QueryResult
from agent.widgets import WidgetSpec, WidgetStep

router = APIRouter(tags=["widgets"])


class WidgetData(PinnedWidget):
    """A pinned widget with freshly built data and pipeline steps."""

    result: QueryResult
    steps: list[WidgetStep]


class WidgetPreview(BaseModel):
    """Freshly built data and pipeline steps for a widget spec that is not pinned."""

    result: QueryResult
    steps: list[WidgetStep]


def _pinned(runtime: RuntimeDep, user_id: str, widget_id: str) -> PinnedWidget:
    pinned = runtime.widgets.get(user_id, widget_id)
    if pinned is None:
        raise HTTPException(404, "That widget isn't pinned.")
    return pinned


@router.get("/widgets")
def list_widgets(
    runtime: RuntimeDep, principal: CurrentPrincipal
) -> list[PinnedWidget]:
    """The caller's pinned widgets, oldest first (`GET /widgets`)."""
    return runtime.widgets.list(principal.user_id)


@router.post("/widgets/preview")
def preview_widget(spec: WidgetSpec, svc: Queries) -> WidgetPreview:
    """Rebuild a widget from its spec without pinning it (keeps chat widgets live)."""
    built = widgets.build(svc, spec)
    return WidgetPreview(result=built.result, steps=built.steps)


@router.post("/widgets", status_code=201)
def pin_widget(
    spec: WidgetSpec, runtime: RuntimeDep, principal: CurrentPrincipal, svc: Queries
) -> PinnedWidget:
    """Pin a widget (`POST /widgets`). Its query is run first, so a spec the caller may
    not see or that is invalid is rejected (403/400) before anything is saved.
    """
    svc.query(spec.query)  # 403/400 before saving anything the caller can't see
    return runtime.widgets.add(principal.user_id, spec)


@router.get("/widgets/{widget_id}/data")
def widget_data(
    widget_id: str, runtime: RuntimeDep, principal: CurrentPrincipal, svc: Queries
) -> WidgetData:
    """Rebuild a pinned widget against the current clock and the caller's scope (`GET
    /widgets/{widget_id}/data`). 404 when it is not pinned.
    """
    pinned = _pinned(runtime, principal.user_id, widget_id)
    built = widgets.build(svc, pinned.spec())
    return WidgetData(**pinned.model_dump(), result=built.result, steps=built.steps)


@router.delete("/widgets/{widget_id}", status_code=204)
def unpin_widget(
    widget_id: str, runtime: RuntimeDep, principal: CurrentPrincipal
) -> Response:
    """Remove a pinned widget (`DELETE /widgets/{widget_id}`). 404 when the caller has
    no such pin.
    """
    if not runtime.widgets.delete(principal.user_id, widget_id):
        raise HTTPException(404, "That widget isn't pinned.")
    return Response(status_code=204)
