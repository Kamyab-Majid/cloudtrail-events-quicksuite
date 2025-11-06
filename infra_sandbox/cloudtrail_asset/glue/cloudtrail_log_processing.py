import sys
import os
import re
import math
import time
import logging
import threading
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

import boto3
from awsglue.utils import getResolvedOptions
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.context import SparkContext
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, explode, to_date, to_timestamp, from_utc_timestamp
from pyspark.sql.utils import AnalysisException

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
log_lock = threading.Lock()

def thread_safe_log(level, message):
    with log_lock:
        if level == "info":
            logger.info(message)
        elif level == "warning":
            logger.warning(message)
        elif level == "error":
            logger.error(message)
        else:
            logger.info(message)

def delete_using_paginator(s3_client, paginator, bucket, prefix):
    try:
        objects_to_delete = []
        pages = paginator.paginate(Bucket=bucket, Prefix=prefix)
        for page in pages:
            for obj in page.get("Contents", []):
                objects_to_delete.append({"Key": obj["Key"]})
                if len(objects_to_delete) == 1000:
                    s3_client.delete_objects(Bucket=bucket, Delete={"Objects": objects_to_delete})
                    thread_safe_log("info", f"Deleted 1000 objects from {bucket} under {prefix}")
                    objects_to_delete = []
        if objects_to_delete:
            s3_client.delete_objects(Bucket=bucket, Delete={"Objects": objects_to_delete})
            thread_safe_log("info", f"Deleted {len(objects_to_delete)} remaining objects from {bucket} under {prefix}")
    except Exception as e:
        thread_safe_log("error", f"Error in delete_using_paginator for {prefix}: {e}")
        raise

def delete_using_purge_and_paginator(glue_context, s3_purge_path, retention_period_hours_rounded, s3_client, paginator, bucket, prefix):
    max_retries = 3
    base_sleep = 10
    try:
        for iteration in range(10):
            retry = 0
            while retry < max_retries:
                try:
                    glue_context.purge_s3_path(s3_purge_path, {"retentionPeriod": retention_period_hours_rounded})
                    break
                except Exception as e:
                    msg = str(e)
                    if "SlowDown" in msg or "503" in msg:
                        retry += 1
                        sleep_sec = base_sleep * (2 ** (retry - 1))
                        thread_safe_log("warning", f"S3 SlowDown on purge attempt {iteration+1} retry {retry}. Sleeping {sleep_sec}s for prefix {prefix}")
                        time.sleep(sleep_sec)
                        if retry >= max_retries:
                            thread_safe_log("error", f"Max purge retries reached for prefix {prefix}")
                            raise
                    else:
                        raise
            if iteration < 9:
                time.sleep(2)
        today_suffix = datetime.utcnow().strftime("%Y/%m/%d/")
        if not s3_purge_path.endswith(today_suffix):
            retry = 0
            while retry < max_retries:
                try:
                    delete_using_paginator(s3_client, paginator, bucket, prefix)
                    break
                except Exception as e:
                    msg = str(e)
                    if "SlowDown" in msg or "503" in msg:
                        retry += 1
                        sleep_sec = base_sleep * (2 ** (retry - 1))
                        thread_safe_log("warning", f"S3 SlowDown on paginator delete retry {retry}. Sleeping {sleep_sec}s for prefix {prefix}")
                        time.sleep(sleep_sec)
                        if retry >= max_retries:
                            thread_safe_log("error", f"Max paginator retries for prefix {prefix}")
                            raise
                    else:
                        raise
        thread_safe_log("info", f"Successfully purged {s3_purge_path} retention_hours={retention_period_hours_rounded}")
    except Exception as e:
        thread_safe_log("error", f"delete_using_purge_and_paginator error for {prefix}: {e}")
        raise

def process_region_deletion_async(glue_context, s3_purge_path, retention_period_hours_rounded, s3_client, paginator, bucket, prefix):
    try:
        thread_safe_log("info", f"Starting deletion for {prefix}")
        delete_using_purge_and_paginator(glue_context, s3_purge_path, retention_period_hours_rounded, s3_client, paginator, bucket, prefix)
        res = {"status": "success", "prefix": prefix}
        thread_safe_log("info", f"Deletion success for {prefix}")
        return res
    except Exception as e:
        thread_safe_log("error", f"Deletion failed for {prefix}: {e}")
        return {"status": "error", "prefix": prefix, "error": str(e)}

def extract_region_from_prefix(prefix):
    """Extract AWS region from CloudTrail prefix path."""
    # Pattern: AWSLogs/{account_id}/CloudTrail/{region}/
    match = re.search(r'/CloudTrail/([a-z]{2}-[a-z]+-\d)/', prefix)
    if match:
        return match.group(1)
    return None

