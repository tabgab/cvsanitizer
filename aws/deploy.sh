#!/bin/bash

# CV Sanitizer AWS Deployment Script
# This script deploys the CV Sanitizer to AWS Lambda and API Gateway

set -e

# Configuration
STACK_NAME="cvsanitizer-${ENVIRONMENT:-dev}"
REGION="${AWS_REGION:-us-east-1}"
S3_BUCKET="${S3_BUCKET:-}"
PYTHON_VERSION="${PYTHON_VERSION:-python3.9}"

echo "Deploying CV Sanitizer to AWS"
echo "Stack Name: $STACK_NAME"
echo "Region: $REGION"
echo "Python Version: $PYTHON_VERSION"

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "Error: AWS CLI is not installed"
    exit 1
fi

# Check if AWS credentials are configured
if ! aws sts get-caller-identity &> /dev/null; then
    echo "Error: AWS credentials not configured"
    exit 1
fi

# Create deployment package
echo "Creating Lambda deployment package..."
mkdir -p deployment

# Copy Lambda function
cp aws/lambda_function.py deployment/

# Create requirements file for Lambda
cat > deployment/requirements.txt << EOF
boto3>=1.26.0
botocore>=1.29.0
EOF

# Install dependencies
echo "Installing Python dependencies..."
pip install -r deployment/requirements.txt -t deployment/

# Copy CV Sanitizer modules (if available)
if [ -d "cvsanitizer" ]; then
    echo "Copying CV Sanitizer modules..."
    cp -r cvsanitizer deployment/
fi

# Create ZIP package
echo "Creating deployment package..."
cd deployment
zip -r ../deployment.zip .
cd ..

# Clean up
rm -rf deployment

# Deploy CloudFormation stack
echo "Deploying CloudFormation stack..."
aws cloudformation deploy \
    --template-file aws/cloudformation.yaml \
    --stack-name "$STACK_NAME" \
    --parameter-overrides \
        Environment="$ENVIRONMENT" \
        PythonVersion="$PYTHON_VERSION" \
    --capabilities CAPABILITY_IAM \
    --region "$REGION"

# Get stack outputs
echo "Getting stack outputs..."
BUCKET_NAME=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`BucketName`].OutputValue' \
    --output text)

LAMBDA_ARN=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`LambdaFunctionArn`].OutputValue' \
    --output text)

API_URL=$(aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --query 'Stacks[0].Outputs[?OutputKey==`APIGatewayURL`].OutputValue' \
    --output text)

# Update Lambda function code
echo "Updating Lambda function code..."
aws lambda update-function-code \
    --function-name "$STACK_NAME" \
    --zip-file fileb://deployment.zip \
    --region "$REGION"

# Clean up deployment package
rm deployment.zip

# Print deployment information
echo ""
echo "Deployment completed successfully!"
echo ""
echo "Stack Name: $STACK_NAME"
echo "S3 Bucket: $BUCKET_NAME"
echo "Lambda ARN: $LAMBDA_ARN"
echo "API Gateway URL: $API_URL"
echo ""
echo "To upload PDFs for processing:"
echo "  aws s3 cp your-cv.pdf s3://$BUCKET_NAME/uploads/"
echo ""
echo "To process via API:"
echo "  curl -X POST $API_URL/process -H 'Content-Type: application/json' -d '{\"pdf_url\": \"s3://$BUCKET_NAME/uploads/your-cv.pdf\"}'"
echo ""
echo "To view processed files:"
echo "  aws s3 ls s3://$BUCKET_NAME/processed/"
echo ""
echo "To monitor logs:"
echo "  aws logs tail /aws/lambda/$STACK_NAME --follow --region $REGION"
