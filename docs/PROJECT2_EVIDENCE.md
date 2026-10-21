# Project 2: milestone evidence and submission checklist

Evidence baseline: merged commit [`3dc7044`](https://github.com/RudrakshNanavaty/gluco/tree/3dc7044), reviewed October 21, 2026. This is a team preparation aid, not an awarded grade or evidence that everyone has rehearsed. Recheck the final submission commit and link the actual passing CI run before submitting.

## Four proposed delivered milestones

The team should agree these boundaries and be able to demonstrate each. Relative evidence links resolve to the same revision as this document; use the baseline commit above when reviewing historical evidence.

| Milestone | Result and evidence | Boundary to explain |
|---|---|---|
| **M0 — falsifiable wearable-model evaluation** | [Runnable hypothesis and evaluation](../databricks/docs/M0_EVALUATION.md), [CI wiring](../.github/workflows/test-suite.yaml), [real experiment ledger](../databricks/docs/MODEL_EXPERIMENT_LEDGER.md). Offline CI requires accuracy ≥70% and gain ≥10 percentage points over baseline; the no-signal control must fail. | Synthetic CI validates the instrument. The real published baseline is 60.4153%; best observed development result is 66.8583% on 15 people. The real target remains unmet; no experimental model was promoted. See the investigation and decision in [#117](https://github.com/RudrakshNanavaty/gluco/issues/117). |
| **M1 — reproducible analytics and publication** | [Data contracts](../databricks/DATA_FLOW.md), [publication parity and receipts](../databricks/docs/PUBLICATION_PARITY.md), [managed workflow](../databricks/docs/MANAGED_WORKFLOW.md). Bronze → Silver → rolling features → pinned scores → Gold/Tiger feeds the read-only API. | Historical parity is verified. The prepared job is not an activated recurring deployment. Alert delivery and current freshness require deployment evidence. |
| **M2 — role-aware application and grounded explanations** | [Product and architecture](../README.md), [API reference](reference/http-api.md), [patient-scope and failure tests](../back-end/tests/test_widgets.py). Demonstrate patient/clinician views, one factual chat question and an access-denied case. | Use approved accounts and state the data mode. Chat requires a working provider. Tests do not prove every teammate can sign in. Research context is not diagnosis or glucose measurement. |
| **M3 — replay recovery and engineering reproducibility** | [Retry/cancellation evidence](../databricks/docs/RUNTIME_SAFETY_RESULTS.md), [health checks](../databricks/docs/SESSION_HEALTH.md), [coverage method](COVERAGE.md), [installation](../INSTALL.md), [rehearsal procedure](TEAM_REHEARSAL.md). | Replay is synthetic/historical, not a physical-device feed. Coverage includes unexecuted code and is neither model accuracy nor uptime. |

## Four proposed future milestones

These are next-phase proposals, not completed features or promises of clinical validity.

1. **Activate an observable bounded workflow.** Agree operator, alert recipient, compute budget, schedule and trusted connection configuration. Deploy reviewed notebooks, verify an isolated session, demonstrate an intentional failure alert and record activation settings. Repeating one fixed replay batch does not create new measurements.
2. **Connect one real wearable end to end.** Obtain a permitted representative fixture; document units, calibration, timestamps and identity mapping. Add measured-event Silver normalization and real-session feature/scoring publication. Acceptance: measured input reaches the dashboard with provenance and duplicate-safe retries. The HTTP adapter alone does not complete this path.
3. **Validate on independent participants.** Establish compatible permitted data; predeclare labels, participant separation, baseline and metrics before fitting. Report uncertainty and failures, and apply the [promotion checklist](../databricks/docs/MODEL_PROMOTION_CHECKLIST.md). Retain the current release if acceptance conditions fail.
4. **Strengthen reproducibility and user evidence.** Complete witnessed installations for every member, observe documented user tasks and failure cases, and prioritize meaningful tests for critical uncovered paths. Repeat checks and publish traceable documentation on the final release commit.

## Shared submission checklist

Use the [official assignment](https://github.com/txt/se26f/blob/main/docs/submit/2/proj2.md) for authoritative requirements and upload locations. Keep boxes empty until the evidence exists.

- [ ] Agree the four delivered milestones and verify their demonstrations.
- [ ] Record final merged commit and passing CI run; refresh evidence as necessary.
- [ ] Every teammate completes their own witnessed [rehearsal record](rehearsal/EVIDENCE_TEMPLATE.md); track actual outcomes in [#169](https://github.com/RudrakshNanavaty/gluco/issues/169).
- [ ] Finish and prominently link the 12–30 second teaser. An open PR or script is not a completed video.
- [ ] Finish and link the 2–5 minute walkthrough; keep the application ready for a live demonstration.
- [ ] Finish and visually verify the poster PDF, including delivered work, four future milestones, project value and discussion-channel QR/link.
- [ ] Register and link Gluco's release DOI; a dataset DOI does not identify this project.
- [ ] Complete one shared repository self-assessment, with 0–3 per row, direct evidence and an honest total; explicitly mark unverified items.
- [ ] Prepare the shared submission PDF with poster, repository URL and self-assessment; upload to required course locations.
- [ ] Each person completes the separately requested individual group-work questionnaire.

This checklist does not assert completed videos, poster, DOI, team signatures, human reviews or uploads. The relevant owners must complete and verify those actions.
