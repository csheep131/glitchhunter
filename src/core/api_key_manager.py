"""
API Key Manager for secure storage and retrieval of API keys.

Uses Fernet symmetric encryption from the cryptography library to encrypt
API keys at rest. Keys are decrypted only when needed for API requests.
"""

import base64
import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from core.config import APIKeyManagerConfig
from core.exceptions import APIKeyError

logger = logging.getLogger(__name__)

# Salt size in bytes
SALT_SIZE = 16

# PBKDF2 iterations for key derivation
ITERATIONS = 100000


class APIKeyManager:
    """
    Manages encrypted storage and retrieval of API keys.

    Uses Fernet encryption with a master password derived from an
    environment variable. API keys are stored in an encrypted JSON file.

    Attributes:
        config: Configuration for the API key manager
        _fernet: Fernet instance for encryption/decryption
        _keys: Cached dictionary of decrypted API keys
    """

    def __init__(self, config: Optional[APIKeyManagerConfig] = None) -> None:
        """
        Initialize the API key manager.

        Args:
            config: Configuration for the API key manager.
                   If None, uses default configuration.

        Raises:
            APIKeyError: If master password is not set
        """
        self.config = config or APIKeyManagerConfig()
        self._keys: Dict[str, str] = {}
        self._fernet: Optional[Fernet] = None

        if self.config.enabled:
            self._initialize_encryption()

    def _initialize_encryption(self) -> None:
        """
        Initialize Fernet encryption with master password.

        Raises:
            APIKeyError: If master password is not set or invalid
        """
        password = os.getenv(self.config.encryption_password_env)

        if not password:
            raise APIKeyError(
                f"Master password not set in environment variable: {self.config.encryption_password_env}",
                details={
                    "encryption_password_env": self.config.encryption_password_env
                },
            )

        # Derive encryption key from password using PBKDF2
        salt = self._get_or_create_salt()
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=ITERATIONS,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        self._fernet = Fernet(key)

    def _get_or_create_salt(self) -> bytes:
        """
        Get existing salt or create new one.

        Returns:
            Salt as bytes

        Raises:
            APIKeyError: If salt file cannot be read or written
        """
        key_file_path = Path(self.config.key_file)
        salt_file = key_file_path.with_suffix(".salt")

        # Try to read existing salt
        if salt_file.exists():
            try:
                with open(salt_file, "rb") as f:
                    salt = f.read()
                if len(salt) != SALT_SIZE:
                    raise APIKeyError(
                        "Corrupted salt file - invalid salt size",
                        details={"salt_file": str(salt_file), "expected_size": SALT_SIZE, "actual_size": len(salt)},
                    )
                return salt
            except IOError as e:
                raise APIKeyError(
                    f"Failed to read salt file: {e}",
                    details={"salt_file": str(salt_file)},
                )

        # Create new salt
        salt = os.urandom(SALT_SIZE)

        # Ensure directory exists
        salt_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(salt_file, "wb") as f:
                f.write(salt)
            # Set restrictive permissions (owner read/write only)
            os.chmod(salt_file, 0o600)
            logger.debug(f"Created new salt file: {salt_file}")
            return salt
        except IOError as e:
            raise APIKeyError(
                f"Failed to create salt file: {e}",
                details={"salt_file": str(salt_file)},
            )

    def _load_keys(self) -> None:
        """
        Load and decrypt API keys from file.

        Raises:
            APIKeyError: If key file cannot be read or decrypted
        """
        if not self._fernet:
            return

        key_file_path = Path(self.config.key_file)

        if not key_file_path.exists():
            logger.debug(f"API key file not found: {key_file_path}")
            self._keys = {}
            return

        try:
            with open(key_file_path, "rb") as f:
                encrypted_data = f.read()

            if not encrypted_data:
                self._keys = {}
                return

            decrypted_data = self._fernet.decrypt(encrypted_data)
            self._keys = json.loads(decrypted_data.decode("utf-8"))
            logger.debug(f"Loaded {len(self._keys)} API key(s) from {key_file_path}")

        except Exception as e:
            raise APIKeyError(
                f"Failed to decrypt API keys: {e}",
                details={"key_file": str(key_file_path)},
            )

    def _save_keys(self) -> None:
        """
        Encrypt and save API keys to file.

        Raises:
            APIKeyError: If key file cannot be written or encrypted
        """
        if not self._fernet:
            return

        key_file_path = Path(self.config.key_file)

        # Ensure directory exists
        key_file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            encrypted_data = self._fernet.encrypt(
                json.dumps(self._keys).encode("utf-8")
            )
            with open(key_file_path, "wb") as f:
                f.write(encrypted_data)
            # Set restrictive permissions (owner read/write only)
            os.chmod(key_file_path, 0o600)
            logger.debug(f"Saved API keys to {key_file_path}")

        except Exception as e:
            raise APIKeyError(
                f"Failed to encrypt and save API keys: {e}",
                details={"key_file": str(key_file_path)},
            )

    def get_api_key(self, provider_name: str) -> Optional[str]:
        """
        Get API key for a provider.

        First checks environment variable (pattern: API_KEY_{PROVIDER_NAME}),
        then falls back to encrypted storage.

        Args:
            provider_name: Name of the provider (e.g., "openai", "anthropic")

        Returns:
            API key if found, None otherwise

        Raises:
            APIKeyError: If decryption fails
        """
        # First try environment variable
        env_var_name = f"API_KEY_{provider_name.upper().replace('-', '_')}"
        env_key = os.getenv(env_var_name)
        if env_key:
            logger.debug(f"Found API key for {provider_name} in environment")
            return env_key

        # Then try encrypted storage
        if not self.config.enabled:
            return None

        if not self._keys:
            self._load_keys()

        return self._keys.get(provider_name)

    def set_api_key(self, provider_name: str, api_key: str) -> None:
        """
        Store API key for a provider.

        Args:
            provider_name: Name of the provider
            api_key: API key to store

        Raises:
            APIKeyError: If encryption or save fails
        """
        if not self.config.enabled:
            logger.warning(
                f"API key manager is disabled. Key for {provider_name} not stored."
            )
            return

        if not self._keys:
            self._load_keys()

        self._keys[provider_name] = api_key
        self._save_keys()
        logger.info(f"Stored API key for provider: {provider_name}")

    def delete_api_key(self, provider_name: str) -> bool:
        """
        Delete API key for a provider.

        Args:
            provider_name: Name of the provider

        Returns:
            True if key was deleted, False if key didn't exist

        Raises:
            APIKeyError: If encryption or save fails
        """
        if not self.config.enabled:
            return False

        if not self._keys:
            self._load_keys()

        if provider_name not in self._keys:
            return False

        del self._keys[provider_name]
        self._save_keys()
        logger.info(f"Deleted API key for provider: {provider_name}")
        return True

    def list_providers(self) -> list[str]:
        """
        List all providers with stored API keys.

        Returns:
            List of provider names

        Raises:
            APIKeyError: If decryption fails
        """
        if not self.config.enabled:
            return []

        if not self._keys:
            self._load_keys()

        return list(self._keys.keys())

    def has_key(self, provider_name: str) -> bool:
        """
        Check if API key exists for a provider.

        Args:
            provider_name: Name of the provider

        Returns:
            True if key exists, False otherwise

        Raises:
            APIKeyError: If decryption fails
        """
        # Check environment variable
        env_var_name = f"API_KEY_{provider_name.upper().replace('-', '_')}"
        if os.getenv(env_var_name):
            return True

        # Check encrypted storage
        if not self.config.enabled:
            return False

        if not self._keys:
            self._load_keys()

        return provider_name in self._keys

    def clear_cache(self) -> None:
        """Clear the in-memory cache of decrypted API keys."""
        self._keys = {}
        logger.debug("Cleared API key cache")
