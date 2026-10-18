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
