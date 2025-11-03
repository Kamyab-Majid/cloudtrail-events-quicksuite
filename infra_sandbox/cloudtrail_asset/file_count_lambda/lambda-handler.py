import boto3


def lambda_handler(event, context):
    try:
        s3_client = boto3.client("s3")
        bucket_name = event.get("bucket_name")
        prefix = event.get("prefix")

        paginator = s3_client.get_paginator("list_objects_v2")
        count_iterator = paginator.paginate(Bucket=bucket_name, Prefix=prefix).search(
            "KeyCount"
        )
        total_keys = sum(count for count in count_iterator if count)
        print(f"event: {event}")

        print(f"total keys: {total_keys}, prefix: {prefix}")
        return {"statusCode": 200, "prefix": prefix, "file_count": total_keys}

    except Exception as e:
        return {
            "statusCode": 500,
            "error": str(e),
            "prefix": prefix,
            "file_count": 1000000,
        }
