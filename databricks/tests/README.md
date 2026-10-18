# Local pipeline contract tests

From the repository root:

```sh
uv run --no-project --with-requirements databricks/requirements-test.txt python -m pytest databricks/tests -q
```

These tests use constructed signals and deterministic model doubles. They verify
past-only windows, coverage gates, missing values, minute identity, known daily
cycles, feature contracts, held-out model selection, class ordering, score
bounds, and 24-hour change handling. They need no cloud credentials, study data,
Spark session, trained artifacts, or LLM calls.

The `databricks` CI job runs them independently of app tests. Passing does not
establish model accuracy, external validity, or cloud ingestion correctness.

The experimental-feature tests additionally check unchanged baseline features,
elapsed-time slopes across irregular missing minutes, zero spread/slope for
constant signals, exclusion of future values, baseline rejection gates, and
invariance to absolute timestamp offsets.

Replay tests cover explicit configuration, timezone/range checks, per-session
state paths, immutable resume settings, task dependency/connection propagation,
batch bounds, a bounded dry-run, failure/stop cursor retention, successful
refresh advancement, and stable session-scoped event identities. They do not
replace the remote event-retry and publication smoke test.

Runtime controls additionally cover terminated-run retry, explicit STOP
clearance, active-run refusal, submission-failure recovery, persisted stop status,
synthetic interpolation, missing HR and invalid tick limits.

Accuracy-selection tests check equal participant weighting, training-prediction
threshold selection, deterministic default-threshold ties, invariance to
repeating one participant's windows, and invalid probability rejection. The
separate cloud notebook reproduces baseline predictions before comparing
regularization and threshold selection on nested participant folds.

The nonlinear-temperature study adds tests for a fixed, uncalibrated sigmoid
of SVC decision margins: finite bounded output at extreme margins, monotonic
ordering, preservation of the zero-margin classification boundary and rejection
of nonfinite inputs. The separate cloud notebook reproduces the temperature
control and enforces participant-disjoint fitting; no row-level internal SVC
probability calibration is enabled.
