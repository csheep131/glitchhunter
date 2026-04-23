"""
Provider Factory for creating remote provider instances.

Creates provider instances based on configuration and handles
provider registration and lookup.
"""

import logging
from typing import Dict, List, Optional, Type

from core.api_key_manager import APIKeyManager
from core.config import RemoteProviderConfig, StackCConfig
from core.exceptions import ProviderConfigurationError, RemoteProviderError

from .base_provider import BaseProvider
from .providers.openai_provider import OpenAIProvider

logger = logging.getLogger(__name__)


# Registry of available provider types
PROVIDER_REGISTRY: Dict[str, Type[BaseProvider]] = {
    "openai": OpenAIProvider,
    "azure_openai": OpenAIProvider,  # Azure uses same client with different config
    "ollama": OpenAIProvider,  # Ollama OpenAI-compatible API
    "vllm": OpenAIProvider,  # vLLM OpenAI-compatible API
    "deepseek": OpenAIProvider,  # DeepSeek OpenAI-compatible API
}


class ProviderFactory:
    """
    Factory for creating and managing remote provider instances.

    Handles provider instantiation, configuration, and caching.
    Providers are created on-demand and cached for reuse.

    Attributes:
        config: Stack C configuration
        api_key_manager: API key manager for retrieving keys
        _providers: Cache of created provider instances
    """

    def __init__(
        self,
        config: StackCConfig,
        api_key_manager: Optional[APIKeyManager] = None,
    ) -> None:
        """
        Initialize the provider factory.

        Args:
            config: Stack C configuration
            api_key_manager: Optional API key manager
        """
        self.config = config
        self.api_key_manager = api_key_manager or APIKeyManager()
        self._providers: Dict[str, BaseProvider] = {}

    def get_provider(self, provider_name: str) -> BaseProvider:
        """
        Get or create a provider instance.

        Args:
            provider_name: Name of the provider

        Returns:
            Provider instance

        Raises:
            ProviderConfigurationError: If provider not found or misconfigured
            RemoteProviderError: If provider creation fails
        """
        # Check cache first
        if provider_name in self._providers:
            logger.debug(f"Using cached provider: {provider_name}")
            return self._providers[provider_name]

        # Get provider configuration
        provider_config = self._get_provider_config(provider_name)

        # Create provider instance
        provider = self._create_provider(provider_name, provider_config)

        # Cache and return
        self._providers[provider_name] = provider
        logger.info(f"Created provider instance: {provider_name}")
        return provider

    def _get_provider_config(self, provider_name: str) -> RemoteProviderConfig:
        """
        Get configuration for a provider.

        Args:
            provider_name: Name of the provider

        Returns:
            Provider configuration

        Raises:
            ProviderConfigurationError: If provider not configured
        """
        if provider_name not in self.config.providers:
            available = list(self.config.providers.keys())
            raise ProviderConfigurationError(
                f"Provider '{provider_name}' not configured",
                provider_name=provider_name,
                details={"available_providers": available},
            )

        return self.config.providers[provider_name]

    def _create_provider(
        self, provider_name: str, config: RemoteProviderConfig
    ) -> BaseProvider:
        """
        Create a provider instance from configuration.

        Args:
            provider_name: Name of the provider
            config: Provider configuration

        Returns:
            Provider instance

        Raises:
            ProviderConfigurationError: If provider type not supported
            RemoteProviderError: If provider creation fails
        """
        # Determine provider type from name or URL
        provider_type = self._determine_provider_type(provider_name, config)

        # Get provider class from registry
        provider_class = PROVIDER_REGISTRY.get(provider_type)
        if not provider_class:
            supported = list(PROVIDER_REGISTRY.keys())
            raise ProviderConfigurationError(
                f"Unsupported provider type: {provider_type}",
                provider_name=provider_name,
                field="provider_type",
                details={"supported_types": supported},
            )

        # Retrieve API key if needed
        api_key = self._get_api_key(provider_name, config)

        try:
            # Create provider instance
            provider = provider_class(
                name=provider_name,
                base_url=config.base_url,
                timeout=config.timeout,
                api_key=api_key,
            )
            logger.debug(
                f"Created {provider_type} provider: {provider_name} at {config.base_url}"
            )
            return provider

        except Exception as e:
            raise RemoteProviderError(
                f"Failed to create provider '{provider_name}': {e}",
                provider_name=provider_name,
                details={"provider_type": provider_type, "base_url": config.base_url},
            )

    def _determine_provider_type(
        self, provider_name: str, config: RemoteProviderConfig
    ) -> str:
        """
        Determine provider type from name or URL.

        Args:
            provider_name: Provider name
            config: Provider configuration

        Returns:
            Provider type string
        """
        # Check if name contains type hint
        name_lower = provider_name.lower()

        if "azure" in name_lower:
            return "azure_openai"
        elif "ollama" in name_lower:
            return "ollama"
        elif "vllm" in name_lower:
            return "vllm"
        elif "deepseek" in name_lower:
            return "deepseek"

        # Check URL for type hints
        url_lower = config.base_url.lower()
        if "azure" in url_lower:
            return "azure_openai"
        elif "ollama" in url_lower:
            return "ollama"
        elif "openai" in url_lower:
            return "openai"

        # Default to OpenAI-compatible
        return "openai"

    def _get_api_key(
        self, provider_name: str, config: RemoteProviderConfig
    ) -> Optional[str]:
        """
        Get API key for a provider.

        Args:
            provider_name: Name of the provider
            config: Provider configuration

        Returns:
            API key if available, None otherwise
        """
        # Try environment variable from config
        if config.api_key_env:
            import os

            api_key = os.getenv(config.api_key_env)
            if api_key:
                logger.debug(
                    f"Found API key for {provider_name} in env var {config.api_key_env}"
                )
                return api_key

        # Try API key manager
        if self.api_key_manager:
            api_key = self.api_key_manager.get_api_key(provider_name)
            if api_key:
                return api_key

        logger.warning(f"No API key found for provider: {provider_name}")
        return None

    def list_providers(self) -> List[str]:
        """
        List all configured providers.

        Returns:
            List of provider names
        """
        return list(self.config.providers.keys())

    def list_available_types(self) -> List[str]:
        """
        List all available provider types.

        Returns:
            List of provider type names
        """
        return list(PROVIDER_REGISTRY.keys())

    def get_default_provider(self) -> BaseProvider:
        """
        Get the default provider.

        Returns:
            Default provider instance

        Raises:
            ProviderConfigurationError: If no default provider configured
        """
        return self.get_provider(self.config.default_provider)

    def clear_cache(self) -> None:
        """Clear the provider instance cache."""
        self._providers.clear()
        logger.debug("Cleared provider cache")

    def is_provider_available(self, provider_name: str) -> bool:
        """
        Check if a provider is configured.

        Args:
            provider_name: Name of the provider

        Returns:
            True if provider is configured, False otherwise
        """
        return provider_name in self.config.providers

    def get_fallback_chain(self) -> List[str]:
        """
        Get the fallback chain of providers.

        Returns:
            List of provider names in fallback order
        """
        return self.config.fallback_chain.copy()
