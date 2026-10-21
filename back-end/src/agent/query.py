"""The one place that decides what a user sees and derives every number.

`QueryService` is built per request for one signed-in user. It applies scope
(clinicians see everyone, patients only themselves), the replay clock (only
windows ending at or before "now") and the disclosure rule
(`analysis.compliance`), overlays the live sensor readings on each person's
newest window once the clock has reached it, then answers with plain pydantic
models that the REST API returns as-is and the agents' tools hand to the LLM.
Both read the same numbers because both come through here.

Every public method that names a person takes a reference ("13", "Patient 013"
or the full key) and resolves it itself, so no caller can reach a person's data
without passing scope.
"""

import difflib
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from agent.analysis import query as q
from agent.analysis.compliance import disclose
from agent.analysis.deviation import FeatureDeviation, describe_feature, top_deviations
from agent.analysis.ids import display_name, resolve_participant
from agent.analysis.stats import compute_feature_stats
from agent.auth import Principal
from agent.clock import ReplayClock
from agent.domain.errors import (
    AmbiguousPersonError,
    ForbiddenError,
    PersonNotFoundError,
    QueryError,
)
from agent.domain.metrics import (
    GLUCO_CHANGE,
    GLUCO_SCORE,
    LIVE_METRICS,
    METRICS,
    SENSOR_METRICS,
    unit_of,
)
from agent.domain.models import LiveReading, Window
from agent.live import LiveStore
from agent.store import WindowStore

DEFAULT_HOURS = 168.0
BASELINE_HOURS = 168.0
MAX_SERIES = 200
MAX_POINTS = 10_000
PATIENT_ONLY_OWN = "You can only see your own data."
CHANGE_NOTE = (
    "Changes compare the most recent 24 h window with the one N hours earlier; "
    "standard deviation (SD) scores compare the latest value with this "
    "patient's own last 7 days. These are associations, not causal "
    "relationships, and the Gluco Score is a model estimate, not a "
    "measurement or a diagnosis."
)


class QuerySpec(BaseModel):
    """A generic question to the data: which metrics, whose, when, how reduced."""

    model_config = ConfigDict(extra="forbid")

    metrics: list[str] = Field(default_factory=lambda: [GLUCO_SCORE], min_length=1)
    participants: list[str] | None = None  # None: everyone the user may see
    start: datetime | None = None  # exclusive
    end: datetime | None = None  # inclusive; capped at the replay clock's now
    hours: float | None = Field(default=None, gt=0, le=24 * 90)  # when start is None
    bucket: q.Bucket = "hour"
    agg: q.Agg = "mean"
    group_by: q.GroupBy = "participant"
    sort_by: str | None = None  # rank series by their newest value of this metric
    order: q.Order = "desc"
    limit: int | None = Field(default=None, ge=1, le=MAX_SERIES)


class Series(BaseModel):
    """One series of a result: a display name (never an internal key) and its points."""

    display_name: str  # never an internal participant key
    points: list[dict[str, Any]]


class QueryResult(BaseModel):
    """The answer to a QuerySpec: the resolved range, units and series, how many series
    there were before any cut-off, whether the result was truncated, and one audit line
    per disclosure rule applied.
    """

    as_of: datetime | None
    start: datetime | None
    end: datetime | None
    metrics: list[str]
    units: dict[str, str]
    bucket: q.Bucket
    agg: q.Agg
    group_by: q.GroupBy
    series: list[Series]
    total_series: int
    truncated: bool
    # One line per disclosure rule applied, for the widget's compliance step.
    audit: list[str] = Field(default_factory=list)


class ParticipantRow(BaseModel):
    """A participant's newest window with values rounded; `live_at` is set when live
    readings were applied.
    """

    person_id: str
    display_name: str
    source_dataset: str
    window_end: datetime
    values: dict[str, float | None]
    # When the live readings in `values` were taken; None without live data.
    live_at: datetime | None = None


class MetricChange(BaseModel):
    """One metric's newest value, its value `hours` earlier and the difference, and how
    far the newest value is from the person's own last 7 days (`z_vs_baseline`).
    """

    metric: str
    label: str
    unit: str
    now: float | None
    then: float | None
    delta: float | None
    baseline_mean: float | None
    z_vs_baseline: float | None


