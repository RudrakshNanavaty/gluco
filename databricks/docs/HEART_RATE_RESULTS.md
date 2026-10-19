# Heart-rate information study results

## Decision

Do not promote HR features. The predeclared primary inner-selected procedure
achieves 64.70% accuracy, below the reproduced 65.33% temperature control. HR-only
and temperature+HR also underperform the control. This is a negative development
result on the same reused 15-person cohort; the 70% target remains unmet.

## Source and evaluation controls

All 660 reference windows have sufficient HR coverage. No windows or people
were removed, no label changed, and no HR feature required imputation in this
run. Missing-value imputation remains inside training pipelines for future
missing-data cases. HR summaries are minute-mean statistics, not beat-to-beat
HRV. Participant 001's documented minute-resolution timestamp format is parsed
explicitly; repeated rows in that format are preserved rather than incorrectly
deduplicated. Other participants' fine-resolution duplicate timestamps are
rejected by the minute gate.

Availability statement `01f1cb6f-7087-128b-abe8-fb9910107f01` succeeded.
The preliminary ISO-only parser falsely reported 001's HR missing; that was
corrected from existing source-format documentation before fitting. No outer
model outcomes were used for parsing or quality rules.

Same 660 windows, 15 participants, labels, exclusion, coverage, seed, weights,
threshold and six estimators. All model/feature-group selection and preprocessing
remain inside participant-disjoint training folds. The temperature control
reproduces reference metrics, fold model choices and per-person accuracies;
prior predictions reproduce the saved reference. No model/table/release,
feature contract, replay pin or application setting changed.

## Verified cloud run

- [Run 656971307132031](https://dbc-27a761ea-7108.cloud.databricks.com/?o=7474651454805950#job/163675948117425/run/656971307132031): SUCCESS.
- Task `612331671590131`; MLflow `a9c12f2892d54b0a8252608de043a581`.
- Experiment `/Users/pdpate22@ncsu.edu/Gluco-heart-rate-development`.
- Artifacts `comparison.json`, `held_out_predictions.json`; no observation or
  prediction data files are committed.

## Participant-weighted held-out metrics

| Procedure | Accuracy | Balanced accuracy | AUC | Log loss | Brier |
| --- | ---: | ---: | ---: | ---: | ---: |
| Temperature control | 65.33% | 64.91% | 0.6911 | 0.6445 | 0.2256 |
| HR only | 23.26% | 22.51% | 0.1204 | 0.8988 | 0.3338 |
| Temperature + HR | 62.07% | 61.88% | 0.6077 | 1.3513 | 0.2789 |
| Primary inner selection | 64.70% | 64.35% | 0.6567 | 1.2717 | 0.2567 |
| Prior | 53.33% | 50.00% | Omitted | 0.7651 | 0.2857 |

Lower losses are better. Prior cross-fold AUC is omitted for the same
held-out-class/class-balance reason as preceding reports. No probability
calibration, causal, clinical or cross-device generalization claim is made.

## Paired participant outcomes

| Participant | Windows | Temperature | HR only | Temperature + HR | Primary |
| --- | ---: | ---: | ---: | ---: | ---: |
| big_ideas:001 | 44 | 100.00% | 0.00% | 100.00% | 100.00% |
| big_ideas:002 | 56 | 0.00% | 7.14% | 0.00% | 0.00% |
| big_ideas:003 | 9 | 100.00% | 100.00% | 100.00% | 100.00% |
| big_ideas:004 | 47 | 100.00% | 0.00% | 61.70% | 100.00% |
| big_ideas:005 | 58 | 96.55% | 3.45% | 96.55% | 96.55% |
| big_ideas:006 | 16 | 100.00% | 31.25% | 100.00% | 100.00% |
| big_ideas:007 | 112 | 72.32% | 62.50% | 54.46% | 72.32% |
| big_ideas:008 | 50 | 58.00% | 0.00% | 64.00% | 64.00% |
| big_ideas:009 | 36 | 61.11% | 33.33% | 63.89% | 63.89% |
| big_ideas:010 | 69 | 17.39% | 1.45% | 79.71% | 79.71% |
| big_ideas:011 | 6 | 0.00% | 0.00% | 0.00% | 0.00% |
| big_ideas:012 | 80 | 81.25% | 0.00% | 68.75% | 68.75% |
| big_ideas:013 | 18 | 94.44% | 100.00% | 16.67% | 16.67% |
| big_ideas:014 | 18 | 11.11% | 0.00% | 27.78% | 11.11% |
| big_ideas:016 | 41 | 87.80% | 9.76% | 97.56% | 97.56% |

## Limits and local verification

This result tests only the specified HR summaries and estimators, not whether
HR is universally uninformative. Sample/window overlap means there are only
15 independent people. Do not reverse poor HR predictions or select features
against outer results to inflate accuracy. Additional measured channels can
be examined under separately fixed plans; independent labeled participants
remain necessary to validate any eventual improvement.

77 local tests pass (65 main tests plus 12 HR-summary cases). Changed Python
passes Ruff checks/formatting. Tests cover analytic summaries, exact coverage,
hourly gaps, invalid values, duplicate minutes, time-shift invariance and both
past-only boundaries. Live coverage and reference reproduction passed in cloud.
