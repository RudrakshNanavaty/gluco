-- Diagnostic only: ignores sample-ratio quality, never used for training.
-- Reconstruct the current training candidate windows without changing data.
-- Mirrors train_rolling_risk.py and rolling_risk.window_features.
-- Source timestamps are clock values (TIMESTAMP_NTZ), not UTC observations.
WITH minutes AS (
  SELECT participant_key,
         timestampdiff(MINUTE, TIMESTAMP_NTZ '1970-01-01 00:00:00', minute_ts) AS minute_index,
         enmo_mean_g, temperature_mean_c
  FROM workspace.gluco_silver.shared_sensor_minute_pilot
  WHERE participant_key IN (
    'big_ideas:001','big_ideas:002','big_ideas:003','big_ideas:004',
    'big_ideas:005','big_ideas:006','big_ideas:007','big_ideas:008',
    'big_ideas:009','big_ideas:010','big_ideas:011','big_ideas:012',
    'big_ideas:013','big_ideas:014','big_ideas:016')
    AND acc_sample_ratio BETWEEN 0.8 AND 1
    AND temperature_sample_ratio BETWEEN 0.8 AND 1
), bounds AS (
  SELECT participant_key,
         CAST(ceil((min(minute_index) + 1440) / 60.0) * 60 AS BIGINT) AS first_end,
         max(minute_index) + 1 AS last_end
  FROM minutes GROUP BY participant_key
), candidates AS (
  SELECT participant_key, explode(sequence(first_end, last_end, 60)) AS window_end_minute
  FROM bounds WHERE first_end <= last_end
), available AS (
  SELECT participant_key,
    timestampdiff(MINUTE, TIMESTAMP_NTZ '1970-01-01 00:00:00', minute_ts) AS minute_index
  FROM workspace.gluco_silver.shared_sensor_minute_pilot
  WHERE source_dataset = 'big_ideas'
    AND enmo_mean_g IS NOT NULL AND temperature_mean_c IS NOT NULL
    AND NOT isnan(enmo_mean_g) AND NOT isnan(temperature_mean_c)
    AND abs(enmo_mean_g) <= 1.7976931348623157E308
    AND abs(temperature_mean_c) <= 1.7976931348623157E308
), hours AS (
  SELECT c.participant_key, c.window_end_minute,
    CAST(floor((a.minute_index - (c.window_end_minute - 1440)) / 60) AS INT) AS hour_bin,
    count(a.minute_index) AS observations
  FROM candidates c LEFT JOIN available a
    ON c.participant_key = a.participant_key
    AND a.minute_index >= c.window_end_minute - 1440
    AND a.minute_index < c.window_end_minute
  GROUP BY c.participant_key, c.window_end_minute, hour_bin
), decisions AS (
  SELECT participant_key, window_end_minute,
    sum(observations) >= 1152 AND count_if(observations > 0) = 24
      AND min(observations) >= 30 AS passes_without_sample_filter
  FROM hours GROUP BY participant_key, window_end_minute
), current_counts AS (
  SELECT participant_key, count(*) AS current_accepted
  FROM workspace.gluco_features.rolling_risk_training_windows
  WHERE model_version = '38ec33cb326146c7991650a3164cf440'
  GROUP BY participant_key
)
SELECT d.participant_key, count(*) AS candidates,
  max(c.current_accepted) AS current_accepted,
  count_if(passes_without_sample_filter) AS available_finite_minutes_upper_bound
FROM decisions d JOIN current_counts c USING (participant_key)
GROUP BY d.participant_key ORDER BY d.participant_key;
