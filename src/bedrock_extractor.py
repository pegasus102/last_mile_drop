import json
import logging

import boto3

logger = logging.getLogger(__name__)

BEDROCK_MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"
BEDROCK_REGION = "us-east-1"

REQUIRED_KEYS = ["landmark", "turn_instruction", "door_color", "audio_summary_hindi"]

SYSTEM_PROMPT = (
    "You are a navigation landmark extraction engine for last-mile delivery "
    "in India. You will receive a raw voice transcript from a customer, "
    "often in Hindi, a regional Indian language, or Hinglish (code-mixed "
    "Hindi-English). Extract only the visual navigation details a delivery "
    "driver needs.\n\n"
    "Return ONLY a single valid JSON object with exactly these keys:\n"
    '  "landmark": a short phrase naming the nearest visual landmark '
    "(e.g. shop, temple, tree, statue)\n"
    '  "turn_instruction": a short directional instruction '
    "(e.g. \"take left after the landmark\")\n"
    '  "door_color": the color of the door/gate if mentioned, otherwise '
    '"unknown"\n'
    '  "audio_summary_hindi": a one-line summary of the directions '
    "written in Hindi (Devanagari script)\n\n"
    "Rules:\n"
    "- Output JSON only. No markdown, no code fences, no commentary, no "
    "preamble.\n"
    "- If a field cannot be determined from the transcript, use the "
    'string "unknown" for that field.\n'
    "- Keep each field concise (a few words to a short phrase).\n"
)


def _build_client():
    """Create a Bedrock Runtime client."""
    return boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)


def _build_request_body(transcript_text: str) -> str:
    """Construct the Anthropic Messages API request body for Bedrock."""
    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 300,
        "temperature": 0,
        "system": SYSTEM_PROMPT,
        "messages": [
            {
                "role": "user",
                "content": (
                    "Voice transcript:\n"
                    f'"""{transcript_text}"""\n\n'
                    "Extract the JSON now."
                ),
            }
        ],
    }
    return json.dumps(payload)


def _safe_parse_json(raw_text: str) -> dict:
    """Safely parse a JSON object out of the model's raw text output."""
    cleaned = raw_text.strip()

    # Strip accidental markdown code fences if the model adds them.
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.replace("json", "", 1).strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        # Fallback: attempt to locate the first { ... } block in the text.
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            logger.error("Could not locate JSON object in model output: %s", raw_text)
            return _fallback_payload()
        try:
            parsed = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON from model output: %s", raw_text)
            return _fallback_payload()

    return _ensure_required_keys(parsed)


def _ensure_required_keys(parsed: dict) -> dict:
    """Guarantee all required keys exist, filling missing ones with 'unknown'."""
    if not isinstance(parsed, dict):
        return _fallback_payload()

    for key in REQUIRED_KEYS:
        if key not in parsed or not isinstance(parsed[key], str) or not parsed[key].strip():
            parsed[key] = "unknown"

    return {key: parsed[key] for key in REQUIRED_KEYS}


def _fallback_payload() -> dict:
    """Return a safe default payload when extraction fails entirely."""
    return {key: "unknown" for key in REQUIRED_KEYS}


def extract_landmarks(transcript_text: str) -> dict:
    """
    Extract structured navigation landmarks from a raw voice transcript
    using Amazon Bedrock (Claude 3 Haiku).

    Args:
        transcript_text: Raw transcript text (Hindi / regional / Hinglish)
                          describing the delivery landmark.

    Returns:
        A dictionary with keys: landmark, turn_instruction, door_color,
        audio_summary_hindi. Falls back to "unknown" values on any
        extraction or parsing failure.
    """
    if not transcript_text or not transcript_text.strip():
        logger.warning("Empty transcript_text passed to extract_landmarks.")
        return _fallback_payload()

    try:
        client = _build_client()
        body = _build_request_body(transcript_text)

        response = client.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            body=body,
            contentType="application/json",
            accept="application/json",
        )

        response_body = json.loads(response["body"].read())
        content_blocks = response_body.get("content", [])

        raw_text = "".join(
            block.get("text", "") for block in content_blocks if block.get("type") == "text"
        )

        if not raw_text.strip():
            logger.error("Bedrock returned no text content: %s", response_body)
            return _fallback_payload()

        return _safe_parse_json(raw_text)

    except Exception:
        logger.exception("Bedrock landmark extraction failed.")
        return _fallback_payload()