CREATE OR REPLACE VIEW "cloudtrail_user_summary" AS 
SELECT
  user_principal_id
, user_type
, COUNT(*) total_api_calls
, COUNT(DISTINCT event_date) active_days
, COUNT(DISTINCT region) regions_accessed
, COUNT(DISTINCT eventsource) services_used
, COUNT(DISTINCT eventname) unique_actions
, SUM(is_failed) failed_attempts
, MAX(event_time) last_activity
, MIN(event_time) first_activity
FROM
  cloudtrail_flattened
GROUP BY 1, 2
