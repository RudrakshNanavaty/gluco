"""The disclosure rule every query result passes before anyone sees it.

`QueryService.query()` applies it to each result it returns, so the REST API,
the agents' tools and pinned widgets all show the same thing. Series only ever
carry display names, never internal participant keys, and pooled cohort points
built from too few people to stay anonymous are hidden. It is code, not a
prompt, so the model can neither skip it nor talk its way past it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agent.auth import Principal

if TYPE_CHECKING:
    from agent.query import Series

# Pooled cohort points from fewer people than this are hidden (small-cell rule).
MIN_COHORT_CELL = 3


def _suppress_small_cells(
    points: list[dict[str, Any]], metrics: list[str]
) -> tuple[list[dict[str, Any]], int]:
    hidden = 0
    kept = []
    for point in points:
        if point.get("participants", MIN_COHORT_CELL) < MIN_COHORT_CELL:
            hidden += 1
            point = {**point, **dict.fromkeys(metrics)}
        kept.append(point)
    return kept, hidden


def disclose(
    series: list[Series], *, pooled: bool, metrics: list[str], principal: Principal
) -> tuple[list[Series], list[str]]:
    """The series with only what may be shown, plus one audit line per rule."""
    audit = [
        "Scope: clinician panel"
        if principal.role == "clinician"
        else "Scope: your own data only"
    ]
    if not pooled:
        return series, audit
    hidden = 0
    cleaned = []
    for s in series:
        points, count = _suppress_small_cells(s.points, metrics)
        hidden += count
        cleaned.append(s.model_copy(update={"points": points}))
    audit.append(
        f"{hidden} cohort points from fewer than {MIN_COHORT_CELL} people hidden"
        if hidden
        else f"Every cohort point pools at least {MIN_COHORT_CELL} people"
    )
    return cleaned, audit
