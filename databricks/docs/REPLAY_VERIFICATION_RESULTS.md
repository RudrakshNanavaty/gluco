# Bounded replay verification results

## Result

The configurable controller successfully prepared and processed exactly five
reserved minutes in the new session `replay-config-check-v1`. No background
controller or one-second sensor sender was started. The existing
`continuous-oct4-v1` session and backend session setting were preserved.

## Cloud runs

- Preparation: `806445321821758`, task `305386761502672`, SUCCESS.
- Five-minute replay: `476724347443338`, all three tasks SUCCESS:
  emit `628993511306439`, Bronze `955647851361841`, refresh `716645804654344`.
- Existing model pin: `38ec33cb326146c7991650a3164cf440`.
- Fixture: `overnight-v1`, 66 participants. Analytics interval: five minutes.

## Verified checks

| Check | Observed result |
| --- | --- |
| Initial historical windows | 11,088 |
| Emitted events | 330 inserted, immediate retry inserted zero |
| Tiger raw event identities | 330 rows / 330 unique keys |
| Bronze event identities | 330 rows / 330 unique keys, 66 sensor IDs |
| Published dashboard windows | 11,154 unique participant/end-time keys, 66 participants |
| Full-window coverage | Every Tiger payload reports 1,440 minutes |
| Score bounds / model pin | All checked payloads have valid 0–100 scores and the expected release |
| Delta/Tiger key equality | Exact equality across all 11,154 windows |
| Delta/Tiger metric equality | Zero maximum difference for score, motion mean, skin-temperature mean and HR mean; nulls match |
| Saved controller cursor | Advanced from 11520 to 11525 only after successful refresh |
| Repeat completed endpoint | No new submitted run; cursor and last successful run unchanged |
| Historical session preserved | Row count, participant count, latest timestamp and ordered payload digest unchanged |

The original session had 11,088 windows / 66 participants. Comparing an ordered
MD5 digest checks equality against the pre-run snapshot, not a cryptographic
security property. Source/result rows and local verification configuration were
not committed; runtime files are in the ignored per-session directory.

## Timestamp verification detail

Initial key comparison using typed SQL Statement API timestamps flagged a
precision mismatch: the API renders timestamps to milliseconds although the
stored values retain microseconds. A diagnostic query showed both forms side
by side. Comparing `unix_micros(window_end)` to exact PostgreSQL epoch
microseconds resolved the representation issue without changing stored data
or weakening key equality. Reusable SQL is in `../sql/replay_verification.sql`.

## Remaining scope

This checks synthetic minute replay and analytics publication, not physical
sensors, a continuously running service, HTTP ingestion, or the one-second
sensor sender. This first run did not exercise remote cancellation. A later isolated test
verified bounded sensor publication and partial-batch cancellation/recovery;
see `RUNTIME_SAFETY_RESULTS.md`. No model retraining
or promotion occurred; the 60.42% development baseline is unchanged. Changes are under review in draft PR #91, stacked after #89 and #90.
