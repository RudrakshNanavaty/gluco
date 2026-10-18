# Model-data and validation readiness — October 18, 2026

## Label and quality audit

Read-only `databricks/sql/model_label_readiness.sql` checked all 16 staged
BIG IDEAs participants, not an error-selected exclusion list. Statement
`01f1cb3e-c6a8-160c-9872-8929d92be3a3` succeeded.

- Exactly one demographics record and one distinct HbA1c value per participant
  in both staged source CSV and Bronze.
- Target values agree exactly from source to Bronze and Silver for all 16.
- Source-derived study labels agree with Silver and saved training labels for
  all 15 included people; each saved participant has one label.
- All 15 included participants pass the existing subject-summary eligibility
  policy and retain a total of 660 accepted rolling windows.
- Participant 015 remains excluded, fails subject-summary eligibility and has
  no saved training windows. No exclusion was changed based on model errors.

The three particularly difficult temperature-only participants have no label
mapping mismatch or eligibility failure under these checks:

| Participant | Accepted windows | Usable / observed minutes | Usable fraction of observed | Elapsed span (minutes) |
| --- | ---: | ---: | ---: | ---: |
| 002 | 56 | 10,492 / 10,506 | 99.87% | 11,726 |
| 011 | 6 | 11,009 / 11,031 | 99.80% | 14,508 |
| 014 | 18 | 7,872 / 7,881 | 99.89% | 9,502 |

Usable fraction of observed is not coverage of elapsed time. Gaps are absent
from its denominator. Accepted windows still pass the separate 24-hour total
and hourly gates. These findings do not establish independent clinical truth
of the original labels or sensor calibration, only faithful label propagation
and eligibility under the existing contract. There is no justified label
correction, error-selected exclusion or relaxed coverage policy here.

## Additional-cohort investigation

This is a targeted search, not proof that no suitable dataset exists. No
external dataset has been downloaded or approved for inclusion.

| Source | Verified evidence | Suitability / remaining work |
| --- | --- | --- |
| [BIG IDEAs v1.1.3](https://physionet.org/content/big-ideas-glycemic-wearable/1.1.3/) | Current public page lists the same 001–016 participant folders and HbA1c demographics | Version changes are not new people; the approved current training roster already uses 15 of these 16 |
| [AI-READI v3 documentation](https://docs.aireadi.org/) | Describes 2,280 participants and a multimodal dataset | Potential independent research cohort, but compatibility with this wrist-temperature classifier is not established |
| [AI-READI data domains](https://docs.aireadi.org/docs/3/dataset/data-domain) and [wearable documentation](https://docs.aireadi.org/docs/3/dataset/wearable-activity-monitor/) | HbA1c is documented; listed activity variables include HR/SpO2, while temperature is listed under environmental sensors | Ambient temperature must not be substituted for wrist skin temperature. Verify the actual release manifest/sensor channels before proposing any ingestion or a different model contract |
| [22-person prediabetes study](https://arxiv.org/html/2410.02692v1) | Uses CGM and smartwatch acceleration; labels combine FPG, OGTT and HbA1c; classifiers use glucose-derived features | Different input/target task; not a verified drop-in temperature cohort or comparable accuracy benchmark. A compatible downloadable release and permissions were not established |

[AI-READI access](https://fairhub.io/datasets/3/access) requires institutional
CILogon, research/training information, a publicly shared research purpose,
license acceptance and Azure storage details. No account application, agreement,
storage provisioning or sharing of user details was performed. Access alone
would not solve the unresolved signal/target compatibility questions.

The [SweetDeep preprint](https://arxiv.org/html/2512.03471v1) describes a
285-person ND-versus-T2D task using ECG/PPG/BIA-derived features and demographic
information. That is not the current wrist-temperature/HbA1c-group task; its
reported patient-level accuracy cannot be imported as Gluco's score. A
compatible downloadable wrist-temperature release was not established here.

## Implication for the 70% target

The best previous descriptive development group is temperature-only at 65.33%
(#116), not a promoted model. The audit does not recover new training signal or
prove a higher accuracy. A single predeclared fixed nonlinear-temperature
comparison is recorded separately in `NONLINEAR_TEMPERATURE_PLAN.md`. Its
primary nested selection procedure and each fixed candidate must all be
reported; the best outer result must not replace the primary procedure after
viewing results. Further confidence requires new independently labeled people,
not synthetic replay or repeated windows from these same participants.
