-- Read-only audit. Run statements separately in the SQL editor.
-- These are minute-level prefilters, not the complete 24-hour acceptance gate.
SELECT source_dataset,
       count(*) AS observed_minutes,
       count(DISTINCT participant_key) AS participants,
       count_if(enmo_mean_g IS NULL OR temperature_mean_c IS NULL) AS incomplete_minutes,
       count_if(acc_sample_ratio BETWEEN 0.8 AND 1
                AND temperature_sample_ratio BETWEEN 0.8 AND 1) AS sample_ratio_passing_minutes,
       count_if((enmo_mean_g IS NULL OR temperature_mean_c IS NULL)
                AND acc_sample_ratio BETWEEN 0.8 AND 1
                AND temperature_sample_ratio BETWEEN 0.8 AND 1) AS incomplete_minutes_passing_prefilter,
       count_if(acc_invalid_rows > 0 OR temperature_invalid_rows > 0) AS minutes_with_parse_errors
FROM workspace.gluco_silver.shared_sensor_minute_pilot
GROUP BY source_dataset;

-- Version-separated evaluation coverage. This does not count rejected candidate
-- windows; reconstructing those requires the exact training window generator.
WITH person_windows AS (
  SELECT model_version, feature_version, participant_key, cohort_label,
         count(*) AS windows
  FROM workspace.gluco_features.rolling_risk_training_windows
  GROUP BY model_version, feature_version, participant_key, cohort_label
)
SELECT model_version, feature_version, cohort_label,
       count(*) AS participants, sum(windows) AS windows,
       min(windows) AS minimum_windows_per_person,
       max(windows) AS maximum_windows_per_person
FROM person_windows
GROUP BY model_version, feature_version, cohort_label
ORDER BY model_version, cohort_label;
