"""Numeric stability and zero-boundary preservation for uncalibrated scores."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tiger"))
from margin_scores import margin_scores


def test_large_margins_are_finite_monotone_and_preserve_zero_boundary():
    x = np.array([-1e6, -1, 0, 1, 1e6])
    p = margin_scores(x)
    assert np.isfinite(p).all() and ((p >= 0) & (p <= 1)).all()
    assert (np.diff(p) >= 0).all() and p[2] == 0.5
    np.testing.assert_array_equal(p >= 0.5, x >= 0)


@pytest.mark.parametrize("x", [np.nan, np.inf, -np.inf])
def test_nonfinite_margin_is_rejected(x):
    with pytest.raises(ValueError):
        margin_scores([x])
