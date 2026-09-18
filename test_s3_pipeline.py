import os
import json
import sys

# Force LocalStack and region configuration
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "test"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test"
os.environ["DYNAMODB_ENDPOINT_URL"] = "http://localhost:4566"
os.environ["TABLE_NAME"] = "Deliveries"

sys.path.insert(0, '.aws-sam/build/WhisperProcessor')

from bedrock_extractor import extract_landmarks
from index import lambda_handler, _get_dynamodb_table

sample_transcript = "Bhaiya, Peepal ke ped ke paas aake left le lena, wahan laal rang ka gate hai, 1st floor."

print("==================================================")
print("🤖 STEP 1: Direct Google Gemini AI Extraction Test")
print("==================================================")
print(f"Input Transcript: \"{sample_transcript}\"")
gemini_output = extract_landmarks(sample_transcript)
print("\n✨ Gemini Raw JSON Output:")
print(json.dumps(gemini_output, indent=2, ensure_ascii=False))

print("\n==================================================")
print("🚀 STEP 2: Running Lambda S3 Event Simulation")
print("==================================================")
mock_s3_event = {
    "Records": [
        {
            "eventSource": "aws:s3",
            "s3": {
                "bucket": {"name": "last-mile-drop-bucket"},
                "object": {"key": "transcripts/sample_order_99.txt"}
            }
        }
    ]
}

response = lambda_handler(mock_s3_event, None)
print("📥 Lambda Execution Response:")
print(json.dumps(response, indent=2))

print("\n==================================================")
print("📦 STEP 3: Verifying Local DynamoDB Record Retrieval")
print("==================================================")
try:
    table = _get_dynamodb_table()
    result = table.get_item(Key={"package_id": "sample_order_99"})
    stored_item = result.get("Item")
    
    if stored_item:
        print("✅ SUCCESS! Record found in local DynamoDB table 'Deliveries':")
        print(json.dumps(stored_item, indent=2, default=str))
    else:
        print("❌ WARNING: Lambda executed, but item 'sample_order_99' was not found in DynamoDB.")
except Exception as e:
    print(f"⚠️ Error querying LocalStack DynamoDB: {e}")
print("==================================================")
EOF