CREATE OR REPLACE VIEW "cloudtrail_resource_changes" AS 
SELECT
*
FROM
  cloudtrail_flattened
WHERE ((operation_type IN ('Create', 'Delete', 'Update')) AND (managementevent = 'true'))
