"""Predeclared training-only operating-point selection for development."""

import numpy as np

THRESHOLDS = (0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65)


def participant_weights(groups):
    groups = np.asarray(groups)
    _, inverse, counts = np.unique(groups, return_inverse=True, return_counts=True)
    return len(groups) / (len(counts) * counts[inverse])


def select_threshold(target, probability, groups):
    """Use inner out-of-fold predictions only; deterministic ties prefer 0.5."""
    target, probability, groups = map(np.asarray, (target, probability, groups))
    if not (target.ndim == probability.ndim == groups.ndim == 1):
        raise ValueError("Expected one-dimensional inputs")
    if len(target) == 0 or not (len(target) == len(probability) == len(groups)):
        raise ValueError("Expected equal nonempty inputs")
    if set(np.unique(target)) != {0, 1}:
        raise ValueError("Both binary classes required")
    if (
        not np.isfinite(probability).all()
        or ((probability < 0) | (probability > 1)).any()
    ):
        raise ValueError("Probabilities must be finite and in [0, 1]")
    w = participant_weights(groups)

    def rank(threshold):
        correct = (probability >= threshold) == target
        accuracy = np.average(correct, weights=w)
        balanced = np.mean(
            [np.average(correct[target == c], weights=w[target == c]) for c in (0, 1)]
        )
        return (
            -round(float(accuracy), 6),
            -round(float(balanced), 6),
            round(abs(threshold - 0.5), 6),
            threshold,
        )

    return min(THRESHOLDS, key=rank)
