"""CDK Main app"""

import aws_cdk as cdk

from infra_sandbox.cloudtrail_stack import CloudTrailWithKmsAndIcebergStack

app = cdk.App()

stack = CloudTrailWithKmsAndIcebergStack(
    app, "CloudTrailWithKmsStack"
)

app.synth()
