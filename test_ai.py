import os
import json
from google import genai

# Automatically grabs the key you exported in your terminal
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

transcript = "Bhaiya, come to MG Road, stop opposite Sharma Sweets, go behind the big Peepal tree, you will see a red gate. That's my house."

prompt = (
    "Extract the key visual landmarks from this delivery instruction. "
    "Return ONLY valid JSON with three keys: 'landmark', 'turn_instruction', and 'door_color'. "
    "Do not include markdown or other text.\n\n"
    f"Transcript: {transcript}"
)

print("🤖 Sending raw transcript to Google Gemini...")

try:
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=prompt
    )
    
    print("\n✅ Success! Extracted JSON payload:")
    print(response.text)
    
except Exception as e:
    print(f"\n❌ Error: {e}")