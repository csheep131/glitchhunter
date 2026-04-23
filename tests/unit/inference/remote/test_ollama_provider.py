"""
Unit tests for Ollama Provider.

Tests cover:
- Provider initialization and configuration
- OpenAI-compatible mode chat completion
- Native Ollama API chat completion
- Embeddings in both modes
- Error handling and retry logic
- Health checks and model listing
"""

import asyncio
import json
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import respx

from core.exceptions import RateLimitExceededError, RemoteProviderError
from inference.remote.base_provider import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    EmbeddingRequest,
    EmbeddingResponse,
    HealthStatus,
)
from inference.remote.providers.ollama_provider import OllamaProvider


class TestOllamaProviderInit:
    """Tests for OllamaProvider initialization."""

    def test_default_initialization(self) -> None:
        """Test default initialization parameters."""
        provider = OllamaProvider()

        assert provider.name == "ollama"
        assert provider.base_url == "http://localhost:11434"
        assert provider.timeout == 120
        assert provider._api_key is None
        assert provider.max_retries == 3
        assert provider.use_openai_mode is True
        assert provider.streaming_enabled is False

    def test_custom_initialization(self) -> None:
        """Test custom initialization parameters."""
        provider = OllamaProvider(
            name="local-ollama",
            base_url="http://192.168.1.100:11434",
            timeout=60,
            max_retries=5,
            use_openai_mode=False,
            streaming_enabled=True,
        )

        assert provider.name == "local-ollama"
        assert provider.base_url == "http://192.168.1.100:11434"
        assert provider.timeout == 60
        assert provider.max_retries == 5
        assert provider.use_openai_mode is False
        assert provider.streaming_enabled is True

    def test_base_url_trailing_slash_removal(self) -> None:
        """Test that trailing slashes are removed from base URL."""
        provider = OllamaProvider(base_url="http://localhost:11434/")
        assert provider.base_url == "http://localhost:11434"

    def test_api_key_optional(self) -> None:
        """Test that API key is optional for Ollama."""
        provider = OllamaProvider()
        assert provider.get_api_key() is None

        provider_with_key = OllamaProvider(api_key="ollama-key")
        assert provider_with_key.get_api_key() == "ollama-key"

    def test_get_provider_name(self) -> None:
        """Test provider name retrieval."""
        provider = OllamaProvider(name="test-ollama")
        assert provider.get_provider_name() == "test-ollama"


class TestOllamaProviderOpenAIMode:
    """Tests for OllamaProvider OpenAI-compatible mode."""

    @pytest.mark.asyncio
    async def test_basic_chat_completion_openai_mode(
        self, respx_mock: respx.MockRouter
    ) -> None:
        """Test basic chat completion in OpenAI mode."""
        mock_response = {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "llama2",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "Hello! How can I help?"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        }

        respx_mock.post("http://localhost:11434/v1/chat/completions").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        provider = OllamaProvider(use_openai_mode=True)
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="Hello")],
            model="llama2",
        )

        response = await provider.chat_completion(request)

        assert response.content == "Hello! How can I help?"
        assert response.model == "llama2"
        assert response.prompt_tokens == 10
        assert response.completion_tokens == 20
        assert response.total_tokens == 30
        assert response.finish_reason == "stop"

        await provider.close()

    @pytest.mark.asyncio
    async def test_chat_completion_with_api_key(
        self, respx_mock: respx.MockRouter
    ) -> None:
        """Test chat completion with API key in OpenAI mode."""
        mock_response = {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "llama2",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "Response"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15},
        }

        route = respx_mock.post("http://localhost:11434/v1/chat/completions")
        route.mock(return_value=httpx.Response(200, json=mock_response))

        provider = OllamaProvider(api_key="ollama-key", use_openai_mode=True)
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="Test")],
            model="llama2",
        )

        response = await provider.chat_completion(request)

        # Verify Authorization header was sent
        assert route.calls.last is not None
        assert route.calls.last.request.headers.get("Authorization") == "Bearer ollama-key"

        await provider.close()

    @pytest.mark.asyncio
    async def test_chat_completion_with_parameters_openai_mode(
        self, respx_mock: respx.MockRouter
    ) -> None:
        """Test chat completion with custom parameters in OpenAI mode."""
        mock_response = {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "codellama",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "Code response"},
                    "finish_reason": "length",
                }
            ],
            "usage": {"prompt_tokens": 15, "completion_tokens": 50, "total_tokens": 65},
        }

        route = respx_mock.post("http://localhost:11434/v1/chat/completions")
        route.mock(return_value=httpx.Response(200, json=mock_response))

        provider = OllamaProvider(use_openai_mode=True)
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="Write code")],
            model="codellama",
            temperature=0.3,
            max_tokens=100,
            top_p=0.8,
            stop=["```", "END"],
        )

        response = await provider.chat_completion(request)

        # Verify parameters were sent
        assert route.calls.last is not None
        request_payload = json.loads(route.calls.last.request.content)
        assert request_payload["temperature"] == 0.3
        assert request_payload["max_tokens"] == 100
        assert request_payload["top_p"] == 0.8
        assert request_payload["stop"] == ["```", "END"]

        assert response.content == "Code response"
        assert response.finish_reason == "length"

        await provider.close()


