import os
import json
import sys

# Force LocalStack environment
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
os.environ["AWS_ACCESS_KEY_ID"] = "test"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test"
os.environ["DYNAMODB_ENDPOINT_URL"] = "http://localhost:4566"
os.environ["TABLE_NAME"] = "Deliveries"

sys.path.insert(0, '.aws-sam/build/WhisperProcessor')

from bedrock_extractor import extract_landmarks
from index import _get_dynamodb_table

# 🌟 YOUR NEW CUSTOM USER MESSAGE (Change this to test anything!)
custom_transcript = "Gali number 3 mein aana, samne ek bada neela dabba milega, uske bagal wala ghar hai, 2nd floor."
package_id = "order_custom_101"

print(f"🎙️ Processing New Transcript for package '{package_id}':")
print(f"\"{custom_transcript}\"\n")

# 1. Extract via Gemini
extracted_landmarks = extract_landmarks(custom_transcript)
print("✨ Gemini Extracted JSON:")
print(json.dumps(extracted_landmarks, indent=2, ensure_ascii=False))

# 2. Save to LocalStack DynamoDB
table = _get_dynamodb_table()
item = {
    "package_id": package_id,
    "landmarks": extracted_landmarks,
    "notifications_enabled": True,
    "doorbell_state": "IDLE",
    "ping_count": 0,
}
table.put_item(Item=item)
print(f"\n📦 Saved item into LocalStack DynamoDB table 'Deliveries' for {package_id}!")

# 3. Export to a local JSON file so the frontend can read it instantly
frontend_payload = {
    "package_id": package_id,
    "landmarks": extracted_landmarks
}
with open("current_delivery.json", "w", encoding="utf-8") as f:
    json.dump(frontend_payload, f, indent=2, ensure_ascii=False)

print("🌐 Exported payload to 'current_delivery.json' for the frontend UI.")
EOF