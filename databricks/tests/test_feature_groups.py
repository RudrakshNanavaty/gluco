"""Keep single-sensor ablations free of other-sensor and target columns."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tiger"))
from feature_groups import FEATURE_GROUPS, feature_indices
from rolling_risk import FEATURES


def test_groups_partition_signal_features_and_only_combined_has_correlation():
    movement, temperature = map(
        set, (FEATURE_GROUPS["movement"], FEATURE_GROUPS["temperature"])
    )
    assert len(movement) == 6 and len(temperature) == 5
    assert movement.isdisjoint(temperature)
    assert movement | temperature == set(FEATURES) - {"motion_temperature_corr"}
    assert FEATURE_GROUPS["combined"] == tuple(FEATURES)


def test_explicit_column_mapping_survives_extra_target_or_identifier_columns():
    columns = ["cohort_label", *reversed(FEATURES), "participant_key"]
    for group in FEATURE_GROUPS:
        selected = [columns[i] for i in feature_indices(group, columns)]
        assert selected == list(FEATURE_GROUPS[group])
        assert "cohort_label" not in selected and "participant_key" not in selected


@pytest.mark.parametrize(
    "group,columns",
    [
        ("typo", FEATURES),
        ("movement", FEATURES[1:]),
        ("combined", FEATURES + [FEATURES[0]]),
    ],
)
def test_unknown_incomplete_or_duplicate_schema_fails(group, columns):
    with pytest.raises(ValueError):
        feature_indices(group, columns)
