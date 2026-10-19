-- Read-only session snapshot. :session_id is a bound STRING parameter.
-- Historical event time is reported, never compared with wall-clock freshness.
WITH d AS (
  SELECT * FROM workspace.gluco_demo.dashboard_windows WHERE session_id = :session_id
), p AS (
  SELECT * FROM workspace.gluco_demo.replay_risk_models WHERE session_id = :session_id
), r AS (
  SELECT * FROM workspace.gluco_models.rolling_risk_releases
  WHERE model_version IN (SELECT model_version FROM p)
), scored AS (
  SELECT s.participant_key,s.window_end,count(*) AS score_rows,
         min(s.wearable_risk_indicator) AS score
  FROM workspace.gluco_demo.dashboard_risk_scores s
  WHERE s.session_id = :session_id AND s.risk_model_version IN (SELECT model_version FROM p)
  GROUP BY s.participant_key,s.window_end
), score_health AS (
  SELECT count_if(s.score_rows IS NULL OR s.score_rows <> 1
                  OR NOT (d.wearable_risk_indicator <=> s.score)) AS score_sync_issues
  FROM d LEFT JOIN scored s USING (participant_key,window_end)
), per_time AS (
  SELECT window_end,count(DISTINCT participant_key) AS participants FROM d GROUP BY window_end
), bronze AS (
  SELECT * FROM workspace.gluco_bronze.sensor_events
  WHERE get_json_object(raw_payload,'$.measurements.demo.session_id') = :session_id
)
SELECT count(*) AS windows,
       count(DISTINCT struct(participant_key,window_end)) AS unique_window_keys,
       count(DISTINCT participant_key) AS participants,
       count_if(participant_key IS NULL OR window_end IS NULL) AS invalid_keys,
       count_if(wearable_risk_indicator IS NULL OR isnan(wearable_risk_indicator)
                OR wearable_risk_indicator < 0 OR wearable_risk_indicator > 100) AS invalid_scores,
       count_if(motion_mean_g IS NULL OR isnan(motion_mean_g) OR abs(motion_mean_g) = CAST('Infinity' AS DOUBLE)
                OR temperature_mean_c_24h IS NULL OR isnan(temperature_mean_c_24h)
                OR abs(temperature_mean_c_24h) = CAST('Infinity' AS DOUBLE)) AS invalid_features,
       count_if(window_minutes IS NULL OR window_minutes <> 1440) AS invalid_window_lengths,
       count_if(demo_only IS NULL OR NOT demo_only OR training_eligible IS NULL OR training_eligible) AS unsafe_demo_flags,
       count_if(synthetic_fraction IS NULL OR isnan(synthetic_fraction)
                OR synthetic_fraction < 0 OR synthetic_fraction > 1) AS invalid_synthetic_fractions,
       cast(min(window_end) AS STRING) AS earliest_event_time,
       cast(max(window_end) AS STRING) AS latest_event_time,
       (SELECT min(participants) FROM per_time) AS minimum_participants_per_window,
       (SELECT count(*) FROM p) AS pin_rows,
       (SELECT min(model_version) FROM p) AS pinned_model,
       (SELECT count(*) FROM r) AS release_rows,
       (SELECT min(feature_version) FROM r) AS feature_version,
       (SELECT min(artifact_path) FROM r) AS artifact_path,
       (SELECT score_sync_issues FROM score_health) AS score_sync_issues,
       (SELECT count(*) FROM bronze) AS bronze_events,
       (SELECT count(DISTINCT struct(sensor_id,observed_at,event_id)) FROM bronze) AS unique_bronze_keys
FROM d;
