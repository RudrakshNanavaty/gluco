# Databricks status and audit history

## Current repository status — October 18, 2026

- Refreshed all remote branches; local main fast-forwarded to `38d1c50`.
  This feature branch starts from that revision. No environment/secret files
  were pulled or overwritten during the repository refresh.
- Native GitHub stack #104 is fully merged: #89 (tests/CI), #90 (coverage and
  robust-feature study), #91 (configurable replay/recovery), #100 (regularization
  experiment). There are no pending prerequisite merges in that stack.
- Issues #85, #86 and #87 are closed. The final #88 provenance investigation
  is now complete: the exact three incomplete minutes have no temperature
  samples in source CSVs or Bronze, and small valid ACC tails are preserved
  by the full outer join. All three fail the unchanged training prefilter.
  See `INCOMPLETE_MINUTE_FINDINGS.md`; documentation review is pending.
- All 65 Databricks tests pass on refreshed main. Main CI run `39157694766`
  passed backend, frontend and Databricks. Historical test counts below refer
  to their original implementation points.
- Reference model accuracy is 60.42%; the 62.11% regularization result is
  reused-cohort development evidence, not a promoted or independently validated
  model. No candidate model artifact or application pin was changed.
- Bounded cloud replay, exact Delta/Tiger parity, five sensor ticks and canceled
  batch recovery were verified in separate sessions (see the linked result
  documents). This repository refresh did not rerun those cloud experiments,
  restart application services, or verify a currently running sensor feed.
- GitHub issue/PR descriptions have been reconciled with merged/closed state;
  old progress comments are marked as historical. Local environment settings
  and Clerk sign-in remain separate from this pipeline audit.

## Reading the history

The sections below are dated progress snapshots. Earlier statements such as
“next work,” “not reconstructed,” or hardcoded replay refer to the state at
that point, not current outstanding work. Later findings and the snapshot
above supersede them. See `ACCURACY_EXPERIMENT_RESULTS.md`,
`REPLAY_VERIFICATION_RESULTS.md` and `RUNTIME_SAFETY_RESULTS.md` for evidence.

## Baseline audit — October 17, 2026

Verified on 2026-10-17 through the Databricks CLI/SQL Statement API and a
read-only Tiger PostgreSQL connection. No training, ingestion, replay, or
publication job was started. SELECT queries used the existing SQL warehouse.

## Verified baseline

- Workspace code: `/Shared/gluco`.
- Lakeflow pipeline: `Gluco2026` (`be535e7b-53d0-49c2-8ef2-f71f7810365f`).
  Its latest inspected update completed; pipeline was idle.
- Session: `continuous-oct4-v1`.
- Databricks `workspace.gluco_demo.dashboard_windows`: 11,088 rows, 11,088 unique
  participant/time keys, 66 participants, no missing or out-of-range scores.
- Demo synthetic fractions range from 0 to 1. No dashboard row is marked
  `training_eligible`.
- Tiger `gold.dashboard_windows`: matching session count (11,088), participant
  count (66), and model version. This is aggregate agreement, not row-by-row
  equivalence.
- Published history ends at `2026-10-04T11:00:00Z`. Publication timestamps are
  separate from these simulated event times.
- Session model: `38ec33cb326146c7991650a3164cf440`, feature contract
  `wearable-24h-v1`. The pinned release resolves to an existing release record.
- Model artifact location recorded by the release:
  `/Volumes/workspace/gluco_models/artifacts/38ec33cb326146c7991650a3164cf440/rolling_risk.joblib`.
  Artifact directories were listed; model deserialization was not performed.

## Real minute data

`workspace.gluco_silver.shared_sensor_minute_pilot`:

| Dataset | Participants | Rows | Unique participant/minute keys | Missing motion or temperature |
| --- | ---: | ---: | ---: | ---: |
| BIG IDEAs | 16 | 155,116 | 155,116 | 3 |
| IMU50 | 1 | 6,777 | 6,777 | 0 |

The 66-person demo roster does not mean all 66 participants' raw data passed
through this Silver table. Prepared replay inputs are a separate path.
Missing minute values require checking downstream quality-gate behavior before
assuming they are defects or filling them.

## Gaps and next work

1. Add focused local tests for `rolling_risk.py`: past-only window boundaries,
   missing-data coverage gates, duplicate minute rejection, feature consistency,
   and score/model contract validation. Include them in CI.
