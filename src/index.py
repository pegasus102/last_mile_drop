import json
import logging
import os
import urllib.parse

import boto3

from bedrock_extractor import extract_landmarks
from cedar_evaluator import evaluate_cedar_policy

logger = logging.getLogger()
logger.setLevel(logging.INFO)

DYNAMODB_ENDPOINT_URL = os.environ.get("DYNAMODB_ENDPOINT_URL", "http://localhost:4566")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
TABLE_NAME = os.environ.get("TABLE_NAME", "Deliveries")

MAX_PING_COUNT = 2

# Sample transcript used until real voice-to-text transcription is wired in.
SAMPLE_TRANSCRIPT = (
    "Bhaiya, Peepal ke ped ke paas aake left le lena, "
    "wahan laal rang ka gate hai, 1st floor."
)


def _get_dynamodb_table():
    """Initialize the DynamoDB resource (pointed at LocalStack) and return the table."""
    dynamodb = boto3.resource(
        "dynamodb",
        endpoint_url=DYNAMODB_ENDPOINT_URL,
        region_name=AWS_REGION,
    )
    return dynamodb.Table(TABLE_NAME)


def _extract_package_id_from_key(object_key: str) -> str:
    """
    Derive a package_id from the S3 object key.
    Expected key format: e.g. "voice-notes/<package_id>.wav"
    Falls back to the full decoded key (minus extension) if no folder prefix exists.
    """
    decoded_key = urllib.parse.unquote_plus(object_key)
    filename = decoded_key.rsplit("/", 1)[-1]
    package_id = filename.rsplit(".", 1)[0]
    return package_id


def _response(status_code: int, body: dict) -> dict:
    """Build a standard API Gateway proxy-style response."""
    return {
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body),
    }


def _parse_api_body(event: dict) -> dict:
    """
    Parse the incoming request payload whether it arrives as a raw dict
    (direct Lambda invoke / local testing) or as an API Gateway proxy
    event with a JSON string in "body".
    """
    if "body" in event:
        raw_body = event.get("body") or "{}"
        if isinstance(raw_body, str):
            try:
                return json.loads(raw_body)
            except json.JSONDecodeError:
                logger.error("Failed to parse request body JSON: %s", raw_body)
                return {}
        if isinstance(raw_body, dict):
            return raw_body
    return event


def _process_s3_upload(event: dict) -> dict:
    """
    Handles S3 ObjectCreated events for uploaded customer voice notes.

    For each S3 record:
      1. Extracts package_id from the object key.
      2. Runs Bedrock landmark extraction on the voice transcript.
      3. Persists the delivery state (landmarks + doorbell defaults) to DynamoDB.
    """
    records = event.get("Records", [])
    table = _get_dynamodb_table()
    processed_package_ids = []

    for record in records:
        try:
            s3_info = record.get("s3", {})
            object_key = s3_info.get("object", {}).get("key", "")

            if not object_key:
                logger.warning("Record missing S3 object key: %s", record)
                continue

            package_id = _extract_package_id_from_key(object_key)

            # TODO: Replace SAMPLE_TRANSCRIPT with real transcribed audio text
            # once speech-to-text ingestion is wired into the pipeline.
            landmarks = extract_landmarks(SAMPLE_TRANSCRIPT)

            item = {
                "package_id": package_id,
                "landmarks": landmarks,
                "notifications_enabled": True,
                "doorbell_state": "IDLE",
                "ping_count": 0,
            }

            table.put_item(Item=item)
            processed_package_ids.append(package_id)

            logger.info("Processed voice note for package_id=%s", package_id)

        except Exception:
            logger.exception("Failed to process S3 record: %s", record)

    return _response(
        200,
        {
            "message": "Voice note processing complete.",
            "processed_package_ids": processed_package_ids,
        },
    )


