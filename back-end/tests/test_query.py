from datetime import timedelta

import pytest
from support import OTHER, PID, FakeTime

from agent.auth import CLINICIAN, patient
from agent.clock import ReplayClock
from agent.domain.errors import ForbiddenError, QueryError
from agent.domain.metrics import GLUCO_CHANGE, GLUCO_SCORE, METRICS
from agent.query import QueryService, QuerySpec


def test_clinician_sees_everyone_patient_only_themselves(clinician, me):
    assert len(clinician.visible()) == 17
    assert me.visible() == [PID]
    assert [r.person_id for r in me.participants()] == [PID]


def test_patient_cannot_name_anyone_else_even_by_short_ref(me):
    assert me.resolve("13") == PID
    for ref in ("2", OTHER, "nobody"):
        with pytest.raises(ForbiddenError):
            me.resolve(ref)
    with pytest.raises(ForbiddenError):
        me.query(QuerySpec(participants=["2"]))


def test_every_per_person_method_checks_scope_itself(me):
    """No caller has to remember to resolve first: a raw key is refused too."""
    assert me.participant("13").person_id == PID
    assert me.explain(PID).change.person_id == PID
    calls = (
        lambda ref: me.participant(ref),
        lambda ref: me.explain(ref),
        lambda ref: me.compare_to_cohort(ref, GLUCO_SCORE),
    )
    for call in calls:
        for ref in ("2", OTHER):
            with pytest.raises(ForbiddenError):
                call(ref)


def test_patient_gets_no_cohort_data(me):
    with pytest.raises(ForbiddenError):
        me.query(QuerySpec(group_by="cohort"))
    with pytest.raises(ForbiddenError):
        me.cohort_overview()
    assert me.explain(PID).cohort_position is None
    assert me.catalog().group_bys == ["participant"]


def test_query_defaults_to_the_last_week_hourly(clinician):
    result = clinician.query(QuerySpec(participants=["13"]))
    assert result.end == clinician.as_of()
    assert result.start == result.end - timedelta(hours=168)
    [series] = result.series
    assert len(series.points) == 168
    assert series.display_name == "Patient 013"
    assert result.units == {GLUCO_SCORE: METRICS[GLUCO_SCORE].unit}


def test_query_rejects_bad_specs_with_help(clinician):
    with pytest.raises(QueryError) as exc:
        clinician.query(QuerySpec(metrics=["glucose"]))
    suggestions = exc.value.details["suggestions"]
    assert isinstance(suggestions, list)
    assert "gluco_score" in suggestions
    with pytest.raises(QueryError):
        clinician.query(QuerySpec(sort_by="hr_mean_bpm_24h"))
    with pytest.raises(QueryError):
        clinician.query(QuerySpec(start=clinician.as_of(), end=clinician.as_of()))


def test_ranking_with_one_value_per_participant(clinician):
    result = clinician.query(
        QuerySpec(bucket="all", agg="last", sort_by=GLUCO_SCORE, order="asc", limit=3)
    )
    values = [s.points[0][GLUCO_SCORE] for s in result.series]
    assert values == sorted(values)
    assert (result.total_series, len(result.series), result.truncated) == (17, 3, True)
    lowest = clinician.participants(GLUCO_SCORE, "asc")[0]
    assert result.series[0].display_name == lowest.display_name


def test_cohort_series_pools_everyone_by_day(clinician):
    result = clinician.query(
        QuerySpec(metrics=["hr_mean_bpm_24h"], bucket="day", group_by="cohort")
    )
    [series] = result.series
    assert series.display_name == "Cohort"
    assert all(p["participants"] >= 16 for p in series.points)
    assert result.audit[-1] == "Every cohort point pools at least 3 people"


def test_cohort_points_pooled_from_too_few_people_are_hidden(clinician):
    result = clinician.query(
        QuerySpec(participants=["13", "2"], bucket="day", group_by="cohort")
    )
    [series] = result.series
    assert series.points
    assert all(p[GLUCO_SCORE] is None for p in series.points)
    assert "hidden" in result.audit[-1]


def test_explain_change_compares_with_then_and_with_own_week(clinician):
    report = clinician.explain(PID, hours=24).change
    gluco = next(c for c in report.changes if c.metric == GLUCO_SCORE)
    assert report.then_window_end == report.now_window_end - timedelta(hours=24)
    assert gluco.delta is not None
    assert gluco.delta < -40  # the pinned sharp drop
    assert gluco.z_vs_baseline is not None
    assert gluco.z_vs_baseline < -2
    assert GLUCO_CHANGE not in {c.metric for c in report.changes}
    assert 0 < len(report.largest_shifts) <= 3


def test_imu_participant_has_no_heart_rate_and_that_is_not_an_error(clinician):
    row = clinician.participant(clinician.resolve("IMU-00"))
    assert row.values["hr_mean_bpm_24h"] is None
    report = clinician.explain(row.person_id).change
    hr = next(c for c in report.changes if c.metric == "hr_mean_bpm_24h")
    assert (hr.now, hr.delta) == (None, None)
    with pytest.raises(QueryError):
        clinician.compare_to_cohort(row.person_id, "hr_mean_bpm_24h")


def test_cohort_overview(clinician):
    overview = clinician.cohort_overview()
    assert overview.participants == 17
    assert overview.lowest_gluco[0].person_id == clinician.participants()[0].person_id
    assert all((r.values[GLUCO_CHANGE] or 0) < 0 for r in overview.biggest_drops)
    assert PID in {r.person_id for r in overview.biggest_drops}
    assert overview.gluco_score is not None
    assert overview.gluco_score.n == 17


def test_compare_to_cohort(clinician):
    comparison = clinician.compare_to_cohort(PID, GLUCO_SCORE)
    assert comparison.cohort_size == 17
    assert comparison.direction == "below"


def test_everything_stops_at_the_replay_clock(store):
    time = FakeTime()
    clock = ReplayClock(store.data_range, seconds_per_hour=10, time_source=time)
    svc = QueryService(store, clock, CLINICIAN)
    start = clock.now()
    assert start is not None
    assert svc.participant(PID).window_end == start
    result = svc.query(QuerySpec(participants=[PID], hours=1000, bucket="raw"))
    assert result.series[0].points[-1]["t"] == start

    time.now += 30  # three simulated hours
    now = clock.now()
    assert now is not None
    fresh = svc.windows_between(start, now)
    assert len(fresh) == 3 * 17
    patient_view = QueryService(store, clock, patient(PID))
    assert len(patient_view.windows_between(start, now)) == 3
