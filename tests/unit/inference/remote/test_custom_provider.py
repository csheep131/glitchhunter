"""
Unit tests for Custom Provider.

Tests cover:
- Provider initialization and configuration
- CustomProviderConfig validation
- Chat completion with different request formats
- Response parsing with JSON paths
- Embeddings functionality
- Error handling and retry logic
- Health checks
"""

import asyncio
import json
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import respx

from core.exceptions import APIKeyError, RateLimitExceededError, RemoteProviderError
from inference.remote.base_provider import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    EmbeddingRequest,
    EmbeddingResponse,
    HealthStatus,
)
from inference.remote.providers.custom_provider import (
    CustomProvider,
    CustomProviderConfig,
)


class TestCustomProviderConfig:
    """Tests for CustomProviderConfig dataclass."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = CustomProviderConfig()

        assert config.endpoint == "/v1/chat/completions"
        assert config.request_format == "openai"
        assert config.response_path == "choices.0.message.content"
        assert config.auth_method == "bearer"
        assert config.headers == {}
        assert config.timeout == 120
        assert config.health_endpoint == "/health"
        assert config.health_method == "GET"
        assert config.embeddings_endpoint is None

    def test_custom_config(self) -> None:
        """Test custom configuration values."""
        config = CustomProviderConfig(
            endpoint="/api/chat",
            request_format="anthropic",
            response_path="content.0.text",
            auth_method="api_key",
            headers={"X-Custom-Header": "value"},
            timeout=60,
            health_endpoint="/api/health",
            health_method="POST",
            embeddings_endpoint="/api/embeddings",
            embeddings_format="openai",
            embeddings_response_path="data.0.embedding",
        )

        assert config.endpoint == "/api/chat"
        assert config.request_format == "anthropic"
        assert config.response_path == "content.0.text"
        assert config.auth_method == "api_key"
        assert config.headers == {"X-Custom-Header": "value"}
        assert config.timeout == 60
        assert config.health_endpoint == "/api/health"
        assert config.health_method == "POST"
        assert config.embeddings_endpoint == "/api/embeddings"

    def test_invalid_request_format(self) -> None:
        """Test validation of request_format."""
        with pytest.raises(ValueError) as exc_info:
            CustomProviderConfig(request_format="invalid")

        assert "Invalid request_format" in str(exc_info.value)

    def test_invalid_auth_method(self) -> None:
        """Test validation of auth_method."""
        with pytest.raises(ValueError) as exc_info:
            CustomProviderConfig(auth_method="invalid")

        assert "Invalid auth_method" in str(exc_info.value)

    def test_valid_formats(self) -> None:
        """Test all valid request formats."""
        for fmt in ["openai", "anthropic", "raw"]:
            config = CustomProviderConfig(request_format=fmt)
            assert config.request_format == fmt

    def test_valid_auth_methods(self) -> None:
        """Test all valid auth methods."""
        for method in ["bearer", "api_key", "none"]:
            config = CustomProviderConfig(auth_method=method)
            assert config.auth_method == method


class TestCustomProviderInit:
    """Tests for CustomProvider initialization."""

    def test_default_initialization(self) -> None:
        """Test default initialization parameters."""
        provider = CustomProvider()

        assert provider.name == "custom"
        assert provider.base_url == "http://localhost:8080"
        assert provider.timeout == 120
        assert provider._api_key is None
        assert isinstance(provider.config, CustomProviderConfig)
        assert provider.config.endpoint == "/v1/chat/completions"

    def test_custom_initialization(self) -> None:
        """Test custom initialization parameters."""
        custom_config = CustomProviderConfig(
            endpoint="/api/v1/generate",
            request_format="raw",
            auth_method="none",
        )

        provider = CustomProvider(
            name="my-custom-api",
            base_url="https://api.example.com",
            timeout=90,
            api_key="custom-key-123",
            config=custom_config,
        )

        assert provider.name == "my-custom-api"
        assert provider.base_url == "https://api.example.com"
        assert provider.timeout == 90
        assert provider.get_api_key() == "custom-key-123"
        assert provider.config.endpoint == "/api/v1/generate"
        assert provider.config.request_format == "raw"
        assert provider.config.auth_method == "none"

    def test_base_url_trailing_slash_removal(self) -> None:
        """Test that trailing slashes are removed from base URL."""
        provider = CustomProvider(base_url="https://api.example.com/")
        assert provider.base_url == "https://api.example.com"

    def test_api_key_management(self) -> None:
        """Test API key getter and setter."""
        provider = CustomProvider(api_key="initial-key")
        assert provider.get_api_key() == "initial-key"

        provider.set_api_key("updated-key")
        assert provider.get_api_key() == "updated-key"

    def test_get_provider_name(self) -> None:
        """Test provider name retrieval."""
        provider = CustomProvider(name="test-provider")
        assert provider.get_provider_name() == "test-provider"


class TestCustomProviderOpenAIFormat:
    """Tests for CustomProvider with OpenAI format."""

    @pytest.mark.asyncio
    async def test_chat_completion_openai_format(
        self, respx_mock: respx.MockRouter
    ) -> None:
        """Test chat completion with OpenAI format."""
        mock_response = {
            "id": "custom-123",
            "model": "custom-model",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "Hello from custom API!"},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        }

        respx_mock.post("http://localhost:8080/v1/chat/completions").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        provider = CustomProvider(api_key="sk-test123")
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="Hello")],
            model="custom-model",
        )

        response = await provider.chat_completion(request)

        assert response.content == "Hello from custom API!"
        assert response.model == "custom-model"
        assert response.prompt_tokens == 10
        assert response.completion_tokens == 20
        assert response.total_tokens == 30
        assert response.finish_reason == "stop"

        await provider.close()

    @pytest.mark.asyncio
    async def test_chat_completion_with_bearer_auth(
        self, respx_mock: respx.MockRouter
    ) -> None:
        """Test chat completion with Bearer authentication."""
        mock_response = {
            "choices": [
                {"index": 0, "message": {"content": "Response"}, "finish_reason": "stop"}
            ],
            "usage": {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15},
        }

        route = respx_mock.post("http://localhost:8080/v1/chat/completions")
        route.mock(return_value=httpx.Response(200, json=mock_response))

        provider = CustomProvider(
            api_key="bearer-token-123",
            config=CustomProviderConfig(auth_method="bearer"),
        )
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="Test")],
            model="test-model",
        )

        response = await provider.chat_completion(request)

        # Verify Authorization header
        assert route.calls.last is not None
        assert route.calls.last.request.headers.get("Authorization") == "Bearer bearer-token-123"

        await provider.close()

    @pytest.mark.asyncio
    async def test_chat_completion_with_api_key_auth(
        self, respx_mock: respx.MockRouter
    ) -> None:
        """Test chat completion with API key authentication."""
        mock_response = {
            "choices": [
                {"index": 0, "message": {"content": "Response"}, "finish_reason": "stop"}
            ],
            "usage": {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15},
        }

        route = respx_mock.post("http://localhost:8080/v1/chat/completions")
        route.mock(return_value=httpx.Response(200, json=mock_response))

        provider = CustomProvider(
            api_key="api-key-123",
            config=CustomProviderConfig(auth_method="api_key"),
        )
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="Test")],
            model="test-model",
        )

        response = await provider.chat_completion(request)

        # Verify X-API-Key header
        assert route.calls.last is not None
        assert route.calls.last.request.headers.get("X-API-Key") == "api-key-123"

        await provider.close()

    @pytest.mark.asyncio
    async def test_chat_completion_no_auth(self) -> None:
        """Test chat completion without authentication."""
        provider = CustomProvider(
            config=CustomProviderConfig(auth_method="none")
        )
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="Hello")],
            model="test-model",
        )

        with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {
                "choices": [
                    {"index": 0, "message": {"content": "Response"}, "finish_reason": "stop"}
                ],
                "usage": {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15},
            }

            # Should not raise APIKeyError
            response = await provider.chat_completion(request)
            assert response.content == "Response"


class TestCustomProviderAnthropicFormat:
    """Tests for CustomProvider with Anthropic format."""

    @pytest.mark.asyncio
    async def test_chat_completion_anthropic_format(
        self, respx_mock: respx.MockRouter
    ) -> None:
        """Test chat completion with Anthropic format."""
        mock_response = {
            "id": "msg_0123456789",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "Anthropic-style response"}],
            "model": "claude-custom",
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 10, "output_tokens": 20},
        }

        config = CustomProviderConfig(
            endpoint="/v1/messages",
            request_format="anthropic",
            response_path="content.0.text",
        )

        respx_mock.post("http://localhost:8080/v1/messages").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        provider = CustomProvider(api_key="sk-test123", config=config)
        request = ChatCompletionRequest(
            messages=[
                ChatMessage(role="system", content="You are helpful"),
                ChatMessage(role="user", content="Hello"),
            ],
            model="claude-custom",
        )

        response = await provider.chat_completion(request)

        assert response.content == "Anthropic-style response"
        assert response.model == "claude-custom"

        # Verify system prompt was extracted
        assert respx_mock.calls.last is not None
        request_payload = json.loads(respx_mock.calls.last.request.content)
        assert "system" in request_payload
        assert request_payload["system"] == "You are helpful"

        await provider.close()

    @pytest.mark.asyncio
    async def test_anthropic_format_max_tokens_default(
        self, respx_mock: respx.MockRouter
    ) -> None:
        """Test Anthropic format includes default max_tokens."""
        mock_response = {
            "id": "msg_0123456789",
            "content": [{"type": "text", "text": "Response"}],
            "model": "claude-custom",
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 5, "output_tokens": 10},
        }

        config = CustomProviderConfig(
            request_format="anthropic",
            response_path="content.0.text",
        )

        route = respx_mock.post("http://localhost:8080/v1/chat/completions")
        route.mock(return_value=httpx.Response(200, json=mock_response))

        provider = CustomProvider(api_key="sk-test123", config=config)
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="Hello")],
            model="claude-custom",
        )

        await provider.chat_completion(request)

        # Verify max_tokens was added
        assert route.calls.last is not None
        request_payload = json.loads(route.calls.last.request.content)
        assert request_payload["max_tokens"] == 1024

        await provider.close()


class TestCustomProviderRawFormat:
    """Tests for CustomProvider with raw format."""

    @pytest.mark.asyncio
    async def test_chat_completion_raw_format(
        self, respx_mock: respx.MockRouter
    ) -> None:
        """Test chat completion with raw format."""
        mock_response = {
            "response": "Raw API response",
            "tokens_used": 25,
            "status": "success",
        }

        config = CustomProviderConfig(
            endpoint="/api/generate",
            request_format="raw",
            response_path="response",
        )

        respx_mock.post("http://localhost:8080/api/generate").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        provider = CustomProvider(api_key="key-123", config=config)
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="Generate")],
            model="raw-model",
            extra_kwargs={"temperature": 0.8, "max_length": 100},
        )

        response = await provider.chat_completion(request)

        assert response.content == "Raw API response"

        # Verify raw format includes extra_kwargs
        assert respx_mock.calls.last is not None
        request_payload = json.loads(respx_mock.calls.last.request.content)
        assert request_payload["temperature"] == 0.8
        assert request_payload["max_length"] == 100

        await provider.close()

    @pytest.mark.asyncio
    async def test_raw_format_preserves_extra_kwargs(
        self, respx_mock: respx.MockRouter
    ) -> None:
        """Test that raw format preserves extra kwargs."""
        mock_response = {"result": "Success"}

        config = CustomProviderConfig(
            request_format="raw",
            response_path="result",
        )

        route = respx_mock.post("http://localhost:8080/v1/chat/completions")
        route.mock(return_value=httpx.Response(200, json=mock_response))

        provider = CustomProvider(api_key="key-123", config=config)
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="Test")],
            model="test",
            extra_kwargs={"custom_param": "value", "another_param": 42},
        )

        await provider.chat_completion(request)

        assert route.calls.last is not None
        request_payload = json.loads(route.calls.last.request.content)
        assert request_payload["custom_param"] == "value"
        assert request_payload["another_param"] == 42

        await provider.close()


class TestCustomProviderJSONPathExtraction:
    """Tests for CustomProvider JSON path extraction."""

    def test_extract_json_path_simple(self) -> None:
        """Test simple JSON path extraction."""
        provider = CustomProvider()
        data = {"content": "Hello", "model": "test"}

        result = provider._extract_json_path(data, "content")
        assert result == "Hello"

    def test_extract_json_path_nested(self) -> None:
        """Test nested JSON path extraction."""
        provider = CustomProvider()
        data = {
            "choices": [
                {
                    "message": {"content": "Nested content"},
                    "finish_reason": "stop",
                }
            ]
        }

        result = provider._extract_json_path(data, "choices.0.message.content")
        assert result == "Nested content"

    def test_extract_json_path_array_index(self) -> None:
        """Test JSON path extraction with array index."""
        provider = CustomProvider()
        data = {
            "results": ["first", "second", "third"]
        }

        result = provider._extract_json_path(data, "results.1")
        assert result == "second"

    def test_extract_json_path_not_found(self) -> None:
        """Test JSON path extraction when path not found."""
        provider = CustomProvider()
        data = {"content": "Hello"}

        result = provider._extract_json_path(data, "nonexistent.path")
        assert result is None

    def test_extract_json_path_invalid_index(self) -> None:
        """Test JSON path extraction with invalid array index."""
        provider = CustomProvider()
        data = {"results": ["first", "second"]}

        result = provider._extract_json_path(data, "results.5")
        assert result is None

    def test_extract_json_path_empty_path(self) -> None:
        """Test JSON path extraction with empty path."""
        provider = CustomProvider()
        data = {"content": "Hello"}

        result = provider._extract_json_path(data, "")
        assert result is None

    def test_extract_usage_standard(self) -> None:
        """Test usage extraction from standard response."""
        provider = CustomProvider()
        data = {
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30,
            }
        }

        usage = provider._extract_usage(data)
        assert usage["prompt_tokens"] == 10
        assert usage["completion_tokens"] == 20
        assert usage["total_tokens"] == 30

    def test_extract_usage_missing(self) -> None:
        """Test usage extraction when missing."""
        provider = CustomProvider()
        data = {"content": "Hello"}

        usage = provider._extract_usage(data)
        assert usage["prompt_tokens"] == 0
        assert usage["completion_tokens"] == 0
        assert usage["total_tokens"] == 0

    def test_extract_finish_reason_openai(self) -> None:
        """Test finish reason extraction from OpenAI format."""
        provider = CustomProvider()
        data = {
            "choices": [
                {"index": 0, "message": {"content": "Hi"}, "finish_reason": "stop"}
            ]
        }

        result = provider._extract_finish_reason(data)
        assert result == "stop"

    def test_extract_finish_reason_anthropic(self) -> None:
        """Test finish reason extraction from Anthropic format."""
        provider = CustomProvider()
        data = {
            "stop_reason": "end_turn",
            "content": [{"type": "text", "text": "Hi"}],
        }

        result = provider._extract_finish_reason(data)
        assert result == "end_turn"

    def test_extract_finish_reason_missing(self) -> None:
        """Test finish reason extraction when missing."""
        provider = CustomProvider()
        data = {"content": "Hello"}

        result = provider._extract_finish_reason(data)
        assert result == "unknown"


class TestCustomProviderEmbeddings:
    """Tests for CustomProvider embeddings functionality."""

    @pytest.mark.asyncio
    async def test_embeddings_configured(
        self, respx_mock: respx.MockRouter
    ) -> None:
        """Test embeddings when endpoint is configured."""
        mock_response = {
            "data": [
                {"embedding": [0.1, 0.2, 0.3, 0.4, 0.5], "index": 0}
            ],
            "model": "embedding-model",
            "usage": {"prompt_tokens": 5, "total_tokens": 5},
        }

        config = CustomProviderConfig(
            embeddings_endpoint="/api/embeddings",
            embeddings_response_path="data.0.embedding",
        )

        respx_mock.post("http://localhost:8080/api/embeddings").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        provider = CustomProvider(api_key="key-123", config=config)
        request = EmbeddingRequest(
            input="Test text for embedding",
            model="embedding-model",
        )

        response = await provider.embeddings(request)

        assert len(response.embeddings) == 1
        assert response.embeddings[0] == [0.1, 0.2, 0.3, 0.4, 0.5]
        assert response.model == "embedding-model"

        await provider.close()

    @pytest.mark.asyncio
    async def test_embeddings_not_configured(self) -> None:
        """Test embeddings raises error when not configured."""
        provider = CustomProvider()
        request = EmbeddingRequest(
            input="Test text",
            model="embedding-model",
        )

        with pytest.raises(NotImplementedError) as exc_info:
            await provider.embeddings(request)

        assert "does not have embeddings endpoint configured" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_embeddings_fallback_paths(
        self, respx_mock: respx.MockRouter
    ) -> None:
        """Test embeddings with fallback extraction paths."""
        # Response without data.0.embedding, should try embeddings.0
        mock_response = {
            "embeddings": [[0.1, 0.2, 0.3]],
            "model": "embedding-model",
        }

        config = CustomProviderConfig(
            embeddings_endpoint="/api/embeddings",
            embeddings_response_path="invalid.path",  # Invalid path to trigger fallback
        )

        respx_mock.post("http://localhost:8080/api/embeddings").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        provider = CustomProvider(api_key="key-123", config=config)
        request = EmbeddingRequest(
            input="Test text",
            model="embedding-model",
        )

        response = await provider.embeddings(request)

        assert len(response.embeddings) == 1
        assert response.embeddings[0] == [0.1, 0.2, 0.3]

        await provider.close()


class TestCustomProviderHealthCheck:
    """Tests for CustomProvider health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_healthy_get(
        self, respx_mock: respx.MockRouter
    ) -> None:
        """Test health check with GET method."""
        respx_mock.get("http://localhost:8080/health").mock(
            return_value=httpx.Response(200, json={"status": "ok"})
        )

        provider = CustomProvider()
        status = await provider.health_check()

        assert status.healthy is True
        assert "healthy" in status.message.lower()
        assert status.latency_ms is not None

        await provider.close()

    @pytest.mark.asyncio
    async def test_health_check_healthy_post(
        self, respx_mock: respx.MockRouter
    ) -> None:
        """Test health check with POST method."""
        config = CustomProviderConfig(health_method="POST")

        respx_mock.post("http://localhost:8080/health").mock(
            return_value=httpx.Response(200, json={"status": "ok"})
        )

        provider = CustomProvider(config=config)
        status = await provider.health_check()

        assert status.healthy is True

        await provider.close()

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(
        self, respx_mock: respx.MockRouter
    ) -> None:
        """Test health check when unhealthy."""
        respx_mock.get("http://localhost:8080/health").mock(
            return_value=httpx.Response(503, json={"error": "Service unavailable"})
        )

        provider = CustomProvider()
        status = await provider.health_check()

        assert status.healthy is False
        assert "503" in status.message

        await provider.close()

    @pytest.mark.asyncio
    async def test_health_check_no_endpoint_configured(self) -> None:
        """Test health check when no endpoint configured."""
        config = CustomProviderConfig(health_endpoint=None)

        provider = CustomProvider(config=config)
        status = await provider.health_check()

        # Should return healthy with note about no endpoint
        assert status.healthy is True
        assert "no health endpoint" in status.message.lower()

    @pytest.mark.asyncio
    async def test_health_check_connection_error(self) -> None:
        """Test health check with connection error."""
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.ConnectError(
                "Connection refused", request=None
            )

            provider = CustomProvider()
            status = await provider.health_check()

            assert status.healthy is False
            assert "Cannot connect" in status.message


