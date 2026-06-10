"""Utility functions for the experiment app."""

import hashlib
import base64
from django.conf import settings


def generate_completion_code(participant_id: int) -> str:
    """
    Generate a verifiable completion code.

    Format: MJAI-{participant_id}-{checksum}
    Example: MJAI-142-A3B7

    The checksum is derived from:
    - participant_id
    - a secret salt from settings

    Args:
        participant_id: The database ID of the participant

    Returns:
        A unique, verifiable completion code string
    """
    secret_salt = getattr(settings, 'COMPLETION_CODE_SALT', 'default-salt-change-in-production')

    # Create hash of participant_id + salt
    data = f"{participant_id}{secret_salt}"
    hash_bytes = hashlib.sha256(data.encode()).digest()

    # Take first 4 characters of base64 encoding (uppercase, alphanumeric only)
    checksum_raw = base64.b64encode(hash_bytes).decode()
    # Filter to alphanumeric and take first 4
    checksum = ''.join(c for c in checksum_raw if c.isalnum())[:4].upper()

    return f"MJAI-{participant_id}-{checksum}"


def verify_completion_code(code: str) -> tuple[bool, int]:
    """
    Verify a completion code and return (valid, participant_id).

    Args:
        code: The completion code to verify

    Returns:
        (True, participant_id) if valid
        (False, 0) if invalid
    """
    try:
        parts = code.strip().upper().split('-')
        if len(parts) != 3 or parts[0] != 'MJAI':
            return False, 0

        participant_id = int(parts[1])
        expected_code = generate_completion_code(participant_id)

        if code.strip().upper() == expected_code.upper():
            return True, participant_id
        return False, 0
    except (ValueError, IndexError):
        return False, 0
