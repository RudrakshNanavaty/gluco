import re
from collections.abc import Iterator
from typing import Any

import pytest
from support import OTHER, PID

from agent.domain.metrics import GLUCO_SCORE


async def test_list_participants_sorts_and_caps(invoke_clinician, clinician):
    out = await invoke_clinician("list_participants", top_k=3)
    scores = [p["values"][GLUCO_SCORE] for p in out["participants"]]
    assert scores == sorted(scores)
    assert (out["rows"], out["total_participants"]) == (3, 17)
    assert out["as_of"] == clinician.as_of().isoformat()
    bad = await invoke_clinician("list_participants", top_k=0)
    assert bad["code"] == "bad_argument"


async def test_get_participant_resolves_short_refs_and_charts_the_week(
    invoke_clinician,
):
    out = await invoke_clinician("get_participant", person_id="P013")
    assert out["latest"]["person_id"] == PID
    assert out["gluco_week"]["points"] == 168
    [series] = out["chart"]["series"]
    assert len(series["points"]) <= 48
    assert out["chart"]["downsampled"] is True


async def test_unknown_person_is_a_payload_not_an_exception(invoke_clinician):
    out = await invoke_clinician("get_participant", person_id="99")
    assert out["code"] == "not_found"
    assert out["rows"] == 0


async def test_explain_change_combines_history_and_cohort(invoke_clinician):
    out = await invoke_clinician("explain_change", person_id="13")
    assert out["change"]["person_id"] == PID
    assert out["cohort_position"]
    assert GLUCO_SCORE in out["chart"]["metrics"]
    assert "->" in out["summary"]


async def test_query_data_keeps_llm_payloads_bounded(invoke_clinician):
    out = await invoke_clinician(
        "query_data", metrics=[GLUCO_SCORE, "hr_mean_bpm_24h"], bucket="hour"
    )
    points = sum(len(s["points"]) for s in out["chart"]["series"])
    assert len(out["chart"]["series"]) == 17
    assert points <= 240
    bad = await invoke_clinician("query_data", metrics=["glucose"])
    assert bad["code"] == "bad_argument"
    assert "gluco_score" in bad["suggestions"]


async def test_cohort_tools(invoke_clinician):
    overview = await invoke_clinician("cohort_overview")
    assert overview["overview"]["participants"] == 17
    compare = await invoke_clinician(
        "compare_to_cohort", person_id="13", metric="hr_mean_bpm_24h"
    )
    assert compare["comparison"]["percentile_method"] == "normal_approximation"


async def test_patient_tools_are_bound_to_the_patient(invoke_patient):
    status = await invoke_patient("get_my_status")
    assert status["latest"]["person_id"] == PID
    change = await invoke_patient("explain_my_change", hours=12)
    assert change["change"]["hours"] == 12
    assert "cohort_position" not in change
    trend = await invoke_patient("get_my_trend", metric="motion_mean_g", bucket="day")
    assert trend["trend"]["metric"] == "motion_mean_g"
    data = await invoke_patient("query_my_data", metrics=[GLUCO_SCORE], agg="min")
    assert [s["display_name"] for s in data["chart"]["series"]] == ["Patient 013"]


# --- Patient isolation: no parameter names a person --------------------------------

PERSON_PARAM = re.compile(r"person|participant|patient|subject|user|(^|_)id$", re.I)
OTHER_REFS = [OTHER, "P002", "Patient 002", "2", "*", "all"]


def _owners(value: Any) -> Iterator[str]:
    """Every person id or display name a tool result names."""
    if isinstance(value, dict):
        for key, item in value.items():
            if key in ("display_name", "person_id") and isinstance(item, str):
                yield item
            else:
                yield from _owners(item)
    elif isinstance(value, list):
        for item in value:
            yield from _owners(item)


def test_no_patient_tool_parameter_is_named_like_a_person(patient_tools):
    # The free-text parameters (metric, metrics, title) can carry any string, so
    # this only rules out a parameter built to take a person; the sweep below
    # covers the free text. QueryService checks scope as well (test_query.py).
    assert patient_tools
    for name, tool in patient_tools.items():
        params = tool.params_json_schema.get("properties", {})
        named = [p for p in params if PERSON_PARAM.search(p)]
        assert not named, f"{name} takes {named}"


@pytest.mark.parametrize("other", OTHER_REFS)
async def test_other_participants_in_free_text_never_reach_their_data(
    invoke_patient, other
):
    calls = [
        ("get_my_trend", {"metric": other}),
        ("query_my_data", {"metrics": [other]}),
        ("query_my_data", {"metrics": [GLUCO_SCORE, other], "bucket": "all"}),
        ("build_my_widget", {"title": other, "metrics": [other]}),
        ("build_my_widget", {"title": other, "metrics": [GLUCO_SCORE]}),
    ]
    seen: set[str] = set()
    for name, args in calls:
        seen |= set(_owners(await invoke_patient(name, **args)))
    assert seen <= {"Patient 013", PID}
    assert seen, "no call returned any data, so the sweep proves nothing"
