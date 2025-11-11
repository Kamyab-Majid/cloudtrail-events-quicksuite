from typing import List

import boto3

s3_client = boto3.client("s3")


def lambda_handler(event, context):
    """
    Recursively list all day-level prefixes in CloudTrail logs structure.
    Expected structure: raw-cloudtrail-logs/AWSLogs/{account}/CloudTrail/{region}/{year}/{month}/{day}/
    """
    bucket_name = event["bucket_name"]
    base_prefix = event["base_prefix"]

    day_prefixes = []

    try:
        # Get all regions
        regions = list_prefixes(bucket_name, base_prefix)

        for region_prefix in regions:
            # Get all years for this region
            years = list_prefixes(bucket_name, region_prefix)

            for year_prefix in years:
                # Get all months for this year
                months = list_prefixes(bucket_name, year_prefix)

                for month_prefix in months:
                    # Get all days for this month
                    days = list_prefixes(bucket_name, month_prefix)
                    day_prefixes.extend(days)

        return {
            "statusCode": 200,
            "day_prefixes": day_prefixes,
            "total_count": len(day_prefixes),
        }

    except Exception as e:
        print(f"Error listing prefixes: {str(e)}")
        return {"statusCode": 500, "error": str(e), "day_prefixes": []}


def list_prefixes(bucket: str, prefix: str) -> List[str]:
    """
    List all common prefixes (subdirectories) under the given prefix.
    """
    prefixes = []
    paginator = s3_client.get_paginator("list_objects_v2")

    pages = paginator.paginate(Bucket=bucket, Prefix=prefix, Delimiter="/")

    for page in pages:
        if "CommonPrefixes" in page:
            for common_prefix in page["CommonPrefixes"]:
                prefixes.append(common_prefix["Prefix"])

    return prefixes
