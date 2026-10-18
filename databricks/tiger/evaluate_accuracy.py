# Databricks notebook source
"""Development-only regularization and training-only threshold comparison."""

# COMMAND ----------
# MAGIC %pip install "scikit-learn==1.5.2" "mlflow-skinny>=2.22,<3"
# COMMAND ----------
dbutils.library.restartPython()
# COMMAND ----------
import json
import sys

import mlflow
import numpy as np
import pandas as pd
from pyspark.sql import functions as F
from sklearn.base import clone
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    brier_score_loss,
    log_loss,
    roc_auc_score,
)
from sklearn.model_selection import LeaveOneGroupOut, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

# Upload to a separate development folder; never replace production notebooks.
dbutils.widgets.text("project_root", "")
dbutils.widgets.text("experiment_path", "")
dbutils.widgets.text("reference_release", "38ec33cb326146c7991650a3164cf440")
root = dbutils.widgets.get("project_root")
experiment = dbutils.widgets.get("experiment_path")
reference = dbutils.widgets.get("reference_release")
if not root or not experiment:
    raise ValueError("Explicit development project_root and experiment_path required")
sys.path.insert(0, root)
from accuracy_selection import select_threshold
from rolling_risk import FEATURES

spark.conf.set("spark.sql.session.timeZone", "UTC")
expected = {f"big_ideas:{i:03d}" for i in range(1, 17)} - {"big_ideas:015"}
saved = (
    spark.table("workspace.gluco_features.rolling_risk_training_windows")
    .where(F.col("model_version") == reference)
    .limit(5001)
    .toPandas()
)
keys = ["participant_key", "window_end_minute"]
if (
    len(saved) != 660
    or set(saved.participant_key) != expected
    or saved.duplicated(keys).any()
):
    raise ValueError("Unexpected reference cohort or duplicate windows")
saved = saved.sort_values(keys).reset_index(drop=True)
labels = saved.groupby("participant_key").cohort_label
if (labels.nunique() != 1).any():
    raise ValueError("Inconsistent participant labels")
label_map = labels.first().to_dict()
X = saved[FEATURES].to_numpy(float)
y = saved.cohort_label.to_numpy(int)
groups = saved.participant_key.to_numpy()
if not np.isfinite(X).all() or set(y) != {0, 1}:
    raise ValueError("Invalid reference features/labels")
models = {
    "prior": DummyClassifier(strategy="prior"),
    "logistic_c01": Pipeline(
        [
            ("scale", StandardScaler()),
            ("model", LogisticRegression(C=0.1, max_iter=2000, random_state=42)),
        ]
    ),
    "logistic_c1": Pipeline(
        [
            ("scale", StandardScaler()),
            ("model", LogisticRegression(C=1, max_iter=2000, random_state=42)),
        ]
    ),
    "forest_depth3": RandomForestClassifier(
        n_estimators=64, max_depth=3, min_samples_leaf=20, random_state=42, n_jobs=1
    ),
}
baseline_names = tuple(models)
for c in (0.001, 0.01):
    models[f"logistic_c{c}"] = Pipeline(
        [
            ("scale", StandardScaler()),
            ("model", LogisticRegression(C=c, max_iter=2000, random_state=42)),
        ]
    )
candidates = [("baseline", name) for name in models]


def weights(g):
    counts = pd.Series(g).value_counts()
    return np.array([len(g) / (len(counts) * counts[key]) for key in g])


def matrix(family, idx):
    return X[idx]


def fit_predict(candidate, train, valid):
    family, name = candidate
    assert set(groups[train]).isdisjoint(groups[valid])
    model = clone(models[name])
    w = weights(groups[train])
    if isinstance(model, Pipeline):
        model.fit(
            matrix(family, train),
            y[train],
            scale__sample_weight=w,
            model__sample_weight=w,
        )
    else:
        model.fit(matrix(family, train), y[train], sample_weight=w)
    return np.round(
        model.predict_proba(matrix(family, valid))[:, list(model.classes_).index(1)], 12
    )


def inner_scores(idx):
    people = np.unique(groups[idx])
    person_labels = np.array([label_map[k] for k in people])
    splits = list(
        StratifiedKFold(3, shuffle=True, random_state=42).split(people, person_labels)
    )
    scores = {}
    inner_predictions = {}
    for candidate in candidates:
        pred = np.full(len(idx), np.nan)
        for train_people, valid_people in splits:
            train = idx[np.isin(groups[idx], people[train_people])]
            valid_mask = np.isin(groups[idx], people[valid_people])
            pred[valid_mask] = fit_predict(candidate, train, idx[valid_mask])
        inner_predictions[candidate] = pred.copy()
        scores[candidate] = (
            -round(
                float(
                    balanced_accuracy_score(
                        y[idx], pred >= 0.5, sample_weight=weights(groups[idx])
                    )
                ),
                6,
            ),
            round(
                float(
                    log_loss(
                        y[idx], pred, sample_weight=weights(groups[idx]), labels=[0, 1]
                    )
                ),
                6,
            ),
        )
    return scores, inner_predictions


