"""Unpublished feature extension; never used by the current dashboard release."""

import numpy as np

from rolling_risk import FEATURES, window_features

EXPERIMENT_FEATURE_VERSION = "wearable-24h-robust-v1"
EXTRA_FEATURES = [
    "motion_iqr_g",
    "temperature_iqr_c",
    "motion_slope_g_per_hour",
    "temperature_slope_c_per_hour",
]
EXPERIMENT_FEATURES = [*FEATURES, *EXTRA_FEATURES]


def experimental_window_features(times, motion, temperature, end):
    """Keep baseline eligibility and use elapsed time, without imputing gaps."""
    baseline = window_features(times, motion, temperature, end)
    if baseline is None:
        return None
    left, right = np.searchsorted(times, [end - 1440, end])
    t = (times[left:right] - (end - 1440)) / 60.0
    a, c = motion[left:right], temperature[left:right]
    centered = t - t.mean()
    denominator = centered @ centered

    def slope(values):
        return float(centered @ (values - values.mean()) / denominator)

    extra = [
        float(np.quantile(a, 0.75) - np.quantile(a, 0.25)),
        float(np.quantile(c, 0.75) - np.quantile(c, 0.25)),
        slope(a),
        slope(c),
    ]
    return {**baseline, **dict(zip(EXTRA_FEATURES, extra))}
