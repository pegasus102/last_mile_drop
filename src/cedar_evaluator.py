import json
import logging
import shutil
import subprocess
import tempfile
import os

logger = logging.getLogger(__name__)

CEDAR_BINARY = "cedar"
POLICY_FILE = "policy.cedar"

PRINCIPAL_TYPE = "User"
PRINCIPAL_ID = "DeliveryDriver"

RESOURCE_MAP = {
    "ReadLandmark": ("Package", "VoiceData"),
    "PingDoorbell": ("Package", "DeliverySession"),
}

FALLBACK_THRESHOLDS = {
    "ReadLandmark": 500,
    "PingDoorbell": 20,
}


def _build_context(distance_meters) -> dict:
    """Build the Cedar evaluation context payload."""
    return {
        "driver_status": "ON_DUTY",
        "distance_meters": int(distance_meters),
    }


def _cedar_cli_available() -> bool:
    """Check whether the Cedar CLI binary is available on PATH."""
    return shutil.which(CEDAR_BINARY) is not None


def _fallback_evaluate(action: str, distance_meters) -> bool:
    """
    Pure-Python fallback authorization logic, mirroring policy.cedar,
    used when the Cedar CLI is unavailable in the runtime environment.
    """
    try:
        distance = int(distance_meters)
    except (TypeError, ValueError):
        logger.error("Invalid distance_meters value for fallback evaluation: %s", distance_meters)
        return False

    threshold = FALLBACK_THRESHOLDS.get(action)
    if threshold is None:
        logger.warning("Unknown action '%s' in fallback evaluator. Denying by default.", action)
        return False

    allowed = distance <= threshold
    logger.info(
        "Fallback evaluation: action=%s distance=%sm threshold=%sm -> %s",
        action, distance, threshold, "ALLOW" if allowed else "DENY",
    )
    return allowed


def _build_cedar_context_and_entities_files(context: dict) -> tuple:
    """
    Write temporary context and entities JSON files for the Cedar CLI call.
    Returns (context_file_path, entities_file_path).
    """
    context_fd, context_path = tempfile.mkstemp(suffix="_context.json")
    with os.fdopen(context_fd, "w") as f:
        json.dump(context, f)

    entities_fd, entities_path = tempfile.mkstemp(suffix="_entities.json")
    with os.fdopen(entities_fd, "w") as f:
        json.dump([], f)  # No additional entity data required for this policy set.

    return context_path, entities_path


def _run_cedar_cli(action: str, context: dict) -> bool:
    """Invoke the Cedar CLI authorize command and parse its stdout for ALLOW/DENY."""
    context_path, entities_path = _build_cedar_context_and_entities_files(context)

    try:
        resource_type, resource_id = RESOURCE_MAP.get(action, ("Package", "Unknown"))

        cmd = [
            CEDAR_BINARY,
            "authorize",
            "--policies", POLICY_FILE,
            "--entities", entities_path,
            "--principal", f'{PRINCIPAL_TYPE}::"{PRINCIPAL_ID}"',
            "--action", f'Action::"{action}"',
            "--resource", f'{resource_type}::"{resource_id}"',
            "--context", context_path,  # Fixed: Now passing the file path instead of inline JSON
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )

        stdout = result.stdout or ""
        stderr = result.stderr or ""

        if result.returncode != 0:
            logger.warning("Cedar CLI exited with code %s. stderr=%s", result.returncode, stderr)

        decision = "ALLOW" in stdout.upper()
        logger.info("Cedar CLI decision for action=%s: %s", action, "ALLOW" if decision else "DENY")
        return decision

    finally:
        for path in (context_path, entities_path):
            try:
                os.remove(path)
            except OSError:
                pass


def evaluate_cedar_policy(action: str, distance_meters) -> bool:
    """
    Evaluate whether the DeliveryDriver is authorized to perform `action`
    given the current `distance_meters` from the delivery pin.

    Attempts to shell out to the Cedar CLI for a real policy evaluation
    against policy.cedar. If the Cedar CLI is unavailable or the call
    fails unexpectedly, falls back to equivalent Python distance-check
    logic so the system degrades gracefully.

    Args:
        action: "ReadLandmark" or "PingDoorbell".
        distance_meters: Current distance of the driver from the pin.

    Returns:
        True if authorized, False otherwise.
    """
    context = _build_context(distance_meters)

    if not _cedar_cli_available():
        logger.warning("Cedar CLI not found on PATH. Using Python fallback evaluator.")
        return _fallback_evaluate(action, distance_meters)

    try:
        return _run_cedar_cli(action, context)
    except (subprocess.SubprocessError, OSError, ValueError):
        logger.exception("Cedar CLI invocation failed. Falling back to Python evaluator.")
        return _fallback_evaluate(action, distance_meters)