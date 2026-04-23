"""
Remote Providers for GlitchHunter.

Provider implementations for various remote inference APIs.

Exports:
    - OpenAIProvider: OpenAI-compatible provider
    - AnthropicProvider: Anthropic Claude API provider
    - OllamaProvider: Ollama local API provider
    - CustomProvider: Configurable generic provider
    - CustomProviderConfig: Configuration for CustomProvider
"""

from .anthropic_provider import AnthropicProvider
from .custom_provider import CustomProvider, CustomProviderConfig
from .ollama_provider import OllamaProvider
from .openai_provider import OpenAIProvider

__all__ = [
    "OpenAIProvider",
    "AnthropicProvider",
    "OllamaProvider",
    "CustomProvider",
    "CustomProviderConfig",
]