2. Inspect provenance and coverage for the prepared 66-person fixture. Preserve
   the separation between real research data and synthetic replay.
3. Make replay reusable: `continuous_demo.py` still hardcodes October 4 dates and
   an older model release. Build configurable runs with a new session; retain
   existing model pins and history.
4. Reconcile deployment examples with the verified release. Some committed run
   JSON files contain placeholder hosts or historical model IDs. Do not submit
   them unchanged.
5. Validate a bounded replay in a new session, including event retry idempotency,
   Bronze ingestion, score publication, and aggregate/row-level Tiger agreement.
6. Verify the fast sensor path separately. Tiger `gold.dashboard_live` returned
   66 rows but no non-null `sensor_published_at` values for the current session.
   Existing analytics do not establish a running sensor feed.

Clerk sign-in is a separate application concern and does not block this work.
Credentials remain in ignored local configuration or managed secrets, never here.


## Coverage follow-up

Read-only SQL in `databricks/sql/coverage_audit.sql` verified:

- BIG IDEAs: 153,400 / 155,116 minutes pass the training sample-ratio prefilter.
  All three incomplete minutes fail that prefilter. No minute reports source
  parse errors. The actual 24-hour acceptance gate still applies afterward.
- IMU50: 6,772 / 6,777 minutes pass the same sample-ratio check, with no
  incomplete minutes or reported parse errors. This does not make IMU50 labeled
  training data.
- Current release training windows: class 0 has 7 people / 401 windows (18–112
  per person); class 1 has 8 people / 259 windows (6–69 per person).
- Total accepted training windows: 660 across 15 people. Window counts are not
  balanced even though participant counts are similar. Preserve equal total
  participant weights and participant-held-out evaluation.
- Candidate-window rejection counts have not yet been reconstructed. Passing
  the minute prefilter alone does not establish 24-hour window eligibility.

## Reconstructed 24-hour window rejection audit

`databricks/sql/window_rejection_audit.sql` reconstructs the training script's
15-person roster, sample-ratio prefilter, hourly candidate ends and past-only
24-hour bounds. It then applies the same count/nonfinite/hourly-bin gates and
compares accepted participant/end-time keys with the saved release.

Verified against the existing warehouse:

- 2,653 candidate windows; 660 accepted (24.9%).
- 734 rejected for fewer than 1,152 observations (80% of 24 hours).
- A further 1,259 rejected for an hourly coverage gap: fewer than 30 observations
  in an hour or an absent hour, despite passing the total-observation gate.
- No additional nonfinite-input rejections after the minute prefilter.
- Zero accepted-key differences versus the saved release, across all 15 people.

Rejection categories follow code precedence and are mutually exclusive, not
independent counts of every failed condition. Initial warmup time before the
first candidate is not counted as a rejected window. These results describe
availability of already-prefiltered minutes, not raw device missingness alone.

The next investigation should separate elapsed gaps from minutes lost to the
sample-ratio prefilter and measure consecutive gaps by participant. Preserve
existing coverage thresholds for the baseline. Any proposed alternative must
be evaluated inside a participant-held-out experiment rather than chosen simply
to maximize accepted windows or performance on reused held-out results.

## Gap attribution and filter-loss diagnostic

`minute_gap_audit.sql` uses a complete minute grid between each approved
participant's first and last sample-ratio-passing minute. Across those spans:

- 180,885 elapsed minute positions = 149,076 passing + 31,599 absent Silver
  minutes + 210 present-but-filtered minutes.
- 99.34% of non-passing minute positions are absent Silver rows. This is a
  Silver availability finding, not proof of a physical device failure. Source
  acquisition/processing provenance would be needed to assign a root cause.
- Longest combined gap is 3,340 minutes (55.7 hours); the longest contiguous
  present-but-filtered run is two minutes.
- The lowest accepted-window contributors include participant 011 (6/218),
  participant 003 (9/161), and participant 006 (16/216). Participant 013 has
  18/179 despite only 518 absent and 17 filtered minutes, illustrating how
  overlapping windows and a strict hourly gate amplify short gaps.

`filter_loss_upper_bound.sql` reruns the original candidate ends with all
available finite Silver measurements, ignoring sample ratios for diagnosis
only. It preserves the 80% total and 30-per-hour gates:

