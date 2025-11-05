# CloudTrail Stack Deployment Guide

## Prerequisites
- AWS CLI installed and configured
- An S3 bucket for Lambda code and Glue scripts

## Deployment Steps

### 1. Package Lambda Functions and Glue Scripts
```bash
./package-assets.sh
```

This creates a `deployment-assets/` directory with:
- `lambda/count-files.zip`
- `lambda/last-days.zip`
- `lambda/max-count.zip`
- `glue/cloudtrail_log_processing.py`

### 2. Upload Assets to S3
```bash
# Create S3 bucket (one-time)
aws s3 mb s3://my-cloudtrail-assets

# Upload assets
aws s3 sync deployment-assets/ s3://my-cloudtrail-assets/
```

### 3. Deploy the CloudFormation Stack
```bash
aws cloudformation deploy \
  --template-file template.yaml \
  --stack-name CloudTrailStack \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    AssetsBucket=my-cloudtrail-assets \
    ResourcePrefix=cloudtrail \
    Environment=dev \
    LogExpirationDays=14 \
    NumberOfWorkers=5 \
  --s3-bucket my-cloudtrail-assets
```

## Parameters

- **ResourcePrefix**: Prefix for resource names (default: `cloudtrail`)
- **Environment**: Environment name like dev, prod (default: `dev`)
- **LogExpirationDays**: Days to retain logs (default: `14`)
- **NumberOfWorkers**: Number of Glue workers (default: `5`)

## Multiple Deployments

To deploy multiple instances in the same account, use different ResourcePrefix values:

```bash
# Team 1 deployment
aws cloudformation deploy \
  --template-file template.yaml \
  --stack-name Team1CloudTrailStack \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    AssetsBucket=my-cloudtrail-assets \
    ResourcePrefix=team1 \
    Environment=prod\
  --s3-bucket my-cloudtrail-assets

# Team 2 deployment
aws cloudformation deploy \
  --template-file template.yaml \
  --stack-name Team2CloudTrailStack \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    AssetsBucket=my-cloudtrail-assets \
    ResourcePrefix=team2 \
    Environment=prod\
  --s3-bucket my-cloudtrail-assets
```

## Files to Share
- `template.yaml` - CloudFormation template
- `package-assets.sh` - Script to package Lambda code
- `infra_sandbox/cloudtrail_asset/` - Lambda and Glue code
- `DEPLOYMENT.md` - This deployment guide