class ChangeReport(BaseModel):
    """How a participant's metrics changed between their newest window and the one
    `hours` earlier, with the sensor metrics furthest from their own last 7 days.
    """

    person_id: str
    display_name: str
    as_of: datetime | None
    hours: float
    now_window_end: datetime
    then_window_end: datetime | None
    changes: list[MetricChange]
    largest_shifts: list[str]  # sensor metrics most unusual vs their own week
    note: str = CHANGE_NOTE


class Explanation(BaseModel):
    """A ChangeReport and, for clinicians, where the person sits against everyone's
    newest windows.
    """

    change: ChangeReport
    # Where the person sits against everyone's newest windows; clinicians only.
    cohort_position: list[FeatureDeviation] | None


class CohortComparison(BaseModel):
    """A participant's value on one metric against everyone's newest windows: z-score,
    percentile (normal approximation) and direction relative to the median.
    """

    person_id: str
    metric: str
    unit: str
    value: float
    cohort_median: float
    cohort_mean: float
    z_score: float
    percentile: float
    direction: str
    cohort_size: int
    percentile_method: str = "normal_approximation"


class MetricSummary(BaseModel):
    """Mean, median, standard deviation, minimum, maximum and count of one metric."""

    mean: float
    median: float
    stddev: float
    min: float
    max: float
    n: int


class CohortOverview(BaseModel):
    """A summary of everyone's newest windows: per-metric summaries, the lowest Gluco
    Scores and the biggest 24-hour drops and gains.
    """

    as_of: datetime | None
    participants: int
    gluco_score: MetricSummary | None
    lowest_gluco: list[ParticipantRow]
    biggest_drops: list[ParticipantRow]
    biggest_gains: list[ParticipantRow]
    metrics: dict[str, MetricSummary]


class MetricInfo(BaseModel):
    """The catalog entry for one metric."""

    name: str
    label: str
    unit: str
    description: str
    higher_is_better: bool | None
    live: bool


class ParticipantInfo(BaseModel):
    """The catalog entry for one visible participant."""

    person_id: str
    display_name: str
    source_dataset: str


class Catalog(BaseModel):
    """What can be queried: the metrics, the participants the user may see, the data
    range and the allowed buckets, aggregations and groupings.
    """

    as_of: datetime | None
    data_start: datetime | None
    data_end: datetime | None
    metrics: list[MetricInfo]
    participants: list[ParticipantInfo]
    buckets: list[str]
    aggs: list[str]
    group_bys: list[str]


def _utc(t: datetime | None) -> datetime | None:
    if t is None:
        return None
    return t if t.tzinfo else t.replace(tzinfo=UTC)


def _round(value: float | None, digits: int = 4) -> float | None:
    return None if value is None else round(value, digits)


def _summary(values: Sequence[float | None]) -> MetricSummary | None:
    present = [v for v in values if v is not None]
    stats = compute_feature_stats({"v": v} for v in present).get("v")
    if stats is None:
        return None
    return MetricSummary(
        mean=round(stats.mean, 4),
        median=round(stats.p50, 4),
        stddev=round(stats.stddev, 4),
        min=round(min(present), 4),
        max=round(max(present), 4),
        n=len(present),
    )


def check_metrics(metrics: Sequence[str]) -> None:
    """Raise QueryError, listing the available metrics and close matches, when a name is
    not a known metric.
    """
    for metric in metrics:
        if metric not in METRICS:
            raise QueryError(
                f"Unknown metric {metric!r}.",
                available_metrics=list(METRICS),
                suggestions=difflib.get_close_matches(
                    metric, list(METRICS), n=3, cutoff=0.4
                ),
            )


