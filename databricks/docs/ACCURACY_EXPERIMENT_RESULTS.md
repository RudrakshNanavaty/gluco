# Regularization and threshold experiment results

## Decision

Stronger regularization is a development candidate for follow-up. Retain the
currently published model: no artifact, release, replay pin, or app setting was
changed. Threshold tuning is not recommended by this comparison.

The same 660 real windows from 15 participants and original 12 features were
used. Baseline and prior predictions reproduced the saved release exactly.
All preprocessing, model selection and threshold selection used training
participants only, inside nested participant-held-out evaluation. This is a
reused development cohort, not an independent validation set.

## Verified run

- [Databricks run 488143797513486](https://dbc-27a761ea-7108.cloud.databricks.com/?o=7474651454805950#job/333493150209186/run/488143797513486)
- Notebook task: `849832658009506` (SUCCESS).
- MLflow: `ddf7ca9d0d0f479cb40fd6f5e5c58e9c`, experiment
  `/Users/pdpate22@ncsu.edu/Gluco-accuracy-v2-development`, artifact `comparison.json`.
- Reference release: `38ec33cb326146c7991650a3164cf440`.
- One completed comparison. An initial submission was canceled before the
  corrected notebook was submitted; it supplies no comparison result.

## Participant-weighted held-out window metrics

| Pipeline | Accuracy | Balanced accuracy | AUC | Log loss | Brier |
| --- | ---: | ---: | ---: | ---: | ---: |
| Original | 60.42% | 60.03% | 0.5953 | 0.8244 | 0.2788 |
| Stronger regularization candidates | 62.11% | 61.84% | 0.6064 | 0.7187 | 0.2558 |
| Inner-selected thresholds | 57.93% | 57.10% | 0.5771 | 0.7497 | 0.2700 |
| Prior | 53.33% | 50.00% | See note | 0.7651 | 0.2857 |

Regularization improves accuracy by **1.69 percentage points**, balanced accuracy
by 1.81 points, and reduces log loss and Brier loss. Lower values are better for
those two losses. This does not establish calibrated probabilities. Prior AUC
is omitted because its probability varies with the held-out participant's class.

The regularized pipeline adds only logistic C=0.001 and C=0.01 to the existing
candidate set. It keeps the original threshold 0.5 and inner selection rule
(balanced accuracy, then log loss). Inner folds selected C=0.01 in 8 outer folds,
original C=0.1 in 3, and the existing forest in 4. No single estimator has been
chosen against the outer results or published as a final model.

## Paired participant results

| Participant | Windows | Original accuracy | Regularized accuracy |
| --- | ---: | ---: | ---: |
| big_ideas:001 | 44 | 100.00% | 100.00% |
| big_ideas:002 | 56 | 3.57% | 0.00% |
| big_ideas:003 | 9 | 100.00% | 100.00% |
| big_ideas:004 | 47 | 85.11% | 85.11% |
| big_ideas:005 | 58 | 96.55% | 96.55% |
| big_ideas:006 | 16 | 100.00% | 100.00% |
| big_ideas:007 | 112 | 67.86% | 85.71% |
| big_ideas:008 | 50 | 56.00% | 58.00% |
| big_ideas:009 | 36 | 38.89% | 38.89% |
| big_ideas:010 | 69 | 11.59% | 11.59% |
| big_ideas:011 | 6 | 0.00% | 0.00% |
| big_ideas:012 | 80 | 57.50% | 57.50% |
| big_ideas:013 | 18 | 94.44% | 94.44% |
| big_ideas:014 | 18 | 16.67% | 11.11% |
| big_ideas:016 | 41 | 78.05% | 92.68% |

Three participants improve, two worsen, and ten are unchanged. Most gains come
from participants 007 and 016. These descriptive differences do not establish a
statistically reliable gain. Overlapping windows are not independent people.

## Next step

Review the predeclared plan, implementation and paired results. Obtain new
independently labeled participants for a locked validation of the candidate
selection procedure. Preserve both negative experiments. Do not repeatedly
expand candidates in response to these outer-fold outcomes. Before any later
promotion, fit and version an artifact using training-only selection and verify
feature/inference parity in a fresh replay session.

Local validation: all 65 Databricks tests pass; changed Python sources pass
Ruff checks (notebook Spark globals declared) and formatting. No medical or
cross-device generalization claim is supported.
