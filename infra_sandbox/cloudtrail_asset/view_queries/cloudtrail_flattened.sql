CREATE OR REPLACE VIEW "cloudtrail_flattened" AS 
SELECT
  eventversion
, eventtime
, event_time
, event_date
, region
, eventsource
, eventname
, awsregion
, sourceipaddress
, useragent
, errorcode
, errormessage
, requestid
, eventid
, eventtype
, useridentity.type user_type
, useridentity.principalid user_principal_id
, useridentity.arn user_arn
, useridentity.accountid user_account_id
, useridentity.username user_name
, recipientaccountid
, readonly
, managementevent
, eventcategory
, requestparameters
, responseelements
, HOUR(event_time) hour_of_day
, DAY_OF_WEEK(event_time) day_of_week
, (CASE WHEN (errorcode IS NOT NULL) THEN 1 ELSE 0 END) is_failed
, (CASE WHEN (useridentity.type = 'Root') THEN 1 ELSE 0 END) is_root_user
, (CASE WHEN (eventname LIKE '%Create%') THEN 'Create' WHEN (eventname LIKE '%Delete%') THEN 'Delete' WHEN ((eventname LIKE '%Update%') OR (eventname LIKE '%Modify%') OR (eventname LIKE '%Put%')) THEN 'Update' WHEN ((eventname LIKE '%Get%') OR (eventname LIKE '%Describe%') OR (eventname LIKE '%List%')) THEN 'Read' ELSE 'Other' END) operation_type
, (CASE WHEN ((hour(event_time) >= 9) AND (hour(event_time) <= 17)) THEN 'Business Hours' ELSE 'Off Hours' END) time_category
FROM
  cloudtrail_events
WHERE (event_date >= (current_date - INTERVAL  '90' DAY))
