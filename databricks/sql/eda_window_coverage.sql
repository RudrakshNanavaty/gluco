WITH raw AS (
 SELECT regexp_extract(_metadata.file_path,'/([0-9]{3})/[^/]+$',1) AS subject_id,
        coalesce(try_cast(datetime_raw AS TIMESTAMP_NTZ),cast(try_to_timestamp(datetime_raw,'M/d/yy H:mm') AS TIMESTAMP_NTZ)) AS event_ts,
        try_cast(eda_raw AS DOUBLE) AS eda,
        (datetime_raw RLIKE '^[0-9]{1,2}/[0-9]{1,2}/[0-9]{2} [0-9]{1,2}:[0-9]{2}$') AS coarse_clock
 FROM read_files('/Volumes/workspace/gluco_raw/source_files/big_ideas/[0-9][0-9][0-9]/EDA_*.csv',
 format=>'csv',header=>true,schema=>'datetime_raw STRING, eda_raw STRING')
), minutes AS (
 SELECT concat('big_ideas:',subject_id) AS participant_key,date_trunc('minute',event_ts) AS minute_ts,
 count(*) AS rows,count(DISTINCT event_ts) AS unique_times,min(CASE WHEN coarse_clock THEN 1 ELSE 0 END) AS coarse_only,
 count_if(eda >= 0 AND NOT isnan(eda) AND abs(eda) < CAST('Infinity' AS DOUBLE)) AS valid_samples,
 avg(CASE WHEN eda >= 0 AND NOT isnan(eda) AND abs(eda) < CAST('Infinity' AS DOUBLE) THEN eda END) AS eda_mean
 FROM raw WHERE event_ts IS NOT NULL AND subject_id <> '015'
 GROUP BY subject_id,date_trunc('minute',event_ts)
), valid AS (
 SELECT *,timestampdiff(MINUTE,TIMESTAMP_NTZ '1970-01-01 00:00:00',minute_ts) AS minute_index
 FROM minutes WHERE valid_samples BETWEEN 192 AND 240 AND (coarse_only=1 OR rows=unique_times) AND rows=valid_samples
), saved AS (
 SELECT participant_key,window_end_minute FROM workspace.gluco_features.rolling_risk_training_windows
 WHERE model_version='38ec33cb326146c7991650a3164cf440'
), hourly AS (
 SELECT s.participant_key,s.window_end_minute,
 floor((v.minute_index-(s.window_end_minute-1440))/60) AS hour_bin,count(v.minute_index) AS observations
 FROM saved s LEFT JOIN valid v ON s.participant_key=v.participant_key
 AND v.minute_index>=s.window_end_minute-1440 AND v.minute_index<s.window_end_minute
 GROUP BY s.participant_key,s.window_end_minute,hour_bin
), coverage AS (
 SELECT participant_key,window_end_minute,sum(observations) AS observations,
 (sum(observations)>=1152 AND count_if(observations>0)=24 AND min(observations)>=30) AS eda_eligible
 FROM hourly GROUP BY participant_key,window_end_minute
)
SELECT participant_key,count(*) AS reference_windows,count_if(eda_eligible) AS eda_eligible_windows,
 min(observations) AS minimum_eda_minutes,max(observations) AS maximum_eda_minutes
FROM coverage GROUP BY participant_key ORDER BY participant_key
