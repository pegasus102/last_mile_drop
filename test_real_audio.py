import os
import json
import boto3
from google import genai
import sys
import time

# Ensure Python can find your src modules
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
from bedrock_extractor import SYSTEM_PROMPT, _ensure_schema

def process_all_audio_files():
    client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
    endpoint_url = os.environ.get("DYNAMODB_ENDPOINT_URL", "http://localhost:4566")
    dynamodb = boto3.resource("dynamodb", endpoint_url=endpoint_url, region_name="us-east-1")
    table = dynamodb.Table("Deliveries")
    
    packages = ["pkg_test_001", "pkg_test_002", "pkg_test_003", "pkg_test_004"]
    
    for pkg_id in packages:
        file_path = f"audio/{pkg_id}.m4a"
        if not os.path.exists(file_path):
            print(f"⚠️ Skipping {pkg_id}: File {file_path} not found.")
            continue
            
        print(f"\n🎤 Uploading {file_path} to Gemini...")
        audio_file = client.files.upload(file=file_path)
        
        prompt = f"{SYSTEM_PROMPT}\n\nPlease listen to the provided customer voice note and extract the navigation details."
        
        try:
            response = client.models.generate_content(
                model="gemini-3.1-flash-lite",
                contents=[prompt, audio_file]
            )
            
            cleaned = response.text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.strip("`").replace("json", "", 1).strip()
                
            parsed = json.loads(cleaned)
            final_payload = _ensure_schema(parsed)
            
            print(f"✅ Extracted Payload for {pkg_id}:")
            print(json.dumps(final_payload, indent=2))
            
            table.put_item(
                Item={
                    "package_id": pkg_id,
                    "status": "OUTFORDELIVERY",
                    "landmarks": final_payload
                }
            )
            print(f"💾 Saved {pkg_id} to LocalStack.")
            
            # Small delay to avoid API rate limits
            time.sleep(2)
            
        except Exception as e:
            print(f"❌ Error processing {pkg_id}: {e}")

if __name__ == "__main__":
    process_all_audio_files()