class TestCustomProviderErrorHandling:
    """Tests for CustomProvider error handling."""

    @pytest.mark.asyncio
    async def test_api_key_required_for_bearer(
        self, respx_mock: respx.MockRouter
    ) -> None:
        """Test that API key is required for bearer auth."""
        provider = CustomProvider(
            config=CustomProviderConfig(auth_method="bearer")
        )
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="Hello")],
            model="test",
        )

        with pytest.raises(APIKeyError) as exc_info:
            await provider.chat_completion(request)

        assert "API key required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_api_key_required_for_api_key_auth(self) -> None:
        """Test that API key is required for api_key auth."""
        provider = CustomProvider(
            config=CustomProviderConfig(auth_method="api_key")
        )
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="Hello")],
            model="test",
        )

        with pytest.raises(APIKeyError) as exc_info:
            await provider.chat_completion(request)

        assert "API key required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invalid_api_key(
        self, respx_mock: respx.MockRouter
    ) -> None:
        """Test handling of invalid API key."""
        respx_mock.post("http://localhost:8080/v1/chat/completions").mock(
            return_value=httpx.Response(401, json={"error": "Unauthorized"})
        )

        provider = CustomProvider(api_key="invalid-key")
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="Hello")],
            model="test",
        )

        with pytest.raises(APIKeyError) as exc_info:
            await provider.chat_completion(request)

        assert "Invalid API key" in str(exc_info.value)

        await provider.close()

    @pytest.mark.asyncio
    async def test_rate_limit_error(
        self, respx_mock: respx.MockRouter
    ) -> None:
        """Test handling of rate limit error."""
        respx_mock.post("http://localhost:8080/v1/chat/completions").mock(
            return_value=httpx.Response(
                429,
                json={"error": "Rate limit exceeded"},
                headers={"Retry-After": "60"},
            )
        )

        provider = CustomProvider(api_key="key-123", max_retries=0)
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="Hello")],
            model="test",
        )

        with pytest.raises(RemoteProviderError) as exc_info:
            await provider.chat_completion(request)

        assert "All 1 attempts failed" in str(exc_info.value)

        await provider.close()

    @pytest.mark.asyncio
    async def test_server_error_with_retry(
        self, respx_mock: respx.MockRouter
    ) -> None:
        """Test retry on server errors."""
        respx_mock.post("http://localhost:8080/v1/chat/completions").mock(
            side_effect=[
                httpx.Response(500, json={"error": "Server error"}),
                httpx.Response(200, json={
                    "choices": [
                        {"index": 0, "message": {"content": "Success"}, "finish_reason": "stop"}
                    ],
                    "usage": {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15},
                }),
            ]
        )

        provider = CustomProvider(api_key="key-123", max_retries=2)
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="Hello")],
            model="test",
        )

        response = await provider.chat_completion(request)

        assert response.content == "Success"
        assert len(respx_mock.calls) == 2

        await provider.close()

    @pytest.mark.asyncio
    async def test_response_parsing_error(self) -> None:
        """Test error when response parsing fails."""
        provider = CustomProvider(
            api_key="key-123",  # Need API key for auth
            config=CustomProviderConfig(response_path="nonexistent.path"),
        )

        with patch.object(provider, "_make_request", new_callable=AsyncMock) as mock_request:
            mock_request.return_value = {"content": "Hello"}

            request = ChatCompletionRequest(
                messages=[ChatMessage(role="user", content="Hello")],
                model="test",
            )

            with pytest.raises(RemoteProviderError) as exc_info:
                await provider.chat_completion(request)

            assert "Could not extract content" in str(exc_info.value)


