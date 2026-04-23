"""
Unit tests for API Key Manager.

Tests cover encryption, storage, retrieval, and error handling.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from core.api_key_manager import APIKeyManager, SALT_SIZE
from core.config import APIKeyManagerConfig
from core.exceptions import APIKeyError


class TestAPIKeyManagerInit:
    """Tests for APIKeyManager initialization."""

    def test_init_with_default_config(self) -> None:
        """Test initialization with default configuration."""
        manager = APIKeyManager()
        assert manager.config.enabled is True
        assert manager.config.key_file == ".glitchhunter/api_keys.enc"
        assert (
            manager.config.encryption_password_env == "GLITCHHUNTER_MASTER_PASSWORD"
        )

    def test_init_with_custom_config(self) -> None:
        """Test initialization with custom configuration."""
        config = APIKeyManagerConfig(
            enabled=True,
            key_file="/tmp/test_keys.enc",
            encryption_password_env="TEST_PASSWORD",
        )
        manager = APIKeyManager(config)
        assert manager.config.key_file == "/tmp/test_keys.enc"
        assert manager.config.encryption_password_env == "TEST_PASSWORD"

    def test_init_disabled(self) -> None:
        """Test initialization with disabled manager."""
        config = APIKeyManagerConfig(enabled=False)
        manager = APIKeyManager(config)
        assert manager.config.enabled is False
        assert manager._fernet is None

    def test_init_missing_password_raises(self) -> None:
        """Test that missing password raises APIKeyError."""
        with patch.dict(os.environ, {}, clear=False):
            # Ensure password is not set
            if "GLITCHHUNTER_MASTER_PASSWORD" in os.environ:
                del os.environ["GLITCHHUNTER_MASTER_PASSWORD"]

            with pytest.raises(APIKeyError) as exc_info:
                APIKeyManager(APIKeyManagerConfig(enabled=True))

            assert "Master password not set" in exc_info.value.message
            assert "GLITCHHUNTER_MASTER_PASSWORD" in exc_info.value.message


class TestAPIKeyManagerStorage:
    """Tests for API key storage and retrieval."""

    @pytest.fixture
    def temp_key_file(self) -> str:
        """Create temporary key file path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield str(Path(tmpdir) / "test_keys.enc")

    @pytest.fixture
    def manager(self, temp_key_file: str) -> APIKeyManager:
        """Create APIKeyManager with temporary file."""
        os.environ["TEST_MASTER_PASSWORD"] = "test_password_123"
        config = APIKeyManagerConfig(
            enabled=True,
            key_file=temp_key_file,
            encryption_password_env="TEST_MASTER_PASSWORD",
        )
        return APIKeyManager(config)

    def test_set_and_get_api_key(self, manager: APIKeyManager) -> None:
        """Test setting and retrieving an API key."""
        # Set API key
        manager.set_api_key("openai", "sk-test123")

        # Get API key
        key = manager.get_api_key("openai")
        assert key == "sk-test123"

    def test_get_nonexistent_key_returns_none(self, manager: APIKeyManager) -> None:
        """Test that nonexistent key returns None."""
        key = manager.get_api_key("nonexistent")
        assert key is None

    def test_delete_api_key(self, manager: APIKeyManager) -> None:
        """Test deleting an API key."""
        # Set and verify key
        manager.set_api_key("anthropic", "sk-ant456")
        assert manager.get_api_key("anthropic") == "sk-ant456"

        # Delete key
        result = manager.delete_api_key("anthropic")
        assert result is True

        # Verify deletion
        assert manager.get_api_key("anthropic") is None

    def test_delete_nonexistent_key_returns_false(self, manager: APIKeyManager) -> None:
        """Test that deleting nonexistent key returns False."""
        result = manager.delete_api_key("nonexistent")
        assert result is False

    def test_list_providers(self, manager: APIKeyManager) -> None:
        """Test listing providers with stored keys."""
        manager.set_api_key("openai", "sk-test1")
        manager.set_api_key("anthropic", "sk-test2")
        manager.set_api_key("google", "sk-test3")

        providers = manager.list_providers()
        assert len(providers) == 3
        assert "openai" in providers
        assert "anthropic" in providers
        assert "google" in providers

    def test_has_key(self, manager: APIKeyManager) -> None:
        """Test checking if key exists."""
        manager.set_api_key("openai", "sk-test")

        assert manager.has_key("openai") is True
        assert manager.has_key("anthropic") is False

    def test_clear_cache(self, manager: APIKeyManager) -> None:
        """Test clearing the key cache."""
        manager.set_api_key("openai", "sk-test")

        # Verify key is cached
        assert manager.get_api_key("openai") == "sk-test"

        # Clear cache
        manager.clear_cache()

        # Key should still be retrievable (reloaded from file)
        assert manager.get_api_key("openai") == "sk-test"

    def test_environment_variable_takes_precedence(
        self, manager: APIKeyManager, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that environment variable takes precedence over stored key."""
        # Store key
        manager.set_api_key("openai", "sk-stored")

        # Set environment variable
        monkeypatch.setenv("API_KEY_OPENAI", "sk-env")

        # Should return env key
        key = manager.get_api_key("openai")
        assert key == "sk-env"

    def test_persistence_across_instances(
        self, temp_key_file: str
    ) -> None:
        """Test that keys persist across manager instances."""
        os.environ["TEST_MASTER_PASSWORD"] = "test_password_123"
        config = APIKeyManagerConfig(
            enabled=True,
            key_file=temp_key_file,
            encryption_password_env="TEST_MASTER_PASSWORD",
        )

        # First manager stores key
        manager1 = APIKeyManager(config)
        manager1.set_api_key("openai", "sk-persist")

        # Second manager retrieves key
        manager2 = APIKeyManager(config)
        key = manager2.get_api_key("openai")
        assert key == "sk-persist"


class TestAPIKeyManagerEncryption:
    """Tests for encryption functionality."""

    @pytest.fixture
    def temp_key_file(self) -> str:
        """Create temporary key file path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield str(Path(tmpdir) / "test_keys.enc")

    def test_keys_are_encrypted(self, temp_key_file: str) -> None:
        """Test that keys are stored encrypted."""
        os.environ["TEST_MASTER_PASSWORD"] = "test_password_123"
        config = APIKeyManagerConfig(
            enabled=True,
            key_file=temp_key_file,
            encryption_password_env="TEST_MASTER_PASSWORD",
        )

        manager = APIKeyManager(config)
        manager.set_api_key("openai", "sk-secret-key")

        # Read raw file content
        with open(temp_key_file, "rb") as f:
            encrypted_data = f.read()

        # Encrypted data should not contain plaintext key
        assert b"sk-secret-key" not in encrypted_data
        assert len(encrypted_data) > 0

    def test_salt_file_created(self, temp_key_file: str) -> None:
        """Test that salt file is created."""
        os.environ["TEST_MASTER_PASSWORD"] = "test_password_123"
        config = APIKeyManagerConfig(
            enabled=True,
            key_file=temp_key_file,
            encryption_password_env="TEST_MASTER_PASSWORD",
        )

        manager = APIKeyManager(config)
        manager.set_api_key("openai", "sk-test")

        salt_file = Path(temp_key_file).with_suffix(".salt")
        assert salt_file.exists()

        # Check salt size
        with open(salt_file, "rb") as f:
            salt = f.read()
        assert len(salt) == SALT_SIZE

    def test_wrong_password_fails_decryption(self, temp_key_file: str) -> None:
        """Test that wrong password fails to decrypt."""
        os.environ["TEST_MASTER_PASSWORD"] = "correct_password"
        config = APIKeyManagerConfig(
            enabled=True,
            key_file=temp_key_file,
            encryption_password_env="TEST_MASTER_PASSWORD",
        )

        # Store key with correct password
        manager1 = APIKeyManager(config)
        manager1.set_api_key("openai", "sk-test")

        # Try to read with wrong password
        os.environ["TEST_MASTER_PASSWORD"] = "wrong_password"
        with pytest.raises(APIKeyError) as exc_info:
            APIKeyManager(config)

        assert "decrypt" in exc_info.value.message.lower()


class TestAPIKeyManagerDisabled:
    """Tests for disabled API key manager."""

    def test_disabled_manager_returns_none(self) -> None:
        """Test that disabled manager returns None for get_api_key."""
        config = APIKeyManagerConfig(enabled=False)
        manager = APIKeyManager(config)

        key = manager.get_api_key("openai")
        assert key is None

    def test_disabled_manager_does_not_store(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test that disabled manager does not store keys."""
        config = APIKeyManagerConfig(enabled=False)
        manager = APIKeyManager(config)

        manager.set_api_key("openai", "sk-test")

        # Should log warning
        assert "disabled" in caplog.text.lower()

    def test_disabled_manager_list_returns_empty(self) -> None:
        """Test that disabled manager returns empty list."""
        config = APIKeyManagerConfig(enabled=False)
        manager = APIKeyManager(config)

        providers = manager.list_providers()
        assert providers == []

    def test_disabled_manager_has_key_returns_false(self) -> None:
        """Test that disabled manager returns False for has_key."""
        config = APIKeyManagerConfig(enabled=False)
        manager = APIKeyManager(config)

        assert manager.has_key("openai") is False


class TestAPIKeyManagerErrors:
    """Tests for error handling."""

    def test_corrupted_salt_file_raises(self) -> None:
        """Test that corrupted salt file raises APIKeyError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = Path(tmpdir) / "test_keys.enc"
            salt_file = key_file.with_suffix(".salt")

            # Create corrupted salt file (wrong size)
            salt_file.write_bytes(b"too_short")

            os.environ["TEST_MASTER_PASSWORD"] = "test_password"
            config = APIKeyManagerConfig(
                enabled=True,
                key_file=str(key_file),
                encryption_password_env="TEST_MASTER_PASSWORD",
            )

            with pytest.raises(APIKeyError) as exc_info:
                APIKeyManager(config)

            assert "Corrupted salt file" in exc_info.value.message
