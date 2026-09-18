import json
import sys

# Add the staged build directory to python path
sys.path.insert(0, '.aws-sam/build/WhisperProcessor')

from index import lambda_handler

# Pass a payload that includes an action or matches what your API expects
mock_event = {
    "body": json.dumps({
        "action": "PROCESS_TRANSCRIPT", # Or whatever action your router maps to extraction
        "transcript": "Deliver to building 4B, right next to the blue provision store, leave it at the yellow door."
    })
}

print("🚀 Running Local Lambda Test...")
response = lambda_handler(mock_event, None)

print("\n📥 Status Code Received:", response.get("statusCode"))
print("📦 Response Body:")
print(json.dumps(json.loads(response.get("body")), indent=2, ensure_ascii=False))