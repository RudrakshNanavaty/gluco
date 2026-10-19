# First controlled rolling-model experiment

## Objective

Compare a small predeclared wearable-feature extension with the existing
60.4% participant-weighted window accuracy baseline. No improvement is assumed.
The development cohort is reused: results cannot be called external validation.

## Fixed controls

- Same 15 approved BIG IDEAs participants; preserve participant 015 exclusion.
- Same 660 accepted real windows, labels, timestamps, original 12 features and
  feature definitions. Assert exact participant/window-end key agreement.
- No synthetic/demo input, CGM, HbA1c, patient identifier, or cohort label in X.
- Same outer leave-one-participant-out folds, inner three-fold participant
  stratification, candidate estimator set, seed and participant weighting.
- Preprocessing and selection happen inside each training fold. Keep the
  current baseline, including prior classifier, in the same comparison.
- Do not tune coverage thresholds using already viewed held-out outcomes.

## Predeclared comparison

1. Reproduce the baseline report and saved keys before running alternatives.
2. Compare the original 12 features with an extended vector containing exactly
   four additional robust summaries: motion IQR, skin-temperature IQR, and
   least-squares motion and temperature slopes over elapsed window time.
3. Compute all summaries on the same observed minutes; never interpolate gaps.
   Use relative elapsed minutes for slopes, with explicit units per hour.
4. Preserve current estimator hyperparameters and selection rules for this
   first experiment. Select feature family and estimator only within inner
   folds; the outer participant stays untouched until evaluation.
5. Define a new feature contract/version and tests. Never overwrite an existing
   artifact or change a running session's pinned model.

## Reporting and decision

Report participant-weighted accuracy, balanced accuracy, ROC AUC, log loss and
Brier loss for both pipelines and the prior baseline. Include paired per-person
results and window counts so a gain driven by one participant is visible.
Record the larger search space and reused-cohort limitation. Better accuracy
alone does not justify probability calibration claims or deployment.

The next implementation should produce a separate versioned MLflow experiment
and an offline comparison report. Do not auto-promote a release. If results
justify further investigation, validate schema/inference parity and publish only
to a fresh test replay session before updating app configuration.

## Separate data follow-up

Check whether large Silver gaps correspond to source-file gaps or processing
loss using bounded source checks. Avoid rereading all high-frequency files by
default. Additional independently labeled people are more valuable evidence
than simply creating more overlapping windows from the current cohort.
