# Databricks notebook source
"""Development-only predeclared EDA information comparison."""

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
from sklearn.impute import SimpleImputer
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
from eda_features import EDA_FEATURES, eda_window_features
from rolling_risk import FEATURES

TEMPERATURE = (
    "temperature_mean_c",
    "temperature_std_c",
    "temperature_p10_c",
    "temperature_p90_c",
    "temperature_daily_amplitude_c",
)
FEATURE_GROUPS = {
    "temperature": TEMPERATURE,
    "eda": EDA_FEATURES,
    "temperature_eda": TEMPERATURE + EDA_FEATURES,
}
ALL_FEATURES = list(FEATURES) + list(EDA_FEATURES)

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
# Read staged EDA only; no Bronze/Silver writes or label-based filtering.
paths = [
    f"/Volumes/workspace/gluco_raw/source_files/big_ideas/{key.split(':')[1]}/EDA_{key.split(':')[1]}.csv"
    for key in sorted(expected)
]
raw = (
    spark.read.option("header", True)
    .option("mode", "FAILFAST")
    .schema("datetime_raw STRING, eda_raw STRING")
    .csv(paths)
    .select("*", F.col("_metadata.file_path").alias("source_file"))
)
raw = (
    raw.withColumn(
        "participant_key",
        F.concat(
            F.lit("big_ideas:"),
            F.regexp_extract("source_file", r"/([0-9]{3})/[^/]+$", 1),
        ),
    )
    .withColumn(
        "event_ts",
        F.expr(
            "coalesce(try_cast(datetime_raw AS TIMESTAMP_NTZ),cast(try_to_timestamp(datetime_raw,'M/d/yy H:mm') AS TIMESTAMP_NTZ))"
        ),
    )
    .withColumn(
        "coarse_clock",
        F.col("datetime_raw").rlike(
            r"^[0-9]{1,2}/[0-9]{1,2}/[0-9]{2} [0-9]{1,2}:[0-9]{2}$"
        ),
    )
    .withColumn("eda", F.expr("try_cast(eda_raw AS DOUBLE)"))
)
valid = (F.col("eda") >= 0) & ~F.isnan("eda") & (F.abs("eda") < F.lit(float("inf")))
# Aggregate once in Spark; retain only bounded minute summaries in driver memory.
# No DataFrame cache API is required (compatible with serverless compute).
summary = (
    raw.withColumn("minute_ts", F.date_trunc("minute", "event_ts"))
    .groupBy("participant_key", "minute_ts")
    .agg(
        F.count("*").alias("rows"),
        F.countDistinct("event_ts").alias("unique_times"),
        F.min(F.when(F.col("coarse_clock"), 1).otherwise(0)).alias("coarse_only"),
        F.count(F.when(valid, 1)).alias("valid_samples"),
        F.avg(F.when(valid, F.col("eda"))).alias("eda_mean"),
    )
    .withColumn(
        "minute_index",
        F.expr("timestampdiff(MINUTE,TIMESTAMP_NTZ '1970-01-01 00:00:00',minute_ts)"),
    )
    .drop("minute_ts")
    .limit(300001)
    .toPandas()
)
if len(summary) > 300000 or summary.minute_index.isna().any():
    raise ValueError("EDA minute volume or timestamp parse check failed")
clock_resolution = {
    str(key): int((part.coarse_only == 1).sum())
    for key, part in summary.groupby("participant_key")
}
mask = (
    summary.valid_samples.between(192, 240)
    & (summary.rows == summary.valid_samples)
    & ((summary.coarse_only == 1) | (summary.rows == summary.unique_times))
)
eda_minutes = summary.loc[mask, ["participant_key", "minute_index", "eda_mean"]].copy()
if set(eda_minutes.participant_key) != expected:
    raise ValueError("Unexpected usable EDA roster")
minute_arrays = {
    key: (
        part.sort_values("minute_index").minute_index.to_numpy(),
        part.sort_values("minute_index").eda_mean.to_numpy(),
    )
    for key, part in eda_minutes.groupby("participant_key")
}
extra = []
coverage = {}
for row in saved.itertuples():
    f = eda_window_features(
        *minute_arrays[row.participant_key], int(row.window_end_minute)
    )
    extra.append(f if f is not None else {name: np.nan for name in EDA_FEATURES})
    counts = coverage.setdefault(
        row.participant_key, {"windows": 0, "eda_available": 0}
    )
    counts["windows"] += 1
    counts["eda_available"] += int(f is not None)
data = saved.copy()
for name in EDA_FEATURES:
    data[name] = [f[name] for f in extra]
X = data[ALL_FEATURES].to_numpy(float)
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
candidates = [(family, name) for family in FEATURE_GROUPS for name in models]


def weights(g):
    counts = pd.Series(g).value_counts()
    return np.array([len(g) / (len(counts) * counts[key]) for key in g])


def matrix(family, idx):
    return X[idx][:, [ALL_FEATURES.index(name) for name in FEATURE_GROUPS[family]]]


