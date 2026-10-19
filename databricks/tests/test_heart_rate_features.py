"""Window boundaries and missing-HR rules for a new sensor family."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tiger"))
from heart_rate_features import HR_FEATURES, heart_rate_features


def test_known_constant_heart_rate():
    f = heart_rate_features(np.arange(1440), np.full(1440, 72), 1440)
    assert tuple(f) == HR_FEATURES
    assert f == {"hr_mean_bpm": 72, "hr_std_bpm": 0, "hr_p10_bpm": 72, "hr_p90_bpm": 72}


def test_future_samples_are_excluded():
    t = np.arange(1442)
    v = np.full(1442, 72.0)
    v[1440:] = 1e9
    assert heart_rate_features(t, v, 1440)["hr_mean_bpm"] == 72


def test_exact_eighty_percent_coverage_passes():
    t = np.arange(1440)
    t = t[t % 5 != 0]
    assert (
        len(t) == 1152
        and heart_rate_features(t, np.ones(len(t)) * 72, 1440) is not None
    )
    assert heart_rate_features(t[1:], np.ones(len(t) - 1) * 72, 1440) is None


def test_missing_hour_fails_even_with_high_total_coverage():
    t = np.arange(60, 1440)
    assert heart_rate_features(t, np.ones(len(t)) * 72, 1440) is None


@pytest.mark.parametrize("bad", [np.nan, np.inf, 0, -1])
def test_invalid_observed_hr_returns_missing_window(bad):
    v = np.ones(1440) * 72
    v[500] = bad
    assert heart_rate_features(np.arange(1440), v, 1440) is None


def test_duplicate_or_unsorted_minutes_rejected():
    with pytest.raises(ValueError):
        heart_rate_features([1, 1], [72, 72], 1440)
    with pytest.raises(ValueError):
        heart_rate_features([2, 1], [72, 72], 1440)


def test_time_shift_preserves_features():
    t = np.arange(1440)
    v = 70 + np.sin(t / 60)
    assert heart_rate_features(t, v, 1440) == heart_rate_features(
        t + 30000000, v, 30001440
    )
