import pytest
from guardrail_eval import (
    CATEGORIES,
    ROLES,
    Case,
    Outcome,
    Trial,
    load_cases,
    wilson_upper,
)


def test_wilson_upper_with_no_events_is_still_above_zero():
    assert wilson_upper(0, 100) == pytest.approx(0.037, abs=0.001)
    assert wilson_upper(0, 12) > 0.2  # a small cell gives a wide bound


def test_wilson_upper_when_everything_fails_is_one():
    assert wilson_upper(10, 10) == pytest.approx(1.0)


def test_wilson_upper_with_no_trials_is_one():
    assert wilson_upper(0, 0) == 1.0


def test_wilson_upper_grows_with_events():
    assert wilson_upper(1, 50) > wilson_upper(0, 50)
    assert wilson_upper(5, 50) > wilson_upper(1, 50)


def _case(expect: str) -> Case:
    return Case(role="patient", text="x", expect=expect, source="agent")


def test_a_decline_prompt_fails_if_any_repeat_passes_it():
    out = Outcome(_case("diagnosis"), [Trial(True, "diagnosis"), Trial(False, "none")])
    assert out.failed
    assert out.flaky


def test_a_pass_prompt_fails_if_any_repeat_declines_it():
    out = Outcome(_case("none"), [Trial(False, "none"), Trial(True, "diagnosis")])
    assert out.failed


def test_a_decline_in_the_wrong_category_is_a_mismatch_not_a_failure():
    out = Outcome(_case("treatment"), [Trial(True, "diagnosis")])
    assert not out.failed
    assert out.mismatch


def test_a_prompt_whose_every_call_errored_is_not_scored():
    out = Outcome(_case("diagnosis"), [], ["TimeoutError: slow"])
    assert not out.scored
    assert not out.failed


def test_the_shipped_cases_are_valid_and_cover_both_roles():
    cases = load_cases()
    assert {c.role for c in cases} == set(ROLES)
    assert any(c.should_decline for c in cases)
    assert any(not c.should_decline for c in cases)
    assert {c.expect for c in cases} <= {*CATEGORIES, "none"}
