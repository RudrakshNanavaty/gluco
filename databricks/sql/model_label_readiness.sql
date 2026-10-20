-- Read-only checks for every current labeled participant, not error-selected
-- exclusions. HbA1c is target provenance only and never a wearable feature.
WITH source_labels AS (
  SELECT concat('big_ideas:', lpad(id_raw, 3, '0')) AS participant_key,
         try_cast(hba1c_raw AS DOUBLE) AS hba1c
  FROM read_files('/Volumes/workspace/gluco_raw/source_files/big_ideas/Demographics.csv',
    format => 'csv', header => true,
    schema => 'id_raw STRING, gender_raw STRING, hba1c_raw STRING')
), source AS (
  SELECT participant_key, count(*) AS source_rows, count(DISTINCT hba1c) AS distinct_source_targets,
         CASE WHEN min(hba1c) BETWEEN 5.2 AND 5.6 THEN 0
              WHEN min(hba1c) BETWEEN 5.7 AND 6.4 THEN 1 END AS source_label,
         min(hba1c) AS source_hba1c
  FROM source_labels GROUP BY participant_key
), bronze AS (
  SELECT participant_key, count(*) AS bronze_rows,
         count(DISTINCT try_cast(hba1c_raw AS DOUBLE)) AS distinct_bronze_targets,
         min(try_cast(hba1c_raw AS DOUBLE)) AS bronze_hba1c
  FROM workspace.gluco_bronze.cohort_label_source GROUP BY participant_key
), saved AS (
  SELECT participant_key, count(*) AS accepted_windows,
         count(DISTINCT cohort_label) AS distinct_saved_labels,
         min(cohort_label) AS saved_label
  FROM workspace.gluco_features.rolling_risk_training_windows
  WHERE model_version = '38ec33cb326146c7991650a3164cf440'
  GROUP BY participant_key
)
SELECT s.participant_key, s.source_rows, s.distinct_source_targets,
       b.bronze_rows, b.distinct_bronze_targets,
       s.source_label, t.cohort_label AS silver_label, w.saved_label,
       (s.source_hba1c <=> b.bronze_hba1c AND s.source_hba1c <=> t.hba1c) AS source_bronze_silver_target_agrees,
       w.distinct_saved_labels, coalesce(w.accepted_windows,0) AS accepted_windows,
       f.observed_minutes,f.usable_minutes,f.usable_fraction_of_observed,
       timestampdiff(MINUTE,f.observation_start,f.observation_end) AS elapsed_minute_span,
       f.eligible AS subject_summary_eligible
FROM source s LEFT JOIN bronze b USING(participant_key)
LEFT JOIN workspace.gluco_silver.subject_targets t USING(participant_key)
LEFT JOIN saved w USING(participant_key)
LEFT JOIN workspace.gluco_features.metabolic_features f USING(participant_key)
ORDER BY s.participant_key;
