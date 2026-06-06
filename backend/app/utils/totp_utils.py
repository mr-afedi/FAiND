"""TOTP secret validation helpers (Root Admin 2FA)."""
import base64
import re

_PLACEHOLDER_SECRETS = frozenset(
    {
        "YOUR_TOTP_SECRET_BASE32",
        "CHANGE_ME",
        "CHANGEME",
    }
)


def normalize_totp_secret(secret: str) -> str:
    return re.sub(r"\s+", "", secret.strip()).upper()


def is_valid_totp_secret(secret: str | None) -> bool:
    if not secret or not secret.strip():
        return False
    cleaned = normalize_totp_secret(secret)
    if cleaned in _PLACEHOLDER_SECRETS:
        return False
    try:
        base64.b32decode(cleaned, casefold=True)
        return True
    except Exception:
        return False
