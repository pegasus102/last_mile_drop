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

deliveries = [
    {
        "package_id": "pkg_test_001",
        "transcript": "Bhaiya, main gate se andar aake right le lena. Wahan ek bada banyan tree hai, uske samne wala green gate."
    },
    {
        "package_id": "pkg_test_002",
        "transcript": "Haan hello, main ghar pe nahi hu, parcel guard ko mat dena. Andar aake Tower B ke basement parking mein lift ke pass rakh dena. Black colour ka door hai."
    }
]

table = _get_dynamodb_table()

for delivery in deliveries:
    print(f"🎙️ Processing {delivery['package_id']}...")
    extracted_landmarks = extract_landmarks(delivery['transcript'])
    
    item = {
        "package_id": delivery["package_id"],
        "landmarks": extracted_landmarks,
        "notifications_enabled": True,
        "doorbell_state": "IDLE",
        "ping_count": 0,
    }
    table.put_item(Item=item)
    print(f"✅ Saved {delivery['package_id']} to DynamoDB!\n")

print("🎉 Batch 1 processing complete!")
