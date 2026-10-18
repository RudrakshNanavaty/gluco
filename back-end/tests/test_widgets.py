import json

from agent.domain.metrics import GLUCO_SCORE

STAGES = ["design", "fetch", "compliance", "bind"]
RANKING = {
    "title": "Lowest Gluco Scores",
    "kind": "ranking",
    "query": {
        "metrics": [GLUCO_SCORE],
        "hours": 168,
        "bucket": "all",
        "agg": "last",
        "sort_by": GLUCO_SCORE,
        "order": "asc",
        "limit": 5,
    },
}


async def test_build_widget_runs_the_whole_pipeline(invoke_clinician):
    out = await invoke_clinician(
        "build_widget",
        title="Lowest",
        kind="ranking",
        metrics=[GLUCO_SCORE],
        participants=[],  # what models send for "everyone"
    )
    widget = out["widget"]
    assert [step["stage"] for step in widget["steps"]] == STAGES
    assert widget["query"]["bucket"] == "all"
    assert "start" not in widget["query"]  # relative, so a pin follows the clock
    series = out["chart"]["series"]
    assert len(series) == 5
    assert "demo:" not in json.dumps(out)
    scores = [s["points"][-1][GLUCO_SCORE] for s in series]
    assert scores == sorted(scores)


async def test_a_patient_widget_only_ever_shows_their_own_data(invoke_patient):
    out = await invoke_patient(
        "build_my_widget", title="My heart rate", metrics=["hr_mean_bpm_24h"]
    )
    [series] = out["chart"]["series"]
    assert series["display_name"] == "Patient 013"
    compliance = next(s for s in out["widget"]["steps"] if s["stage"] == "compliance")
    assert "your own data only" in compliance["text"]
    assert out["widget"]["kind"] == "trend"


async def test_build_widget_failures_are_payloads(invoke_clinician):
    bad = await invoke_clinician(
        "build_widget", title="x", kind="trend", metrics=["glucose"]
    )
    assert bad["code"] == "bad_argument"


SMALL_COHORT = {"participants": ["13", "2"], "bucket": "day", "group_by": "cohort"}


def test_post_query_hides_small_cells_and_internal_keys(client, as_clinician):
    """The disclosure rule holds outside widgets too, not only in the pipeline."""
    body = client.post("/query", json=SMALL_COHORT, headers=as_clinician).json()
    assert all(p[GLUCO_SCORE] is None for p in body["series"][0]["points"])
    assert "hidden" in body["audit"][-1]
    named = client.post(
        "/query", json={"participants": ["13", "2"]}, headers=as_clinician
    ).json()
    assert "demo:" not in json.dumps(named["series"])


async def test_tool_charts_hide_small_cells_and_internal_keys(invoke_clinician):
    out = await invoke_clinician("query_data", metrics=[GLUCO_SCORE], **SMALL_COHORT)
    assert all(p[GLUCO_SCORE] is None for p in out["chart"]["series"][0]["points"])
    named = await invoke_clinician(
        "query_data", metrics=[GLUCO_SCORE], participants=["13", "2"]
    )
    assert "demo:" not in json.dumps(named["chart"])


def test_pin_list_refresh_and_unpin(client, as_clinician, as_patient):
    pinned = client.post("/widgets", json=RANKING, headers=as_clinician)
    assert pinned.status_code == 201
    wid = pinned.json()["id"]
    assert [w["id"] for w in client.get("/widgets", headers=as_clinician).json()] == [
        wid
    ]
    assert client.get("/widgets", headers=as_patient).json() == []  # per user

    data = client.get(f"/widgets/{wid}/data", headers=as_clinician).json()
    assert [step["stage"] for step in data["steps"]] == STAGES
    assert len(data["result"]["series"]) == 5
    assert client.get(f"/widgets/{wid}/data", headers=as_patient).status_code == 404

    assert client.delete(f"/widgets/{wid}", headers=as_clinician).status_code == 204
    assert client.get("/widgets", headers=as_clinician).json() == []


def test_a_chat_widget_rebuilds_without_pinning(client, as_clinician, as_patient):
    data = client.post("/widgets/preview", json=RANKING, headers=as_clinician).json()
    assert [step["stage"] for step in data["steps"]] == STAGES
    assert len(data["result"]["series"]) == 5
    assert client.get("/widgets", headers=as_clinician).json() == []  # not pinned
    mine = client.post("/widgets/preview", json=RANKING, headers=as_patient).json()
    assert [s["display_name"] for s in mine["result"]["series"]] == ["Patient 013"]


def test_patients_cannot_pin_cohort_views(client, as_patient):
    spec = {
        "title": "Panel",
        "kind": "cohort_trend",
        "query": {"metrics": [GLUCO_SCORE], "group_by": "cohort"},
    }
    assert client.post("/widgets", json=spec, headers=as_patient).status_code == 403


async def test_every_clinician_widget_kind_builds(invoke_clinician):
    cases = {
        "trend": {"metrics": [GLUCO_SCORE], "participants": ["13"]},
        "ranking": {"metrics": [GLUCO_SCORE]},
        "cohort_trend": {"metrics": ["hr_mean_bpm_24h"]},
        "stat": {"metrics": [GLUCO_SCORE]},
        "table": {"metrics": [GLUCO_SCORE, "hr_mean_bpm_24h", "motion_mean_g"]},
        "heatmap": {"metrics": [GLUCO_SCORE], "limit": 6},
    }
    for kind, args in cases.items():
        out = await invoke_clinician("build_widget", title=kind, kind=kind, **args)
        assert "error" not in out, (kind, out)
        assert [s["stage"] for s in out["widget"]["steps"]] == STAGES
        assert "demo:" not in json.dumps(out["chart"]), kind


async def test_a_clinician_stat_defaults_to_the_panel_average(invoke_clinician):
    panel = await invoke_clinician(
        "build_widget", title="Panel", kind="stat", metrics=[GLUCO_SCORE]
    )
    assert panel["widget"]["query"]["group_by"] == "cohort"
    one = await invoke_clinician(
        "build_widget",
        title="One",
        kind="stat",
        metrics=[GLUCO_SCORE],
        participants=["13"],
    )
    assert one["widget"]["query"]["group_by"] == "participant"


async def test_heatmap_is_patients_by_day(invoke_clinician):
    out = await invoke_clinician(
        "build_widget",
        title="Heat",
        kind="heatmap",
        metrics=[GLUCO_SCORE],
        limit=6,
    )
    assert out["widget"]["query"]["bucket"] == "day"
    assert len(out["chart"]["series"]) == 6


async def test_patient_widget_kinds_stay_on_their_own_data(invoke_patient):
    for kind in ("trend", "stat", "table"):
        out = await invoke_patient(
            "build_my_widget",
            title=kind,
            kind=kind,
            metrics=[GLUCO_SCORE, "hr_mean_bpm_24h"],
        )
        assert "error" not in out, (kind, out)
        assert [s["display_name"] for s in out["chart"]["series"]] == ["Patient 013"]
    refused = await invoke_patient(
        "build_my_widget", title="x", kind="heatmap", metrics=[GLUCO_SCORE]
    )
    assert "error" in refused or "heatmap" not in str(refused.get("widget"))
