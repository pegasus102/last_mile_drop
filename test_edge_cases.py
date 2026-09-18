import json
from src.bedrock_extractor import extract_landmarks

# A list of challenging test cases to ensure your parsing and fallbacks never break
test_cases = [
    {
        "name": "1. Standard Hinglish",
        "transcript": "Come to MG Road, stop opposite Sharma Sweets, red gate."
    },
    {
        "name": "2. Missing Information (Testing 'unknown' injection)",
        "transcript": "Just come to the big banyan tree and call me."
    },
    {
        "name": "3. Heavy Regional Hindi",
        "transcript": "Bhaiya mandir ke paas aake left le lena, waha ek neela darwaza hai."
    },
    {
        "name": "4. Empty String (Testing instant fallback trigger)",
        "transcript": "   "
    }
]

print("🧪 Running Edge Case Tests on Google Gemini Extractor...\n")

for i, test in enumerate(test_cases):
    print(f"--- Test {test['name']} ---")
    print(f"Input: '{test['transcript']}'")
    
    # Call your actual application function
    result = extract_landmarks(test['transcript'])
    
    print("Output JSON:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("\n")