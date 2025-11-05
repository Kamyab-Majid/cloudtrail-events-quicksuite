#!/bin/bash
# Script to package Lambda functions and Glue scripts for deployment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="$SCRIPT_DIR/deployment-assets"

echo "Creating deployment assets..."

# Create output directory
mkdir -p "$OUTPUT_DIR/lambda"
mkdir -p "$OUTPUT_DIR/glue"

# Package Lambda functions
echo "Packaging count-files Lambda..."
cd "$SCRIPT_DIR/infra_sandbox/cloudtrail_asset/file_count_lambda"
zip -r "$OUTPUT_DIR/lambda/count-files.zip" .

echo "Packaging last-days Lambda..."
cd "$SCRIPT_DIR/infra_sandbox/cloudtrail_asset/last_7_days_lambda"
zip -r "$OUTPUT_DIR/lambda/last-days.zip" .

echo "Packaging max-count Lambda..."
cd "$SCRIPT_DIR/infra_sandbox/cloudtrail_asset/max_file_count_lambda"
zip -r "$OUTPUT_DIR/lambda/max-count.zip" .

# Copy Glue script
echo "Copying Glue script..."
cp "$SCRIPT_DIR/infra_sandbox/cloudtrail_asset/cloudtrail_log_processing.py" "$OUTPUT_DIR/glue/"

echo ""
echo "✅ Assets packaged successfully in: $OUTPUT_DIR"
echo ""
echo "Next steps:"
echo "1. Upload assets to your S3 bucket:"
echo "   aws s3 sync $OUTPUT_DIR s3://YOUR-BUCKET-NAME/"
echo ""
echo "2. Deploy the CloudFormation template with AssetsBucket parameter"
