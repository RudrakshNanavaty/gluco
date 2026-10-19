"""Past-only summaries of EDA minute means, preserving source units."""

import numpy as np

EDA_FEATURES = ("eda_mean", "eda_std", "eda_p10", "eda_p90")


def eda_window_features(times, values, end):
    times, values = np.asarray(times), np.asarray(values, dtype=float)
    if times.ndim != 1 or values.ndim != 1 or len(times) != len(values):
        raise ValueError("Expected equal one-dimensional minute arrays")
    if not np.isfinite(times).all() or (np.diff(times) <= 0).any():
        raise ValueError("Minute coordinates must be finite, unique and increasing")
    if (times != np.floor(times)).any():
        raise ValueError("Expected integer minute coordinates")
    left, right = np.searchsorted(times, [end - 1440, end])
    t, eda = times[left:right], values[left:right]
    if len(t) < 1152 or not np.isfinite(eda).all() or (eda < 0).any():
        return None
    hours = ((t - (end - 1440)) // 60).astype(int)
    if (np.bincount(hours, minlength=24) < 30).any():
        return None
    return dict(
        zip(
            EDA_FEATURES,
            map(
                float,
                (
                    np.mean(eda),
                    np.std(eda, ddof=1),
                    np.quantile(eda, 0.1),
                    np.quantile(eda, 0.9),
                ),
            ),
        )
    )
