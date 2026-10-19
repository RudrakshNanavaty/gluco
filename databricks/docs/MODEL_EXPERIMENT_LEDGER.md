# Rolling-model development experiment ledger — October 18, 2026

## Current interpretation

**70% has not been achieved under the recorded evaluation.** The highest
observed development accuracy is 66.86% from the nonlinear temperature study,
with worse AUC and probability losses than its 65.33% temperature control.
That mixed result was not promoted. Adding HR or EDA did not improve the
primary procedures. No source channel, difficult participant, prediction
polarity or threshold was selected against outer outcomes to claim 70%.

Every comparison below reuses the same 660 real windows from 15 approved
BIG IDEAs participants. They are development comparisons, not independent
validation; additional measured channels are not additional independent people.
The original published feature/model contract and application pin remain
unchanged by these experiments. See each PR for live review/merge status rather
than treating this dated ledger as a deployment status monitor.

## Results retained, including negatives

| Investigation | Reported procedure | Accuracy | Evidence |
| --- | --- | ---: | --- |
| Original reference | Existing nested estimator selection | 60.42% | #85, #89 |
| Robust summaries | Extended feature family | 54.37% | #90, ROBUST_FEATURE_RESULTS.md |
| Robust summaries | Joint feature-family/estimator selection | 59.31% | #90 |
| Stronger regularization | Existing inputs, expanded fixed logistic candidates | 62.11% | #100, ACCURACY_EXPERIMENT_RESULTS.md |
| Threshold alternative | Inner-selected model/threshold | 57.93% | #100 |
| Sensor-group ablation | Temperature-only group (descriptive, no group winner deployed) | 65.33% | #116, SENSOR_GROUP_RESULTS.md |
| Sensor-group ablation | Movement-only group | 26.04% | #116 |
| Nonlinear temperature | Predeclared primary inner selection | 66.86% | #118, NONLINEAR_TEMPERATURE_RESULTS.md |
| Additional HR information | Predeclared primary Temperature vs Temperature+HR selection | 64.70% | #122, HEART_RATE_RESULTS.md |
| Additional EDA information | Predeclared primary Temperature vs Temperature+EDA selection | 65.33% | #124, EDA_RESULTS.md |

Some result documents live on their respective PR branches until merged.
The prior classifier's participant-weighted accuracy is 53.33%; its cross-fold
AUC is omitted because fold-specific class balance makes that comparison
misleading. Accuracy is the average of per-person window accuracies, not the
fraction of 660 independent people correctly classified.

## Data/provenance findings relevant to next work

- Source/Bronze/Silver/saved labels agree for all 15 included people; the
  difficult participants cannot be relabeled or removed based on their errors
  (#118, MODEL_DATA_READINESS.md).
- The three incomplete Silver minutes originate from source-temperature absence
  with short valid ACC tails. Existing gates exclude them (#114).
- All 660 saved windows have quality-passing HR and EDA coverage. HR requires
  the documented minute-resolution parser for 001; EDA files are fine resolution.
  No people/windows were dropped or actually imputed in these sensor studies.
- EDA staging verified 15 published-file checksums and made about 1.32 GB of
  source data available; it did not trigger a pipeline refresh or change a
  Delta/Tiger table, release, inference contract or app configuration.

## Remaining work toward reliable improvement

A compatible independently labeled cohort has not yet been established. The
targeted source review in MODEL_DATA_READINESS.md records known signal, target
and access mismatches; it is not proof that no suitable cohort exists.
Keep all negative results and the fixed evaluation controls. A future study
must define its information source and selection procedure before outcomes,
and must not keep expanding this reused outer search until a number passes 70%.
Any candidate promotion separately requires versioned training artifacts,
feature/inference parity checks and a fresh isolated replay, beyond a score.

The repeatable session-health tool in #120 checks data-contract snapshots;
it does not validate model accuracy or establish a live feed. TLS changes were
left aside at the user's request and are not part of these model studies.
