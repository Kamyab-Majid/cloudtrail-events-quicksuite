def lambda_handler(event, context):
    try:
        file_counts = event.get("fileCounts", [])

        max_count = 0
        max_prefix = ""

        for item in file_counts:
            payload = item.get("Payload", {})
            if payload.get("statusCode") == 200:
                count = payload.get("file_count", 0)
                if count > max_count:
                    max_count = count
                    max_prefix = payload.get("prefix", "")
        print(f"event: {event}")
        print(
            f"max_count: {max_count}, max_prefix: {max_prefix}, file_counts: {file_counts}"
        )
        return {
            "statusCode": 200,
            "maxCount": max_count,
            "maxPrefix": max_prefix,
            "totalDaysProcessed": len(file_counts),
        }

    except Exception as e:
        return {"statusCode": 500, "error": str(e), "maxCount": 0}
