"""Analytical checks for an unpublished feature family."""

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tiger"))
from experimental_features import EXPERIMENT_FEATURES, experimental_window_features
from rolling_risk import FEATURES, window_features


def test_extension_preserves_baseline_features_exactly():
    t = np.arange(1440)
    a, c = 2 + np.sin(t / 200), 32 + np.cos(t / 100)
    result = experimental_window_features(t, a, c, 1440)
    assert list(result) == EXPERIMENT_FEATURES
    assert {k: result[k] for k in FEATURES} == window_features(t, a, c, 1440)


def test_slopes_use_elapsed_hours_across_irregular_gaps():
    t = np.arange(1440)
    t = t[t % 5 != 0]  # Exactly 80% coverage, regularly missing actual minutes.
    result = experimental_window_features(t, 2 + 0.1 * t / 60, 30 + 0.2 * t / 60, 1440)
    assert result["motion_slope_g_per_hour"] == pytest.approx(0.1)
    assert result["temperature_slope_c_per_hour"] == pytest.approx(0.2)


def test_constant_signals_have_zero_iqr_and_slope():
    result = experimental_window_features(
        np.arange(1440), np.ones(1440), np.full(1440, 32), 1440
    )
    assert result["motion_iqr_g"] == 0
    assert result["temperature_iqr_c"] == 0
    assert result["motion_slope_g_per_hour"] == 0
    assert result["temperature_slope_c_per_hour"] == 0


def test_extra_features_exclude_values_at_and_after_window_end():
    t = np.arange(1442)
    a, c = np.ones(len(t)), np.full(len(t), 32.0)
    a[t >= 1440] = 1e9
    c[t >= 1440] = -1e9
    result = experimental_window_features(t, a, c, 1440)
    assert result["motion_iqr_g"] == 0
    assert result["temperature_slope_c_per_hour"] == 0


def test_extension_keeps_original_rejection_gate():
    t = np.arange(31, 1440)
    assert (
        experimental_window_features(t, np.ones(len(t)), np.ones(len(t)), 1440) is None
    )


def test_slopes_are_invariant_to_absolute_time_offset():
    t = np.arange(1440)
    a, c = t / 60, 30 + t / 120
    result = experimental_window_features(t, a, c, 1440)
    shifted = experimental_window_features(t + 30000000, a, c, 30001440)
    assert result == shifted
