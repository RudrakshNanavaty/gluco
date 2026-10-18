# Bounded sensor and cloud cancellation/recovery verification

## Scope

Both checks used isolated synthetic session `replay-runtime-safety-v1`, the
existing `overnight-v1` fixture and pinned model
`38ec33cb326146c7991650a3164cf440`. No background sender was left running. No
production session configuration, raw study source or model release changed.

Preparation/export run `624617062887182` completed successfully. Its bank export
was written to a separate runtime-test directory in the source-files Volume,
then downloaded to the ignored local session directory. No study data or runtime
bank is committed.

## Sensor publication

`fast_sensor.py --max-ticks 5 --snapshots-only --skip-bootstrap` exited normally
with exactly five successful writes and status `stopped` (about 6.2 seconds
including startup). The joined `gold.dashboard_live` view exposed:

- 66 rows, all with sensor publication timestamps.
- 66 explicitly synthetic snapshot payloads.
- 50 unavailable HR values, preserving IMU50 missingness.
- Zero canonical minute events from this snapshots-only run.

The sender performed no schema creation, view replacement or grants in this
mode. Interpolation semantics and missingness are also tested locally. This is
bounded publication verification, not evidence of an indefinitely running feed
or measured one-second physiological samples.

## Cancellation after partial processing

Test run `1092585675444724` inserted all 330 events and ingested them into Bronze.
A test-only read-only delay task sat between ingestion and refresh. Once that
task was running, `stop` canceled the cloud run. The delay was canceled and
refresh skipped; emit and Bronze had already succeeded.

Verified before recovery:

- Cloud result CANCELED, with refresh not published.
- Cursor remained 11520 and pending run identity was retained.
- STOP marker persisted; stored status was `stop_requested`.
- Tiger history remained at the seeded 11,088 windows.
- A retry without explicit STOP clearance failed and preserved the marker.

## Explicit recovery

`retry --resume-stopped` verified the prior run was terminal, cleared STOP under
explicit operator control, archived that run identity and resubmitted the same
11520–11525 batch. Recovery run `604495051079293` succeeded.

- Re-emission inserted zero additional events; its duplicate retry inserted zero.
- Raw event count stayed at 330 with 330 unique keys.
- Published windows became 11,154 across 66 participants.
- Cursor advanced to 11525 only after successful refresh; pending state cleared.
- The original session's count and ordered payload digest remained unchanged.

The local suite has 58 passing checks. The new retry operation rejects active
runs and preserves old pending state if a new submission fails. It does not
silently clear STOP, change model pins, or skip an unsuccessful batch.

## Limits

The cancellation target was a deliberately controlled boundary after ingestion,
not every possible mid-transaction failure or machine crash. The sensor test
used snapshots-only mode, leaving canonical minute emission to the separately
verified replay controller. HTTP/device ingestion and a continuously running
service are outside this verification. Model accuracy remains 60.42% on the
existing reused development cohort.
