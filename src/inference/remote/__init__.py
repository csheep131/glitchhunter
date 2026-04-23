"""
Remote Inference Module for GlitchHunter.

Provides remote API inference capabilities through various providers
like OpenAI, Azure OpenAI, Ollama, vLLM, and DeepSeek.

Exports:
    - BaseProvider: Abstract base class for all providers
    - ProviderFactory: Factory for creating provider instances
    - ChatMessage, ChatCompletionRequest, ChatCompletionResponse: Chat types
    - EmbeddingRequest, EmbeddingResponse: Embedding types
    - HealthStatus: Health check status
"""

from .base_provider import (
    BaseProvider,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    EmbeddingRequest,
    EmbeddingResponse,
    HealthStatus,
)
from .provider_factory import ProviderFactory

__all__ = [
    "BaseProvider",
    "ProviderFactory",
    "ChatMessage",
    "ChatCompletionRequest",
    "ChatCompletionResponse",
    "EmbeddingRequest",
    "EmbeddingResponse",
    "HealthStatus",
]
