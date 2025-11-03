CREATE OR REPLACE VIEW "cloudtrail_security_events" AS 
SELECT
  event_date
, event_time
, region
, eventname
, user_type
, user_principal_id
, sourceipaddress
, errorcode
, errormessage
, (CASE WHEN (user_type = 'Root') THEN 'Root Account Usage' WHEN (errorcode IN ('AccessDenied', 'UnauthorizedOperation')) THEN 'Access Denied' WHEN ((eventname = 'ConsoleLogin') AND (errorcode IS NOT NULL)) THEN 'Failed Login' WHEN (eventname LIKE '%Policy%') THEN 'Policy Change' WHEN (eventname IN ('CreateUser', 'CreateRole', 'CreateAccessKey', 'DeleteUser')) THEN 'IAM Change' WHEN ((eventname LIKE '%Bucket%') AND (eventname LIKE '%Public%')) THEN 'S3 Public Access' ELSE 'Other Security Event' END) alert_type
, (CASE WHEN ((user_type = 'Root') OR (errorcode IN ('AccessDenied', 'UnauthorizedOperation'))) THEN 'High' WHEN ((eventname LIKE '%Policy%') OR (eventname IN ('CreateUser', 'CreateRole', 'CreateAccessKey'))) THEN 'Medium' ELSE 'Low' END) severity
FROM
  cloudtrail_flattened
WHERE ((is_root_user = 1) OR (errorcode IN ('AccessDenied', 'UnauthorizedOperation')) OR (eventname IN ('ConsoleLogin', 'CreateUser', 'CreateRole', 'CreateAccessKey', 'DeleteUser')) OR (eventname LIKE '%Policy%'))
