"""Operating-point selection must weight people equally and reject bad inputs."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tiger"))
from accuracy_selection import participant_weights, select_threshold


def test_each_person_has_equal_total_weight():
    groups = np.array(["a"] * 20 + ["b"] * 2)
    w = participant_weights(groups)
    assert w[groups == "a"].sum() == pytest.approx(w[groups == "b"].sum())


def test_threshold_learns_from_inner_predictions():
    assert (
        select_threshold([0, 0, 1, 1], [0.1, 0.2, 0.41, 0.44], ["a", "b", "c", "d"])
        == 0.4
    )


def test_tied_decisions_prefer_default_threshold():
    assert select_threshold([0, 1], [0.1, 0.9], ["a", "b"]) == 0.5


def test_repeating_one_person_does_not_change_selection():
    y, p, g = [0, 1], [0.42, 0.46], ["a", "b"]
    assert select_threshold(y, p, g) == select_threshold(
        [0] * 50 + [1], [0.42] * 50 + [0.46], ["a"] * 50 + ["b"]
    )


@pytest.mark.parametrize("p", [[float("nan"), 0.6], [-0.1, 0.6], [0.1, 1.1]])
def test_invalid_probabilities_fail(p):
    with pytest.raises(ValueError):
        select_threshold([0, 1], p, ["a", "b"])
