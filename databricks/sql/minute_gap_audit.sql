-- Read-only gap attribution within each participant's first/last passing minute.
-- 'Absent' means no Silver row, not a proven hardware recording failure.
WITH source AS (
  SELECT participant_key,
         timestampdiff(MINUTE, TIMESTAMP_NTZ '1970-01-01 00:00:00', minute_ts) AS minute_index,
         coalesce(acc_sample_ratio BETWEEN 0.8 AND 1
                  AND temperature_sample_ratio BETWEEN 0.8 AND 1, false) AS passes
  FROM workspace.gluco_silver.shared_sensor_minute_pilot
  WHERE source_dataset = 'big_ideas' AND participant_key <> 'big_ideas:015'
), bounds AS (
  SELECT participant_key, min(CASE WHEN passes THEN minute_index END) AS first_minute,
         max(CASE WHEN passes THEN minute_index END) AS last_minute
  FROM source GROUP BY participant_key
), grid AS (
  SELECT participant_key, explode(sequence(first_minute, last_minute, 1)) AS minute_index
  FROM bounds
), states AS (
  SELECT g.participant_key, g.minute_index,
         CASE WHEN s.minute_index IS NULL THEN 'absent_silver'
              WHEN s.passes THEN 'passing' ELSE 'filtered' END AS status
  FROM grid g LEFT JOIN source s USING (participant_key, minute_index)
), lagged AS (
  SELECT *, lag(status) OVER (PARTITION BY participant_key ORDER BY minute_index) AS previous
  FROM states
), islands AS (
  SELECT *, sum(CASE WHEN status = previous THEN 0 ELSE 1 END)
    OVER (PARTITION BY participant_key ORDER BY minute_index) AS island
  FROM lagged
), runs AS (
  SELECT participant_key, status, island, count(*) AS minutes
  FROM islands GROUP BY participant_key, status, island
), loss_runs AS (
  SELECT participant_key, minute_index,
         minute_index - row_number() OVER (PARTITION BY participant_key ORDER BY minute_index) AS island
  FROM states WHERE status <> 'passing'
), combined AS (
  SELECT participant_key, max(minutes) AS longest_combined_gap
  FROM (SELECT participant_key, island, count(*) AS minutes
        FROM loss_runs GROUP BY participant_key, island)
  GROUP BY participant_key
)
SELECT r.participant_key,
       sum(r.minutes) AS elapsed_minutes,
       sum(CASE WHEN status = 'passing' THEN minutes ELSE 0 END) AS passing_minutes,
       sum(CASE WHEN status = 'absent_silver' THEN minutes ELSE 0 END) AS absent_minutes,
       sum(CASE WHEN status = 'filtered' THEN minutes ELSE 0 END) AS filtered_minutes,
       max(CASE WHEN status = 'absent_silver' THEN minutes ELSE 0 END) AS longest_absent_gap,
       max(CASE WHEN status = 'filtered' THEN minutes ELSE 0 END) AS longest_filtered_run,
       max(coalesce(c.longest_combined_gap, 0)) AS longest_combined_gap
FROM runs r LEFT JOIN combined c USING (participant_key)
GROUP BY r.participant_key ORDER BY r.participant_key;
