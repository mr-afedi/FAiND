"""
AES-256-GCM encryption for sensitive fields (hidden answers, tip amounts).
Key must be a 32-byte base64url-encoded string set in the environment.
"""
import os
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from app.core.config import get_settings

settings = get_settings()


def _get_key() -> bytes:
    raw = settings.ENCRYPTION_KEY
    key = base64.urlsafe_b64decode(raw.encode())
    if len(key) != 32:
        raise ValueError("ENCRYPTION_KEY must decode to exactly 32 bytes (use a base64url-encoded 32-byte value)")
    return key


def encrypt(plaintext: str) -> str:
    """Encrypt a string using AES-256-GCM. Returns base64url-encoded nonce+ciphertext."""
    key = _get_key()
    nonce = os.urandom(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    combined = nonce + ciphertext
    return base64.urlsafe_b64encode(combined).decode("utf-8")


def decrypt(token: str) -> str:
    """Decrypt a base64url-encoded nonce+ciphertext string. Returns plaintext."""
    key = _get_key()
    combined = base64.urlsafe_b64decode(token.encode("utf-8"))
    nonce = combined[:12]
    ciphertext = combined[12:]
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode("utf-8")
