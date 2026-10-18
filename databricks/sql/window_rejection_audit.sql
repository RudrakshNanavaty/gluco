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
), hourly AS (
  SELECT c.participant_key, c.window_end_minute,
         CAST(floor((m.minute_index - (c.window_end_minute - 1440)) / 60) AS INT) AS hour_bin,
         count(m.minute_index) AS observations,
         count_if(m.enmo_mean_g IS NULL OR m.temperature_mean_c IS NULL
                  OR isnan(m.enmo_mean_g) OR isnan(m.temperature_mean_c)
                  OR abs(m.enmo_mean_g) > 1.7976931348623157E308
                  OR abs(m.temperature_mean_c) > 1.7976931348623157E308) AS nonfinite
  FROM candidates c LEFT JOIN minutes m
    ON c.participant_key = m.participant_key
   AND m.minute_index >= c.window_end_minute - 1440
   AND m.minute_index < c.window_end_minute
  GROUP BY c.participant_key, c.window_end_minute, hour_bin
), decisions AS (
  SELECT participant_key, window_end_minute, sum(observations) AS usable_minutes,
         CASE WHEN sum(observations) < 1152 THEN 'below_80_percent'
              WHEN sum(nonfinite) > 0 THEN 'nonfinite_input'
              WHEN count_if(observations > 0) < 24 OR min(observations) < 30
                THEN 'hourly_coverage_gap'
              ELSE 'accepted' END AS decision
  FROM hourly GROUP BY participant_key, window_end_minute
), saved AS (
  SELECT participant_key, window_end_minute
  FROM workspace.gluco_features.rolling_risk_training_windows
  WHERE model_version = '38ec33cb326146c7991650a3164cf440'
), comparison AS (
  SELECT coalesce(d.participant_key, s.participant_key) AS participant_key,
         d.decision, d.usable_minutes,
         CASE WHEN d.decision = 'accepted' AND s.participant_key IS NULL THEN 1
              WHEN s.participant_key IS NOT NULL AND coalesce(d.decision, '') <> 'accepted' THEN 1
              ELSE 0 END AS saved_window_mismatch
  FROM decisions d FULL OUTER JOIN saved s
    ON d.participant_key = s.participant_key AND d.window_end_minute = s.window_end_minute
)
SELECT participant_key, count(decision) AS candidate_windows,
       count_if(decision = 'accepted') AS accepted_windows,
       count_if(decision = 'below_80_percent') AS rejected_total_coverage,
       count_if(decision = 'hourly_coverage_gap') AS rejected_hourly_coverage,
       count_if(decision = 'nonfinite_input') AS rejected_nonfinite,
       sum(saved_window_mismatch) AS saved_window_mismatches
FROM comparison GROUP BY participant_key ORDER BY participant_key;