def create_spark_session(logging_bucket_name: str) -> SparkSession:
    spark_builder = (
        SparkSession.builder
        .config("spark.sql.extensions", "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
        .config("spark.sql.catalog.glue_catalog", "org.apache.iceberg.spark.SparkCatalog")
        .config("spark.sql.catalog.glue_catalog.catalog-impl", "org.apache.iceberg.aws.glue.GlueCatalog")
        .config("spark.sql.catalog.glue_catalog.io-impl", "org.apache.iceberg.aws.s3.S3FileIO")
        .config("spark.sql.catalog.glue_catalog.warehouse", f"s3://{logging_bucket_name}/glue_job_tmp/")
        .config("spark.sql.files.maxPartitionBytes", "134217728")
        .config("spark.sql.files.openCostInBytes", "4194304")
        .config("spark.sql.adaptive.enabled", "true")
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
        .config("spark.sql.adaptive.coalescePartitions.minPartitionNum", "1")
        .config("spark.sql.adaptive.coalescePartitions.initialPartitionNum", "20")
        .config("spark.sql.adaptive.maxRecordsPerPartition", "2000000")
        .config("spark.sql.adaptive.advisoryPartitionSizeInBytes", "268435456")
        .config("spark.sql.autoBroadcastJoinThreshold", "10485760")
        .config("spark.serializer", "org.apache.spark.serializer.KryoSerializer")
        .config("spark.sql.execution.arrow.pyspark.enabled", "true")
        .config("spark.sql.adaptive.localShuffleReader.enabled", "true")
        .config("spark.sql.json.compression.codec", "gzip")
        .config("spark.sql.caseSensitive", "false")
    )
    return spark_builder.getOrCreate()

def process_dataframe_with_partitioning(df, spark_context, stage_name):
    try:
        row_count = df.count()
        optimal_partitions = max(1, int(row_count / 200000))
        current_partitions = df.rdd.getNumPartitions()
        if optimal_partitions != current_partitions:
            df = df.repartition(optimal_partitions, "event_date")
            thread_safe_log("info", f"{stage_name} repartitioned from {current_partitions} to {optimal_partitions}")
        else:
            thread_safe_log("info", f"{stage_name} partitions OK {current_partitions}")
    except Exception as e:
        thread_safe_log("warning", f"{stage_name} partition optimize failed: {e}")
        df = df.repartition("event_date")
    return df

from pyspark.sql.types import StructType, StructField, StringType, BooleanType, ArrayType, MapType

def get_cloudtrail_schema():
    """Define explicit CloudTrail schema matching AWS Athena CloudTrail table definition."""
    return StructType([
        StructField("eventVersion", StringType(), True),
        StructField("userIdentity", StructType([
            StructField("type", StringType(), True),
            StructField("principalId", StringType(), True),
            StructField("arn", StringType(), True),
            StructField("accountId", StringType(), True),
            StructField("invokedBy", StringType(), True),
            StructField("accessKeyId", StringType(), True),
            StructField("userName", StringType(), True),
            StructField("sessionContext", StructType([
                StructField("attributes", StructType([
                    StructField("mfaAuthenticated", StringType(), True),
                    StructField("creationDate", StringType(), True)
                ]), True),
                StructField("sessionIssuer", StructType([
                    StructField("type", StringType(), True),
                    StructField("principalId", StringType(), True),
                    StructField("arn", StringType(), True),
                    StructField("accountId", StringType(), True),
                    StructField("username", StringType(), True)
                ]), True),
                StructField("ec2RoleDelivery", StringType(), True),
                StructField("webIdFederationData", StructType([
                    StructField("federatedProvider", StringType(), True),
                    StructField("attributes", MapType(StringType(), StringType()), True)
                ]), True)
            ]), True)
        ]), True),
        StructField("eventTime", StringType(), True),
        StructField("eventSource", StringType(), True),
        StructField("eventName", StringType(), True),
        StructField("awsRegion", StringType(), True),
        StructField("sourceIpAddress", StringType(), True),
        StructField("userAgent", StringType(), True),
        StructField("errorCode", StringType(), True),
        StructField("errorMessage", StringType(), True),
        StructField("requestParameters", StringType(), True),
        StructField("responseElements", StringType(), True),
        StructField("additionalEventData", StringType(), True),
        StructField("requestId", StringType(), True),
        StructField("eventId", StringType(), True),
        StructField("resources", ArrayType(StructType([
            StructField("arn", StringType(), True),
            StructField("accountId", StringType(), True),
            StructField("type", StringType(), True)
        ])), True),
        StructField("eventType", StringType(), True),
        StructField("apiVersion", StringType(), True),
        StructField("readOnly", StringType(), True),
        StructField("recipientAccountId", StringType(), True),
        StructField("serviceEventDetails", StringType(), True),
        StructField("sharedEventID", StringType(), True),
        StructField("vpcEndpointId", StringType(), True),
        StructField("tlsDetails", StructType([
            StructField("tlsVersion", StringType(), True),
            StructField("cipherSuite", StringType(), True),
            StructField("clientProvidedHostHeader", StringType(), True)
        ]), True),
        StructField("managementEvent", StringType(), True),
        StructField("eventCategory", StringType(), True),
        StructField("vpcEndpointAccountId", StringType(), True)
    ])

def get_cloudtrail_records_schema():
    """Wrapper schema for CloudTrail files that have Records array."""
    return StructType([
        StructField("Records", ArrayType(get_cloudtrail_schema()), True)
    ])

def cleanup_dataframe_cache(df, stage_name):
    try:
        df.unpersist()
        thread_safe_log("info", f"{stage_name} unpersisted")
    except Exception as e:
        thread_safe_log("warning", f"{stage_name} unpersist failed: {e}")

args = getResolvedOptions(
    sys.argv,
    [
        "JOB_NAME",
        "input_path",
        "output_path",
        "database_name",
        "account_id",
        "retention_days_for_processed_logs",
        "prefix"
    ]
)

JOB_NAME = args["JOB_NAME"]
s3_input_path = args["input_path"]
s3_output_path = args["output_path"]
database_name = args["database_name"]
account_id = args["account_id"]
retention_days_for_processed_logs = int(args["retention_days_for_processed_logs"])
specific_prefix = args["prefix"]

if not s3_input_path or not s3_output_path:
    thread_safe_log("error", "input_path or output_path missing")
    raise ValueError("input_path or output_path missing")

# Extract region from prefix
region_to_process = extract_region_from_prefix(specific_prefix)
if not region_to_process:
    thread_safe_log("error", f"Could not extract region from prefix: {specific_prefix}")
    raise ValueError(f"Invalid prefix format: {specific_prefix}")

thread_safe_log("info", f"Extracted region from prefix: {region_to_process}")

logging_bucket_name = s3_input_path.split("/")[2]
s3_client = boto3.client("s3")
paginator = s3_client.get_paginator("list_objects_v2")
glue_context = None

spark = create_spark_session(logging_bucket_name)
sc = spark.sparkContext
glueContext = GlueContext(sc)
glue_context = glueContext
job = Job(glueContext)
job.init(JOB_NAME, args)

today_utc = datetime.utcnow()
current_date_str = today_utc.strftime("%Y-%m-%d")
table_name = "cloudtrail_events"
table_output_path = f"{s3_output_path.rstrip('/')}/{table_name}"

# Use the specific prefix provided
if specific_prefix:
    # Ensure prefix ends with / for consistency
    if not specific_prefix.endswith("/"):
        specific_prefix = f"{specific_prefix}/"
    subfolders = [specific_prefix]
    thread_safe_log("info", f"Processing specific prefix: {specific_prefix}")
else:
    thread_safe_log("error", "No prefix provided")
    job.commit()
    sys.exit(1)

if not subfolders:
    thread_safe_log("info", f"No prefixes to process. Exiting.")
    job.commit()
    sys.exit(0)

deletion_futures = []
max_concurrent_deletions = 3
successful_deletions = 0
failed_deletions = 0

with ThreadPoolExecutor(max_workers=max_concurrent_deletions) as executor:
    for day_prefix in subfolders:
        region_input_path = f"s3://{logging_bucket_name}/{day_prefix}"
        thread_safe_log("info", f"Processing prefix {region_input_path}")
        start_time = time.time()
        cloudtrail_records_schema = get_cloudtrail_records_schema()
        
        try:
            # Read with explicit schema to avoid duplicate column issues from schema inference
            df_raw = (
                spark.read.option("recursiveFileLookup", "true")
                .option("multiLine", "true")
                .option("mode", "PERMISSIVE")
                .option("columnNameOfCorruptRecord", "_corrupt_record")
                .schema(cloudtrail_records_schema)
                .json(region_input_path)
            )
        except Exception as e:
            thread_safe_log("error", f"Read failure for {region_input_path}: {e}")
            continue

        if "_corrupt_record" in df_raw.columns:
            corrupt_count = df_raw.filter(col("_corrupt_record").isNotNull()).count()
            if corrupt_count > 0:
                thread_safe_log("warning", f"Found {corrupt_count} corrupt records in {region_input_path}")
            df_raw = df_raw.filter(col("_corrupt_record").isNull()).drop("_corrupt_record")

        if "Records" in df_raw.columns:
            df = df_raw.select(explode(col("Records")).alias("record")).select("record.*")
        else:
            thread_safe_log("warning", f"No Records array in {region_input_path}; attempting to infer top-level records")
            df = df_raw



        if "eventTime" in df.columns:
            df = df.withColumn("event_time", to_timestamp(col("eventTime")))
            df = df.withColumn("event_time_local", from_utc_timestamp(col("event_time"), "America/Toronto"))
            df = df.withColumn("event_date", to_date(col("event_time_local")))
        else:
            df = df.withColumn("event_time", to_timestamp(col("eventTime")))
            df = df.withColumn("event_date", to_date(col("event_time")))
        
        # Add region as a column for partitioning
        from pyspark.sql.functions import lit
        df = df.withColumn("region", lit(region_to_process))

        df = process_dataframe_with_partitioning(df, sc, f"prefix_{day_prefix}")

        df = df.sortWithinPartitions("event_time")

        temp_view = f"tmp_{table_name}_{region_to_process.replace('-', '_')}_{current_date_str.replace('-', '_')}"
        df.createOrReplaceTempView(temp_view)

        try:
            create_db_sql = f"CREATE DATABASE IF NOT EXISTS glue_catalog.{database_name}"
            spark.sql(create_db_sql)
            
            # Check if table exists
            table_exists = False
            try:
                spark.sql(f"DESCRIBE TABLE glue_catalog.{database_name}.{table_name}")
                table_exists = True
                thread_safe_log("info", f"Table glue_catalog.{database_name}.{table_name} already exists")
            except AnalysisException:
                table_exists = False
            
            if not table_exists:
                # Create table with schema from the first batch of data
                create_table_sql = f"""
                    CREATE TABLE glue_catalog.{database_name}.{table_name} 
                    USING iceberg 
                    LOCATION '{table_output_path}' 
                    TBLPROPERTIES ('format-version'='2') 
                    PARTITIONED BY (region, event_date)
                    AS SELECT * FROM {temp_view}
                """
                spark.sql(create_table_sql)
                thread_safe_log("info", f"Created Iceberg table glue_catalog.{database_name}.{table_name} with partitions (region, event_date)")
            else:
                # Table exists, just insert data
                insert_sql = f"INSERT INTO glue_catalog.{database_name}.{table_name} SELECT * FROM {temp_view}"
                spark.sql(insert_sql)
                thread_safe_log("info", f"Inserted data into glue_catalog.{database_name}.{table_name} for region={region_to_process}, event_date={current_date_str}")
        except Exception as e:
            thread_safe_log("error", f"Failed to create/insert into table: {e}")
            raise

        cleanup_dataframe_cache(df, f"prefix_{day_prefix}")

        end_time = time.time()
        processing_hours = (end_time - start_time) / 3600
        retention_period_hours_rounded = math.ceil(max(1, processing_hours))
        thread_safe_log("info", f"Processed {day_prefix} in {processing_hours:.2f}h -> retention hours {retention_period_hours_rounded}")

        s3_purge_path = region_input_path if region_input_path.endswith("/") else f"{region_input_path}/"
        future = executor.submit(
            process_region_deletion_async,
            glueContext,
            s3_purge_path,
            retention_period_hours_rounded,
            s3_client,
            paginator,
            logging_bucket_name,
            day_prefix
        )
        deletion_futures.append(future)

    for fut in as_completed(deletion_futures):
        try:
            res = fut.result(timeout=600)
            if res.get("status") == "success":
                successful_deletions += 1
            else:
                failed_deletions += 1
        except Exception as e:
            failed_deletions += 1
            thread_safe_log("error", f"Deletion future exception: {e}")

thread_safe_log("info", f"Deletion summary: {successful_deletions} success, {failed_deletions} failed")

try:
    retention_cutoff = (datetime.utcnow() - timedelta(days=retention_days_for_processed_logs)).strftime("%Y-%m-%d")
    delete_query = f"DELETE FROM glue_catalog.{database_name}.{table_name} WHERE event_date < DATE '{retention_cutoff}'"
    spark.sql(delete_query)
    expire_query = f"CALL glue_catalog.system.expire_snapshots(table => 'glue_catalog.{database_name}.{table_name}', retain_last => 2)"
    spark.sql(expire_query)
    remove_orphan_query = f"CALL glue_catalog.system.remove_orphan_files(table => 'glue_catalog.{database_name}.{table_name}', dry_run => false)"
    spark.sql(remove_orphan_query)
    thread_safe_log("info", f"Retention cleanup executed for glue_catalog.{database_name}.{table_name} older than {retention_cutoff}")
except Exception as e:
    thread_safe_log("error", f"Retention cleanup failed: {e}")

spark.catalog.clearCache()
thread_safe_log("info", "Job completed")
job.commit()