class TestOllamaProviderNativeMode:
    """Tests for OllamaProvider native API mode."""

    @pytest.mark.asyncio
    async def test_basic_chat_completion_native_mode(
        self, respx_mock: respx.MockRouter
    ) -> None:
        """Test basic chat completion in native mode."""
        mock_response = {
            "model": "llama2",
            "created_at": "2024-01-01T00:00:00.000000Z",
            "message": {
                "role": "assistant",
                "content": "Native response",
            },
            "done": True,
            "total_duration": 1234567890,
            "load_duration": 123456,
            "prompt_eval_count": 10,
            "eval_count": 25,
        }

        respx_mock.post("http://localhost:11434/api/chat").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        provider = OllamaProvider(use_openai_mode=False)
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="Hello")],
            model="llama2",
        )

        response = await provider.chat_completion(request)

        assert response.content == "Native response"
        assert response.model == "llama2"
        assert response.prompt_tokens == 10
        assert response.completion_tokens == 25
        assert response.total_tokens == 35
        assert response.finish_reason == "stop"

        await provider.close()

    @pytest.mark.asyncio
    async def test_chat_completion_native_mode_with_options(
        self, respx_mock: respx.MockRouter
    ) -> None:
        """Test chat completion with options in native mode."""
        mock_response = {
            "model": "mistral",
            "created_at": "2024-01-01T00:00:00.000000Z",
            "message": {
                "role": "assistant",
                "content": "Mistral response",
            },
            "done": True,
            "prompt_eval_count": 8,
            "eval_count": 15,
        }

        route = respx_mock.post("http://localhost:11434/api/chat")
        route.mock(return_value=httpx.Response(200, json=mock_response))

        provider = OllamaProvider(use_openai_mode=False)
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="Test")],
            model="mistral",
            temperature=0.5,
            max_tokens=50,
            top_p=0.9,
        )

        response = await provider.chat_completion(request)

        # Verify options were sent
        assert route.calls.last is not None
        request_payload = json.loads(route.calls.last.request.content)
        assert "options" in request_payload
        assert request_payload["options"]["temperature"] == 0.5
        assert request_payload["options"]["num_predict"] == 50
        assert request_payload["options"]["top_p"] == 0.9

        await provider.close()

    @pytest.mark.asyncio
    async def test_chat_completion_default_model(self) -> None:
        """Test chat completion uses default model when not specified."""
        provider = OllamaProvider(use_openai_mode=False)

        with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "model": "llama2",
                "message": {"role": "assistant", "content": "Response"},
                "done": True,
                "prompt_eval_count": 5,
                "eval_count": 10,
            }

            request = ChatCompletionRequest(
                messages=[ChatMessage(role="user", content="Hello")],
                model="",  # Empty model
            )

            await provider.chat_completion(request)

            # Verify default model was used
            assert mock_request.call_args is not None
            payload = mock_request.call_args[0][2]
            assert payload["model"] == "llama2"