def _handle_fetch_hud(payload: dict) -> dict:
    """
    Handles action == "FETCH_HUD".

    Evaluates Cedar policy for ReadLandmark (500m) and PingDoorbell (20m),
    then returns the driver-facing HUD payload.
    """
    package_id = payload.get("package_id")
    distance_meters = payload.get("distance_meters")

    if not package_id or distance_meters is None:
        return _response(
            400, {"error": "Missing required fields: package_id, distance_meters."}
        )

    read_landmark_allowed = evaluate_cedar_policy("ReadLandmark", distance_meters)

    if not read_landmark_allowed:
        return _response(
            403, {"error": "Cedar Privacy Shield: Outside 500m radius."}
        )

    table = _get_dynamodb_table()
    result = table.get_item(Key={"package_id": package_id})
    item = result.get("Item")

    if not item:
        return _response(404, {"error": f"No delivery found for package_id={package_id}."})

    notifications_enabled = item.get("notifications_enabled", True)
    doorbell_allowed = evaluate_cedar_policy("PingDoorbell", distance_meters)

    if not notifications_enabled:
        doorbell_status = "DIRECT_CALL_ONLY"
    elif doorbell_allowed:
        doorbell_status = "AVAILABLE"
    else:
        doorbell_status = "DIRECT_CALL_ONLY"

    return _response(
        200,
        {
            "landmarks": item.get("landmarks"),
            "doorbell_allowed": bool(doorbell_allowed and notifications_enabled),
            "doorbell_status": doorbell_status,
            "current_doorbell_state": item.get("doorbell_state", "IDLE"),
        },
    )


def _handle_ping_doorbell(payload: dict) -> dict:
    """
    Handles action == "PING_DOORBELL".

    Evaluates Cedar policy for PingDoorbell (20m), enforces the 2-ping cap,
    and updates the doorbell state machine accordingly.
    """
    package_id = payload.get("package_id")
    distance_meters = payload.get("distance_meters")

    if not package_id or distance_meters is None:
        return _response(
            400, {"error": "Missing required fields: package_id, distance_meters."}
        )

    doorbell_allowed = evaluate_cedar_policy("PingDoorbell", distance_meters)

    if not doorbell_allowed:
        return _response(
            403, {"error": "Cedar Privacy Shield: Outside 20m doorbell radius."}
        )

    table = _get_dynamodb_table()
    result = table.get_item(Key={"package_id": package_id})
    item = result.get("Item")

    if not item:
        return _response(404, {"error": f"No delivery found for package_id={package_id}."})

    ping_count = int(item.get("ping_count", 0))

    if ping_count >= MAX_PING_COUNT:
        table.update_item(
            Key={"package_id": package_id},
            UpdateExpression="SET doorbell_state = :state",
            ExpressionAttributeValues={":state": "MAX_PINGS_EXCEEDED"},
        )
        return _response(
            200,
            {
                "doorbell_state": "MAX_PINGS_EXCEEDED",
                "next_action": "DIRECT_CALL_REQUIRED",
            },
        )

    new_count = ping_count + 1

    table.update_item(
        Key={"package_id": package_id},
        UpdateExpression="SET doorbell_state = :state, ping_count = :count",
        ExpressionAttributeValues={":state": "RINGING_30S", ":count": new_count},
    )

    return _response(
        200,
        {
            "doorbell_state": "RINGING_30S",
            "ping_count": new_count,
        },
    )


def lambda_handler(event, context):
    """
    Unified entry point handling two distinct trigger types:

    1. S3 ObjectCreated events (voice note upload -> Bedrock extraction -> DynamoDB).
    2. API Gateway JSON requests (Driver HUD fetch and Digital Doorbell pings),
       distinguished by an "action" field of "FETCH_HUD" or "PING_DOORBELL".
    """
    if isinstance(event, dict) and event.get("Records"):
        return _process_s3_upload(event)

    payload = _parse_api_body(event)
    action = payload.get("action")

    if action == "FETCH_HUD":
        return _handle_fetch_hud(payload)

    if action == "PING_DOORBELL":
        return _handle_ping_doorbell(payload)

    logger.warning("Unrecognized event/action: %s", json.dumps(event, default=str))
    return _response(400, {"error": f"Unrecognized action: {action}"})