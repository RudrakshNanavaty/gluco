"""Synthetic snapshot semantics, with no database calls."""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tiger"))
from fast_sensor import sensor_payload, run


def test_sensor_interpolation_and_provenance():
    previous = {"enmo_mean_g": 0.1, "temperature_mean_c": 30, "hr_mean_bpm": 60}
    current = {"enmo_mean_g": 0.3, "temperature_mean_c": 32, "hr_mean_bpm": 80}
    result = sensor_payload(
        previous, current, 0.5, datetime(2026, 1, 1, tzinfo=timezone.utc)
    )
    assert result["latest_motion_g"] == pytest.approx(0.2)
    assert result["latest_skin_temperature_c"] == 31
    assert result["latest_hr_bpm"] == 70
    assert result["latest_sensor_is_synthetic"] is True
    assert result["latest_sensor_source_resolution_seconds"] == 60
    assert result["latest_sensor_update_interval_seconds"] == 1


def test_missing_hr_stays_missing():
    row = {"enmo_mean_g": 0.1, "temperature_mean_c": 32, "hr_mean_bpm": None}
    assert (
        sensor_payload(row, row, 0.5, datetime.now(timezone.utc))["latest_hr_bpm"]
        is None
    )


def test_zero_tick_limit_fails_before_any_io():
    with pytest.raises(ValueError, match="positive"):
        run(max_ticks=0)
