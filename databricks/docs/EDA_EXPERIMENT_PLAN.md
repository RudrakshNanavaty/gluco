# Predeclared EDA information comparison

## Scope and primary hypothesis

HR did not improve the temperature control. Separately test one additional
measured E4 channel, electrodermal activity (EDA), rather than changing labels,
thresholds, exclusions or hyperparameter grids. This remains another reused-
cohort development study, not independent validation or a guaranteed 70% result.

Stage only EDA files for the same 15 approved participants, verifying each
against current PhysioNet SHA256 and the public mirror manifest. Preserve
existing files and abort on mismatch; no pipeline refresh or source overwrite.
Record downloaded bytes and source parsing/availability before fitting.

## Fixed feature and quality contract

Aggregate finite nonnegative EDA readings into minute means. At the documented
4 Hz source cadence, retain minutes with 192–240 valid rows and no invalid
readings. Use source-clock TIMESTAMP_NTZ and explicit documented timestamp
formats; no inferred clock shifts or fabricated subminute order. For files
with fine-resolution timestamps, reject duplicate-timestamp minutes. If a file
is documented to have only minute-resolution timestamps, preserve repeated
rows and report that source fact before fitting, rather than silently deduping.

Four past-only 24-hour summaries of minute means: mean, sample standard deviation,
10th and 90th percentiles. Require 1,152 retained minutes and >=30 in each of
24 relative hour bins. No interpolation. Retain all original 660 windows and
15 participants, including missing EDA summaries as NaN if coverage fails.
Fit median imputation only inside training folds, without missingness/coverage
indicators; abort if a feature has no observed training values.

## Evaluation

Fixed groups: Temperature (5), EDA only (4), Temperature+EDA (9). The primary
procedure selects Temperature versus Temperature+EDA and estimator only in
inner participant-stratified folds, using balanced accuracy then log loss.
EDA-only is descriptive, not eligible for primary group selection.

Use the same six candidates from #116, seed 42, equal participant weighting,
threshold 0.5, outer leave-one-participant-out evaluation and training-only
preprocessing. No added nonlinear candidates or adaptive grids. Reproduce the
65.33% temperature control's metrics, fold selections and per-person accuracies,
and saved prior predictions, before interpreting results.

Log all five metrics and paired outcomes, availability and held-out predictions
in separate MLflow artifacts. Report primary and every descriptive group even
if negative; do not choose a better outer score as a replacement primary.
No model artifacts/releases, feature contract, session pins or app settings
are published. HR and all earlier negative results remain recorded.
