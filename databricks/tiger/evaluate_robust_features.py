# Databricks notebook source
"""Development-only nested comparison. Never publishes a model or dashboard."""

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
from rolling_risk import FEATURES, arrays
from experimental_features import (
    EXPERIMENT_FEATURES,
    EXPERIMENT_FEATURE_VERSION,
    experimental_window_features,
)

spark.conf.set("spark.sql.session.timeZone", "UTC")
expected = {f"big_ideas:{i:03d}" for i in range(1, 17)} - {"big_ideas:015"}
source = (
    spark.table("workspace.gluco_silver.shared_sensor_minute_pilot")
    .where(F.col("participant_key").isin(sorted(expected)))
    .where(
        F.col("acc_sample_ratio").between(0.8, 1)
        & F.col("temperature_sample_ratio").between(0.8, 1)
    )
    .select("participant_key", "minute_ts", "enmo_mean_g", "temperature_mean_c")
    .limit(500001)
    .toPandas()
)
if len(source) > 500000 or set(source.participant_key) != expected:
    raise ValueError("Unexpected source roster or size")
source["minute_index"] = (
    pd.to_datetime(source.minute_ts).astype("datetime64[ns]").astype("int64")
    // 60_000_000_000
)
saved = (
    spark.table("workspace.gluco_features.rolling_risk_training_windows")
    .where(F.col("model_version") == reference)
    .limit(5001)
    .toPandas()
)
if len(saved) != 660 or set(saved.participant_key) != expected:
    raise ValueError("Reference does not match predeclared 660-window cohort")
keys = ["participant_key", "window_end_minute"]
if saved.duplicated(keys).any():
    raise ValueError("Duplicate reference window keys")
labels = saved.groupby("participant_key").cohort_label
if (labels.nunique() != 1).any():
    raise ValueError("Inconsistent labels")
label_map = labels.first().to_dict()
rows = []
for key, part in source.groupby("participant_key"):
    t, a, c = arrays(part, "minute_index")
    first_end = int(((t[0] + 1440 + 59) // 60) * 60)
    for end in range(first_end, int(t[-1] + 1) + 1, 60):
        features = experimental_window_features(t, a, c, end)
        if features is not None:
            rows.append(
                {
                    "participant_key": key,
                    "window_end_minute": end,
                    "cohort_label": int(label_map[key]),
                    **features,
                }
            )
data = pd.DataFrame(rows).sort_values(keys).reset_index(drop=True)
saved = saved.sort_values(keys).reset_index(drop=True)
if not data[keys].equals(saved[keys]):
    raise ValueError("Accepted window keys differ from reference")
np.testing.assert_allclose(data[FEATURES], saved[FEATURES], rtol=1e-10, atol=1e-10)
if not np.array_equal(data.cohort_label, saved.cohort_label):
    raise ValueError("Labels differ from reference")
X = data[EXPERIMENT_FEATURES].to_numpy(float)
y = data.cohort_label.to_numpy(int)
groups = data.participant_key.to_numpy()
if not np.isfinite(X).all():
    raise ValueError("Nonfinite experiment feature")

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
candidates = [(family, name) for family in ["baseline", "extended"] for name in models]


def weights(g):
    counts = pd.Series(g).value_counts()
    return np.array([len(g) / (len(counts) * counts[key]) for key in g])


def matrix(family, idx):
    return X[idx, : len(FEATURES)] if family == "baseline" else X[idx]


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
    for candidate in candidates:
        pred = np.full(len(idx), np.nan)
        for train_people, valid_people in splits:
            train = idx[np.isin(groups[idx], people[train_people])]
            valid_mask = np.isin(groups[idx], people[valid_people])
            pred[valid_mask] = fit_predict(candidate, train, idx[valid_mask])
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
    return scores


def metrics(target, pred, w):
    return {
        "accuracy": float(accuracy_score(target, pred >= 0.5, sample_weight=w)),
        "balanced_accuracy": float(
            balanced_accuracy_score(target, pred >= 0.5, sample_weight=w)
        ),
        "roc_auc": float(roc_auc_score(target, pred, sample_weight=w)),
        "log_loss": float(log_loss(target, pred, sample_weight=w, labels=[0, 1])),
        "brier": float(brier_score_loss(target, pred, sample_weight=w)),
    }


mlflow.set_tracking_uri("databricks")
mlflow.set_experiment(experiment)
with mlflow.start_run(run_name="robust-v1-nested-participant-comparison") as run:
    predictions = {
        name: np.full(len(y), np.nan)
        for name in ["baseline", "extended", "joint_selection", "prior"]
    }
    folds = []
    for train, valid in LeaveOneGroupOut().split(X, y, groups):
        scores = inner_scores(train)
        chosen = {}
        for mode in ["baseline", "extended", "joint_selection"]:
            eligible = [
                c for c in candidates if mode == "joint_selection" or c[0] == mode
            ]
            selected = min(eligible, key=lambda c: scores[c])
            predictions[mode][valid] = fit_predict(selected, train, valid)
            chosen[mode] = list(selected)
        predictions["prior"][valid] = fit_predict(("baseline", "prior"), train, valid)
        key = groups[valid[0]]
        folds.append(
            {
                "participant": key,
                "windows": len(valid),
                "selected": chosen,
                "metrics": {
                    name: {
                        "accuracy": float(np.mean((p[valid] >= 0.5) == y[valid])),
                        "brier": float(np.mean((p[valid] - y[valid]) ** 2)),
                    }
                    for name, p in predictions.items()
                },
            }
        )
        print("Completed held-out fold", len(folds), "of", len(expected), flush=True)
    # Baseline agreement is mandatory, not an optional performance comparison.
    np.testing.assert_allclose(
        predictions["baseline"] * 100, saved.held_out_score, atol=1e-8, rtol=0
    )
    np.testing.assert_allclose(
        predictions["prior"] * 100, saved.baseline_score, atol=1e-8, rtol=0
    )
    report = {
        "reference_release": reference,
        "feature_version": EXPERIMENT_FEATURE_VERSION,
        "features": EXPERIMENT_FEATURES,
        "windows": len(data),
        "participants": len(expected),
        "baseline_reproduced": True,
        "window_keys_match": True,
        "metrics": {
            name: metrics(y, p, weights(groups)) for name, p in predictions.items()
        },
        "folds": folds,
        "promoted": False,
        "limitations": [
            "Reused development cohort; not external validation",
            "15 independent people, not 660 independent samples",
            "Extended and joint searches are larger than baseline search",
            "Coverage policy unchanged; no imputation or synthetic training",
        ],
    }
    mlflow.log_params(
        {
            "reference_release": reference,
            "feature_version": EXPERIMENT_FEATURE_VERSION,
            "windows": len(data),
            "participants": len(expected),
            "promoted": False,
        }
    )
    mlflow.log_metrics(
        {
            f"{name}.{metric}": value
            for name, result in report["metrics"].items()
            for metric, value in result.items()
        }
    )
    mlflow.log_dict(report, "comparison.json")
    report["experiment_run_id"] = run.info.run_id
# No model artifacts, release-table writes, or dashboard publication.
dbutils.notebook.exit(json.dumps(report))
