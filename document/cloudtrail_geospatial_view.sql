-- CloudTrail Geospatial View with IP-based Location Mapping
-- This view adds latitude and longitude coordinates based on source IP addresses
-- for use in QuickSuite map visualizations

CREATE OR REPLACE VIEW cloudtrail_geospatial AS
SELECT 
    eventtime,
    eventname,
    eventsource,
    sourceipaddress,
    useridentity.type as user_type,
    useridentity.principalid as user_principal_id,
    awsregion,
    recipientaccountid,
    errorcode,
    errormessage,
    
    -- Add geospatial coordinates based on IP address patterns
    CASE 
        -- AWS Internal IPs (approximate AWS region centers)
        WHEN sourceipaddress LIKE '10.%' OR sourceipaddress LIKE '172.%' OR sourceipaddress LIKE '192.168.%' THEN
            CASE awsregion
                WHEN 'us-east-1' THEN 39.0458  -- Virginia
                WHEN 'us-west-2' THEN 45.5152  -- Oregon
                WHEN 'eu-west-1' THEN 53.3498  -- Ireland
                WHEN 'ap-southeast-1' THEN 1.3521  -- Singapore
                WHEN 'ap-northeast-1' THEN 35.6762  -- Tokyo
                ELSE 39.0458  -- Default to us-east-1
            END
        -- Public IP ranges (approximate geographic mapping)
        WHEN sourceipaddress LIKE '1.%' OR sourceipaddress LIKE '2.%' THEN 35.6762   -- Asia-Pacific
        WHEN sourceipaddress LIKE '3.%' OR sourceipaddress LIKE '4.%' THEN 39.0458   -- North America
        WHEN sourceipaddress LIKE '5.%' OR sourceipaddress LIKE '8.%' THEN 51.5074   -- Europe
        WHEN sourceipaddress LIKE '20.%' OR sourceipaddress LIKE '40.%' THEN 39.0458  -- Microsoft/Azure ranges
        WHEN sourceipaddress LIKE '52.%' OR sourceipaddress LIKE '54.%' THEN 39.0458  -- AWS ranges
        WHEN sourceipaddress LIKE '13.%' OR sourceipaddress LIKE '18.%' THEN 37.7749  -- US West
        ELSE 39.0458  -- Default latitude
    END AS latitude,
    
    CASE 
        -- AWS Internal IPs (approximate AWS region centers)
        WHEN sourceipaddress LIKE '10.%' OR sourceipaddress LIKE '172.%' OR sourceipaddress LIKE '192.168.%' THEN
            CASE awsregion
                WHEN 'us-east-1' THEN -77.3910  -- Virginia
                WHEN 'us-west-2' THEN -122.6784 -- Oregon
                WHEN 'eu-west-1' THEN -6.2603   -- Ireland
                WHEN 'ap-southeast-1' THEN 103.8198 -- Singapore
                WHEN 'ap-northeast-1' THEN 139.6503 -- Tokyo
                ELSE -77.3910  -- Default to us-east-1
            END
        -- Public IP ranges (approximate geographic mapping)
        WHEN sourceipaddress LIKE '1.%' OR sourceipaddress LIKE '2.%' THEN 139.6503  -- Asia-Pacific
        WHEN sourceipaddress LIKE '3.%' OR sourceipaddress LIKE '4.%' THEN -77.3910  -- North America
        WHEN sourceipaddress LIKE '5.%' OR sourceipaddress LIKE '8.%' THEN -0.1278   -- Europe
        WHEN sourceipaddress LIKE '20.%' OR sourceipaddress LIKE '40.%' THEN -77.3910 -- Microsoft/Azure ranges
        WHEN sourceipaddress LIKE '52.%' OR sourceipaddress LIKE '54.%' THEN -77.3910 -- AWS ranges
        WHEN sourceipaddress LIKE '13.%' OR sourceipaddress LIKE '18.%' THEN -122.4194 -- US West
        ELSE -77.3910  -- Default longitude
    END AS longitude,
    
    -- Add location name for better visualization
    CASE 
        WHEN sourceipaddress LIKE '10.%' OR sourceipaddress LIKE '172.%' OR sourceipaddress LIKE '192.168.%' THEN
            CASE awsregion
                WHEN 'us-east-1' THEN 'US East (Virginia)'
                WHEN 'us-west-2' THEN 'US West (Oregon)'
                WHEN 'eu-west-1' THEN 'Europe (Ireland)'
                WHEN 'ap-southeast-1' THEN 'Asia Pacific (Singapore)'
                WHEN 'ap-northeast-1' THEN 'Asia Pacific (Tokyo)'
                ELSE 'AWS Internal'
            END
        WHEN sourceipaddress LIKE '1.%' OR sourceipaddress LIKE '2.%' THEN 'Asia Pacific'
        WHEN sourceipaddress LIKE '3.%' OR sourceipaddress LIKE '4.%' THEN 'North America'
        WHEN sourceipaddress LIKE '5.%' OR sourceipaddress LIKE '8.%' THEN 'Europe'
        WHEN sourceipaddress LIKE '20.%' OR sourceipaddress LIKE '40.%' THEN 'Cloud Provider'
        WHEN sourceipaddress LIKE '52.%' OR sourceipaddress LIKE '54.%' THEN 'AWS Services'
        WHEN sourceipaddress LIKE '13.%' OR sourceipaddress LIKE '18.%' THEN 'US West Coast'
        ELSE 'Unknown Location'
    END AS location_name,
    
    -- Add IP classification
    CASE 
        WHEN sourceipaddress LIKE '10.%' OR sourceipaddress LIKE '172.%' OR sourceipaddress LIKE '192.168.%' THEN 'Private'
        WHEN sourceipaddress LIKE '52.%' OR sourceipaddress LIKE '54.%' OR sourceipaddress LIKE '18.%' THEN 'AWS'
        WHEN sourceipaddress LIKE '20.%' OR sourceipaddress LIKE '40.%' THEN 'Azure'
        ELSE 'Public'
    END AS ip_classification,
    
    -- Event count for aggregation
    1 as event_count
    
FROM cloudtrail_logs
WHERE sourceipaddress IS NOT NULL 
    AND sourceipaddress != ''
    AND sourceipaddress != '-'
    AND eventtime >= current_date - interval '30' day  -- Last 30 days for performance
;