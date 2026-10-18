"""Clinician tools: the whole cohort, any participant, any question.

Every tool reads through the clinician's QueryService, so scope and the replay
clock apply here exactly as they do in the REST API.
"""

from typing import Any, Literal

from agents import FunctionTool, function_tool

from agent.analysis.ids import display_name
from agent.domain.metrics import GLUCO_SCORE, metric_label
from agent.query import QueryService, QuerySpec
from agent.tools.base import (
    MAX_ROWS,
    answer,
    dump,
    explain,
    parse_time,
    result,
    safe_tool,
    status,
)
from agent.tools.widgets import build_widget_tool


def build(svc: QueryService) -> list[FunctionTool]:
    @function_tool
    @safe_tool
    def list_participants(
        sort_by: str = GLUCO_SCORE,
        order: Literal["asc", "desc"] = "asc",
        top_k: int = 20,
    ) -> dict[str, Any]:
        """List participants with their newest values, sorted.

        Use for rankings and follow-up lists: lowest Gluco Score first is
        sort_by="gluco_score", order="asc"; biggest 24 h drops first is
        sort_by="gluco_change_24h", order="asc".

        Args:
            sort_by: A metric name from the catalog, or "person_id".
            order: "asc" (lowest first) or "desc" (highest first).
            top_k: How many participants to return (1-200).
        """
        if not 1 <= top_k <= MAX_ROWS:
            raise ValueError(f"top_k must be between 1 and {MAX_ROWS}")
        rows = svc.participants(sort_by, order)
        shown = rows[:top_k]
        return result(
            summary=(
                f"{len(shown)} of {len(rows)} patients by "
                f"{metric_label(sort_by)} ({order})"
            ),
            rows=len(shown),
            as_of=svc.as_of(),
            participants=[dump(r) for r in shown],
            total_participants=len(rows),
        )

    @function_tool
    @safe_tool
    def get_participant(person_id: str) -> dict[str, Any]:
        """One participant's newest values and their Gluco Score over the last 7 days.

        Args:
            person_id: The participant, e.g. "13", "P013", "IMU-13" or the full key.
        """
        return status(svc, person_id)

    @function_tool
    @safe_tool
    def explain_change(person_id: str, hours: float = 24) -> dict[str, Any]:
        """Why a participant's Gluco Score moved: what changed with it.

        Returns, for the Gluco Score and every sensor metric, the newest value,
        the value `hours` earlier, the delta, and how unusual the newest value is
        for this person's own last 7 days (z_vs_baseline). Also lists the sensor
        metrics where they sit furthest from the cohort right now. These are
        associations, not causes.

        Args:
            person_id: The participant, e.g. "13" or the full key.
            hours: How far back to compare (default 24).
        """
        return explain(svc, person_id, hours)

    @function_tool
    @safe_tool
    def compare_to_cohort(person_id: str, metric: str) -> dict[str, Any]:
        """Compare one metric of one participant with everyone's newest values.

        Returns the value, cohort median and mean, z-score and percentile.

        Args:
            person_id: The participant, e.g. "13" or the full key.
            metric: A metric name from the catalog, e.g. "hr_mean_bpm_24h".
        """
        comparison = svc.compare_to_cohort(person_id, metric)
        return result(
            summary=(
                f"{display_name(comparison.person_id)} {metric_label(metric)}: "
                f"{comparison.value} vs "
                f"panel median {comparison.cohort_median}"
            ),
            rows=1,
            as_of=svc.as_of(),
            comparison=dump(comparison),
        )

    @function_tool
    @safe_tool
    def cohort_overview() -> dict[str, Any]:
        """Summarise the cohort now: Gluco Score spread, lowest scores, biggest
        24 h drops and gains, and every metric's mean, median and range."""
        overview = svc.cohort_overview()
        return result(
            summary=f"Panel of {overview.participants} patients",
            rows=overview.participants,
            as_of=svc.as_of(),
            overview=dump(overview),
        )

    @function_tool
    @safe_tool
    def query_data(
        metrics: list[str],
        participants: list[str] | None = None,
        hours: float = 168,
        start: str | None = None,
        end: str | None = None,
        bucket: Literal["raw", "hour", "day", "all"] = "day",
        agg: Literal["mean", "median", "min", "max", "first", "last", "delta"] = "mean",
        group_by: Literal["participant", "cohort"] = "participant",
        sort_by: str | None = None,
        order: Literal["asc", "desc"] = "desc",
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Answer any other question about the data with one structured query.

        Examples: cohort average heart rate by day (metrics=["hr_mean_bpm_24h"],
        bucket="day", group_by="cohort"); who moved least this week
        (metrics=["motion_mean_g"], bucket="all", sort_by="motion_mean_g",
        order="asc", limit=5); a person's daily Gluco Score low
        (participants=["13"], bucket="day", agg="min").

        Args:
            metrics: Metric names from the catalog.
            participants: Who to include (short refs are fine); omit for everyone.
            hours: Look back this many hours from now when start is not given.
            start: ISO-8601 start (exclusive); overrides hours.
            end: ISO-8601 end (inclusive); defaults to now.
            bucket: "raw" (every hourly window), "hour", "day", or "all" (one value).
            agg: How to reduce each bucket. "delta" is last minus first.
            group_by: "participant" (one series each) or "cohort" (pooled).
            sort_by: Rank series by their newest value of this metric.
            order: "asc" or "desc" for sort_by.
            limit: Keep only this many series after sorting.
        """
        return answer(
            svc,
            QuerySpec(
                metrics=metrics,
                participants=participants or None,
                hours=hours,
                start=parse_time(start),
                end=parse_time(end),
                bucket=bucket,
                agg=agg,
                group_by=group_by,
                sort_by=sort_by,
                order=order,
                limit=limit,
            ),
        )

    return [
        list_participants,
        get_participant,
        explain_change,
        compare_to_cohort,
        cohort_overview,
        query_data,
        build_widget_tool(svc),
    ]
