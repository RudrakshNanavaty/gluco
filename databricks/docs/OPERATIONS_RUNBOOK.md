# Databricks workflow handoff

## Distinguish the three paths

1. Study files in the source Volume feed Bronze and Silver, then past-only
   wearable features, held-out evaluation and versioned model artifacts.
2. A bounded synthetic replay sends idempotent minute events into Tiger, ingests
   them into Bronze, refreshes rolling windows/scores and publishes to Tiger.
3. FastAPI reads Tiger. Its optional `simulate_live` wrapper generates display
   readings over real history; it does not ingest measurements or refresh
   Databricks. A moving dashboard alone does not prove pipeline progress.

Never train on synthetic replay or use app simulation as model evidence.

## Before a bounded run

- Review and merge the relevant PRs; deploy from the resulting reviewed commit.
- Use an isolated session ID and a complete explicit ReplayConfig: anchor,
  prepare/start/stop instants with timezone, fixture, model pin and cadence.
  Do not reuse legacy default dates/model IDs for a new session.
- Confirm CLI identity/profile, warehouse, existing secret scope access and the
  intended read/write service roles. Never paste secret values into issues.
- Preserve the original session's expected counts. Prepare the isolated bank
  using the existing controller workflow; record the cloud run and commit.
- Run the session health command documented in SESSION_HEALTH.md (PR #120).
  A new unprepared session should fail; don't weaken assertions to hide that.

## During and after

Use the bounded controller actions rather than an unbounded background sender.
Record run IDs, terminal result, exact expected participant/window/event counts,
model pin and cursor. A snapshot can be healthy while the job is stopped; check
both. Verify the expected new cursor only follows successful refresh/publication.
Re-run session health. Use the bounded command in `PUBLICATION_PARITY.md` to compare exact dashboard
keys and numeric values between Delta and Tiger when validating publication; session health alone
queries Delta and cannot certify Tiger parity. See REPLAY_VERIFICATION_RESULTS.md
and RUNTIME_SAFETY_RESULTS.md for previously exercised procedures and limits.

On failure: stop the controller, inspect the cloud terminal state, preserve
pending batch/cursor evidence, and use explicit retry only after the old run is
terminal. `--resume-stopped` intentionally clears STOP; never clear it silently.
Do not delete events or manually advance a cursor to make a check pass.

## Recurring operation: release checklist

Before enabling a schedule, choose a responsible operator, compute/run budget,
source contract, cadence, stop/expiry policy and notification destination.
Require single active execution per session, bounded retries and an alert for
failed/expired runs and unexpected count/model changes. Keep training/model
promotion separate from refresh/publication. Test cancellation and recovery in
an isolated session. Retain run links and sanitized aggregate health reports.

No recurring schedule or physical-device integration is enabled by this PR.
Those require an agreed deployment contract and review of cloud cost and writes.
An authenticated read-only cloud check also depends on access still being valid;
a historical successful run is not a claim of current service availability.
