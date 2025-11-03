"""CDK Main app"""

# import json
import os

import aws_cdk as cdk
from cdk_nag import AwsSolutionsChecks

from infra_sandbox.cloudtrail_stack import CloudTrailWithKmsAndIcebergStack

app = cdk.App()

environment = os.environ.get("ENVIRONMENT", "dev")
# Grab the config from cdk.json context(s)
config_vars = app.node.try_get_context(environment)

env = cdk.Environment(account=config_vars["account-id"], region=config_vars["region"])
print(env)
account = config_vars["account-id"]
region = os.getenv("CDK_DEFAULT_REGION", "us-east-1")

CloudTrailWithKmsAndIcebergStack(
    app, "CloudTrailWithKmsStack", env_vars=config_vars, log_expiration_days=12, env=env
)


cdk.Aspects.of(app).add(AwsSolutionsChecks())

app.synth()
