# Sensor-group development comparison

## Finding and decision

Temperature-only features achieve 65.33% participant-weighted held-out window
accuracy, compared with 62.11% for Combined and 26.04% for Movement in this
predeclared comparison. Temperature-only also improves balanced accuracy,
AUC, log loss and Brier loss relative to Combined.

This is descriptive evidence on the same reused 15-person development cohort.
No feature group was selected for deployment, and no model artifact, published
feature contract, table, session pin or app setting was changed. The published
reference remains the 12-feature model with 60.42% reference accuracy.

## Controls and verified run

- Plan predeclared in #114 before execution; follow-up tracked in #115.
- Same 660 real windows, original labels, 15 approved participants and 015
  exclusion; unchanged coverage and sample-ratio gates.
- Fixed candidates and threshold 0.5 from #100. Each group's estimator is
  selected using only inner participant-stratified folds. Scaling and fitting
  stay inside training folds, with equal total participant weights.
- Outer leave-one-participant-out evaluation; disjoint participant assertions.
- Original baseline/prior predictions reproduce the saved release per window.
- Combined reproduces all five metrics, estimator selections, window counts
  and per-person accuracies from MLflow reference
  `ddf7ca9d0d0f479cb40fd6f5e5c58e9c` within strict numerical tolerances.
- [Databricks run 603498498602491](https://dbc-27a761ea-7108.cloud.databricks.com/?o=7474651454805950#job/882887170646055/run/603498498602491): SUCCESS.
- Task `1046034804007697`; MLflow `14db0b9a30fd4199b655b5a136d470f8`,
  experiment `/Users/pdpate22@ncsu.edu/Gluco-sensor-group-development`.
- MLflow artifacts: `comparison.json` and `held_out_predictions.json`. Study
  observations/prediction files are not committed to Git.

## Participant-weighted held-out window metrics

| Group / reference | Accuracy | Balanced accuracy | AUC | Log loss | Brier |
| --- | ---: | ---: | ---: | ---: | ---: |
| Original 12-feature reference | 60.42% | 60.03% | 0.5953 | 0.8244 | 0.2788 |
| Combined, regularized (12) | 62.11% | 61.84% | 0.6064 | 0.7187 | 0.2558 |
| Movement only (6) | 26.04% | 24.42% | 0.3109 | 0.8507 | 0.3217 |
| Temperature only (5) | 65.33% | 64.91% | 0.6911 | 0.6445 | 0.2256 |
| Prior reference | 53.33% | 50.00% | See note | 0.7651 | 0.2857 |

Lower log loss and Brier loss are better. Prior AUC is omitted because its
fold-specific probability depends on the held-out class via training class
balance; that cross-fold AUC is misleading. Better losses here do not establish
probability calibration.

Temperature-only accuracy exceeds Combined by 3.23 percentage points and the
original reference by 4.92 points. These are development differences, not
independently validated gains. The study does not reach 70%.

## Paired participant results

| Participant | Windows | Combined accuracy | Movement accuracy | Temperature accuracy |
| --- | ---: | ---: | ---: | ---: |
| big_ideas:001 | 44 | 100.00% | 0.00% | 100.00% |
| big_ideas:002 | 56 | 0.00% | 0.00% | 0.00% |
| big_ideas:003 | 9 | 100.00% | 100.00% | 100.00% |
| big_ideas:004 | 47 | 85.11% | 42.55% | 100.00% |
| big_ideas:005 | 58 | 96.55% | 51.72% | 96.55% |
| big_ideas:006 | 16 | 100.00% | 75.00% | 100.00% |
| big_ideas:007 | 112 | 85.71% | 0.00% | 72.32% |
| big_ideas:008 | 50 | 58.00% | 0.00% | 58.00% |
| big_ideas:009 | 36 | 38.89% | 30.56% | 61.11% |
| big_ideas:010 | 69 | 11.59% | 13.04% | 17.39% |
| big_ideas:011 | 6 | 0.00% | 66.67% | 0.00% |
| big_ideas:012 | 80 | 57.50% | 0.00% | 81.25% |
| big_ideas:013 | 18 | 94.44% | 11.11% | 94.44% |
| big_ideas:014 | 18 | 11.11% | 0.00% | 11.11% |
| big_ideas:016 | 41 | 92.68% | 0.00% | 87.80% |

Relative to Combined, temperature-only improves four people (004/009/010/012),
worsens two (007/016), and leaves nine unchanged. Three participants (002/011/014)
still have 0%, 0%, and 11.11% temperature-only accuracy respectively. The average
does not represent consistent performance across people.

Movement-only selects the prior in all seven class-0 outer folds and the forest
in all eight class-1 folds. This pattern is an observed consequence of the
training-fold selection procedure on this small cohort, not evidence that
held-out labels were used for selection: each prediction's fitting/selection
participants are asserted disjoint from its held-out participant. It highlights
selection instability and weak transfer under this procedure. Do not reverse
its predictions or retune thresholds against these outer results to manufacture
a higher reported accuracy.

Temperature-only selects logistic C=0.01 in 12 folds and C=0.1 in three.
Combined retains the same fold selections as #100. The report preserves all
fold selections and paired results for review.

## Interpretation and next work

The result suggests the temperature summaries carry more useful predictive
information than movement summaries under this fixed procedure. It does not
show that temperature causes HbA1c differences, that movement is universally
uninformative, or which individual temperature feature matters.

Combined also includes movement-temperature correlation, absent from both
single-sensor groups. This study cannot isolate that correlation feature's
individual effect. It also does not establish reliable improvement across
independent cohorts or different devices. No statistical significance or
calibrated clinical probability claim is made.

Next: independently audit recording quality and label provenance for difficult
participants without excluding people based on errors or changing verified
labels. Establish a new independently labeled validation cohort before making
promotion claims. Preserve this result and the earlier negative experiments;
do not continually expand candidates in response to the same outer results.

## Local validation

All 70 Databricks tests pass. New tests enforce fixed feature groups, exclude
cross-channel/target/ID columns from single-sensor inputs and reject malformed
schemas. Ruff checks and formatting pass for changed Python, with Spark globals
declared for the notebook. The cloud run enforces reference reproduction and
participant-disjoint fitting assertions.
