# Read-only Delta–Tiger publication verification

A successful cloud run and valid Delta tables do not establish that the app's
Tiger dashboard rows match. `tiger/publication_parity.py` checks that boundary.

From the repo root, use the existing Databricks CLI login and a PostgreSQL
connection supplied securely through the `GLUCO_TIGER_CONNINFO` environment
variable. Do not paste credentials into shell history, issues, or this document.
The tool does not load or overwrite environment files.

```sh
uv run --python 3.12 --no-project \
  --with-requirements databricks/requirements-parity.txt \
  python databricks/tiger/publication_parity.py \
  --session continuous-oct4-v1 \
  --warehouse a75228c068d4e415 \
  --expected-windows 11088 \
  --expected-model 38ec33cb326146c7991650a3164cf440
```

Use `--cli /absolute/path/to/databricks` and `--profile` when needed. Keep the
existing connection's TLS configuration; this tool does not disable certificate
verification or establish a new trust configuration. Supply a read-only account.
The transaction also enforces read-only execution, 30-second SQL timeout and a
15-second connection timeout. Databricks polling is bounded to 120 seconds with
a 30-second timeout per CLI call and cancellation of its statement on expiry.

Pause replay/publication while comparing: the two systems are read separately,
not in one distributed transaction. Run before and after a bounded publication
and retain both aggregate reports alongside the actual replay run/cursor.
Never use an unrelated successful research run as publication lineage.

The check requires nonempty snapshots of at most 15,000 rows, an explicit expected
row count and release, no duplicate participant/time keys, equal exact keys and
matching finite motion mean, temperature mean, risk indicator and synthetic
fraction (absolute tolerance 1e-9). Timestamps use epoch microseconds on both
sides; SQL API timestamp strings can lose submillisecond precision. Delta
release identity comes from the session pin and Tiger's from each payload.

Exit codes: 0 match, 1 mismatch, 2 operational/invalid-result error. JSON includes
only aggregate counts, mismatch/error counts and statement ID; rows, credentials
and database/cloud error bodies are never printed. Oversized, truncated or
multi-chunk SQL responses fail rather than passing an incomplete comparison.

Run session health as well: equality does not independently validate every
feature, numeric range, eligibility flag, model artifact, payload field or
active feed. This does not prove that a selected job produced these rows;
record the publisher run/session association separately. No writes, DDL,
notifications, recurring schedules, model promotion or service restart occurs.

## Verified original session

Read-only check of `continuous-oct4-v1`: both systems contain 11,088 unique
windows, exact microsecond keys match, all model identities match the expected
release, and all four metric differences are zero. Databricks statement:
`01f1cc38-fb62-12bb-b1f4-30752642b838`. This is a historical snapshot verification,
not a claim of active ingestion or publication freshness.
