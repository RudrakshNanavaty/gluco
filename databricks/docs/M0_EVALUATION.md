# M0: reproducible evaluation and research decision

Research hypothesis: wearable-only past-24-hour features achieve at least 70%
participant-weighted held-out accuracy and improve over a label-only baseline.
This concerns the study's HbA1c grouping, not glucose prediction or diagnosis.

## Offline CI demonstration

From the repository root, without cloud credentials:

```bash
uv run --python 3.12 --no-project --with-requirements databricks/requirements-eval.txt python databricks/tiger/evaluate_m0.py --output /tmp/m0.json
```

The deterministic fixture generates 20 artificial participants, two complete
1440-minute traces each. It calls the production `window_features`, trains a
fixed logistic model with scaling fitted only on training participants, and
leaves one entire participant out. Equal participant weighting is explicit.
The baseline always predicts class zero (50% on this balanced fixture).
Acceptance requires accuracy >=70% AND improvement >=10 percentage points.
This fixture deliberately contains a strong artificial temperature signal.
It demonstrates the instrument, not the real-world hypothesis.

`--no-signal` removes label information and must exit 1. CI checks that exact
status, so an execution error cannot masquerade as the expected negative result.
Invalid arguments exit 2. JSON reports are retained as workflow artifacts.
Thresholds can be set explicitly with `--min-accuracy` and `--min-gain`.
There is no cloud data, secret, training-table write or model publication.

## Real evidence and spiral decision

The published real-data baseline achieved 60.4153% participant-weighted accuracy
versus 53.3333% for the prior baseline: 660 overlapping windows but only 15 people.
The best observed development result was 66.8583%; 70% remains unmet. Multiple
experiments reused this small cohort, so the best result is exploratory and
requires independent confirmation. No model was promoted.

Decision: persevere with the pipeline and reproducible evaluation, retain
negative studies, and re-plan model validation around additional independent
participants rather than relaxing the target or counting windows as people.
See issues #117, #121, #123 and their experiment PRs #118, #122, #124.
Real nested evaluation requires the authorized Databricks cohort and workspace;
see `tiger/evaluate_accuracy.py`. The offline fixture is not a replacement for
that experiment, and its result must never be displayed as Gluco model accuracy.

## Completion boundaries

Review/merge #114, #116, #118, #120, #122, #124 before treating their contents as
main-branch evidence. Session health instructions arrive in #120. Bounded replay
and retry tests demonstrate pipeline behavior; they do not establish a physical
sensor deployment, continuous monitoring, or a production service-level promise.
Cloud recurrence needs an explicit session, model pin, cadence, stop condition,
compute budget and alert destination. Keep schedules paused until these are
reviewed, and run the read-only health check before and after a bounded replay.
