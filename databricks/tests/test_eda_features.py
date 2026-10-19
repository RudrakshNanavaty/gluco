"""Past-only EDA summaries and explicit zero-versus-missing behavior."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tiger"))
from eda_features import EDA_FEATURES, eda_window_features


def test_known_constant_heart_rate():
    f = eda_window_features(np.arange(1440), np.full(1440, 72), 1440)
    assert tuple(f) == EDA_FEATURES
    assert f == {"eda_mean": 72, "eda_std": 0, "eda_p10": 72, "eda_p90": 72}


def test_future_samples_are_excluded():
    t = np.arange(1442)
    v = np.full(1442, 72.0)
    v[1440:] = 1e9
    assert eda_window_features(t, v, 1440)["eda_mean"] == 72


def test_exact_eighty_percent_coverage_passes():
    t = np.arange(1440)
    t = t[t % 5 != 0]
    assert (
        len(t) == 1152
        and eda_window_features(t, np.ones(len(t)) * 72, 1440) is not None
    )
    assert eda_window_features(t[1:], np.ones(len(t) - 1) * 72, 1440) is None


def test_missing_hour_fails_even_with_high_total_coverage():
    t = np.arange(60, 1440)
    assert eda_window_features(t, np.ones(len(t)) * 72, 1440) is None


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf, -1])
def test_invalid_observed_hr_returns_missing_window(bad):
    v = np.ones(1440) * 72
    v[500] = bad
    assert eda_window_features(np.arange(1440), v, 1440) is None


def test_duplicate_or_unsorted_minutes_rejected():
    with pytest.raises(ValueError):
        eda_window_features([1, 1], [72, 72], 1440)
    with pytest.raises(ValueError):
        eda_window_features([2, 1], [72, 72], 1440)


def test_time_shift_preserves_features():
    t = np.arange(1440)
    v = 70 + np.sin(t / 60)
    assert eda_window_features(t, v, 1440) == eda_window_features(
        t + 30000000, v, 30001440
    )


def test_linear_series_matches_analytic_summaries():
    n = 1440
    f = eda_window_features(np.arange(n), 60 + np.arange(n) / n, n)
    assert f["eda_mean"] == pytest.approx(60 + (n - 1) / (2 * n))
    assert f["eda_std"] == pytest.approx(np.sqrt(n * (n + 1) / 12) / n)
    assert f["eda_p10"] == pytest.approx(60 + 0.1 * (n - 1) / n)
    assert f["eda_p90"] == pytest.approx(60 + 0.9 * (n - 1) / n)


def test_values_before_left_boundary_do_not_enter_window():
    t = np.arange(-1, 1440)
    v = np.full(len(t), 72.0)
    v[0] = 1e9
    assert eda_window_features(t, v, 1440)["eda_mean"] == 72


def test_observed_zero_is_valid_not_a_missing_window():
    result = eda_window_features(np.arange(1440), np.zeros(1440), 1440)
    assert result == {name: 0.0 for name in EDA_FEATURES}
