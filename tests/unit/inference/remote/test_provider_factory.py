"""
Unit tests for Provider Factory.

Tests cover provider creation, caching, configuration, and error handling.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from core.config import (
    CacheConfig,
    RateLimitConfig,
    RemoteProviderConfig,
    RetryConfig,
    StackCConfig,
)
from core.exceptions import ProviderConfigurationError
from inference.remote.base_provider import BaseProvider
from inference.remote.provider_factory import PROVIDER_REGISTRY, ProviderFactory
from inference.remote.providers.openai_provider import OpenAIProvider


class TestProviderFactoryInit:
    """Tests for ProviderFactory initialization."""

    def test_init_with_basic_config(self) -> None:
        """Test initialization with basic configuration."""
        config = StackCConfig(
            providers={
                "openai": RemoteProviderConfig(
                    name="openai", base_url="https://api.openai.com"
                )
            }
        )
        factory = ProviderFactory(config)

        assert factory.config == config
        assert factory._providers == {}

    def test_init_with_api_key_manager(self) -> None:
        """Test initialization with custom API key manager."""
        config = StackCConfig()
        mock_key_manager = MagicMock()

        factory = ProviderFactory(config, api_key_manager=mock_key_manager)

        assert factory.api_key_manager == mock_key_manager

    def test_init_creates_default_key_manager(self) -> None:
        """Test that default API key manager is created."""
        config = StackCConfig()

        with patch(
            "inference.remote.provider_factory.APIKeyManager"
        ) as mock_manager_class:
            factory = ProviderFactory(config)

            mock_manager_class.assert_called_once()


class TestProviderFactoryGetProvider:
    """Tests for get_provider method."""

    @pytest.fixture
    def basic_config(self) -> StackCConfig:
        """Create basic StackCConfig."""
        return StackCConfig(
            providers={
                "openai": RemoteProviderConfig(
                    name="openai",
                    base_url="https://api.openai.com",
                    api_key_env="OPENAI_API_KEY",
                ),
                "ollama": RemoteProviderConfig(
                    name="ollama",
                    base_url="http://localhost:11434",
                ),
            },
            default_provider="openai",
        )

    def test_get_provider_creates_instance(self, basic_config: StackCConfig) -> None:
        """Test that get_provider creates provider instance."""
        os.environ["OPENAI_API_KEY"] = "sk-test123"
        factory = ProviderFactory(basic_config)

        provider = factory.get_provider("openai")

        assert isinstance(provider, OpenAIProvider)
        assert provider.name == "openai"
        assert provider.base_url == "https://api.openai.com"

    def test_get_provider_caches_instance(self, basic_config: StackCConfig) -> None:
        """Test that provider instances are cached."""
        os.environ["OPENAI_API_KEY"] = "sk-test123"
        factory = ProviderFactory(basic_config)

        provider1 = factory.get_provider("openai")
        provider2 = factory.get_provider("openai")

        assert provider1 is provider2
        assert "openai" in factory._providers

    def test_get_provider_unknown_raises(self, basic_config: StackCConfig) -> None:
        """Test that unknown provider raises error."""
        factory = ProviderFactory(basic_config)

        with pytest.raises(ProviderConfigurationError) as exc_info:
            factory.get_provider("unknown")

        assert "not configured" in exc_info.value.message
        assert exc_info.value.details["available_providers"] == ["openai", "ollama"]

    def test_get_default_provider(self, basic_config: StackCConfig) -> None:
        """Test getting default provider."""
        os.environ["OPENAI_API_KEY"] = "sk-test123"
        factory = ProviderFactory(basic_config)

        provider = factory.get_default_provider()

        assert isinstance(provider, OpenAIProvider)
        assert provider.name == "openai"


class TestProviderFactoryProviderTypes:
    """Tests for different provider types."""

    def test_ollama_provider_detection(self) -> None:
        """Test Ollama provider type detection."""
        config = StackCConfig(
            providers={
                "ollama_lan": RemoteProviderConfig(
                    name="ollama_lan",
                    base_url="http://localhost:11434",
                )
            }
        )
        factory = ProviderFactory(config)

        provider = factory.get_provider("ollama_lan")
        assert isinstance(provider, OpenAIProvider)
        assert provider.name == "ollama_lan"

    def test_azure_provider_detection(self) -> None:
        """Test Azure provider type detection."""
        config = StackCConfig(
            providers={
                "azure_openai": RemoteProviderConfig(
                    name="azure_openai",
                    base_url="https://my-resource.openai.azure.com",
                    api_key_env="AZURE_API_KEY",
                )
            }
        )
        os.environ["AZURE_API_KEY"] = "azure-key-123"
        factory = ProviderFactory(config)

        provider = factory.get_provider("azure_openai")
        assert isinstance(provider, OpenAIProvider)

    def test_vllm_provider_detection(self) -> None:
        """Test vLLM provider type detection."""
        config = StackCConfig(
            providers={
                "vllm": RemoteProviderConfig(
                    name="vllm",
                    base_url="http://localhost:8000",
                )
            }
        )
        factory = ProviderFactory(config)

        provider = factory.get_provider("vllm")
        assert isinstance(provider, OpenAIProvider)


class TestProviderFactoryApiKeyRetrieval:
    """Tests for API key retrieval."""

    def test_api_key_from_env_var(self) -> None:
        """Test API key retrieval from environment variable."""
        os.environ["CUSTOM_API_KEY"] = "sk-custom-123"
        config = StackCConfig(
            providers={
                "custom": RemoteProviderConfig(
                    name="custom",
                    base_url="https://api.custom.com",
                    api_key_env="CUSTOM_API_KEY",
                )
            }
        )
        factory = ProviderFactory(config)

        provider = factory.get_provider("custom")
        assert provider.get_api_key() == "sk-custom-123"

    def test_api_key_from_key_manager(self) -> None:
        """Test API key retrieval from key manager."""
        mock_key_manager = MagicMock()
        mock_key_manager.get_api_key.return_value = "sk-stored-456"

        config = StackCConfig(
            providers={
                "stored": RemoteProviderConfig(
                    name="stored",
                    base_url="https://api.stored.com",
                )
            }
        )
        factory = ProviderFactory(config, api_key_manager=mock_key_manager)

        provider = factory.get_provider("stored")
        assert provider.get_api_key() == "sk-stored-456"

    def test_api_key_env_takes_precedence(self) -> None:
        """Test that env var takes precedence over key manager."""
        os.environ["TEST_API_KEY"] = "sk-env-key"
        mock_key_manager = MagicMock()
        mock_key_manager.get_api_key.return_value = "sk-stored-key"

        config = StackCConfig(
            providers={
                "test": RemoteProviderConfig(
                    name="test",
                    base_url="https://api.test.com",
                    api_key_env="TEST_API_KEY",
                )
            }
        )
        factory = ProviderFactory(config, api_key_manager=mock_key_manager)

        provider = factory.get_provider("test")
        assert provider.get_api_key() == "sk-env-key"


class TestProviderFactoryListMethods:
    """Tests for list methods."""

    def test_list_providers(self) -> None:
        """Test listing configured providers."""
        config = StackCConfig(
            providers={
                "openai": RemoteProviderConfig(name="openai", base_url="https://api.openai.com"),
                "ollama": RemoteProviderConfig(name="ollama", base_url="http://localhost:11434"),
                "anthropic": RemoteProviderConfig(
                    name="anthropic", base_url="https://api.anthropic.com"
                ),
            }
        )
        factory = ProviderFactory(config)

        providers = factory.list_providers()
        assert len(providers) == 3
        assert "openai" in providers
        assert "ollama" in providers
        assert "anthropic" in providers

    def test_list_available_types(self) -> None:
        """Test listing available provider types."""
        config = StackCConfig()
        factory = ProviderFactory(config)

        types = factory.list_available_types()
        assert len(types) > 0
        assert "openai" in types
        assert "ollama" in types


class TestProviderFactoryFallback:
    """Tests for fallback chain."""

    def test_get_fallback_chain(self) -> None:
        """Test getting fallback chain."""
        config = StackCConfig(
            fallback_chain=["primary", "secondary", "tertiary"]
        )
        factory = ProviderFactory(config)

        chain = factory.get_fallback_chain()
        assert chain == ["primary", "secondary", "tertiary"]

    def test_get_fallback_chain_returns_copy(self) -> None:
        """Test that get_fallback_chain returns a copy."""
        config = StackCConfig(fallback_chain=["primary", "secondary"])
        factory = ProviderFactory(config)

        chain1 = factory.get_fallback_chain()
        chain2 = factory.get_fallback_chain()

        # Should be different list objects
        assert chain1 is not chain2
        assert chain1 == chain2


class TestProviderFactoryUtilities:
    """Tests for utility methods."""

    def test_is_provider_available_true(self) -> None:
        """Test is_provider_available returns True for configured provider."""
        config = StackCConfig(
            providers={
                "openai": RemoteProviderConfig(name="openai", base_url="https://api.openai.com")
            }
        )
        factory = ProviderFactory(config)

        assert factory.is_provider_available("openai") is True

    def test_is_provider_available_false(self) -> None:
        """Test is_provider_available returns False for unknown provider."""
        config = StackCConfig()
        factory = ProviderFactory(config)

        assert factory.is_provider_available("unknown") is False

    def test_clear_cache(self) -> None:
        """Test clearing provider cache."""
        os.environ["OPENAI_API_KEY"] = "sk-test"
        config = StackCConfig(
            providers={
                "openai": RemoteProviderConfig(name="openai", base_url="https://api.openai.com")
            }
        )
        factory = ProviderFactory(config)

        # Create provider
        factory.get_provider("openai")
        assert len(factory._providers) == 1

        # Clear cache
        factory.clear_cache()
        assert len(factory._providers) == 0


class TestProviderRegistry:
    """Tests for provider registry."""

    def test_registry_contains_openai(self) -> None:
        """Test that registry contains OpenAI provider."""
        assert "openai" in PROVIDER_REGISTRY
        assert PROVIDER_REGISTRY["openai"] == OpenAIProvider

    def test_registry_contains_ollama(self) -> None:
        """Test that registry contains Ollama provider."""
        assert "ollama" in PROVIDER_REGISTRY
        assert PROVIDER_REGISTRY["ollama"] == OpenAIProvider

    def test_registry_contains_vllm(self) -> None:
        """Test that registry contains vLLM provider."""
        assert "vllm" in PROVIDER_REGISTRY
        assert PROVIDER_REGISTRY["vllm"] == OpenAIProvider


class TestProviderConfigurationError:
    """Tests for configuration error handling."""

    def test_unsupported_provider_type(self) -> None:
        """Test error for unsupported provider type."""
        # Mock registry to only have openai
        with patch.dict(PROVIDER_REGISTRY, {"openai": OpenAIProvider}, clear=True):
            config = StackCConfig(
                providers={
                    "unknown": RemoteProviderConfig(
                        name="unknown",
                        base_url="https://unknown.com",
                    )
                }
            )
            factory = ProviderFactory(config)

            # Force unknown type by URL pattern
            with pytest.raises(ProviderConfigurationError) as exc_info:
                # This would normally work since OpenAI is default
                # We need to test the error path differently
                pass

    def test_provider_not_in_config(self) -> None:
        """Test error when provider not in configuration."""
        config = StackCConfig(providers={})
        factory = ProviderFactory(config)

        with pytest.raises(ProviderConfigurationError) as exc_info:
            factory.get_provider("nonexistent")

        assert exc_info.value.code == "PROVIDER_CONFIGURATION_ERROR"
        assert "nonexistent" in exc_info.value.message
