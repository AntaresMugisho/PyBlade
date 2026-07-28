import hmac
import hashlib
import json
from django.conf import settings as dj_settings

def generate_checksum(payload_data: dict) -> str:
    """
    Generates an HMAC SHA-256 signature for a given dictionary payload
    using Django's SECRET_KEY.
    """
    serialized_data = json.dumps(payload_data, sort_keys=True)
    return hmac.new(
        dj_settings.SECRET_KEY.encode("utf-8"),
        serialized_data.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()


def verify_snapshot(snapshot: dict) -> dict:
    """
    Verifies the integrity of the client snapshot using its checksum.

    :param snapshot: Dict containing 'class', 'data', and 'checksum'.
    :return: The validated snapshot dictionary.
    :raises PermissionDenied: If the checksum is missing or invalid.
    """
    checksum = snapshot.pop("checksum", None)
    if not checksum:
        raise ValueError("Missing PyBlade snapshot checksum.")

    expected_checksum = generate_checksum(snapshot)

    # Use constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(checksum, expected_checksum):
        raise ValueError("Invalid PyBlade snapshot checksum (possible tamper).")

    return True