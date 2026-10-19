# EDA information study results

## Decision

Do not promote EDA features. The predeclared primary procedure selected the
existing temperature family in all 15 outer folds and reproduces its 65.33%
accuracy. Temperature+EDA scores 51.04%, and EDA-only 36.64%. The 70% target
remains unmet. Preserve this negative result and the separate negative HR study
in #122 rather than switching to an outer-fold-selected feature family.

The best earlier observed accuracy remains 66.86% from #118's mixed nonlinear
comparison, whose AUC and probability losses worsened. Neither that result nor
these studies establishes independent validation or justifies promotion.

## Staging and availability

[Staging run 1027806033713704](https://dbc-27a761ea-7108.cloud.databricks.com/?o=7474651454805950#job/726206235839263/run/1027806033713704)
succeeded, ensuring 15 EDA CSVs (1,316,738,259 bytes, about 1.32 GB) are available
for the unchanged approved cohort. Each source path was checked against the
published v1.1.3 SHA256 manifest and the matching public v1.1.2 mirror hash.
Existing matching files are retained; mismatching files abort staging rather
than being overwritten. Only missing files are downloaded atomically.

Dataset attribution: [BIG IDEAs Lab Glycemic Variability and Wearable Device
Data v1.1.3](https://physionet.org/content/big-ideas-glycemic-wearable/1.1.3/).
No source or prediction data files are committed. New source availability does
not mean new independent participants.

Read-only availability statement `01f1cb70-8e7c-1d1b-a659-0f289c722663` passed:
all 660 original windows have EDA coverage under the predeclared gates. The
notebook independently reproduced that coverage, so no windows/people were
dropped and no EDA values required imputation in this run. All selected EDA
files have fine-resolution clock strings; the coarse-minute format count is
zero for every participant. The HR-specific 001 format exception is not applied
to EDA. Invalid or duplicate fine-resolution samples cannot pass the minute gate.

## Verified evaluation

- [Run 810871797359838](https://dbc-27a761ea-7108.cloud.databricks.com/?o=7474651454805950#job/228741439441617/run/810871797359838): SUCCESS.
- Task `1061051233527553`; MLflow `462dfbde9299468c97f46338e860df50`.
- Experiment `/Users/pdpate22@ncsu.edu/Gluco-EDA-development`.
- Artifacts `comparison.json`, `held_out_predictions.json` preserve full
  availability, source resolution, estimator selections and held-out predictions.
- Plan/staging commit `d885c42`, evaluation implementation `5eacd72` and bounded
  aggregation `e892b72` were committed before evaluation.
- Same 660 windows, 15 participants, labels, exclusion, seed, weights, threshold,
  existing coverage rules and six estimator candidates. Four fixed past-only
  EDA minute-mean summaries preserve source units; no physiological/clinical
  calibration is inferred.
- All preprocessing and group/estimator selection stay inside participant-
  disjoint training folds. Temperature control metrics, fold model selections
  and per-person accuracies reproduce #116, and prior predictions match the
  saved reference. Primary selection includes only Temperature and
  Temperature+EDA; EDA-only is a descriptive comparison.

## Participant-weighted held-out metrics

| Procedure | Accuracy | Balanced accuracy | AUC | Log loss | Brier |
| --- | ---: | ---: | ---: | ---: | ---: |
| Temperature control | 65.33% | 64.91% | 0.6911 | 0.6445 | 0.2256 |
| EDA only | 36.64% | 36.35% | 0.2978 | 0.9562 | 0.3610 |
| Temperature + EDA | 51.04% | 50.28% | 0.5807 | 0.7126 | 0.2571 |
| Primary inner selection | 65.33% | 64.91% | 0.6911 | 0.6445 | 0.2256 |
| Prior | 53.33% | 50.00% | Omitted | 0.7651 | 0.2857 |

Lower losses are better. Prior cross-fold AUC is omitted for the documented
held-out-class/class-balance reason. No calibration, clinical or cross-device
claim is made.

## Paired outcomes

| Participant | Windows | Temperature | EDA only | Temperature + EDA | Primary |
| --- | ---: | ---: | ---: | ---: | ---: |
| big_ideas:001 | 44 | 100.00% | 0.00% | 100.00% | 100.00% |
| big_ideas:002 | 56 | 0.00% | 5.36% | 0.00% | 0.00% |
| big_ideas:003 | 9 | 100.00% | 77.78% | 55.56% | 100.00% |
| big_ideas:004 | 47 | 100.00% | 25.53% | 100.00% | 100.00% |
| big_ideas:005 | 58 | 96.55% | 6.90% | 94.83% | 96.55% |
| big_ideas:006 | 16 | 100.00% | 31.25% | 100.00% | 100.00% |
| big_ideas:007 | 112 | 72.32% | 69.64% | 55.36% | 72.32% |
| big_ideas:008 | 50 | 58.00% | 64.00% | 0.00% | 58.00% |
| big_ideas:009 | 36 | 61.11% | 50.00% | 41.67% | 61.11% |
| big_ideas:010 | 69 | 17.39% | 34.78% | 7.25% | 17.39% |
| big_ideas:011 | 6 | 0.00% | 100.00% | 0.00% | 0.00% |
| big_ideas:012 | 80 | 81.25% | 11.25% | 20.00% | 81.25% |
| big_ideas:013 | 18 | 94.44% | 0.00% | 94.44% | 94.44% |
| big_ideas:014 | 18 | 11.11% | 0.00% | 11.11% | 11.11% |
| big_ideas:016 | 41 | 87.80% | 73.17% | 85.37% | 87.80% |

Every primary fold selects Temperature, and all primary predictions/metrics
agree with the reproduced control. For example, EDA-only correctly classifies
011's windows but performs poorly elsewhere; choosing EDA specifically for that
held-out person based on this table would use their outcomes for selection.
No such selection is performed.

## Limits, checks and remaining evidence

This tests fixed EDA summaries/estimators, not every possible EDA signal method.
There are still only 15 independent labeled people despite repeated windows
and additional channels. These accumulated development comparisons cannot be
presented as an independent test. The 70% target is not achieved, and selecting
models, people, labels or thresholds against observed outer results would not
establish a reliable gain.

78 local tests pass (65 main plus 13 EDA-summary tests). Changed Python passes
Ruff checks/formatting. Tests cover analytic summaries, exact coverage, hourly
gaps, invalid values, legitimate zero values, duplicate minutes, time shifts
and both past-only boundaries. Source checksums and coverage and reference
reproduction are verified in cloud.

The staging operation adds/verifies EDA source files only. No existing source
file was overwritten, no pipeline refresh was triggered, and no Delta/Tiger
table, model artifact/release, published feature contract, session pin or app
setting changed. Further reliable validation needs compatible independently
labeled participants; access/availability remains unresolved as documented in
#118's MODEL_DATA_READINESS.md. Any future sensor method needs a separate fixed
plan, not automatic expansion until this reused outer score crosses 70%.