class TestCustomProviderCustomHeaders:
    """Tests for CustomProvider custom headers functionality."""

    @pytest.mark.asyncio
    async def test_custom_headers(self, respx_mock: respx.MockRouter) -> None:
        """Test that custom headers are included."""
        mock_response = {
            "choices": [
                {"index": 0, "message": {"content": "Response"}, "finish_reason": "stop"}
            ],
            "usage": {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15},
        }

        config = CustomProviderConfig(
            headers={
                "X-Custom-Header": "custom-value",
                "X-Another-Header": "another-value",
            }
        )

        route = respx_mock.post("http://localhost:8080/v1/chat/completions")
        route.mock(return_value=httpx.Response(200, json=mock_response))

        provider = CustomProvider(api_key="key-123", config=config)
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="Test")],
            model="test",
        )

        await provider.chat_completion(request)

        assert route.calls.last is not None
        headers = route.calls.last.request.headers
        assert headers.get("X-Custom-Header") == "custom-value"
        assert headers.get("X-Another-Header") == "another-value"

        await provider.close()


class TestCustomProviderCleanup:
    """Tests for CustomProvider cleanup."""

    @pytest.mark.asyncio
    async def test_close_method(self) -> None:
        """Test explicit close method."""
        provider = CustomProvider()

        # Trigger client creation
        client = await provider._get_client()
        assert client is not None
        assert not client.is_closed

        await provider.close()
        assert provider._client is None or provider._client.is_closed

    @pytest.mark.asyncio
    async def test_multiple_close_calls(self) -> None:
        """Test that multiple close calls don't cause errors."""
        provider = CustomProvider()

        await provider.close()
        await provider.close()  # Should not raise
