import os

import aws_cdk.aws_events as events
from aws_cdk import Aws, Duration, RemovalPolicy, Stack
from aws_cdk import aws_cloudtrail as cloudtrail
from aws_cdk import aws_events_targets as targets
from aws_cdk import aws_glue_alpha as alpha_glue
from aws_cdk import aws_iam as iam
from aws_cdk import aws_kms as kms
from aws_cdk import aws_s3 as s3
from cdk_nag import NagSuppressions
from constructs import Construct
from playbook.cdk.eventbridge_construct import PlaybookEventBridgeRule
from playbook.cdk.lambda_construct import PlaybookLambdaFunction
from playbook.cdk.stepfunction_construct import PlaybookStepFunctionSM


class CloudTrailWithKmsAndIcebergStack(Stack):
    def __init__(
        self,
        scope: Construct,
        id: str,
        env_vars,
        env,
        log_expiration_days: int,
        **kwargs,
    ):
        with open(
            os.path.join(
                os.path.dirname(__file__),
                "cloudtrail_asset",
                "cloudtrail_logs_orchestrator.asl.json",
            )
        ) as f:
            step_function_definition_str = f.read()

        super().__init__(scope, id, **kwargs)

        account_id = env_vars["account-id"]
        region = env_vars["region"]

        cloudtrail_bucket_name = (
            f"{env_vars['env']}-{account_id}-cloudtrail-logs-bucket"
        )

        # Create KMS key for CloudTrail
        kms_key = kms.Key(
            self,
            "CloudTrailLogsKey",
            alias="alias/cloudtrail-logs-key",
            enable_key_rotation=True,
            removal_policy=RemovalPolicy.RETAIN,
        )

        # Allow account root full key access
        kms_key.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AllowRootAccountFullAccess",
                principals=[iam.AccountRootPrincipal()],
                actions=["kms:*"],
                resources=["*"],
            )
        )

        # CloudTrail requires GenerateDataKey permission
        kms_key.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AllowCloudTrailGenerateDataKey",
                principals=[iam.ServicePrincipal("cloudtrail.amazonaws.com")],
                actions=[
                    "kms:GenerateDataKey*",
                    "kms:DescribeKey",
                ],
                resources=["*"],
                conditions={
                    "StringLike": {
                        "kms:EncryptionContext:aws:cloudtrail:arn": f"arn:aws:cloudtrail:{region}:{account_id}:trail/*"
                    }
                },
            )
        )

        # CloudTrail decrypt permissions
        kms_key.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AllowCloudTrailDecrypt",
                principals=[iam.ServicePrincipal("cloudtrail.amazonaws.com")],
                actions=[
                    "kms:Decrypt",
                    "kms:ReEncryptFrom",
                ],
                resources=["*"],
                conditions={
                    "StringEquals": {"kms:CallerAccount": account_id},
                    "StringLike": {
                        "kms:EncryptionContext:aws:cloudtrail:arn": f"arn:aws:cloudtrail:{region}:{account_id}:trail/*"
                    },
                },
            )
        )

        # S3 bucket for CloudTrail logs with processing structure
        trail_bucket = s3.Bucket(
            self,
            "CloudTrailLogsBucket",
            bucket_name=cloudtrail_bucket_name,
            encryption=s3.BucketEncryption.KMS,
            encryption_key=kms_key,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            object_ownership=s3.ObjectOwnership.BUCKET_OWNER_ENFORCED,
            lifecycle_rules=[
                s3.LifecycleRule(
                    expiration=Duration.days(14),
                    prefix="athena_output",
                ),
                s3.LifecycleRule(
                    expiration=Duration.days(14),
                    prefix="raw-cloudtrail-logs",
                ),
                s3.LifecycleRule(
                    expiration=Duration.days(14),
                    prefix="spark-ui",
                ),
            ],
        )

        # Allow CloudTrail to GetBucketAcl
        trail_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AllowCloudTrailGetBucketAcl",
                principals=[iam.ServicePrincipal("cloudtrail.amazonaws.com")],
                actions=["s3:GetBucketAcl"],
                resources=[trail_bucket.bucket_arn],
            )
        )

        # Allow CloudTrail to PutObject
        trail_bucket.add_to_resource_policy(
            iam.PolicyStatement(
                sid="AllowCloudTrailPutObject",
                principals=[iam.ServicePrincipal("cloudtrail.amazonaws.com")],
                actions=["s3:PutObject"],
                resources=[
                    f"{trail_bucket.bucket_arn}/raw-cloudtrail-logs/AWSLogs/{account_id}/*"
                ],
                conditions={
                    "StringEquals": {"s3:x-amz-acl": "bucket-owner-full-control"}
                },
            )
        )

        # Suppress CDK-Nag Warnings
        NagSuppressions.add_stack_suppressions(
            self,
            suppressions=[
                {
                    "id": "AwsSolutions-IAM5",
                    "reason": "The IAM entity contains wildcard permissions and it needs them.",
                },
                {
                    "id": "AwsSolutions-SF1",
                    "reason": "The Step Function does not log ALL events to CloudWatch Logs.",
                },
                {
                    "id": "AwsSolutions-SF2",
                    "reason": "The Step Function does not have X-Ray tracing enabled.",
                },
            ],
        )

        # IAM Role for Glue
        glue_role = iam.Role(
            self,
            "GlueJobRole",
            assumed_by=iam.ServicePrincipal("glue.amazonaws.com"),
            role_name=f"nfl-dna-gridiron-su-glue-cloudtrail-{env_vars['env']}",
            inline_policies={
                "glue-job-policy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=[
                                "s3:GetObject",
                                "s3:PutObject",
                                "s3:ListBucket",
                                "s3:DeleteObject",
                            ],
                            resources=[
                                trail_bucket.bucket_arn,
                                f"{trail_bucket.bucket_arn}/*",
                            ],
                        ),
                        iam.PolicyStatement(
                            actions=[
                                "s3:ListAllMyBuckets",
                            ],
                            resources=["*"],
                        ),
                        iam.PolicyStatement(
                            actions=[
                                "kms:Decrypt",
                                "kms:DescribeKey",
                                "kms:GenerateDataKey",
                            ],
                            resources=[kms_key.key_arn],
                        ),
                    ]
                )
            },
        )

        glue_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "glue:GetTable",
                    "glue:GetTables",
                    "glue:BatchCreatePartition",
                    "glue:BatchDeletePartition",
                    "glue:BatchGetPartition",
                    "glue:UpdatePartition",
                    "glue:UpdateTable",
                    "glue:GetDatabase",
                    "glue:CreateDatabase",
                    "glue:CreateTable",
                ],
                resources=[
                    f"arn:aws:glue:{region}:{account_id}:database/cloudtrail_logs",
                    f"arn:aws:glue:{region}:{account_id}:catalog",
                    f"arn:aws:glue:{region}:{account_id}:table/cloudtrail_logs/*",
                    f"arn:aws:glue:{region}:{account_id}:database/default",
                ],
            )
        )

        glue_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "iam:PassRole",
                ],
                resources=[glue_role.role_arn],
            )
        )

        glue_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "logs:CreateLogGroup",
                    "logs:CreateLogStream",
                    "logs:PutLogEvents",
                ],
                resources=[
                    f"arn:aws:logs:{region}:{account_id}:log-group:/aws-glue/jobs*",
                    f"arn:aws:logs:{region}:{account_id}:log-group:/aws-glue/crawlers*",
                ],
            )
        )

        default_arguments = {
            "--input_path": f"s3://{cloudtrail_bucket_name}/raw-cloudtrail-logs/",
            "--output_path": f"s3://{cloudtrail_bucket_name}/processed-cloudtrail-logs/",
            "--account_id": account_id,
            "--region": region,
            "--database_name": "cloudtrail_logs",
            "--crawler_role": glue_role.role_arn,
            "--log_level": "INFO",
            "--datalake-formats": "iceberg",
            "--retention_days_for_processed_logs": str(log_expiration_days),
        }

        env_account_id = env_vars.get("account-id", "unknown-account")
        if env_account_id in ["067157108346", "397422540095"]:
            number_of_workers = 10
            worker_type = alpha_glue.WorkerType.G_1_X
        else:
            number_of_workers = 5
            worker_type = alpha_glue.WorkerType.G_1_X

        # Glue Job Definition for CloudTrail processing
        glue_job_name = "infra_glue_transform_cloudtrail_logs"
        _ = alpha_glue.Job(
            self,
            "CloudTrailLoggingGlueJob",
            job_name=glue_job_name,
            role=glue_role,
            worker_count=number_of_workers,
            max_concurrent_runs=25,
            timeout=Duration.hours(10),
            max_retries=2,
            spark_ui=alpha_glue.SparkUIProps(
                enabled=True, bucket=trail_bucket, prefix="spark-ui/"
            ),
            worker_type=worker_type,
            executable=alpha_glue.JobExecutable.python_etl(
                glue_version=alpha_glue.GlueVersion.V4_0,
                python_version=alpha_glue.PythonVersion.THREE,
                script=alpha_glue.Code.from_asset(
                    os.path.join(
                        os.path.dirname(__file__),
                        "cloudtrail_asset",
                        "cloudtrail_log_processing.py",
                    )
                ),
            ),
            default_arguments=default_arguments,
        )

        self.trail_bucket = trail_bucket

        # Lambda functions for orchestration
        file_count_lambda_path = os.path.join(
            os.path.dirname(__file__),
            "cloudtrail_asset",
            "file_count_lambda",
            "lambda-handler.py",
        )
        file_count_lambda = PlaybookLambdaFunction(
            self,
            "CountCloudTrailFilesLambda",
            nag_suppression=NagSuppressions,
            env_vars=env_vars,
            lambda_path=file_count_lambda_path,
            timeout=Duration.minutes(15),
            memory_size=512,
            additional_iam_policies={
                "lambda_policy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["s3:ListBucket"],
                            resources=[
                                f"arn:aws:s3:::{cloudtrail_bucket_name}",
                                f"arn:aws:s3:::{cloudtrail_bucket_name}/*",
                            ],
                        )
                    ]
                )
            },
        )

        last_7_days_lambda_path = os.path.join(
            os.path.dirname(__file__),
            "cloudtrail_asset",
            "last_7_days_lambda",
            "lambda-handler.py",
        )
        last_7_days_lambda = PlaybookLambdaFunction(
            self,
            "GetLastDaysCloudTrailLambda",
            nag_suppression=NagSuppressions,
            env_vars=env_vars,
            function_env_vars={
                "ACCOUNT_ID": account_id,
                "REGION": region,
            },
            lambda_path=last_7_days_lambda_path,
            timeout=Duration.minutes(2),
            additional_iam_policies={
                "lambda_policy": iam.PolicyDocument(
                    statements=[
                        iam.PolicyStatement(
                            actions=["s3:ListBucket"],
                            resources=[
                                f"arn:aws:s3:::{cloudtrail_bucket_name}",
                                f"arn:aws:s3:::{cloudtrail_bucket_name}/*",
                            ],
                        )
                    ]
                )
            },
            memory_size=512,
        )

        max_file_count_lambda_path = os.path.join(
            os.path.dirname(__file__),
            "cloudtrail_asset",
            "max_file_count_lambda",
            "lambda-handler.py",
        )
        max_file_count_lambda = PlaybookLambdaFunction(
            self,
            "FindMaxFileCountCloudTrailLambda",
            nag_suppression=NagSuppressions,
            env_vars=env_vars,
            lambda_path=max_file_count_lambda_path,
            timeout=Duration.minutes(2),
            memory_size=512,
        )

        policy_statements = [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "glue:StartJobRun",
                    "glue:GetJobRun",
                    "glue:GetJobRuns",
                    "glue:BatchStopJobRun",
                ],
                resources=["*"],
            ),
            iam.PolicyStatement(
                sid="AllowS3List",
                effect=iam.Effect.ALLOW,
                actions=["s3:ListAllMyBuckets"],
                resources=["*"],
            ),
            iam.PolicyStatement(
                sid="AllowListCloudTrailBucket",
                effect=iam.Effect.ALLOW,
                actions=["s3:ListBucket"],
                resources=[f"arn:aws:s3:::{cloudtrail_bucket_name}"],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "xray:PutTraceSegments",
                    "xray:PutTelemetryRecords",
                    "xray:GetSamplingRules",
                    "xray:GetSamplingTargets",
                ],
                resources=["*"],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["lambda:InvokeFunction"],
                resources=[
                    f"arn:aws:lambda:{region}:{account_id}:function:{file_count_lambda.function_name}",
                    f"arn:aws:lambda:{region}:{account_id}:function:{last_7_days_lambda.function_name}",
                    f"arn:aws:lambda:{region}:{account_id}:function:{max_file_count_lambda.function_name}",
                ],
            ),
        ]

        step_function_definition_str = step_function_definition_str.replace(
            "cloudtrail_logging_bucket_name", cloudtrail_bucket_name
        )
        step_function_definition_str = step_function_definition_str.replace(
            "{env_vars['account-id']}", account_id
        )
        step_function_definition_str = step_function_definition_str.replace(
            "{env_vars['env']}", env_vars["env"]
        )

        # Create a Step Function to trigger the Glue job
        step_function = PlaybookStepFunctionSM(
            self,
            "CloudTrailLogsStepFunction",
            nag_suppression=NagSuppressions,
            env_vars=env_vars,
            state_machine_policy_statements=policy_statements,
            definition_string=step_function_definition_str,
        )

        event_bridge_rule = PlaybookEventBridgeRule(
            self,
            "CloudTrailLogsEventBridgeRule",
            nag_suppression=NagSuppressions,
            env_vars=env_vars,
            schedule=events.Schedule.cron(minute="0", hour="23", week_day="SUN"),
        )

        # Add the Step Function as a target for the EventBridge rule
        event_bridge_rule.rule.add_target(
            targets.SfnStateMachine(step_function.state_machine)
        )

        # CloudTrail configuration - writes to raw-cloudtrail-logs prefix
        trail = cloudtrail.Trail(
            self,
            "AllEventsTrail",
            bucket=trail_bucket,
            s3_key_prefix="raw-cloudtrail-logs",
            encryption_key=kms_key,
            is_multi_region_trail=True,
            include_global_service_events=True,
            enable_file_validation=True,
            management_events=cloudtrail.ReadWriteType.ALL,
        )
        target_bucket_name = "test-bucket"
        target_bucket = s3.Bucket.from_bucket_name(
            self, "TargetBucketRef", target_bucket_name
        )
        trail.add_s3_event_selector(
            s3_selector=[
                cloudtrail.S3EventSelector(
                    bucket=trail_bucket,
                ),
                cloudtrail.S3EventSelector(
                    bucket=target_bucket,
                ),
            ],
            read_write_type=cloudtrail.ReadWriteType.ALL,
            include_management_events=True,
        )
