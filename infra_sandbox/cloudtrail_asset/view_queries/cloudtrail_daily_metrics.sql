CREATE OR REPLACE VIEW "cloudtrail_daily_metrics" AS 
SELECT
  event_date
, region
, eventsource
, operation_type
, user_type
, time_category
, COUNT(*) total_events
, COUNT(DISTINCT user_principal_id) unique_users
, COUNT(DISTINCT sourceipaddress) unique_ips
, SUM(is_failed) failed_events
, SUM(is_root_user) root_user_events
, COUNT(DISTINCT eventname) unique_api_calls
FROM
  cloudtrail_flattened
GROUP BY 1, 2, 3, 4, 5, 6
