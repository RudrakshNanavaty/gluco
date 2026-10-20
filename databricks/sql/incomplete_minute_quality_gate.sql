-- Run independently of incomplete_minute_provenance.sql; read-only.
-- Return every incomplete BIG IDEAs minute, not only the expected three keys,
-- so newly appearing incomplete rows cannot be hidden by a fixed roster.
SELECT participant_key, cast(minute_ts AS STRING) AS minute_ts,
       enmo_mean_g, temperature_mean_c,
       acc_rows, acc_samples, temperature_rows, temperature_samples,
       acc_invalid_rows, temperature_invalid_rows,
       acc_sample_ratio, temperature_sample_ratio,
       (acc_sample_ratio BETWEEN 0.8 AND 1
        AND temperature_sample_ratio BETWEEN 0.8 AND 1) AS passes_training_prefilter
FROM workspace.gluco_silver.shared_sensor_minute_pilot
WHERE source_dataset = 'big_ideas'
  AND (enmo_mean_g IS NULL OR temperature_mean_c IS NULL)
ORDER BY participant_key, minute_ts;
