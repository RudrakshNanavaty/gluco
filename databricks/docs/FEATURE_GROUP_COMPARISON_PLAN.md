# Next development study: movement versus temperature

## Question

Which sensor groups contribute predictive signal in the existing rolling
classifier? This is a descriptive ablation study, not a search for a guaranteed
70% result or an independent validation of the 62.11% development candidate.
This document is a plan; the comparison has not been run.

## Fixed inputs and evaluation

- Preserve the same 660 real windows, labels, 15 approved participants and
  participant 015 exclusion from release `38ec33cb326146c7991650a3164cf440`.
- Do not relax coverage, fill gaps, add synthetic data, or use glucose/HbA1c,
  participant IDs or device/cohort metadata as features.
- Reproduce the 62.11% regularized combined-feature procedure from #100 before
  interpreting group comparisons. Preserve the original 60.42% reference too.
- Keep outer leave-one-participant-out evaluation and inner three-fold
  participant-stratified selection, seed 42, equal participant weighting and
  fold-local weighted preprocessing.
- Freeze the candidate set from #100: prior, logistic C=0.001/0.01/0.1/1,
  and the existing depth-3 random forest. Keep threshold 0.5. No new candidates
  or threshold search in response to the outer results.

## Predeclared feature groups

| Group | Exact features |
| --- | --- |
| Movement (6) | motion_mean_g, motion_p90_g, motion_median_g, motion_std_g, motion_p99_g, motion_daily_amplitude_g |
| Temperature (5) | temperature_mean_c, temperature_std_c, temperature_p10_c, temperature_p90_c, temperature_daily_amplitude_c |
| Combined (12) | The original 12-feature contract: both groups plus motion_temperature_corr |

Select the estimator within each group's inner folds using the existing
balanced-accuracy/log-loss rule. Do not select a winning group against the
outer results or promote its estimator. Because Combined additionally contains
a cross-channel correlation feature, its difference from either group includes
that coupling signal; this three-group study does not isolate correlation's
individual contribution.

## Deliverables and interpretation

Log a separate MLflow comparison with baseline reproduction, exact window/label
agreement, fold selections, participant-weighted accuracy, balanced accuracy,
AUC, log loss, Brier and paired per-person changes. Report negative results.
Group ablation describes predictive contribution under this procedure; it does
not identify causal effects, validate individual features, or establish device
transfer. All groups reuse the same development cohort. New independently
labeled participants are needed to validate subsequent claims. No model/table,
release, replay pin or app setting is written by the planned notebook.
