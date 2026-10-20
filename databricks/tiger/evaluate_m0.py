"""Offline synthetic instrument check; never evidence of real model accuracy."""

import argparse
import json
from pathlib import Path

import numpy as np
from rolling_risk import FEATURES, window_features
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler


def evaluate(min_accuracy=0.70, min_gain=0.10, signal=True):
    """Exercise production features with participant-disjoint, generated traces."""
    rng = np.random.default_rng(42)
    rows, labels, groups = [], [], []
    times = np.arange(1440)
    for person in range(20):
        label = person % 2
        # Counterfactual removes all label information while retaining valid data.
        offset = 1.5 * label if signal else 0.0
        for _ in range(2):
            motion = np.abs(rng.normal(0.05, 0.01, len(times)))
            temperature = 32 + offset + rng.normal(0, 0.15, len(times))
            values = window_features(times, motion, temperature, 1440)
            if values is None:
                raise ValueError("Generated complete trace failed coverage")
            rows.append([values[name] for name in FEATURES])
            labels.append(label)
            groups.append(person)
    X, y, groups = np.asarray(rows), np.asarray(labels), np.asarray(groups)
    predicted, prior = np.zeros(len(y)), np.zeros(len(y))
    for train, test in LeaveOneGroupOut().split(X, y, groups):
        if set(groups[train]) & set(groups[test]):
            raise ValueError("Participant leakage")
        model = make_pipeline(StandardScaler(), LogisticRegression(C=0.01, solver="liblinear", random_state=42))
        baseline = DummyClassifier(strategy="constant", constant=0)
        model.fit(X[train], y[train])
        baseline.fit(X[train], y[train])
        predicted[test] = model.predict(X[test])
        prior[test] = baseline.predict(X[test])

    # Average people, not overlapping windows. Equal row counts here are intentional.
    def accuracy(pred):
        return float(
            np.mean(
                [
                    np.mean(pred[groups == p] == y[groups == p])
                    for p in np.unique(groups)
                ]
            )
        )

    score, baseline_score = accuracy(predicted), accuracy(prior)
    return {
        "data_kind": "synthetic_instrument_check",
        "real_world_accuracy_claim": False,
        "participants": 20,
        "windows": len(y),
        "accuracy": score,
        "baseline_accuracy": baseline_score,
        "min_accuracy": min_accuracy,
        "min_gain": min_gain,
        "passed": bool(score >= min_accuracy and score - baseline_score >= min_gain),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--min-accuracy", type=float, default=0.70)
    parser.add_argument("--min-gain", type=float, default=0.10)
    parser.add_argument("--no-signal", action="store_true")
    args = parser.parse_args()
    for value in (args.min_accuracy, args.min_gain):
        if not np.isfinite(value) or not 0 <= value <= 1:
            parser.error("Thresholds must be finite values in [0, 1]")
    report = evaluate(args.min_accuracy, args.min_gain, not args.no_signal)
    text = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n")
    print(text)
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
