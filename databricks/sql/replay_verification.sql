-- Bind session_id as a SQL string parameter. This reads existing results only.
SELECT 'dashboard_windows' AS check_name, count(*) AS rows,
       count(DISTINCT struct(participant_key, window_end)) AS unique_keys,
       count(DISTINCT participant_key) AS participants
FROM workspace.gluco_demo.dashboard_windows WHERE session_id = :session_id
UNION ALL
SELECT 'bronze_events', count(*),
       count(DISTINCT struct(sensor_id, observed_at, event_id)),
       count(DISTINCT sensor_id)
FROM workspace.gluco_bronze.sensor_events
WHERE get_json_object(raw_payload, '$.measurements.demo.session_id') = :session_id;

-- Exact cross-system key/metric comparison: typed TIMESTAMP API output is
-- millisecond-rendered, so use integer microseconds rather than its text form.
SELECT participant_key, unix_micros(window_end) AS window_end_epoch_us,
       wearable_risk_indicator, motion_mean_g,
       temperature_mean_c_24h, hr_mean_bpm_24h
FROM workspace.gluco_demo.dashboard_windows
WHERE session_id = :session_id
ORDER BY participant_key, window_end;
