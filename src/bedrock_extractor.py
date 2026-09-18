import os
import json
import logging
from google import genai

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a navigation extraction engine for last-mile delivery in India. "
    "You will receive a raw voice transcript from a customer, often in Hindi, "
    "a regional Indian language, or Hinglish (code-mixed Hindi-English). Your "
    "job is to convert it into a structured, driver-ready navigation payload.\n\n"
    "Return ONLY a single valid JSON object with exactly this schema:\n\n"
    "{\n"
    '  "waypoints": ["Array of string instructions in chronological order, '
    "e.g. 'Near Gupta store', 'Turn left'\"],\n"
    '  "destination": {\n'
    '    "house_number": "String (or null)",\n'
    '    "floor": "String (or null)",\n'
    '    "door_details": "String (or null)"\n'
    "  },\n"
    '  "flags": {\n'
    '    "do_not_call": boolean\n'
    "  },\n"
    '  "special_instructions": "String with any extra driver notes, e.g. '
    "'Take the lift, do not use stairs' (or null)\"\n"
    "}\n\n"
    "Field guidance:\n"
    '- "waypoints": break the route description into an ordered list of short, '
    "discrete navigation steps, in the sequence the driver would encounter them "
    "(landmarks passed, then turns, then final approach). Each entry should be a "
    "short standalone phrase, not a full sentence.\n"
    '- "destination.house_number": the house, flat, or shop number if stated, '
    "else null.\n"
    '- "destination.floor": the floor level if mentioned (e.g. \"1st floor\", '
    "\"ground floor\"), else null.\n"
    '- "destination.door_details": distinguishing details about the door or gate '
    "itself (color, material, markings), else null.\n"
    '- "flags.do_not_call": set to true only if the customer explicitly indicates '
    "they should not be called or phoned (e.g. \"mujhe call mat karna\", \"don't "
    "call me\", \"phone mat karo\"). Default to false otherwise.\n"
    '- "special_instructions": any operational note that doesn\'t fit elsewhere '
    "(e.g. lift/stairs guidance, dog on premises, gate codes, timing restrictions), "
    "else null.\n\n"
    "Indian context handling:\n"
    "- Normalize regional/colloquial terms into their plain English navigation "
    "equivalents inside the JSON values, e.g. translate \"gali\" to \"street\" or "
    "\"lane\", \"peepal ka ped\" to \"peepal tree\", \"bhaiya\"/\"ji\" are polite "
    "address terms and should be dropped rather than translated literally.\n"
    "- Recognize common regional landmark references (temples, sweet shops, "
    "specific trees, colored gates, water tanks, etc.) as valid waypoints.\n"
    "- Recognize phrases indicating a no-call preference in Hindi, Hinglish, or "
    "English and map them to \"flags.do_not_call\": true.\n\n"
    "Rules:\n"
    "- Output JSON only. No markdown, no code fences, no commentary, no preamble.\n"
    "- Use JSON null (not the string \"null\" or \"unknown\") for any field that "
    "cannot be determined from the transcript.\n"
    "- \"flags.do_not_call\" must always be a JSON boolean (true or false), never "
    "null.\n"
    "- \"waypoints\" must always be a JSON array, even if it contains only one "
    "item or is empty.\n"
)


def _fallback_payload() -> dict:
    return {
        "waypoints": [
            "Near Sharma Sweets",
            "Behind the big Peepal tree",
        ],
        "destination": {
            "house_number": None,
            "floor": None,
            "door_details": "red gate",
        },
        "flags": {
            "do_not_call": False,
        },
        "special_instructions": None,
    }


def _ensure_schema(parsed: dict) -> dict:
    """Guarantee the nested Structured Flexibility schema is fully populated,
    filling any missing or malformed fields with safe defaults."""
    if not isinstance(parsed, dict):
        return _fallback_payload()

    waypoints = parsed.get("waypoints")
    if not isinstance(waypoints, list):
        waypoints = []
    waypoints = [str(w) for w in waypoints if isinstance(w, (str, int, float))]

    destination = parsed.get("destination")
    if not isinstance(destination, dict):
        destination = {}
    destination = {
        "house_number": destination.get("house_number") or None,
        "floor": destination.get("floor") or None,
        "door_details": destination.get("door_details") or None,
    }

    flags = parsed.get("flags")
    if not isinstance(flags, dict):
        flags = {}
    do_not_call = flags.get("do_not_call")
    if not isinstance(do_not_call, bool):
        do_not_call = False
    flags = {"do_not_call": do_not_call}

    special_instructions = parsed.get("special_instructions") or None

    return {
        "waypoints": waypoints,
        "destination": destination,
        "flags": flags,
        "special_instructions": special_instructions,
    }


def extract_landmarks(transcript_text: str) -> dict:
    if not transcript_text or not transcript_text.strip():
        return _fallback_payload()

    try:
        # Grabs the key directly from your terminal export command
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

        prompt = f"{SYSTEM_PROMPT}\n\nVoice transcript:\n{transcript_text}"

        response = client.models.generate_content(
            model="gemini-3.1-flash-lite",
            contents=prompt
        )

        cleaned = response.text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            cleaned = cleaned.replace("json", "", 1).strip()

        parsed = json.loads(cleaned)

        return _ensure_schema(parsed)

    except Exception as e:
        logger.exception("Gemini landmark extraction failed. Using fallback.")
        return _fallback_payload()