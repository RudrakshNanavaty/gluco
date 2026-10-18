-- Read-only provenance for the exact three incomplete Silver minutes in #88.
-- Timestamp values are shifted source-clock TIMESTAMP_NTZ, not verified UTC.
-- Direct CSV scans are limited to three temperature files. ACC uses Bronze;
-- its large source CSVs are not rescanned. No imputation or table writes.
WITH targets(participant_key, minute_start) AS (
  VALUES
    ('big_ideas:012', TIMESTAMP_NTZ '2020-05-10 13:41:00'),
    ('big_ideas:013', TIMESTAMP_NTZ '2020-06-02 12:28:00'),
    ('big_ideas:016', TIMESTAMP_NTZ '2020-07-22 10:59:00')
), source_temperature AS (
  SELECT 'big_ideas:012' AS participant_key, datetime_raw, temperature_raw
  FROM read_files('/Volumes/workspace/gluco_raw/source_files/big_ideas/012/TEMP_012.csv',
    format => 'csv', header => true, schema => 'datetime_raw STRING, temperature_raw STRING')
  UNION ALL
  SELECT 'big_ideas:013', datetime_raw, temperature_raw
  FROM read_files('/Volumes/workspace/gluco_raw/source_files/big_ideas/013/TEMP_013.csv',
    format => 'csv', header => true, schema => 'datetime_raw STRING, temperature_raw STRING')
  UNION ALL
  SELECT 'big_ideas:016', datetime_raw, temperature_raw
  FROM read_files('/Volumes/workspace/gluco_raw/source_files/big_ideas/016/TEMP_016.csv',
    format => 'csv', header => true, schema => 'datetime_raw STRING, temperature_raw STRING')
), records AS (
  SELECT 'source_temperature_csv' AS stage, participant_key, datetime_raw,
         try_cast(temperature_raw AS DOUBLE) AS temperature_c
  FROM source_temperature
  UNION ALL
  SELECT 'bronze_temperature', participant_key, datetime_raw,
         try_cast(temperature_raw AS DOUBLE)
  FROM workspace.gluco_bronze.big_ideas_temperature_pilot
  WHERE participant_key IN ('big_ideas:012','big_ideas:013','big_ideas:016')
  UNION ALL
  SELECT 'bronze_acc', participant_key, datetime_raw, CAST(NULL AS DOUBLE)
  FROM workspace.gluco_bronze.big_ideas_acc_pilot
  WHERE participant_key IN ('big_ideas:012','big_ideas:013','big_ideas:016')
), parsed AS (
  SELECT *, try_cast(datetime_raw AS TIMESTAMP_NTZ) AS event_ts FROM records
)
SELECT p.participant_key, p.stage, count(*) AS input_rows,
       count_if(event_ts IS NULL) AS invalid_timestamps,
       count_if(stage <> 'bronze_acc' AND (temperature_c IS NULL OR isnan(temperature_c)
                OR abs(temperature_c) = CAST('Infinity' AS DOUBLE))) AS invalid_temperature_values,
       cast(min(event_ts) AS STRING) AS first_event,
       cast(max(event_ts) AS STRING) AS last_event,
       count_if(event_ts >= t.minute_start AND event_ts < t.minute_start + INTERVAL 1 MINUTE) AS rows_in_target_minute,
       cast(min(CASE WHEN event_ts >= t.minute_start AND event_ts < t.minute_start + INTERVAL 1 MINUTE THEN event_ts END) AS STRING) AS first_in_minute,
       cast(max(CASE WHEN event_ts >= t.minute_start AND event_ts < t.minute_start + INTERVAL 1 MINUTE THEN event_ts END) AS STRING) AS last_in_minute,
       cast(max(CASE WHEN event_ts < t.minute_start THEN event_ts END) AS STRING) AS nearest_before_minute,
       cast(min(CASE WHEN event_ts >= t.minute_start + INTERVAL 1 MINUTE THEN event_ts END) AS STRING) AS nearest_after_minute
FROM parsed p JOIN targets t USING (participant_key)
GROUP BY p.participant_key,p.stage ORDER BY p.participant_key,p.stage;
