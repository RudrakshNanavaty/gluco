# Databricks baseline audit

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

Suggested commit for this document:
`docs(databricks): record verified pipeline baseline and remaining gaps`

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
