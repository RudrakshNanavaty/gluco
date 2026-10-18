-- Read-only bounded provenance check for three previously identified gaps.
-- Direct source reads are restricted to three temperature CSVs (~190 MiB total).
-- ACC is checked in Bronze only; its multi-GB source files are not rescanned.
WITH gaps(participant_key, gap_start, gap_end) AS (
  VALUES
    ('big_ideas:004', TIMESTAMP_NTZ '2020-02-28 04:15:00', TIMESTAMP_NTZ '2020-02-29 19:07:00'),
    ('big_ideas:006', TIMESTAMP_NTZ '2020-03-05 17:45:00', TIMESTAMP_NTZ '2020-03-08 01:23:00'),
    ('big_ideas:011', TIMESTAMP_NTZ '2020-04-09 15:31:00', TIMESTAMP_NTZ '2020-04-11 06:39:00')
), direct_temperature AS (
  SELECT 'big_ideas:004' AS participant_key, datetime_raw FROM read_files(
    '/Volumes/workspace/gluco_raw/source_files/big_ideas/004/TEMP_004.csv',
    format => 'csv', header => true, schema => 'datetime_raw STRING, temperature_raw STRING')
  UNION ALL
  SELECT 'big_ideas:006', datetime_raw FROM read_files(
    '/Volumes/workspace/gluco_raw/source_files/big_ideas/006/TEMP_006.csv',
    format => 'csv', header => true, schema => 'datetime_raw STRING, temperature_raw STRING')
  UNION ALL
  SELECT 'big_ideas:011', datetime_raw FROM read_files(
    '/Volumes/workspace/gluco_raw/source_files/big_ideas/011/TEMP_011.csv',
    format => 'csv', header => true, schema => 'datetime_raw STRING, temperature_raw STRING')
), records AS (
  SELECT 'bronze_acc' AS stage, participant_key, datetime_raw
  FROM workspace.gluco_bronze.big_ideas_acc_pilot
  WHERE participant_key IN ('big_ideas:004','big_ideas:006','big_ideas:011')
  UNION ALL
  SELECT 'bronze_temperature', participant_key, datetime_raw
  FROM workspace.gluco_bronze.big_ideas_temperature_pilot
  WHERE participant_key IN ('big_ideas:004','big_ideas:006','big_ideas:011')
  UNION ALL
  SELECT 'source_temperature_csv', participant_key, datetime_raw FROM direct_temperature
), parsed AS (
  SELECT stage, participant_key, try_cast(datetime_raw AS TIMESTAMP_NTZ) AS event_ts
  FROM records
)
SELECT p.participant_key, p.stage, count(*) AS rows_in_selected_input,
       count_if(event_ts IS NULL) AS unparseable_timestamps,
       count_if(event_ts >= g.gap_start AND event_ts < g.gap_end) AS rows_inside_gap,
       max(CASE WHEN event_ts < g.gap_start THEN event_ts END) AS nearest_before,
       min(CASE WHEN event_ts >= g.gap_end THEN event_ts END) AS nearest_after
FROM parsed p JOIN gaps g USING (participant_key)
GROUP BY p.participant_key, p.stage ORDER BY p.participant_key, p.stage;
