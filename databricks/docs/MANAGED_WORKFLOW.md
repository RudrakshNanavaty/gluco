# Managed bounded workflow and device entry point

## What is connected

`managed_workflow.py` renders one Databricks job DAG:

prepare isolated history → emit one finite batch → Tiger-to-Bronze → refresh
rolling features and publish pinned scores → verify Delta/Tiger publication.

Every task depends on success of the previous task. The final task compares
exact microsecond keys, expected model, explicit expected row count and four
numeric metrics. A verification mismatch fails the job, reaching the configured
failure-email notification. No training or automatic model promotion is added.
The generated job limits concurrency to one, automatic retries to zero and run
duration to 40 minutes. Timeout is a runtime bound, not a currency cost cap.

This is a bounded replay workflow, not an endless stream. It repeats the same
immutable session/batch if rerun; it does not silently advance timestamps or
claim new measured data. A production device stream needs its own reviewed
provider mapping, rolling watermark and source contract.

## Render and deploy

First merge #165 and upload its `publication_parity.py` together with this PR's
`verify_publication` notebook and the existing notebooks into an isolated
Workspace root. Never point at older notebooks and assume new checks are active.
Use an explicit ReplayConfig JSON (fields in `replay_config.py`), with a new
session, approved fixture/model, minute-aligned times, 5/15/60 minute cadence,
and an aligned batch of at most 60 minutes. No credentials belong in that file.

```sh
python databricks/tiger/managed_workflow.py \
  --config /path/to/reviewed-replay-config.json \
  --host YOUR_TIGER_HOST --port YOUR_TIGER_PORT \
  --root /Workspace/Shared/gluco-reviewed/databricks/tiger \
  --alert-email YOUR_OPERATOR_EMAIL --expected-windows EXPECTED_COUNT \
  > /tmp/gluco-managed-job.json
```

Optionally add `--cron` with an approved Quartz expression: the renderer always
sets that schedule PAUSED. Without it the job is manual-only. Rendering performs
no upload, job creation, execution or notification. After reviewing the exact
rendered settings, create with the Databricks CLI `jobs create --json @/tmp/gluco-managed-job.json
--profile se-project-2`. Record its returned job ID. Do one bounded run and
review results before changing an approved schedule to active. Never infer
success just from successful JSON rendering.

The verification notebook uses existing secret-scope user/password keys and
certificate/hostname verification. If the Tiger CA is not in the runtime trust
store, supply a provider-authenticated CA via `--ssl-root-cert` pointing to its
cloud-readable path. Do not trust a CA merely because an unverified peer sent it.
No cloud deployment or certificate provisioning has been performed here.

Failure notification and paused schedule fields follow the
[Databricks Jobs API](https://docs.databricks.com/api/jobs/v2/create-job).
Alert recipient, frequency and compute budget remain operator-owned deployment
inputs; placeholders are not working alerts.

## Measured wearable entry point

The existing `api.py` already authenticates `/v1/events` and `/v1/events/batch`
and idempotently writes Tiger raw events. `wearable_adapter.py` accepts up to
1000 already aggregated, minute-aligned measured observations from stdin JSONL.
A provider adapter must supply pseudonymous sensor_id, timezone-aware observed_at,
provenance=`measured`, enmo_mean_g, temperature_mean_c, optional hr_mean_bpm, and
units={motion:g, temperature:degC, heart_rate:bpm}. It does not fabricate raw
samples, infer calibration, fill missing HR or label a replay as measured.

```sh
python databricks/tiger/wearable_adapter.py \
  --url https://YOUR_INGEST_SERVICE/v1/events < /path/to/measured-minutes.jsonl
# Add --send only after validation and endpoint review.
```

Supply SENSOR_INGEST_API_KEY securely in the environment. No key is printed.
HTTPS is required except loopback development; redirects are rejected to avoid
forwarding the key. A stable sensor/minute event ID makes retries duplicate-safe
under the existing API contract. Existing keys are first-write-wins; corrections
need a separately reviewed revision strategy rather than silent overwrite.
Input is fully validated before sending; on transport failure partial delivery
is possible and rerunning the same records is the recovery path.

This adapter reaches raw ingestion and the generic Bronze copy. The replay-only
feature notebook consumes the separate demo contract; it must not consume these
measured events automatically. Provider-specific sampling/calibration, identity
mapping, measured-event Silver normalization and real-session scoring/publication
need the chosen wearable contract and an actual source fixture. A local HTTP
receipt test verifies transport, not a physical wearable or live Tiger ingestion.

## Remaining activation inputs

The job is prepared as code, not deployed or scheduled. Before activation we
need the real alert destination, frequency/budget, approved cloud CA path where
needed, and reviewed notebook deployment. For physical ingestion we additionally
need the wearable/provider choice and a representative permitted export or API
connection. These missing inputs are explicit; neither live alerts nor a real
wearable feed has been claimed as completed.