def fit_predict(candidate, train, valid):
    family, name = candidate
    assert set(groups[train]).isdisjoint(groups[valid])
    model = clone(models[name])
    w = weights(groups[train])
    if name == "prior":
        model.fit(np.zeros((len(train), 1)), y[train], sample_weight=w)
        probability = model.predict_proba(np.zeros((len(valid), 1)))
    else:
        train_matrix = matrix(family, train)
        if np.isnan(train_matrix).all(axis=0).any():
            raise ValueError("An EDA summary has no observed training-fold values")
        if isinstance(model, Pipeline):
            model = Pipeline(
                [("impute", SimpleImputer(strategy="median")), *model.steps]
            )
            kwargs = {"scale__sample_weight": w, "model__sample_weight": w}
        else:
            model = Pipeline(
                [("impute", SimpleImputer(strategy="median")), ("model", model)]
            )
            kwargs = {"model__sample_weight": w}
        model.fit(train_matrix, y[train], **kwargs)
        probability = model.predict_proba(matrix(family, valid))
    return np.round(probability[:, list(model.classes_).index(1)], 12)


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
reference_run = "14db0b9a30fd4199b655b5a136d470f8"
path = mlflow.artifacts.download_artifacts(
    run_id=reference_run, artifact_path="comparison.json"
)
with open(path) as handle:
    previous = json.load(handle)
if previous["reference_release"] != reference or previous["features"][
    "temperature"
] != list(TEMPERATURE):
    raise ValueError("Reference contract differs")
with mlflow.start_run(run_name="eda-v1-nested-participant-comparison") as run:
    modes = (
        "temperature",
        "eda",
        "temperature_eda",
        "primary_selection",
        "prior",
    )
    predictions = {mode: np.full(len(y), np.nan) for mode in modes}
    folds = []
    for train, valid in LeaveOneGroupOut().split(X, y, groups):
        scores, _ = inner_scores(train)
        chosen = {
            family: min(
                [c for c in candidates if c[0] == family], key=lambda c: scores[c]
            )
            for family in FEATURE_GROUPS
        }
        chosen["primary_selection"] = min(
            [c for c in candidates if c[0] in ("temperature", "temperature_eda")],
            key=lambda c: scores[c],
        )
        chosen["prior"] = ("temperature", "prior")
        for mode, c in chosen.items():
            predictions[mode][valid] = fit_predict(c, train, valid)
        folds.append(
            {
                "participant": str(groups[valid[0]]),
                "label": int(y[valid[0]]),
                "windows": len(valid),
                "selected": {mode: list(c) for mode, c in chosen.items()},
                "accuracy": {
                    mode: float(np.mean((p[valid] >= 0.5) == y[valid]))
                    for mode, p in predictions.items()
                },
            }
        )
        print("Completed held-out participant", len(folds), "of 15", flush=True)
    results = {mode: metrics(y, p, weights(groups)) for mode, p in predictions.items()}
    for key, value in previous["metrics"]["temperature"].items():
        np.testing.assert_allclose(
            results["temperature"][key], value, atol=1e-10, rtol=0
        )
    reference_folds = {f["participant"]: f for f in previous["folds"]}
    for f in folds:
        old = reference_folds[f["participant"]]
        assert (
            f["windows"] == old["windows"]
            and f["selected"]["temperature"][1] == old["selected"]["temperature"][1]
        )
        np.testing.assert_allclose(
            f["accuracy"]["temperature"],
            old["accuracy"]["temperature"],
            atol=1e-12,
            rtol=0,
        )
    np.testing.assert_allclose(
        predictions["prior"] * 100, saved.baseline_score, atol=1e-8, rtol=0
    )
    report = {
        "reference_release": reference,
        "reference_experiment": reference_run,
        "features": FEATURE_GROUPS,
        "windows": 660,
        "participants": 15,
        "control_reproduced": True,
        "eda_coverage": coverage,
        "source_coarse_minutes": clock_resolution,
        "eda_minute_rows": len(eda_minutes),
        "promoted": False,
        "primary_procedure": "primary_selection",
        "metrics": results,
        "folds": folds,
        "limitations": [
            "Reused cohort, not independent validation",
            "EDA summaries preserve source units; no clinical interpretation",
            "No feature-group selection against outer outcomes",
            "Missing EDA imputed only inside training folds without indicators",
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
            for mode, result in results.items()
            for metric, value in result.items()
        }
    )
    mlflow.log_dict(report, "comparison.json")
    mlflow.log_dict(
        {
            "rows": [
                {
                    "participant": str(groups[i]),
                    "window_end_minute": int(saved.window_end_minute.iloc[i]),
                    "label": int(y[i]),
                    **{mode: float(p[i]) for mode, p in predictions.items()},
                }
                for i in range(len(y))
            ]
        },
        "held_out_predictions.json",
    )
    report["experiment_run_id"] = run.info.run_id
dbutils.notebook.exit(json.dumps(report))
