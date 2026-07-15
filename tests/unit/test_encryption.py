"""Unit tests for Fernet encryption module."""
import pytest

from app.utils.encryption import decrypt_text, encrypt_text


@pytest.fixture(autouse=True)
def set_encryption_key(monkeypatch):
    """Ensure ENCRYPTION_KEY is set for all tests via Settings."""
    from app.core.config import Settings
    test_settings = Settings(encryption_key="test-encryption-key-for-unit-tests-min-32-ch")
    monkeypatch.setattr("app.utils.encryption.get_settings", lambda: test_settings)


class TestEncryption:
    def test_encrypt_decrypt_roundtrip(self):
        original = "my-secret-value"
        encrypted = encrypt_text(original)
        assert encrypted != original
        decrypted = decrypt_text(encrypted)
        assert decrypted == original

    def test_different_encryptions_for_same_text(self):
        e1 = encrypt_text("same-text")
        e2 = encrypt_text("same-text")
        assert e1 != e2

    def test_encrypt_empty_string(self):
        encrypted = encrypt_text("")
        assert decrypt_text(encrypted) == ""

    def test_encrypt_unicode(self):
        original = "こんにちは世界 🔐"
        encrypted = encrypt_text(original)
        assert decrypt_text(encrypted) == original


class TestProductionKeyGuard:
    _PROD_KWARGS = {
        "environment": "production",
        "supabase_url": "https://example.supabase.co",
        "supabase_publishable_key": "pk-test",
        "supabase_secret_key": "sk-test",
        "supabase_jwt_secret": "jwt-secret-test",
    }

    def _settings(self, **overrides):
        from app.core.config import Settings

        return Settings(_env_file=None, **{**self._PROD_KWARGS, **overrides})

    def test_production_rejects_passphrase_key(self):
        with pytest.raises(ValueError, match="must be a real Fernet key"):
            self._settings(encryption_key="just-a-passphrase-not-a-fernet-key")

    def test_production_rejects_missing_key(self):
        with pytest.raises(ValueError, match="ENCRYPTION_KEY is required"):
            self._settings(encryption_key=None)

    def test_production_accepts_real_fernet_key(self):
        from cryptography.fernet import Fernet

        settings = self._settings(encryption_key=Fernet.generate_key().decode())
        assert settings.environment == "production"

    def test_development_allows_passphrase_key(self):
        settings = self._settings(environment="development", encryption_key="dev-passphrase")
        assert settings.encryption_key.get_secret_value() == "dev-passphrase"