- 727 candidate windows pass versus 660 currently (+67; 27.4% vs 24.9%).
- Gains occur in participants 003 (+1), 005 (+22), 007 (+22), and 014 (+22).
- 1,926 candidates still fail even under that diagnostic policy.
- Missing/nonfinite values remain excluded. This is an upper bound on retention
  from restoring finite filtered minutes at the same candidate endpoints, not
  an approved training policy or estimated accuracy improvement.

## Decision

Keep existing eligibility thresholds and the 660-window reference set for the
first feature/model comparison. Filter loosening does not address most lost
minute positions and changes the evaluated sample. Prioritize a controlled
feature comparison plus source-provenance follow-up, preserving participant
weighting and nested participant splits. See `MODEL_EXPERIMENT_PLAN.md`.

## Controlled robust-feature experiment completed

The separate development evaluator reproduced the original 660 keys and baseline
predictions, then compared the predeclared extension. Accuracy was 54.37% for
extended features and 59.31% for joint family/model selection, below 60.42% for
the reference. Probability losses also worsened. No promotion occurred. See
`ROBUST_FEATURE_RESULTS.md` for run references, all metrics and limitations.

## Source-gap follow-up completed

Direct scans of three staged temperature CSVs (participants 004, 006, 011)
confirm the selected largest gaps already exist in the staged source inputs.
Source and Bronze temperature row counts and nearest gap boundaries match;
all parsed timestamps are valid. Bronze ACC is also absent inside these gaps.
Large ACC source CSVs were not rescanned. See `SOURCE_GAP_FINDINGS.md` for scope,
limits and the reproducible read-only SQL query. No ETL repair is indicated by
these three checks; underlying acquisition/source provenance remains unknown.


## Configurable replay implementation

The feature-branch controller now accepts explicit session/schedule/model/fixture
configuration through `replay_config.py`, isolates per-session runtime files,
validates immutable saved configuration, propagates connection metadata to all
phases, and supports a bounded `--through-offset`. Fast sensor scheduling shares
that configuration and validates the bank fixture. Legacy unversioned state is
not silently resumed. Local suite: 50 passing tests; targeted lint passed.

Read-only preflight confirmed the intended 66-person fixture and model are ready
for a five-minute new-session run. The live smoke test is blocked by lack of
READ access to secret scope `se-project-2`; no session was created or published.
See `CONFIGURABLE_REPLAY.md` for exact setup, bounded commands and limitations.


## Replay cloud verification completed

After secret-scope access was granted, configurable replay preparation and the
five-minute batch succeeded in isolated session `replay-config-check-v1`.
330 events were inserted; immediate retry inserted zero. Delta and Tiger have
11,154 matching window keys and exactly matching checked metrics. Repeating the
completed endpoint submitted no new run. The original session's ordered payload
digest/counts/latest time remained unchanged. See `REPLAY_VERIFICATION_RESULTS.md`.
The one-second sensor sender and live in-flight cancellation were not exercised.


## Runtime safety follow-up

A separate session `replay-runtime-safety-v1` passed five bounded synthetic
sensor ticks (66 timestamped rows, 50 missing HR values, no minute emissions),
then a cancellation test after Bronze commit and before refresh. The cursor
and 11,088 seeded windows were retained. Explicit retry recovered to 11,154
windows / 330 unique events with no duplicate inserts and no changes to the
original session. Local tests: 58 passed. See `RUNTIME_SAFETY_RESULTS.md`.

## Accuracy development follow-up (October 18, 2026)

A predeclared regularization/threshold comparison reproduced the original
baseline exactly on the same 660 windows / 15 participants. Adding strongly
regularized logistic candidates improved participant-weighted accuracy from
60.42% to 62.11%; inner threshold tuning reduced accuracy to 57.93%. This is
reused-cohort development evidence only. No model or session was promoted.
See [plan](ACCURACY_EXPERIMENT_PLAN.md) and
[full results](ACCURACY_EXPERIMENT_RESULTS.md), including paired participant
outcomes and the independent-validation requirement.

## Exact incomplete-minute follow-up — October 18, 2026

Read-only statements identified the three rows as participants 012/013/016,
each with a short accelerometer tail extending into a minute without any
source temperature samples. Direct staged temperature reads and Bronze agree
on counts and boundary timestamps, with zero temperature rows in those
minutes. Silver's full outer join preserves these partial minutes correctly;
the training prefilter rejects all three. This resolves the specific data-path
question in #88 without explaining the physical recording pauses or changing
any processing/model policy. See `INCOMPLETE_MINUTE_FINDINGS.md` for exact keys,
counts, query identifiers and limitations.