def metrics(target, pred, w, threshold=0.5):
    return {
        "accuracy": float(accuracy_score(target, pred >= threshold, sample_weight=w)),
        "balanced_accuracy": float(
            balanced_accuracy_score(target, pred >= threshold, sample_weight=w)
        ),
        "roc_auc": float(roc_auc_score(target, pred, sample_weight=w)),
        "log_loss": float(log_loss(target, pred, sample_weight=w, labels=[0, 1])),
        "brier": float(brier_score_loss(target, pred, sample_weight=w)),
    }


mlflow.set_tracking_uri("databricks")
mlflow.set_experiment(experiment)
with mlflow.start_run(run_name="accuracy-v2-regularization-threshold") as run:
    modes = ("baseline", "regularized", "threshold_tuned", "prior")
    predictions = {mode: np.full(len(y), np.nan) for mode in modes}
    thresholds = {mode: np.full(len(y), 0.5) for mode in modes}
    folds = []
    for train, valid in LeaveOneGroupOut().split(X, y, groups):
        scores, inner = inner_scores(train)
        base = min(
            [c for c in candidates if c[1] in baseline_names], key=lambda c: scores[c]
        )
        # A small predeclared search: two additional strongly regularized logits.
        regularized = min(candidates, key=lambda c: scores[c])
        tuned = {}
        for candidate in candidates:
            threshold = select_threshold(y[train], inner[candidate], groups[train])
            p, w = inner[candidate], weights(groups[train])
            tuned[candidate] = (
                (
                    -round(
                        float(
                            accuracy_score(y[train], p >= threshold, sample_weight=w)
                        ),
                        6,
                    ),
                    -round(
                        float(
                            balanced_accuracy_score(
                                y[train], p >= threshold, sample_weight=w
                            )
                        ),
                        6,
                    ),
                    round(
                        float(log_loss(y[train], p, sample_weight=w, labels=[0, 1])), 6
                    ),
                ),
                threshold,
            )
        selected = min(candidates, key=lambda c: tuned[c][0])
        chosen = {
            "baseline": base,
            "regularized": regularized,
            "threshold_tuned": selected,
            "prior": ("baseline", "prior"),
        }
        thresholds["threshold_tuned"][valid] = tuned[selected][1]
        for mode, candidate in chosen.items():
            predictions[mode][valid] = fit_predict(candidate, train, valid)
        folds.append(
            {
                "participant": str(groups[valid[0]]),
                "label": int(y[valid[0]]),
                "windows": len(valid),
                "selected": {k: list(v) for k, v in chosen.items()},
                "threshold": float(thresholds["threshold_tuned"][valid][0]),
                "accuracy": {
                    mode: float(
                        np.mean(
                            (predictions[mode][valid] >= thresholds[mode][valid])
                            == y[valid]
                        )
                    )
                    for mode in modes
                },
            }
        )
        print("Completed held-out participant", len(folds), "of 15", flush=True)
    np.testing.assert_allclose(
        predictions["baseline"] * 100, saved.held_out_score, atol=1e-8, rtol=0
    )
    np.testing.assert_allclose(
        predictions["prior"] * 100, saved.baseline_score, atol=1e-8, rtol=0
    )
    report = {
        "reference_release": reference,
        "features": FEATURES,
        "windows": len(saved),
        "participants": 15,
        "baseline_reproduced": True,
        "promoted": False,
        "metrics": {
            mode: metrics(y, p, weights(groups), thresholds[mode])
            for mode, p in predictions.items()
        },
        "folds": folds,
        "limitations": [
            "Reused development cohort; not external validation",
            "15 independent participants; overlapping windows",
            "Threshold tuning changes binary decisions, not probability calibration",
            "No synthetic inputs, new features, or relaxed coverage",
        ],
    }
    mlflow.log_params(
        {
            "reference_release": reference,
            "windows": 660,
            "participants": 15,
            "promoted": False,
        }
    )
    mlflow.log_metrics(
        {
            f"{mode}.{metric}": value
            for mode, result in report["metrics"].items()
            for metric, value in result.items()
        }
    )
    mlflow.log_dict(report, "comparison.json")
    report["experiment_run_id"] = run.info.run_id
dbutils.notebook.exit(json.dumps(report))
