# Fixed nonlinear temperature comparison — October 18, 2026

## Result and decision

The predeclared primary nested selection procedure achieves **66.86% accuracy**
versus 65.33% for the temperature control. It **does not reach 70%**. Although
accuracy and balanced accuracy increase, AUC, log loss and Brier loss worsen.
No release or pipeline is promoted on this mixed development result.

The two fixed nonlinear models alone do not improve accuracy: Gaussian NB
achieves 59.97%, and RBF SVC achieves 52.17%. The primary procedure selected
models using inner participant-disjoint folds, not the outer outcomes.

## Verification

- Same 660 real windows, 15 participants, original labels and exclusions,
  fixed five temperature features, coverage gates, seed and threshold 0.5.
- Original temperature control reproduces every reference metric, fold model
  selection, window count and per-person accuracy from MLflow reference
  `14db0b9a30fd4199b655b5a136d470f8`. Prior predictions reproduce saved values.
- Weighted scaling and fitting remain inside training folds; participants in
  training and validation are asserted disjoint for every fit.
- [Databricks run 465162470603678](https://dbc-27a761ea-7108.cloud.databricks.com/?o=7474651454805950#job/388858448062430/run/465162470603678): SUCCESS.
- Task `233463169531683`; MLflow `e51acdcb28cb44c0a716052da2fc701e`,
  experiment `/Users/pdpate22@ncsu.edu/Gluco-temperature-nonlinear-development`.
- Artifacts: `comparison.json`, `held_out_predictions.json`, retained in MLflow,
  not committed to Git. Plan: `NONLINEAR_TEMPERATURE_PLAN.md`.

## Participant-weighted held-out window metrics

| Procedure | Accuracy | Balanced accuracy | AUC | Log loss | Brier |
| --- | ---: | ---: | ---: | ---: | ---: |
| Temperature control | 65.33% | 64.91% | 0.6911 | 0.6445 | 0.2256 |
| Primary inner selection | 66.86% | 66.55% | 0.6605 | 0.6780 | 0.2385 |
| Fixed Gaussian NB | 59.97% | 61.51% | 0.5851 | 3.3311 | 0.3830 |
| Fixed RBF SVC | 52.17% | 52.19% | 0.4885 | 0.8650 | 0.3164 |
| Prior | 53.33% | 50.00% | Omitted | 0.7651 | 0.2857 |

The RBF SVC uses probability=False; scores are fixed sigmoids of decision
margins to preserve the zero-margin classification boundary and bounded-score
API. They are not calibrated class probabilities. No sample-level internal
calibration CV is used. All reported losses are descriptive score losses;
no model is claimed calibrated. Prior cross-fold AUC is omitted for the reasons
documented in the preceding studies.

## Paired outcomes

| Participant | Windows | Control accuracy | Primary accuracy | Selected primary model |
| --- | ---: | ---: | ---: | --- |
| big_ideas:001 | 44 | 100.00% | 100.00% | gaussian_nb |
| big_ideas:002 | 56 | 0.00% | 0.00% | logistic_c0.01 |
| big_ideas:003 | 9 | 100.00% | 100.00% | logistic_c0.01 |
| big_ideas:004 | 47 | 100.00% | 100.00% | logistic_c0.01 |
| big_ideas:005 | 58 | 96.55% | 96.55% | logistic_c0.01 |
| big_ideas:006 | 16 | 100.00% | 100.00% | logistic_c0.01 |
| big_ideas:007 | 112 | 72.32% | 72.32% | logistic_c0.01 |
| big_ideas:008 | 50 | 58.00% | 92.00% | gaussian_nb |
| big_ideas:009 | 36 | 61.11% | 61.11% | logistic_c0.01 |
| big_ideas:010 | 69 | 17.39% | 17.39% | logistic_c0.01 |
| big_ideas:011 | 6 | 0.00% | 0.00% | logistic_c01 |
| big_ideas:012 | 80 | 81.25% | 81.25% | logistic_c01 |
| big_ideas:013 | 18 | 94.44% | 94.44% | logistic_c0.01 |
| big_ideas:014 | 18 | 11.11% | 0.00% | rbf_svc |
| big_ideas:016 | 41 | 87.80% | 87.80% | logistic_c0.01 |

Only participant 008 improves (58% to 92%); participant 014 worsens (11.11% to
0%); the other 13 are unchanged. The 1.53-percentage-point average increase is
therefore concentrated in one improved participant. The primary procedure
selects logistic C=0.01 in ten folds, C=0.1 in two, Gaussian NB in two, and RBF
SVC in one. This does not demonstrate a stable generalization gain.

## Stop condition and next evidence

The bounded comparison is complete. There is no adaptive expansion of
hyperparameters, reversal of failed predictions, threshold fitting to outer
outcomes, sample-level train/test mixing, synthetic training, or error-selected
participant removal. All results, including negative alternatives, are retained.

The same cohort has now been reused across several development studies.
Continuing to search until its outer score crosses 70% would not establish a
reliable new-participant result. The target remains unmet. The all-participant
label/quality audit in `MODEL_DATA_READINESS.md` found no mapping error or
eligibility failure that justifies changing the difficult participants.

A targeted dataset search did not establish an accessible independent cohort
with compatible wrist-temperature recordings and the same HbA1c target.
Larger cohorts with environmental temperature or different disease labels
cannot simply be substituted. A compatible cohort or an explicitly revised
research task is required for further independent validation. This does not
prove that no such cohort exists; access/compatibility remain unresolved.

No model artifact, table, published feature contract, application setting,
replay pin or Tiger publication changed. The original deployed reference and
its historical 60.42% evaluation remain distinct from development scores.

## Local checks

69 tests pass on this branch based on main `38d1c50` (65 existing plus four
margin-score tests); the five feature-group tests in pending #116 are not yet
part of this branch. Changed Python passes Ruff checks and formatting. These
local tests verify numeric-score behavior; the cloud run verifies reference
reproduction and participant separation. Passing tests do not validate 70%.
