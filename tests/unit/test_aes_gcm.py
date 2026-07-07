from __future__ import annotations

import base64
import os

import pytest

from app.core.config import Settings
from app.utils import aes_gcm


@pytest.fixture(autouse=True)
def set_aes_key(monkeypatch):
    key = base64.urlsafe_b64encode(os.urandom(32)).decode("ascii")
    settings = Settings(encryption_key=key)
    monkeypatch.setattr("app.utils.aes_gcm.get_settings", lambda: settings)


def test_aes_gcm_roundtrip() -> None:
    encrypted = aes_gcm.encrypt_text("sensitive reply", associated_data="reply")

    assert encrypted != "sensitive reply"
    assert aes_gcm.is_encrypted(encrypted)
    assert aes_gcm.decrypt_text(encrypted, associated_data="reply") == "sensitive reply"


def test_aes_gcm_uses_random_nonce() -> None:
    first = aes_gcm.encrypt_text("same")
    second = aes_gcm.encrypt_text("same")

    assert first != second
    assert aes_gcm.decrypt_text(first) == "same"
    assert aes_gcm.decrypt_text(second) == "same"


def test_aes_gcm_rejects_wrong_associated_data() -> None:
    encrypted = aes_gcm.encrypt_text("secret", associated_data="right")

    with pytest.raises(ValueError):
        aes_gcm.decrypt_text(encrypted, associated_data="wrong")


def test_plaintext_passthrough_on_decrypt() -> None:
    assert aes_gcm.decrypt_text("plain") == "plain"