class QueryService:
    """Answers every data question for one signed-in user, applying scope, the replay
    clock and the disclosure rule. See the module description.
    """

    def __init__(
        self,
        store: WindowStore,
        clock: ReplayClock,
        principal: Principal,
        live: LiveStore | None = None,
    ) -> None:
        self._store = store
        self._clock = clock
        self.principal = principal
        self._live = live

    # --- scope and time -----------------------------------------------------

    @property
    def is_clinician(self) -> bool:
        return self.principal.role == "clinician"

    def as_of(self) -> datetime | None:
        return self._clock.now()

    def visible(self) -> list[str]:
        ids = self._store.participants()
        return (
            ids if self.is_clinician else [i for i in ids if self.principal.can_see(i)]
        )

    def resolve(self, ref: str) -> str:
        """The participant key `ref` names, if this user may see it."""
        if self.is_clinician:
            return resolve_participant(ref, self._store.participants())
        own = self.principal.participant_id
        try:
            person_id = resolve_participant(ref, self._store.participants())
        except (PersonNotFoundError, AmbiguousPersonError):
            person_id = None
        if person_id is None or person_id != own:
            raise ForbiddenError(PATIENT_ONLY_OWN)
        return person_id

    def require_clinician(self) -> None:
        if not self.is_clinician:
            raise ForbiddenError(
                "Only clinicians can see data for the whole patient panel."
            )

    def _history(
        self, person_id: str, start: datetime | None = None, end: datetime | None = None
    ) -> list[Window]:
        now = self.as_of()
        if now is None:
            return []
        end = now if end is None else min(end, now)
        return self._store.history(person_id, start, end)

    def _latest(self, person_id: str) -> Window | None:
        """The newest window up to now, with the live readings when there are any."""
        windows = self._history(person_id)
        return self._live_view(windows[-1]) if windows else None

    # --- live readings --------------------------------------------------------

    def _live_for(self, window: Window) -> LiveReading | None:
        """Live readings that belong with `window`: only the person's newest one,
        and only once the clock has reached it (a replay behind the data would
        otherwise see readings from its future)."""
        if self._live is None:
            return None
        newest = self._store.latest(window.person_id)
        now = self.as_of()
        if (
            newest is None
            or now is None
            or newest.window_end > now
            or window.window_end != newest.window_end
        ):
            return None
        return self._live.reading(window.person_id)

    def _live_view(self, window: Window) -> Window:
        """`window` with its live readings applied, when they belong with it.

        The one place readings meet windows: rows, queries and the stream all
        read windows through here.
        """
        reading = self._live_for(window)
        if reading is None:
            return window
        return window.model_copy(
            update={
                "values": {**window.values, **reading.values},
                "live_at": reading.sensor_time,
            }
        )

    def live_readings(self) -> list[LiveReading]:
        """Everyone visible's live readings (for the live stream)."""
        newest = (self._store.latest(pid) for pid in self.visible())
        return [r for w in newest if w and (r := self._live_for(w))]

    def _require_latest(self, person_id: str) -> Window:
        window = self._latest(person_id)
        if window is None:
            raise QueryError(f"There are no readings for {person_id} up to now.")
        return window

    def _row(self, window: Window) -> ParticipantRow:
        """A row for a window already in the live view."""
        return ParticipantRow(
            person_id=window.person_id,
            display_name=display_name(window.person_id),
            source_dataset=window.source_dataset,
            window_end=window.window_end,
            values={k: _round(v) for k, v in window.values.items()},
            live_at=window.live_at,
        )

    # --- generic query ------------------------------------------------------

    def query(self, spec: QuerySpec) -> QueryResult:
        check_metrics(spec.metrics)
        if spec.sort_by is not None and spec.sort_by not in spec.metrics:
            raise QueryError("sort_by must be one of the requested metrics.")
        if spec.group_by == "cohort":
            self.require_clinician()
        people = (
            self.visible()
            if spec.participants is None
            else list(dict.fromkeys(self.resolve(ref) for ref in spec.participants))
        )

        as_of = self.as_of()
        end = _utc(spec.end) or as_of
        if end is not None and as_of is not None:
            end = min(end, as_of)
        start = _utc(spec.start)
        if start is None and end is not None:
            start = end - timedelta(hours=spec.hours or DEFAULT_HOURS)
        if start is not None and end is not None and start >= end:
            raise QueryError("start must be before end.")

        live_metrics = [m for m in spec.metrics if m in LIVE_METRICS]

        def history(pid: str) -> list[Window]:
            """The windows in range; a query up to now that asks for live
            metrics also gets a point at the live reading's time."""
            windows = self._history(pid, start, end)
            if live_metrics and end is not None and end == as_of and windows:
                newest = self._live_view(windows[-1])
                if newest.live_at is not None:
                    windows.append(
                        Window(
                            person_id=pid,
                            source_dataset=newest.source_dataset,
                            window_start=newest.live_at,
                            window_end=newest.live_at,
                            values={m: newest.values.get(m) for m in live_metrics},
                        )
                    )
            return windows

        per_person = {
            pid: q.participant_points(history(pid), spec.metrics, spec.bucket, spec.agg)
            for pid in people
        }
        per_person = {pid: points for pid, points in per_person.items() if points}

        if spec.group_by == "cohort":
            pooled = q.pool(
                list(per_person.values()), spec.metrics, spec.agg, spec.bucket
            )
            series = [Series(display_name="Cohort", points=pooled)]
        else:
            series = [
                Series(display_name=display_name(pid), points=pts)
                for pid, pts in per_person.items()
            ]
            if spec.sort_by is not None:
                metric = spec.sort_by
                series = q.rank(
                    series, lambda s: q.sort_key(s.points, metric), spec.order
                )

        series, audit = disclose(
            series,
            pooled=spec.group_by == "cohort",
            metrics=spec.metrics,
            principal=self.principal,
        )
        total = len(series)
        truncated = False
        if spec.limit is not None and total > spec.limit:
            series, truncated = series[: spec.limit], True
        budget = MAX_POINTS
        for s in series:
            if len(s.points) > budget:
                s.points, truncated = s.points[:budget], True
            budget = max(0, budget - len(s.points))

        return QueryResult(
            as_of=as_of,
            start=start,
            end=end,
            metrics=spec.metrics,
            units={m: unit_of(m) for m in spec.metrics},
            bucket=spec.bucket,
            agg=spec.agg,
            group_by=spec.group_by,
            series=series,
            total_series=total,
            truncated=truncated,
            audit=audit,
        )

    # --- participants -------------------------------------------------------

    def participants(
        self, sort_by: str = GLUCO_SCORE, order: q.Order = "asc"
    ) -> list[ParticipantRow]:
        """Each visible participant's newest window up to now."""
        if sort_by != "person_id":
            check_metrics([sort_by])
        rows = [self._row(w) for pid in self.visible() if (w := self._latest(pid))]
        if sort_by == "person_id":
            return sorted(rows, key=lambda r: r.person_id, reverse=order == "desc")
        return q.rank(rows, lambda r: r.values.get(sort_by), order)

    def participant(self, ref: str) -> ParticipantRow:
        return self._row(self._require_latest(self.resolve(ref)))

    def explain(self, ref: str, hours: float = 24.0) -> Explanation:
        """What changed, plus where the person sits in the cohort for clinicians."""
        person_id = self.resolve(ref)
        return Explanation(
            change=self._change(person_id, hours),
            cohort_position=(
                self._cohort_position(person_id) if self.is_clinician else None
            ),
        )

    def _change(self, person_id: str, hours: float) -> ChangeReport:
        """Now vs `hours` ago, and now vs the person's own last 7 days."""
        if hours <= 0:
            raise QueryError("hours must be positive.")
        now = self._require_latest(person_id)
        then_windows = self._history(
            person_id, end=now.window_end - timedelta(hours=hours)
        )
        then = then_windows[-1] if then_windows else None
        week = self._history(
            person_id, start=now.window_end - timedelta(hours=BASELINE_HOURS)
        )
        baseline = compute_feature_stats(w.values for w in week)

        changes: list[MetricChange] = []
        for metric, spec in METRICS.items():
            if metric == GLUCO_CHANGE:
                continue
            value = now.value(metric)
            before = then.value(metric) if then else None
            stat = baseline.get(metric)
            deviation = (
                describe_feature(metric, value, stat)
                if value is not None and stat
                else None
            )
            changes.append(
                MetricChange(
                    metric=metric,
                    label=spec.label,
                    unit=spec.unit,
                    now=_round(value),
                    then=_round(before),
                    delta=(
                        _round(value - before)
                        if value is not None and before is not None
                        else None
                    ),
                    baseline_mean=_round(stat.mean) if stat else None,
                    z_vs_baseline=_round(deviation.z_score, 2) if deviation else None,
                )
            )
        shifts = sorted(
            (c for c in changes if c.metric in SENSOR_METRICS and c.z_vs_baseline),
            key=lambda c: abs(c.z_vs_baseline or 0.0),
            reverse=True,
        )
        return ChangeReport(
            person_id=person_id,
            display_name=display_name(person_id),
            as_of=self.as_of(),
            hours=hours,
            now_window_end=now.window_end,
            then_window_end=then.window_end if then else None,
            changes=changes,
            largest_shifts=[c.metric for c in shifts[:3]],
        )

    # --- cohort (clinician only) --------------------------------------------

    def _cohort_latest(self) -> list[Window]:
        self.require_clinician()
        return [w for pid in self.visible() if (w := self._latest(pid))]

    def _cohort_position(self, person_id: str, n: int = 5) -> list[FeatureDeviation]:
        """The person's metrics furthest from everyone's newest windows."""
        latest = self._cohort_latest()
        stats = compute_feature_stats(w.values for w in latest)
        mine = self._require_latest(person_id)
        sensors = {k: v for k, v in mine.values.items() if k in SENSOR_METRICS}
        return [
            d.model_copy(
                update={
                    "value": round(d.value, 4),
                    "median": round(d.median, 4),
                    "z_score": round(d.z_score, 2),
                    "percentile": round(d.percentile, 1),
                }
            )
            for d in top_deviations(sensors, stats, n)
        ]

    def compare_to_cohort(self, ref: str, metric: str) -> CohortComparison:
        check_metrics([metric])
        latest = self._cohort_latest()
        person_id = self.resolve(ref)
        stat = compute_feature_stats(w.values for w in latest).get(metric)
        value = self._require_latest(person_id).value(metric)
        if value is None:
            raise QueryError(f"{person_id} has no value for {metric!r}.")
        deviation = describe_feature(metric, value, stat) if stat else None
        if stat is None or deviation is None:
            raise QueryError(f"{metric!r} does not vary across the patient panel.")
        return CohortComparison(
            person_id=person_id,
            metric=metric,
            unit=unit_of(metric),
            value=round(value, 4),
            cohort_median=round(stat.p50, 4),
            cohort_mean=round(stat.mean, 4),
            z_score=round(deviation.z_score, 2),
            percentile=round(deviation.percentile, 1),
            direction=deviation.direction,
            cohort_size=sum(1 for w in latest if w.value(metric) is not None),
        )

    def cohort_overview(self, top_n: int = 3) -> CohortOverview:
        latest = self._cohort_latest()
        rows = [self._row(w) for w in latest]

        def by(metric: str, order: q.Order) -> list[ParticipantRow]:
            return q.rank(rows, lambda r: r.values.get(metric), order)

        drops = [
            r for r in by(GLUCO_CHANGE, "asc") if (r.values.get(GLUCO_CHANGE) or 0) < 0
        ]
        gains = [
            r for r in by(GLUCO_CHANGE, "desc") if (r.values.get(GLUCO_CHANGE) or 0) > 0
        ]
        summaries = {
            metric: summary
            for metric in METRICS
            if (summary := _summary([w.value(metric) for w in latest]))
        }
        return CohortOverview(
            as_of=self.as_of(),
            participants=len(latest),
            gluco_score=summaries.get(GLUCO_SCORE),
            lowest_gluco=by(GLUCO_SCORE, "asc")[:top_n],
            biggest_drops=drops[:top_n],
            biggest_gains=gains[:top_n],
            metrics=summaries,
        )

    # --- catalog and streaming ------------------------------------------------

    def catalog(self) -> Catalog:
        as_of = self.as_of()
        bounds = self._store.data_range()
        return Catalog(
            as_of=as_of,
            data_start=bounds[0] if bounds else None,
            data_end=as_of,
            metrics=[
                MetricInfo(
                    name=name,
                    label=spec.label,
                    unit=spec.unit,
                    description=spec.description,
                    higher_is_better=spec.higher_is_better,
                    live=spec.live,
                )
                for name, spec in METRICS.items()
            ],
            participants=[
                ParticipantInfo(
                    person_id=pid,
                    display_name=display_name(pid),
                    source_dataset=self._store.dataset_of(pid) or "unknown",
                )
                for pid in self.visible()
            ],
            buckets=list(q.BUCKETS),
            aggs=list(q.AGGS),
            group_bys=["participant", "cohort"]
            if self.is_clinician
            else ["participant"],
        )

    def windows_between(self, after: datetime, until: datetime) -> list[ParticipantRow]:
        """Visible windows with after < window_end <= until (for the live stream)."""
        return [
            self._row(self._live_view(w))
            for pid in self.visible()
            for w in self._store.history(pid, after, until)
        ]
