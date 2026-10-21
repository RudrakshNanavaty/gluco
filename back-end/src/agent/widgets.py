"""Dashboard widgets: what one is, and the pipeline that builds it.

The chat agent decides what to show (a kind and a few query arguments). The
stages here do the rest in code, the same way for a new widget and for every
refresh of a pinned one:

1. design:     turn the kind into a re-runnable QuerySpec (relative `hours`,
               never absolute times, so a pinned widget follows the clock);
2. fetch:      run it through the caller's QueryService (scope + replay clock);
3. compliance: report the disclosure rule `QueryService.query()` applied;
4. bind:       return the spec with the data, so a pin can refresh itself.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from agent.domain.errors import QueryError
from agent.domain.metrics import metric_label
from agent.query import QueryResult, QueryService, QuerySpec

WidgetKind = Literal["trend", "ranking", "cohort_trend", "stat", "table", "heatmap"]
Stage = Literal["design", "fetch", "compliance", "bind"]

KIND_SHAPES: dict[WidgetKind, str] = {
    "trend": "Line chart",
    "ranking": "Ranked bars",
    "cohort_trend": "Panel average line",
    "stat": "Stat tile",
    "table": "Comparison table",
    "heatmap": "Heatmap by day",
}


class WidgetSpec(BaseModel):
    """What a pin stores: enough to rebuild the widget at any later time."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=120)
    kind: WidgetKind
    query: QuerySpec


class WidgetStep(BaseModel):
    """One step of the widget pipeline as shown in the UI: its stage and what it did."""

    stage: Stage
    text: str


class BuiltWidget(BaseModel):
    """A widget spec with the data it produced and the pipeline steps that built it."""

    spec: WidgetSpec
    result: QueryResult
    steps: list[WidgetStep]


def design(
    kind: WidgetKind,
    metrics: list[str],
    participants: list[str] | None,
    hours: float,
    agg: str | None,
    order: str,
    limit: int,
    panel: bool = False,
) -> QuerySpec:
    """The query that draws `kind` well.

    `panel` is true for a clinician, whose stat tile with no one named is the
    panel average; a patient's QueryService only ever sees themselves anyway.
    """
    participants = participants or None  # models send [] for "everyone"
    named = participants is not None
    base: dict[str, Any] = {
        "metrics": metrics,
        "participants": participants,
        "hours": hours,
        "bucket": "hour" if hours <= 48 else "day",
        "agg": agg or "mean",
        "order": order,
    }
    # Without named people, keep the chart readable: the `limit` lowest or
    # highest by their newest value.
    top: dict[str, Any] = {} if named else {"sort_by": metrics[0], "limit": limit}
    match kind:
        case "stat":
            group_by = "cohort" if panel and not named else "participant"
            extra = {"metrics": metrics[:1], "group_by": group_by}
        case "heatmap":
            extra = {"metrics": metrics[:1], "bucket": "day", **top}
        case "ranking" | "table":
            extra = {
                "bucket": "all",
                "agg": agg or "last",
                "sort_by": metrics[0],
                "limit": limit,
            }
        case "cohort_trend":
            extra = {"participants": None, "group_by": "cohort"}
        case "trend":
            extra = top
    return QuerySpec.model_validate(base | extra)


def build(svc: QueryService, spec: WidgetSpec) -> BuiltWidget:
    """Run the fetch, compliance and bind stages for an already designed spec."""
    query = spec.query
    labels = ", ".join(metric_label(m) for m in query.metrics)
    steps = [
        WidgetStep(
            stage="design",
            text=f"{KIND_SHAPES[spec.kind]} of {labels}, last {query.hours or 168:g} h",
        )
    ]

    found = svc.query(query)
    points = sum(len(s.points) for s in found.series)
    if points == 0:
        raise QueryError(
            "No data in that range.",
            hint="Use a longer `hours` or another metric.",
        )
    steps.append(
        WidgetStep(
            stage="fetch",
            text=f"Fetched {points} data points across {len(found.series)} series",
        )
    )
    steps.append(WidgetStep(stage="compliance", text="; ".join(found.audit)))
    steps.append(
        WidgetStep(
            stage="bind", text="Bound to a live query: refreshes as data streams in"
        )
    )
    return BuiltWidget(spec=spec, result=found, steps=steps)
