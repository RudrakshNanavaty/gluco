# Exact incomplete-minute provenance (#88)

## Finding

All three incomplete BIG IDEAs Silver rows have valid motion but no temperature
samples in the staged temperature CSV or Bronze temperature table for that
minute. A small tail of accelerometer samples extends beyond the last
pre-gap temperature minute. The full outer join in
`lakeflow_shared_units_pilot.py` deliberately preserves these motion-only
minutes, with zero temperature counts and a null temperature mean.

This is source-temperature availability at recording-segment boundaries, not
evidence of dropped temperature rows during Bronze-to-Silver aggregation.
There is no justification to fill temperatures, relax coverage gates, or
refresh the pipeline to recover nonexistent samples.

## Exact Silver rows and quality gates

Timestamps are shifted source-clock `TIMESTAMP_NTZ`, not verified UTC.
The query enumerates **all** incomplete BIG IDEAs rows, so it does not hide
additional rows by restricting to this expected roster.

| Participant | Incomplete minute | Valid ACC samples | Expected ACC/minute | ACC ratio | Temperature samples | Passes training prefilter |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| 012 | 2020-05-10 13:41 | 12 | 1,920 | 0.006250 | 0 | No |
| 013 | 2020-06-02 12:28 | 36 | 1,920 | 0.018750 | 0 | No |
| 016 | 2020-07-22 10:59 | 4 | 1,920 | 0.002083 | 0 | No |

All three have zero invalid ACC/temperature rows reported by Silver. Their
expected temperature count is 240/minute and their temperature ratio is zero.
Both motion and temperature ratios must be between 0.8 and 1 for training;
these rows cannot reach the rolling-window feature constructor through that
prefilter. The unchanged total and hourly window coverage gates apply to the
remaining minutes afterward.

## Source and Bronze boundary evidence

The nearest temperature sample before the incomplete minute is at `:59.75` in
the preceding minute. In each case, the next temperature sample is after a
recording gap. Direct CSV and Bronze temperature results match exactly on
row count, first/last timestamps, nearest boundary timestamps and zero samples
inside the incomplete minute.

| Participant | Source = Bronze temperature rows | Last temperature before minute | Next temperature | Last Bronze ACC within minute |
| --- | ---: | --- | --- | --- |
| 012 | 2,391,976 | 2020-05-10 13:40:59.75 | 2020-05-10 20:47:27 | 2020-05-10 13:41:00.34375 |
| 013 | 2,795,184 | 2020-06-02 12:27:59.75 | 2020-06-02 13:14:33 | 2020-06-02 12:28:01.09375 |
| 016 | 2,232,584 | 2020-07-22 10:58:59.75 | 2020-07-22 11:37:21 | 2020-07-22 10:59:00.09375 |

Bronze ACC contains exactly the same 12/36/4 rows inside the target minutes as
Silver, starting at `:00`. No unparseable timestamps were found in the selected
source temperature, Bronze temperature or Bronze ACC inputs. No invalid
numeric temperatures were found in the selected source/Bronze temperature
inputs. ACC source CSVs were not rescanned, and numeric ACC raw values were
not independently audited in this follow-up; Silver already reports all those
minute samples as valid.

## Reproduction and scope

Run these read-only SQL files separately on the existing warehouse:

- `databricks/sql/incomplete_minute_quality_gate.sql`
- `databricks/sql/incomplete_minute_provenance.sql`

Verified October 18, 2026 using warehouse `a75228c068d4e415`.
Provenance statement: `01f1cb3b-eb0e-17a4-b1de-1ef9888dc78c` (SUCCEEDED).
Quality-gate statement: `01f1cb3b-fe85-1bea-96ba-25750b4dfe97` (SUCCEEDED).
Initial Silver inventory: `01f1cb3b-d0fb-15a0-9c83-e495a7d258ed` (SUCCEEDED).

Direct reads were limited to `TEMP_012.csv` (74,094,027 bytes), `TEMP_013.csv`
(86,571,943 bytes) and `TEMP_016.csv` (69,166,215 bytes): 229,832,185 bytes
(~219 MiB). Their much larger ACC CSVs (~2.60 GB total) were not rescanned.
No source data or query-result files are committed. SQL returns only aggregate
counts and boundary timestamps; no sample values are exported by the provenance
query.

The files establish the absence of temperature readings and the join/gate
behavior. They do not establish why acquisition paused, byte-for-byte equality
of all source/Bronze values, or the cause of every gap in the dataset. These
three partial minutes are distinct from the large gaps for participants
004/006/011 in `SOURCE_GAP_FINDINGS.md`.

No data, table, coverage policy, model artifact, session pin or Tiger publication
was changed. Model accuracy is unchanged by this audit.
