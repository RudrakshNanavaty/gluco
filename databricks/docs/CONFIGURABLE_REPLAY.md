# Configurable replay (development)

The controller and fast sensor sender share `replay_config.py`. New sessions
require explicit identity, model and timezone-aware schedule; old October 4
values remain only as legacy defaults. Do not reuse a published session ID.

Set these environment variables in the shell running the local controller:

```sh
export GLUCO_REPLAY_SESSION=replay-config-check-v1
export GLUCO_REPLAY_FIXTURE=overnight-v1
export GLUCO_REPLAY_MODEL_VERSION=38ec33cb326146c7991650a3164cf440
export GLUCO_REPLAY_ANCHOR='<ISO timestamp with timezone>'
export GLUCO_REPLAY_PREPARE_AT='<ISO timestamp with timezone>'
export GLUCO_REPLAY_START_AT='<ISO timestamp with timezone>'
export GLUCO_REPLAY_STOP_AT='<ISO timestamp with timezone>'
export GLUCO_REPLAY_CADENCE=5
export DATABRICKS_CLI=/path/to/databricks
export DATABRICKS_PROFILE=se-project-2
export DATABRICKS_NOTEBOOK_ROOT=/Workspace/Shared/gluco/databricks/tiger
export DATABRICKS_SECRET_SCOPE=se-project-2
export TIGER_HOST='<existing Tiger host>'
export TIGER_PORT='<existing Tiger port>'
export TIGER_DATABASE=tsdb
```

Require anchor <= prepare <= scheduled start < stop, with stop no later than
24 hours after the anchor. All real work must occur between prepare and stop.
Preparation/scoring takes time; allow an adequate execution window. Supported
analytics cadences are 5, 15 and 60 minutes. Batch size must be 1–60 minutes.
Database passwords stay in Databricks Secrets, never notebook parameters.

The model release must exist remotely. Local validation checks its format;
`demo_smoke_test` resolves it and enforces the existing per-session pin.
Before submitting, inspect the fixture, source notebook version, permissions,
and generated task plan. Do not submit placeholder deployment values.

## Bounded verification sequence

```sh
python databricks/tiger/continuous_demo.py dry-run --batch-minutes 5 --through-offset 11525
python databricks/tiger/continuous_demo.py prepare
python databricks/tiger/continuous_demo.py advance --batch-minutes 5 --through-offset 11525
python databricks/tiger/continuous_demo.py status
```

Dry-run prints the emit -> Bronze -> refresh task plan without submitting it or
creating session state. `prepare` seeds the existing fixture's eight input days
and seven days of dashboard history. `advance --through-offset 11525` processes
exactly five reserved minutes after a new session's initial cursor 11520. A retry
uses deterministic event IDs; successful batches alone advance the cursor.
Inspect output and verify counts, model pin and timestamps in both Delta and
Tiger. At 66 participants, five minutes implies 330 unique event keys. Repeating
the same completed endpoint must not create another batch. Remote duplicate
retry verification is still required even when unit tests pass.

## Isolation and stop/resume

New state/bank/lock/log files live under ignored
`databricks/local-data/replay/<session>/`. The historical session retains its
old `continuous-demo` location. Existing unversioned state can still be read
with `status` and stopped, but is not silently migrated or resumed.

Configuration is saved with state. A changed session, anchor, fixture, model,
schedule or cadence fails validation. Use a new session for changes. Keep the
same environment when resuming. `stop` leaves history, cursor and pending run
identity intact; clearing a STOP marker must be an explicit operator decision.
The controller does not automatically clear it. A failed batch retains its
pending run and does not advance the cursor; recovery requires investigating
that run rather than silently skipping it.

Existing prepared fixtures are reused. Re-registering `overnight-v1` is not
part of ordinary prepare; `GLUCO_REGISTER_FIXTURE=true` explicitly opts into the
historical registration task. Do not enable it for an unrelated fixture.

## Fast sensor path

The sender imports this same session, schedule and state directory. It checks
saved configuration and bank fixture before writing. The current exported bank
contract is still the frozen 66-person roster. Copy the matching exported bank
to the new session's `live_bank.jsonl` only after checking its fixture. No sender
is started by controller preparation or this documentation. Verify sensor
publication separately from analytics and label interpolated ticks synthetic.

## Current verification status

Local tests and a dry-run passed. Read-only cloud preflight confirmed 760,320
history-minute rows (66 x 11,520), 330 reserved rows for a five-minute batch,
one reference release, and no existing `replay-config-check-v1` session.
Full cloud replay and sensor execution remain unverified: the current account
cannot read Databricks secret scope `se-project-2`. The workspace owner must
provide READ on that existing scope or an appropriately scoped credential
mechanism before running the notebooks. No new session was published.
