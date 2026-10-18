"""Research-pipeline contracts; no cloud credentials or model artifacts required."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tiger"))
from rolling_risk import (
    FEATURES,
    FEATURE_VERSION,
    arrays,
    score_records,
    window_features,
)


def test_window_is_past_only_and_excludes_end():
    times = np.arange(-1, 1442)
    motion = np.full(len(times), 2.0)
    temperature = np.full(len(times), 32.0)
    motion[(times < 0) | (times >= 1440)] = 1e9
    result = window_features(times, motion, temperature, 1440)
    assert result["motion_mean_g"] == 2.0
    assert result["temperature_mean_c"] == 32.0
    assert result["motion_temperature_corr"] == 0.0
    assert all(np.isfinite(list(result.values())))


def test_known_daily_cycle_and_feature_order():
    times = np.arange(1440)
    cycle = np.cos(2 * np.pi * (times // 60) / 24)
    result = window_features(times, 3 + 2 * cycle, 32 + cycle, 1440)
    assert list(result) == FEATURES
    assert result["motion_daily_amplitude_g"] == pytest.approx(2)
    assert result["temperature_daily_amplitude_c"] == pytest.approx(1)
    assert result["motion_temperature_corr"] == pytest.approx(1)


def test_coverage_threshold_is_inclusive():
    # Exactly 48 observations in each hour: 1,152 minutes, or 80%.
    times = np.concatenate([np.arange(h * 60, h * 60 + 48) for h in range(24)])
    assert window_features(times, np.ones(1152), np.ones(1152), 1440) is not None
    assert window_features(times[:-1], np.ones(1151), np.ones(1151), 1440) is None


def test_hourly_gap_fails_even_with_enough_total_minutes():
    times = np.arange(1440)
    times = times[times >= 31]  # First hour has only 29 observations.
    assert (
        window_features(times, np.ones(len(times)), np.ones(len(times)), 1440) is None
    )


@pytest.mark.parametrize("invalid", [np.nan, np.inf, -np.inf])
@pytest.mark.parametrize("signal", ["motion", "temperature"])
def test_nonfinite_input_rejects_window(invalid, signal):
    motion, temperature = np.ones(1440), np.ones(1440)
    (motion if signal == "motion" else temperature)[100] = invalid
    assert window_features(np.arange(1440), motion, temperature, 1440) is None


def test_arrays_sort_and_reject_duplicate_minutes():
    frame = pd.DataFrame(
        {
            "minute": [2, 0, 1],
            "enmo_mean_g": [20, 0, 10],
            "temperature_mean_c": [32, 30, 31],
        }
    )
    times, motion, temperature = arrays(frame, "minute")
    np.testing.assert_array_equal(times, [0, 1, 2])
    np.testing.assert_array_equal(motion, [0, 10, 20])
    np.testing.assert_array_equal(temperature, [30, 31, 32])
    with pytest.raises(ValueError, match="unique"):
        arrays(pd.concat([frame, frame.iloc[:1]]), "minute")


class FixedModel:
    # Reverse class order to catch incorrectly assuming column 1 means class 1.
    classes_ = np.array([1, 0])

    def __init__(self, score):
        self.score = score

    def predict_proba(self, vector):
        assert vector.shape == (1, len(FEATURES))
        return np.array([[self.score, 1 - self.score]])


def scoring_inputs():
    minutes = pd.DataFrame(
        {
            "source_participant_key": ["big_ideas:001"] * 2880,
            "minute_offset": np.arange(2880),
            "enmo_mean_g": np.ones(2880),
            "temperature_mean_c": np.full(2880, 32.0),
        }
    )

    def item(score):
        return {
            "model": FixedModel(score),
            "name": "fixed",
            "minimum": np.full(len(FEATURES), -100),
            "maximum": np.full(len(FEATURES), 100),
        }

    bundle = {
        "feature_version": FEATURE_VERSION,
        "features": FEATURES.copy(),
        "model_version": "test-release",
        "held_out": {"big_ideas:001": item(0.2)},
        "final": item(0.8),
    }
    records = [
        {
            "source_participant_key": "big_ideas:001",
            "participant_key": "demo:big_ideas:001",
            "window_end_offset_minutes": end,
        }
        for end in [1440, 2880]
    ]
    return records, minutes, bundle


def test_held_out_model_and_24h_delta():
    records, minutes, bundle = scoring_inputs()
    result = score_records(records, minutes, bundle)
    assert [r["wearable_risk_indicator"] for r in result] == [20, 20]
    assert [r["risk_change_24h_points"] for r in result] == [None, 0]
    assert result[0]["risk_evaluation"] == "held_out_participant_demo"
    assert result[0]["risk_model_version"] == "test-release"


def test_unknown_participant_uses_unvalidated_final_model():
    records, minutes, bundle = scoring_inputs()
    bundle["held_out"] = {}
    result = score_records(records[:1], minutes, bundle)[0]
    assert result["wearable_risk_indicator"] == 80
    assert result["risk_evaluation"] == "application_unvalidated"
    assert result["risk_cross_device_validated"] is False


@pytest.mark.parametrize(
    "field,value",
    [("feature_version", "other"), ("features", list(reversed(FEATURES)))],
)
def test_model_contract_mismatch_fails_before_scoring(field, value):
    records, minutes, bundle = scoring_inputs()
    bundle[field] = value
    with pytest.raises(ValueError, match="contract mismatch"):
        score_records(records, minutes, bundle)


@pytest.mark.parametrize("score", [np.nan, -0.1, 1.1])
def test_invalid_model_scores_are_rejected(score):
    records, minutes, bundle = scoring_inputs()
    bundle["held_out"]["big_ideas:001"]["model"] = FixedModel(score)
    with pytest.raises(ValueError, match="Invalid risk score"):
        score_records(records, minutes, bundle)
