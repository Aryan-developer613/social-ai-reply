"""AES-256-GCM encryption for sensitive application data."""

from __future__ import annotations

import base64
import hashlib
import os

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.core.config import get_settings

_PREFIX = "aesgcm:v1"
_APP_SALT = b"signalflow:aes-gcm:v1"
_PBKDF2_ITERATIONS = 200_000


def _b64_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def _derive_key(passphrase: str) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=hashlib.sha256(_APP_SALT + passphrase.encode("utf-8")).digest()[:16],
        iterations=_PBKDF2_ITERATIONS,
    )
    return kdf.derive(passphrase.encode("utf-8"))


def _load_key() -> bytes:
    settings = get_settings()
    if not settings.encryption_key:
        raise RuntimeError("ENCRYPTION_KEY must be set before AES-GCM encryption can be used.")

    value = settings.encryption_key.strip()
    try:
        raw = base64.urlsafe_b64decode(value.encode("utf-8"))
    except (ValueError, TypeError):
        raw = b""
    if len(raw) == 32:
        return raw
    return _derive_key(value)


def is_encrypted(value: str | None) -> bool:
    return bool(value and value.startswith(f"{_PREFIX}:"))


def encrypt_text(value: str, *, associated_data: str | None = None) -> str:
    key = _load_key()
    nonce = os.urandom(12)
    aad = associated_data.encode("utf-8") if associated_data else None
    ciphertext = AESGCM(key).encrypt(nonce, value.encode("utf-8"), aad)
    return f"{_PREFIX}:{_b64_encode(nonce)}:{_b64_encode(ciphertext)}"


def decrypt_text(value: str, *, associated_data: str | None = None) -> str:
    if not is_encrypted(value):
        return value
    parts = value.split(":", 3)
    if len(parts) != 4:
        raise ValueError("AES-GCM ciphertext is malformed.")
    _scheme, _version, nonce_b64, ciphertext_b64 = parts
    aad = associated_data.encode("utf-8") if associated_data else None
    try:
        plaintext = AESGCM(_load_key()).decrypt(_b64_decode(nonce_b64), _b64_decode(ciphertext_b64), aad)
    except Exception as exc:
        raise ValueError("AES-GCM ciphertext is invalid or was encrypted with a different key.") from exc
    return plaintext.decode("utf-8")
