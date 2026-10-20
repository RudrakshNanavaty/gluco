"""Publication mismatch and SQL result bounds, without cloud credentials."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tiger"))
from publication_parity import ParityError, compare, delta_rows

MODEL = "a" * 32


def row(instant=1700000000123456):
    return ["person", instant, MODEL, 0.1, 32.1, 60.0, 0.25]


def test_exact_microsecond_key_and_string_numbers_match():
    assert compare([row()], [[str(v) for v in row()]], 1, MODEL)["status"] == "pass"


def test_submillisecond_timestamp_loss_is_detected():
    report = compare([row()], [row(1700000000123000)], 1, MODEL)
    assert report["missing_tiger_keys"] == report["extra_tiger_keys"] == 1
    assert "publication_key_mismatch" in report["failures"]


@pytest.mark.parametrize("field", range(3, 7))
def test_changed_metric_detected(field):
    changed = row()
    changed[field] += 0.01
    assert (
        "numeric_publication_mismatch"
        in compare([row()], [changed], 1, MODEL)["failures"]
    )


def test_equal_counts_do_not_hide_different_keys():
    changed = row()
    changed[0] = "other-person"
    assert (
        "publication_key_mismatch" in compare([row()], [changed], 1, MODEL)["failures"]
    )


def test_wrong_model_on_both_sides_still_fails():
    assert "unexpected_model" in compare([row()], [row()], 1, "b" * 32)["failures"]


def test_wrong_expected_count_fails():
    assert "unexpected_window_count" in compare([row()], [row()], 2, MODEL)["failures"]


@pytest.mark.parametrize("rows", [[], [row(), row()], [[None] * 7], [row()[:3]]])
def test_invalid_empty_duplicate_rows_fail(rows):
    with pytest.raises(ParityError):
        compare(rows, [row()], 1, MODEL)


@pytest.mark.parametrize("value", [None, float("nan"), float("inf")])
def test_invalid_metric_fails(value):
    changed = row()
    changed[3] = value
    with pytest.raises(ParityError, match="invalid_publication_row"):
        compare([row()], [changed], 1, MODEL)


def test_chunked_or_truncated_api_result_cannot_pass():
    def api(*args):
        return {
            "statement_id": "a" * 8
            + "-"
            + "b" * 4
            + "-"
            + "c" * 4
            + "-"
            + "d" * 4
            + "-"
            + "e" * 12,
            "status": {"state": "SUCCEEDED"},
            "manifest": {"total_chunk_count": 2},
            "result": {"data_array": [row()]},
        }

    with pytest.raises(ParityError, match="failed_or_chunked_statement"):
        delta_rows(api, "a" * 16, "safe-session")


def test_session_is_bound_not_interpolated():
    def api(method, path, payload):
        assert payload["parameters"][0]["value"] == "safe-session"
        assert "safe-session" not in payload["statement"]
        return {
            "statement_id": "a" * 8
            + "-"
            + "b" * 4
            + "-"
            + "c" * 4
            + "-"
            + "d" * 4
            + "-"
            + "e" * 12,
            "status": {"state": "SUCCEEDED"},
            "manifest": {"total_chunk_count": 1},
            "result": {"data_array": [row()]},
        }

    assert delta_rows(api, "a" * 16, "safe-session")[1] == [row()]


def test_pending_query_timeout_cancels_its_own_statement(monkeypatch):
    import publication_parity

    ticks = iter([0, 121])
    monkeypatch.setattr(publication_parity.time, "monotonic", lambda: next(ticks))
    identifier = (
        "a" * 8 + "-" + "b" * 4 + "-" + "c" * 4 + "-" + "d" * 4 + "-" + "e" * 12
    )
    calls = []

    def api(method, path, payload):
        calls.append(path)
        return {"statement_id": identifier, "status": {"state": "PENDING"}}

    with pytest.raises(ParityError, match="statement_timeout"):
        delta_rows(api, "a" * 16, "safe-session")
    assert calls[-1] == f"/api/2.0/sql/statements/{identifier}/cancel"


def test_tiny_serialization_difference_within_tolerance_passes():
    changed = row()
    changed[3] += 1e-12
    assert compare([row()], [changed], 1, MODEL)["status"] == "pass"
