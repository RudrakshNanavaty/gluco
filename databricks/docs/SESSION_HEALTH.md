# Repeatable Databricks replay-session health check

`databricks/tiger/session_health.py` turns the manual Databricks snapshot checks
into a read-only JSON report and process exit code. It uses the existing
Databricks CLI profile and SQL warehouse, requires only Python's standard
library, and does not read Tiger passwords or connect directly to PostgreSQL.

## Run

From the repository root with the Databricks CLI on PATH:

```sh
python3 databricks/tiger/session_health.py \
  --session continuous-oct4-v1 \
  --warehouse a75228c068d4e415 \
  --profile se-project-2 \
  --expected-participants 66 \
  --expected-windows 11088 \
  --expected-bronze-events 0 \
  --expected-model 38ec33cb326146c7991650a3164cf440
```

Use `--cli /absolute/path/to/databricks` when it is not on PATH.
Use `--wait-seconds 120` for a warehouse that needs more time to start. The
polling limit defaults to 60 seconds (allowed 1–300); each CLI request also has
a 30-second timeout. If the polling limit expires, the tool requests cancellation
of its own statement. Operational errors produce sanitized error codes, without
printing CLI stderr, authentication details or cloud error bodies.

For the previously completed recovery session:

```sh
python3 databricks/tiger/session_health.py \
  --session replay-runtime-safety-v1 \
  --warehouse a75228c068d4e415 \
  --expected-participants 66 \
  --expected-windows 11154 \
  --expected-bronze-events 330 \
  --expected-model 38ec33cb326146c7991650a3164cf440
```

These expected counts describe the recorded test sessions. Intentional changes
should use the new agreed session contract, rather than updating expectations
just to suppress an unexplained failure.

## Checks and exit codes

- **0 / pass:** all requested snapshot contracts pass.
- **1 / fail:** the query succeeded, but data-contract checks failed. The report
  lists every failure code and the underlying aggregates.
- **2 / error:** the CLI/API operation, response shape or aggregate parsing failed;
  no healthy result is asserted. Argument errors also exit 2.

Checks include nonempty session, unique dashboard and Bronze keys, complete
participant roster at each stored window end, finite/in-range scores and core
features, 24-hour windows, demo-only/nontraining flags, valid synthetic fractions,
exact dashboard/pinned-score agreement, exactly one session model pin and release,
expected feature contract and artifact-path metadata. Optional expected counts
and model version enforce a known roster/history/ingestion target.

The SQL uses a bound session parameter and only reads fixed Gluco tables.
Invalid session/warehouse identifiers are rejected before network calls.
The report contains aggregates and model metadata, not source sensor samples.
The matching release's artifact path is checked; its contents are not downloaded
or deserialized by this tool.

## Interpretation and limits

A historical session ending October 4 is not failed merely because wall-clock
time is later. The report labels historical event time separately from actual
publication freshness; it does not claim an active feed. An original seeded
history can have zero Bronze events, while a newly emitted replay can have 330.
Supply `--expected-bronze-events` when verifying a known ingestion contract.

A completely missing time interval shared by every participant cannot be
identified from roster consistency alone. Supply the agreed expected window
count to detect that loss. Without expected participant counts, an entirely
missing participant is likewise not necessarily detected if every remaining
window has the same reduced roster. A matching count does not establish an
arbitrary temporal range/cadence; exact temporal expectations require a separate
key comparison.

This is a Databricks data snapshot, not Tiger row parity, live-sensor freshness,
job/pipeline lifecycle health, physical-device ingestion, model validation, or
an indefinitely running service test. No scheduling or background process is
created. The existing bounded cross-system and runtime evidence remains in
`REPLAY_VERIFICATION_RESULTS.md` and `RUNTIME_SAFETY_RESULTS.md`.

## Verified October 18, 2026

| Session | Outcome | Windows / unique keys | Participants | Bronze events / unique keys |
| --- | --- | ---: | ---: | ---: |
| continuous-oct4-v1 | pass | 11,088 / 11,088 | 66 | 0 / 0 |
| replay-runtime-safety-v1 | pass | 11,154 / 11,154 | 66 | 330 / 330 |
| health-check-missing-session-v1 (deliberately nonexistent) | fail | 0 / 0 | 0 | 0 / 0 |

Statement IDs respectively: `01f1cb6e-9686-1ebf-b1cf-420a57f29891`,
`01f1cb6e-9863-1a87-9996-27be7cbccd2b`,
`01f1cb6e-9a88-1a82-843e-17e32f3c152f`.

Known-session checks found zero invalid keys/scores/features/window lengths,
unsafe demo flags, invalid synthetic fractions or score-sync issues. Both pin
the original release `38ec33cb326146c7991650a3164cf440`. Deliberately incorrect
window/event expectations also failed in offline evaluation of the live result.
No tables, session state, secrets, pins, application settings or model artifacts
were changed. No query-result/data files are committed.

The branch's local suite has 88 passing tests: 65 main tests plus 23 health-check
cases. Pending model-study PRs have their own additional tests. New checks cover
invariant failures, empty/malformed responses, bound session parameters, pending
polling, timeout cancellation, truncation, sanitized cloud errors and CLI option
propagation. Ruff checks and formatting pass for the new Python files.

## Optional completed-job and freshness checks

Add `--run-id RUN_ID --expected-job-id JOB_ID` to check a particular run alongside
session data. Both IDs are required together. Only `TERMINATED` / `SUCCESS`
passes; active, failed, canceled and missing-end-time runs fail. Optional
`--max-run-age-hours HOURS` rejects completion times in the future or older than
the explicit limit. It uses job completion time, not historical sensor time.

This is a one-shot check. A scheduler may invoke it and alert on nonzero status;
this tool does not create a recurring job, pick a budget or send notifications.
The operator must record which run belongs to which session: the Jobs API
identity check does not establish publication lineage. A selected old successful
run does not rule out later failures. Existing snapshot-only commands retain
their behavior. Cloud error messages, task parameters and authentication details
are not printed.
