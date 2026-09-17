#!/usr/bin/env bash
set -euo pipefail

export AWS_DEFAULT_REGION="us-east-1"

ENDPOINT_URL="http://localhost:4566"
BUCKET_NAME="lastmile-whisper-voice-audio"
TABLE_NAME="Deliveries"
SAMPLE_FILE="sample_voice.mp3"
SAMPLE_KEY="PKG123.mp3"

echo "=================================================="
echo " Last-Mile Whisper — Phase 1 Local Bootstrap"
echo "=================================================="

echo ""
echo "[1/5] Checking LocalStack status..."
if ! curl -s "${ENDPOINT_URL}/_localstack/health" > /dev/null; then
  echo "ERROR: LocalStack does not appear to be running at ${ENDPOINT_URL}."
  echo "Start it first with: localstack start -d"
  exit 1
fi
echo "LocalStack is reachable at ${ENDPOINT_URL}."

echo ""
echo "[2/5] Creating S3 bucket: ${BUCKET_NAME}..."
aws --endpoint-url="${ENDPOINT_URL}" s3api create-bucket \
  --bucket "${BUCKET_NAME}" \
  --region "${AWS_DEFAULT_REGION}" \
  2>/dev/null || echo "Bucket ${BUCKET_NAME} already exists. Skipping."

echo ""
echo "[3/5] Creating DynamoDB table: ${TABLE_NAME}..."
aws --endpoint-url="${ENDPOINT_URL}" dynamodb create-table \
  --table-name "${TABLE_NAME}" \
  --attribute-definitions AttributeName=package_id,AttributeType=S \
  --key-schema AttributeName=package_id,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  2>/dev/null || echo "Table ${TABLE_NAME} already exists. Skipping."

echo ""
echo "[4/5] Creating dummy voice note and uploading to S3..."
echo "This is a dummy audio placeholder for Last-Mile Whisper testing." > "${SAMPLE_FILE}"

aws --endpoint-url="${ENDPOINT_URL}" s3 cp \
  "${SAMPLE_FILE}" \
  "s3://${BUCKET_NAME}/${SAMPLE_KEY}"

echo "Uploaded ${SAMPLE_FILE} to s3://${BUCKET_NAME}/${SAMPLE_KEY}"

echo ""
echo "[5/5] Phase 1 setup complete."
echo ""
echo "=================================================="
echo " Next Steps"
echo "=================================================="
echo ""
echo "1. Start the SAM local API:"
echo "     sam local start-api"
echo ""
echo "2. Open the Driver HUD in your browser:"
echo "     open index.html        # macOS"
echo "     xdg-open index.html    # Linux"
echo "     start index.html       # Windows"
echo ""
echo "=================================================="