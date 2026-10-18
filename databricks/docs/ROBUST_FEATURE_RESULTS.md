# Robust-feature experiment result

## Decision

Retain the original model and feature contract. Neither the extended feature
family nor nested joint feature/estimator selection improved the reference
metrics. No release was created or promoted; Tiger and session pins are unchanged.

## Verified run

Databricks parent run: `740899918143973`; notebook task: `71369751344116`.
MLflow run: `edc5e3d3d98d484bb4e87b810de71ac6` in the separate development
experiment `/Users/pdpate22@ncsu.edu/Gluco-robust-feature-development`.
The one-time run completed successfully. Exact window keys and labels matched
all 660 reference windows, original feature values matched, and reproduced
baseline model/prior held-out predictions passed strict numeric checks.

## Participant-weighted held-out window results

| Pipeline | Accuracy | Balanced accuracy | ROC AUC | Log loss | Brier loss |
| --- | ---: | ---: | ---: | ---: | ---: |
| Original features | 60.42% | 60.03% | 0.5953 | 0.8244 | 0.2788 |
| Extended features | 54.37% | 54.88% | 0.5173 | 1.0105 | 0.3302 |
| Joint family/model selection | 59.31% | 59.40% | 0.5863 | 0.8727 | 0.2917 |
| Prior baseline | 53.33% | 50.00% | See note | 0.7651 | 0.2857 |

Lower log loss and Brier loss are better. Prior AUC is intentionally not used:
its probability changes with the class of the omitted participant, so comparing
that cross-fold AUC is misleading. The original model's log loss remains worse
than the prior baseline; no calibration improvement is claimed.

Joint selection chose the extended family in 7 of 15 outer folds. Accuracy
improved in 3 people, worsened in 2, and was unchanged in 10. These paired results
are descriptive, not significance evidence. Full fold selections and paired
accuracy/Brier results are in the MLflow `comparison.json` artifact.

## Limits and next investigation

This is reused-cohort development on 15 people, not external validation. Do not
keep adding candidates in response to outer-fold results. Keep this negative
result alongside the baseline, rather than changing the report's primary metric.

Next useful data work: inspect bounded source provenance for the largest Silver
gaps and establish whether missing minutes are already absent in source files
or lost during parsing/aggregation. More independently labeled participants or
an external cohort are needed for stronger evidence of generalization.
