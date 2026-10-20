"""Past-only summaries of minute heart-rate means, not beat-to-beat HRV."""

import numpy as np

HR_FEATURES = ("hr_mean_bpm", "hr_std_bpm", "hr_p10_bpm", "hr_p90_bpm")


def heart_rate_features(times, values, end):
    times, values = np.asarray(times), np.asarray(values, dtype=float)
    if times.ndim != 1 or values.ndim != 1 or len(times) != len(values):
        raise ValueError("Expected equal one-dimensional minute arrays")
    if not np.isfinite(times).all() or (np.diff(times) <= 0).any():
        raise ValueError("Minute coordinates must be finite, unique and increasing")
    if (times != np.floor(times)).any():
        raise ValueError("Expected integer minute coordinates")
    left, right = np.searchsorted(times, [end - 1440, end])
    t, hr = times[left:right], values[left:right]
    if len(t) < 1152 or not np.isfinite(hr).all() or (hr <= 0).any():
        return None
    hours = ((t - (end - 1440)) // 60).astype(int)
    if (np.bincount(hours, minlength=24) < 30).any():
        return None
    return dict(
        zip(
            HR_FEATURES,
            map(
                float,
                (
                    np.mean(hr),
                    np.std(hr, ddof=1),
                    np.quantile(hr, 0.1),
                    np.quantile(hr, 0.9),
                ),
            ),
        )
    )
