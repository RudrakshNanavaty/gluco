# Next model-validation and promotion steps

The 70% participant-weighted held-out window-accuracy target remains unmet.
Best observed reused-cohort development result: 66.8583%. Keep the current
published model while this checklist is incomplete. Synthetic M0 success is
instrument evidence, never a promotion metric.

## Freeze the question before collecting or evaluating

- Preserve the current HbA1c grouping and wearable-only past-24-hour input
  contract unless a separately reviewed proposal changes the scientific task.
- Freeze candidate, preprocessing, operating threshold, exclusions, primary
  metric, baseline, participant weighting and uncertainty reporting before
  touching independent evaluation labels.
- Select on development participants only. Do not choose another model after
  observing independent test results and still call those results a held-out test.

## Independent cohort acceptance

Verify licenses/permissions, distinct participant identities, HbA1c label timing
and units, sensor site/calibration, timezones, sampling and missingness. Require
wrist skin temperature where that feature is used; ambient temperature is not
an equivalent signal. Record consent/access restrictions and retain raw data
outside Git. Additional windows from the existing people are not new people.

No compatible independent cohort has yet been established. Current source
investigation and unresolved access/channel questions are in MODEL_DATA_READINESS.md.
Do not provision paid storage, accept data agreements or submit personal details
without the project owner's authorization.

## Evaluate and report

Report per-participant outcomes and all five metrics already used: accuracy,
balanced accuracy, ROC AUC, log loss and Brier score. Resample participants, not
individual overlapping windows, for uncertainty estimates. Preserve negative
results and disclose the many experiments on the 15-person development cohort.
Record cohort size and class composition beside every headline percentage.
Reaching a point estimate of 70% does not establish clinical validity.

## Promotion review

Review accuracy against the frozen target and baseline alongside probability
quality, coverage, subgroup failures and independent evidence. Verify artifact
feature ordering/version, dependency compatibility, release metadata and
read-only scoring on a separate demo session. Compare Delta/Tiger output and
prepare rollback to the existing release. Require human review before changing
the session pin; model training and dashboard publication are separate actions.

Current blockers: an independently labeled compatible cohort and a reviewed
frozen evaluation contract. Further unbounded tuning on these same 15 people
is not a substitute. This checklist makes no new accuracy claim or model change.
