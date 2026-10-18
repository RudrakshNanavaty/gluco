"""Fixed feature subsets for the predeclared sensor-group development study."""

from rolling_risk import FEATURES

MOVEMENT = (
    "motion_mean_g",
    "motion_p90_g",
    "motion_median_g",
    "motion_std_g",
    "motion_p99_g",
    "motion_daily_amplitude_g",
)
TEMPERATURE = (
    "temperature_mean_c",
    "temperature_std_c",
    "temperature_p10_c",
    "temperature_p90_c",
    "temperature_daily_amplitude_c",
)
FEATURE_GROUPS = {
    "movement": MOVEMENT,
    "temperature": TEMPERATURE,
    "combined": tuple(FEATURES),
}


def feature_indices(group, columns):
    """Resolve explicit columns without adding IDs, targets or cross-group terms."""
    if group not in FEATURE_GROUPS:
        raise ValueError("Unknown feature group")
    columns = tuple(columns)
    if len(set(columns)) != len(columns):
        raise ValueError("Duplicate feature columns")
    if not set(FEATURE_GROUPS[group]).issubset(columns):
        raise ValueError("Missing required feature columns")
    return [columns.index(name) for name in FEATURE_GROUPS[group]]
