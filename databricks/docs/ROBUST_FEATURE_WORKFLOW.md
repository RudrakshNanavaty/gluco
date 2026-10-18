# Development-only robust-feature comparison

## Local checks

Run the contract suite described in `../tests/README.md`. The experimental
feature module adds movement and wrist-temperature IQRs and elapsed-time slopes
per hour. Original features, eligibility gates and missing minutes are retained.

## Cloud evaluation

`../tiger/evaluate_robust_features.py` is a Databricks notebook. Its required
widgets are `project_root` (workspace filesystem directory containing both
feature modules), `experiment_path` (a separate MLflow development experiment),
and `reference_release` (the fixed saved baseline).

Upload these files into a separate development folder:

- `rolling_risk.py` and `experimental_features.py` as raw Python files.
- `evaluate_robust_features.py` as a Python notebook.

Run a single notebook task with a 30-minute timeout. No database credentials
are needed: only read access to Silver and saved training windows, and write
access to the new development MLflow experiment. The existing model registry,
release tables, source data and Tiger publication are not modified.

## Mandatory agreement checks

The evaluator reconstructs windows from real Silver data, verifies the exact
660 reference keys and labels, and checks original feature values. It must also
reproduce saved held-out model and prior predictions before logging a successful
comparison. A failed agreement check invalidates the comparison and requires
investigation; do not loosen tolerances to obtain a better metric.

The report compares original-feature selection, extended-feature selection,
joint feature-family/estimator selection and a prior classifier. Every selection
uses inner participant folds, separate from the outer held-out participant.
Equal total participant weights apply to fitting/scaling and aggregate metrics.
Reports include paired outer-fold accuracy/Brier loss, selected candidates,
limitations and the reference release. No model is automatically promoted.

See `MODEL_EXPERIMENT_PLAN.md` for the fixed experimental protocol.
