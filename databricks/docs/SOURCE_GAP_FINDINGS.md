# Bounded source-gap provenance audit

## Result

Three large Silver gaps are also present in the staged temperature CSVs.
Bronze temperature matches direct-source row counts and nearest gap-boundary
samples. There is no evidence that Bronze-to-Silver aggregation introduced
these particular temperature gaps. This does not identify why the original
recordings are discontinuous, nor prove that all pipeline gaps have this cause.

## Scope and verification

Read-only warehouse query: `databricks/sql/source_gap_audit.sql`.
Successful statement: `01f1ca97-60e5-113c-84cf-a0a7b3334643`.

| Participant | Missing whole Silver minutes | Temperature rows in file and Bronze | Source temperature rows inside gap | Invalid timestamps in source/Bronze |
| --- | ---: | ---: | ---: | ---: |
| 004 | 2,332 | 1,798,592 | 0 | 0 |
| 006 | 3,338 | 2,000,000 | 0 | 0 |
| 011 | 2,348 | 2,644,184 | 0 | 0 |

For each participant, the nearest temperature sample before and after the gap
agrees exactly between source and Bronze. Bronze ACC also has zero samples
inside each gap and zero invalid timestamps for these selected participants.
The full query returns boundary timestamps for reproducibility. Historical
source timestamps are shifted clock values (TIMESTAMP_NTZ), not verified UTC.

Direct reads were limited to TEMP_004.csv, TEMP_006.csv and TEMP_011.csv:
55,691,947 + 61,933,511 + 81,873,855 bytes (about 190 MiB total). Source ACC files
were not rescanned; its approximately 2.1 GiB of staged files was avoided.
Bronze ACC input contains about 51.5 million rows for these three participants;
the warehouse aggregated them without exporting raw observations.

## Implications

- Keep gaps missing rather than inventing sensor measurements for training.
- Keep the current eligibility gates and 60.42% reference model unchanged.
- A full Silver refresh would not recover the missing source-temperature samples
  demonstrated here. This is not evidence that retriggering ETL fixes coverage.
- Investigate acquisition/source provenance if more contiguous real data is
  required. Expanding labeled participants remains distinct from synthetic
  replay or overlapping-window expansion.
- A sensible operational follow-up is a reusable coverage report and provenance
  indicators, alongside configurable replay. Do not imply the historical demo
  is a running sensor feed.

No raw files, tables, model artifacts, session pins or Tiger data were modified.
The check establishes timestamp presence and row-count/boundary agreement, not
byte-for-byte equality or numeric-value equality across all source/Bronze rows.
