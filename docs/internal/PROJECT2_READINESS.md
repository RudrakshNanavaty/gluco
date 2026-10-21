# Internal readiness audit — not the submission assessment

Maintainer-facing working notes. This file is public in the repository;
“internal” describes its audience, not confidentiality. The historical scores
below help prioritize work and are not the final team submission.

# Historical progress snapshot — October 21, 2026

Baseline: merged main `3dc7044`. These are provisional team-review scores, not
an official mark. Score only evidence that a tutor can open. This draft does
not count its own unmerged improvements, human rehearsals or unseen media.
The team should review every score before adding this table to the submission.

[Official rubric](https://github.com/txt/se26f/blob/main/docs/submit/2/proj2.md).
Each row uses the assignment's 0–3 scale. No official linear conversion of this
96-point checklist to the 8 repository marks is assumed.

| Area | Criterion | Provisional /3 | Evidence | Limitation / next action |
|---|---|---:|---|---|
| Team | Commit history | 3 | [Open](https://github.com/RudrakshNanavaty/gluco/graphs/contributors) | Substantial merged history |
| Team | Multiple contributors | 3 | [Open](https://github.com/RudrakshNanavaty/gluco/graphs/contributors) | Four contributors visible |
| Team | Distributed contribution | 3 | [Open](https://github.com/RudrakshNanavaty/gluco/graphs/contributors) | Meaningful contributions across the team |
| Team | Cross-component work | 3 | [Open](https://github.com/RudrakshNanavaty/gluco/commits/main) | Contributors span multiple directories |
| Team | Frequent integration | 3 | [Open](https://github.com/RudrakshNanavaty/gluco/pulls?q=is%3Apr+is%3Amerged) | Small changes merged regularly |
| Team | Shared tools | 2 | [Open](https://github.com/RudrakshNanavaty/gluco/blob/3dc7044/CONTRIBUTING.md) | Shared configuration; universal use needs human evidence |
| Team | Everyone can run it | 0 | [Open](https://github.com/RudrakshNanavaty/gluco/issues/169) | Unverified; four personal rehearsals remain unchecked |
| Issues | Issue volume | 3 | [Open](https://github.com/RudrakshNanavaty/gluco/issues?q=is%3Aissue) | Substantial issue history |
| Issues | Resolved issues | 3 | [Open](https://github.com/RudrakshNanavaty/gluco/issues?q=is%3Aissue+is%3Aclosed) | Resolved work visible |
| Issues | Discussion before closure | 2 | [Open](https://github.com/RudrakshNanavaty/gluco/issues?q=is%3Aissue+comments%3A%3E0) | Discussion exists, uneven detail |
| Issues | Failure-oriented work | 2 | [Open](https://github.com/RudrakshNanavaty/gluco/issues/153) | Auth, retry, timeout and error-handling work |
| Issues | Team discussion channel/QR | 0 | [Open](https://github.com/RudrakshNanavaty/gluco/issues/169) | External evidence not supplied |
| Tests | Expected and failure cases | 3 | [Open](https://github.com/RudrakshNanavaty/gluco/actions/runs/39652253677) | Passing unit and live contract checks |
| Tests | Test-code share | 2 | [Open](https://github.com/RudrakshNanavaty/gluco/tree/3dc7044/back-end/tests) | Substantial tests; avoid an unsupported precise ratio |
| Tests | Automated runs | 3 | [Open](https://github.com/RudrakshNanavaty/gluco/blob/3dc7044/.github/workflows/test-suite.yaml) | Main, PR and branch-push automation |
| Tests | Measured coverage/badge | 3 | [Open](https://github.com/RudrakshNanavaty/gluco/tree/coverage-badges) | Live measured endpoints with run/commit provenance |
| Docs | Generated reference | 2 | [Open](https://github.com/RudrakshNanavaty/gluco/blob/3dc7044/docs/reference/README.md) | Generated and stale-checked; descriptions remain uneven |
| Docs | Class/function descriptions | 2 | [Open](https://github.com/RudrakshNanavaty/gluco/blob/3dc7044/docs/reference/back-end.md) | Reference exists; some entries lack descriptions |
| Docs | Worked tutorials | 2 | [Open](https://github.com/RudrakshNanavaty/gluco/blob/3dc7044/INSTALL.md) | Setup and pipeline guides, more worked use cases possible |
| Docs | Product motivation | 3 | [Open](https://github.com/RudrakshNanavaty/gluco/blob/3dc7044/README.md) | Audience, architecture and scientific boundaries explained |
| Docs | Teaser video | 0 | [Open](https://github.com/RudrakshNanavaty/gluco/pull/186) | Link proposed but not merged/verified at baseline |
| Docs | Feature walkthrough | 0 | [Open](https://github.com/RudrakshNanavaty/gluco/blob/3dc7044/README.md) | No linked walkthrough verified |
| Files | README evidence badges | 2 | [Open](https://github.com/RudrakshNanavaty/gluco/blob/3dc7044/README.md) | Coverage/build evidence; full requested set unfinished |
| Files | Ignore rules | 3 | [Open](https://github.com/RudrakshNanavaty/gluco/blob/3dc7044/.gitignore) | Credentials/runtime/data artifacts excluded |
| Files | Installation guide | 3 | [Open](https://github.com/RudrakshNanavaty/gluco/blob/3dc7044/INSTALL.md) | Dedicated detailed guide |
| Files | License | 3 | [Open](https://github.com/RudrakshNanavaty/gluco/blob/3dc7044/LICENSE) | AGPL license present; extension is immaterial |
| Files | Conduct policy | 3 | [Open](https://github.com/RudrakshNanavaty/gluco/blob/3dc7044/CODE_OF_CONDUCT.md) | Dedicated policy present |
| Files | Contribution guide | 3 | [Open](https://github.com/RudrakshNanavaty/gluco/blob/3dc7044/CONTRIBUTING.md) | Branch/review/testing instructions present |
| Files | Quality configs/status | 2 | [Open](https://github.com/RudrakshNanavaty/gluco/blob/3dc7044/.github/workflows/test-suite.yaml) | Tools run; current individual badges are static labels |
| Files | Project DOI | 0 | [Open](https://github.com/RudrakshNanavaty/gluco/blob/3dc7044/README.md) | Dataset DOIs are not Gluco release registration |
| Files | Dependency licenses | 3 | [Open](https://github.com/RudrakshNanavaty/gluco/blob/3dc7044/docs/dependencies/README.md) | Resolved inventory generated and checked |
| Files | AI disclosure/human review | 2 | [Open](https://github.com/RudrakshNanavaty/gluco/blob/3dc7044/README.md#ai-use-and-attribution) | Disclosure/configs/reviews exist; retain traceable human checking |

**Total: 71/96.** Team17/21; issues10/15; tests11/12; docs9/18; files24/30.
Zeros for unseen evidence mean unverified, not proof that the team did no work.

## Items requiring real team actions

- [ ] All four operators and actual witnesses complete issue #169.
- [ ] Review/merge the existing teaser proposal #186 and verify public access,
      duration and placement; do not create competing duplicate teaser work.
- [ ] Record/link the walkthrough and rehearse the live fallback.
- [ ] Supply the actual poster and active discussion-channel QR evidence.
- [ ] Register the team's reviewed software release with Zenodo and verify DOI.
- [ ] Agree final scores, replace any weak evidence links and sum again.
- [ ] Include poster, repository URL and reviewed assessment in the required PDF;
      upload poster to the designated shared folder as well.

The overall 19-point grade also depends on demo, milestones and poster. This
repository checklist alone cannot determine that grade. Model accuracy below
70% is reported honestly; M0 evidence and the recorded decision are separate
from whether the research hypothesis succeeded.
