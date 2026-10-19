# Predeclared heart-rate information comparison

## Hypothesis

Heart rate is staged but absent from the existing 12-feature rolling contract.
Test whether this additional measurement supplies useful information beyond
five temperature summaries. This is a new sensor-information comparison, not a
post-hoc threshold search. It remains reused-cohort development, not external
validation or a guarantee of 70%.

## Fixed controls

- Same 660 saved windows, 15 approved BIG IDEAs participants, original labels,
  participant 015 exclusion, seed 42, threshold 0.5 and participant weights.
- Preserve existing motion/temperature coverage gates and window keys. Do not
  drop poorly classified people or windows because HR is missing.
- Read only staged HR CSVs for the approved roster. Parse shifted source-clock
  timestamps consistently with existing features; no inferred UTC correction.
- Aggregate finite positive HR samples to per-minute means. Require 48–60 valid
  rows and no invalid samples in retained HR minutes. For subjects 002–016,
  reject minutes with duplicate fine-resolution timestamps. Participant 001's
  documented M/d/yy H:mm source format stores repeated minute timestamps;
  preserve those rows rather than incorrectly deduplicating or inventing order.
  Parse this format explicitly alongside the other files' timestamp format.
  This provenance correction is fixed before fitting, without using outcomes.
- Each 24-hour HR window needs >=1,152 retained minutes and >=30 in each relative
  hour bin. No interpolation, forward fill or future samples.
- Exactly four added features: mean, sample standard deviation, 10th and 90th
  percentile of those minute means. These are not beat-to-beat HRV measurements.
- If a saved window lacks HR coverage, its four HR summaries stay missing.
  Median imputation is fitted only on training-fold rows (unweighted median);
  no missingness/coverage indicator is included as an input. Abort if any HR
  summary has no observed training values. Preserve every saved window.

## Comparison and primary procedure

Fixed groups: Temperature (5), Heart rate (4), Temperature + HR (9).
Use the six existing candidates from #100/#116: prior, logistic
C=0.001/0.01/0.1/1, and the existing depth-3 forest. No added nonlinear models.
HR-containing pipelines include fold-local median imputation, then the existing
weighted scaler/logistic or weighted forest. Prior remains the same.

**Primary procedure:** jointly select Temperature versus Temperature + HR and
estimator in inner participant-stratified folds, ranking balanced accuracy then
log loss. HR-only is descriptive and not eligible for primary group selection.
Outer folds leave one participant out. Report each group's independently
inner-selected procedure, primary selection and prior, with all five metrics
and paired participant outcomes. Do not replace the primary result with whichever
outer-scored group happens to have the highest accuracy.

Reproduce #116 temperature metrics, fold selections and per-person accuracies
before interpreting alternatives. Log HR availability and exact window-key
alignment, full held-out predictions and the comparison in separate MLflow
artifacts. Commit no observation or prediction files. Run one bounded comparison;
retain negative results and do not adapt the plan against outer outcomes.

No model release, table, feature contract, replay pin or app setting is published.
Any score crossing 70% is a development result on this reused cohort, not an
independently validated accuracy or a calibration/clinical claim.