class TestOllamaProviderEmbeddings:
    """Tests for OllamaProvider embeddings functionality."""

    @pytest.mark.asyncio
    async def test_embeddings_openai_mode(
        self, respx_mock: respx.MockRouter
    ) -> None:
        """Test embeddings in OpenAI mode."""
        mock_response = {
            "object": "list",
            "data": [
                {
                    "object": "embedding",
                    "embedding": [0.1, 0.2, 0.3, 0.4, 0.5],
                    "index": 0,
                }
            ],
            "model": "nomic-embed-text",
            "usage": {"prompt_tokens": 5, "total_tokens": 5},
        }

        respx_mock.post("http://localhost:11434/v1/embeddings").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        provider = OllamaProvider(use_openai_mode=True)
        request = EmbeddingRequest(
            input="Test text for embedding",
            model="nomic-embed-text",
        )

        response = await provider.embeddings(request)

        assert len(response.embeddings) == 1
        assert response.embeddings[0] == [0.1, 0.2, 0.3, 0.4, 0.5]
        assert response.model == "nomic-embed-text"
        assert response.prompt_tokens == 5

        await provider.close()

    @pytest.mark.asyncio
    async def test_embeddings_native_mode(
        self, respx_mock: respx.MockRouter
    ) -> None:
        """Test embeddings in native mode."""
        mock_response = {
            "embedding": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6],
            "model": "nomic-embed-text",
        }

        respx_mock.post("http://localhost:11434/api/embeddings").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        provider = OllamaProvider(use_openai_mode=False)
        request = EmbeddingRequest(
            input="Test text",
            model="nomic-embed-text",
        )

        response = await provider.embeddings(request)

        assert len(response.embeddings) == 1
        assert response.embeddings[0] == [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
        assert response.model == "nomic-embed-text"

        await provider.close()

    @pytest.mark.asyncio
    async def test_embeddings_multiple_inputs_openai_mode(
        self, respx_mock: respx.MockRouter
    ) -> None:
        """Test embeddings with multiple inputs in OpenAI mode."""
        mock_response = {
            "object": "list",
            "data": [
                {
                    "object": "embedding",
                    "embedding": [0.1, 0.2, 0.3],
                    "index": 0,
                },
                {
                    "object": "embedding",
                    "embedding": [0.4, 0.5, 0.6],
                    "index": 1,
                },
            ],
            "model": "nomic-embed-text",
            "usage": {"prompt_tokens": 10, "total_tokens": 10},
        }

        respx_mock.post("http://localhost:11434/v1/embeddings").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        provider = OllamaProvider(use_openai_mode=True)
        request = EmbeddingRequest(
            input=["First text", "Second text"],
            model="nomic-embed-text",
        )

        response = await provider.embeddings(request)

        assert len(response.embeddings) == 2
        assert response.embeddings[0] == [0.1, 0.2, 0.3]
        assert response.embeddings[1] == [0.4, 0.5, 0.6]

        await provider.close()


class TestOllamaProviderHealthCheck:
    """Tests for OllamaProvider health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_healthy(
        self, respx_mock: respx.MockRouter
    ) -> None:
        """Test health check when Ollama is healthy."""
        mock_response = {
            "models": [
                {"name": "llama2", "size": 3826793244, "digest": "abc123"},
                {"name": "mistral", "size": 4108916688, "digest": "def456"},
            ]
        }

        respx_mock.get("http://localhost:11434/api/tags").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        provider = OllamaProvider()
        status = await provider.health_check()

        assert status.healthy is True
        assert "healthy" in status.message.lower()
        assert "2 models" in status.message
        assert status.latency_ms is not None
        assert status.latency_ms >= 0

        await provider.close()

    @pytest.mark.asyncio
    async def test_health_check_no_models(
        self, respx_mock: respx.MockRouter
    ) -> None:
        """Test health check with no models."""
        mock_response = {"models": []}

        respx_mock.get("http://localhost:11434/api/tags").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        provider = OllamaProvider()
        status = await provider.health_check()

        assert status.healthy is True
        assert "0 models" in status.message

        await provider.close()

    @pytest.mark.asyncio
    async def test_health_check_connection_error(self) -> None:
        """Test health check with connection error."""
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.ConnectError(
                "Connection refused", request=None
            )

            provider = OllamaProvider()
            status = await provider.health_check()

            assert status.healthy is False
            assert "Cannot connect" in status.message

    @pytest.mark.asyncio
    async def test_health_check_server_error(
        self, respx_mock: respx.MockRouter
    ) -> None:
        """Test health check with server error."""
        respx_mock.get("http://localhost:11434/api/tags").mock(
            return_value=httpx.Response(500, json={"error": "Internal server error"})
        )

        provider = OllamaProvider()
        status = await provider.health_check()

        assert status.healthy is False
        assert "500" in status.message


class TestOllamaProviderModelManagement:
    """Tests for OllamaProvider model management functionality."""

    @pytest.mark.asyncio
    async def test_list_models(
        self, respx_mock: respx.MockRouter
    ) -> None:
        """Test listing available models."""
        mock_response = {
            "models": [
                {"name": "llama2", "size": 3826793244},
                {"name": "mistral:7b-instruct", "size": 4108916688},
                {"name": "codellama:13b", "size": 7365959616},
            ]
        }

        respx_mock.get("http://localhost:11434/api/tags").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        provider = OllamaProvider()
        models = await provider.list_models()

        assert len(models) == 3
        assert "llama2" in models
        assert "mistral:7b-instruct" in models
        assert "codellama:13b" in models

        await provider.close()

    @pytest.mark.asyncio
    async def test_list_models_empty(
        self, respx_mock: respx.MockRouter
    ) -> None:
        """Test listing models when none available."""
        mock_response = {"models": []}

        respx_mock.get("http://localhost:11434/api/tags").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        provider = OllamaProvider()
        models = await provider.list_models()

        assert len(models) == 0
        assert models == []

        await provider.close()

    @pytest.mark.asyncio
    async def test_list_models_error(self) -> None:
        """Test list models with error."""
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.ConnectError("Connection refused", request=None)

            provider = OllamaProvider()
            models = await provider.list_models()

            assert models == []

    @pytest.mark.asyncio
    async def test_get_model_info(
        self, respx_mock: respx.MockRouter
    ) -> None:
        """Test getting model information."""
        mock_response = {
            "license": "MIT",
            "modelfile": "# Modelfile content",
            "parameters": "temperature 0.7",
            "template": "{{ .System }} {{ .Prompt }}",
            "details": {
                "format": "gguf",
                "family": "llama",
                "parameter_size": "7B",
            },
        }

        respx_mock.post("http://localhost:11434/api/show").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        provider = OllamaProvider()
        info = await provider.get_model_info("llama2")

        assert info is not None
        assert info["license"] == "MIT"
        assert "details" in info

        await provider.close()

    @pytest.mark.asyncio
    async def test_get_model_info_not_found(
        self, respx_mock: respx.MockRouter
    ) -> None:
        """Test getting non-existent model info."""
        respx_mock.post("http://localhost:11434/api/show").mock(
            return_value=httpx.Response(404, json={"error": "model not found"})
        )

        provider = OllamaProvider()
        info = await provider.get_model_info("nonexistent-model")

        assert info is None

        await provider.close()


class TestOllamaProviderErrorHandling:
    """Tests for OllamaProvider error handling."""

    @pytest.mark.asyncio
    async def test_server_error_with_retry(
        self, respx_mock: respx.MockRouter
    ) -> None:
        """Test retry on server errors."""
        respx_mock.post("http://localhost:11434/v1/chat/completions").mock(
            side_effect=[
                httpx.Response(500, json={"error": "Internal server error"}),
                httpx.Response(503, json={"error": "Service unavailable"}),
                httpx.Response(200, json={
                    "id": "chatcmpl-123",
                    "model": "llama2",
                    "choices": [
                        {"index": 0, "message": {"content": "Success"}, "finish_reason": "stop"}
                    ],
                    "usage": {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15},
                }),
            ]
        )

        provider = OllamaProvider(max_retries=3)
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="Hello")],
            model="llama2",
        )

        response = await provider.chat_completion(request)

        assert response.content == "Success"
        assert len(respx_mock.calls) == 3

        await provider.close()

    @pytest.mark.asyncio
    async def test_rate_limit_error(
        self, respx_mock: respx.MockRouter
    ) -> None:
        """Test handling of rate limit error."""
        respx_mock.post("http://localhost:11434/v1/chat/completions").mock(
            return_value=httpx.Response(
                429,
                json={"error": "Rate limit exceeded"},
                headers={"Retry-After": "30"},
            )
        )

        provider = OllamaProvider(max_retries=0)
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="Hello")],
            model="llama2",
        )

        with pytest.raises(RemoteProviderError) as exc_info:
            await provider.chat_completion(request)

        assert "All 1 attempts failed" in str(exc_info.value)

        await provider.close()

    @pytest.mark.asyncio
    async def test_timeout_error(self) -> None:
        """Test handling of timeout errors."""
        with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = httpx.TimeoutException(
                "Request timed out", request=None
            )

            provider = OllamaProvider(max_retries=0, timeout=5)
            request = ChatCompletionRequest(
                messages=[ChatMessage(role="user", content="Hello")],
                model="llama2",
            )

            with pytest.raises(RemoteProviderError) as exc_info:
                await provider.chat_completion(request)

            assert "timeout" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_empty_response_openai_mode(
        self, respx_mock: respx.MockRouter
    ) -> None:
        """Test handling of empty response in OpenAI mode."""
        mock_response = {
            "id": "chatcmpl-123",
            "model": "llama2",
            "choices": [],
            "usage": {"prompt_tokens": 5, "completion_tokens": 0, "total_tokens": 5},
        }

        respx_mock.post("http://localhost:11434/v1/chat/completions").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        provider = OllamaProvider(use_openai_mode=True)
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="Hello")],
            model="llama2",
        )

        with pytest.raises(RemoteProviderError) as exc_info:
            await provider.chat_completion(request)

        assert "No choices" in str(exc_info.value)

        await provider.close()


class TestOllamaProviderResponseParsing:
    """Tests for OllamaProvider response parsing."""

    def test_parse_openai_response_standard(self) -> None:
        """Test parsing standard OpenAI response."""
        provider = OllamaProvider()
        response_data = {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "llama2",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "Hello!"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        }

        result = provider._parse_openai_response(response_data)

        assert result.content == "Hello!"
        assert result.model == "llama2"
        assert result.prompt_tokens == 10
        assert result.completion_tokens == 20
        assert result.total_tokens == 30

    def test_parse_native_response_standard(self) -> None:
        """Test parsing standard native response."""
        provider = OllamaProvider()
        response_data = {
            "model": "llama2",
            "created_at": "2024-01-01T00:00:00.000000Z",
            "message": {"role": "assistant", "content": "Native response"},
            "done": True,
            "prompt_eval_count": 10,
            "eval_count": 25,
        }

        result = provider._parse_native_response(response_data)

        assert result.content == "Native response"
        assert result.model == "llama2"
        assert result.prompt_tokens == 10
        assert result.completion_tokens == 25
        assert result.total_tokens == 35
        assert result.finish_reason == "stop"

    def test_parse_native_response_missing_usage(self) -> None:
        """Test parsing native response with missing usage data."""
        provider = OllamaProvider()
        response_data = {
            "model": "llama2",
            "message": {"role": "assistant", "content": "Response"},
            "done": True,
        }

        result = provider._parse_native_response(response_data)

        assert result.prompt_tokens == 0
        assert result.completion_tokens == 0
        assert result.total_tokens == 0

    def test_parse_native_embeddings_response(self) -> None:
        """Test parsing native embeddings response."""
        provider = OllamaProvider()
        response_data = {
            "embedding": [0.1, 0.2, 0.3, 0.4, 0.5],
            "model": "nomic-embed-text",
        }

        result = provider._parse_native_embeddings_response(response_data)

        assert len(result.embeddings) == 1
        assert result.embeddings[0] == [0.1, 0.2, 0.3, 0.4, 0.5]
        assert result.model == "nomic-embed-text"


class TestOllamaProviderCleanup:
    """Tests for OllamaProvider cleanup."""

    @pytest.mark.asyncio
    async def test_close_method(self) -> None:
        """Test explicit close method."""
        provider = OllamaProvider()

        # Trigger client creation
        client = await provider._get_client()
        assert client is not None
        assert not client.is_closed

        await provider.close()
        assert provider._client is None or provider._client.is_closed

    @pytest.mark.asyncio
    async def test_multiple_close_calls(self) -> None:
        """Test that multiple close calls don't cause errors."""
        provider = OllamaProvider()

        await provider.close()
        await provider.close()  # Should not raise
