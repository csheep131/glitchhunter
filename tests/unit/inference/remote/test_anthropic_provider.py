"""
Unit tests for Anthropic Provider.

Tests cover:
- Provider initialization and configuration
- Chat completion requests and response parsing
- Error handling and retry logic
- Health checks
- Request format conversion
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
    HealthStatus,
)
from inference.remote.providers.anthropic_provider import AnthropicProvider


class TestAnthropicProviderInit:
    """Tests for AnthropicProvider initialization."""

    def test_default_initialization(self) -> None:
        """Test default initialization parameters."""
        provider = AnthropicProvider()

        assert provider.name == "anthropic"
        assert provider.base_url == "https://api.anthropic.com"
        assert provider.timeout == 120
        assert provider._api_key is None
        assert provider.max_retries == 3
        assert provider.anthropic_version == "2023-06-01"

    def test_custom_initialization(self) -> None:
        """Test custom initialization parameters."""
        provider = AnthropicProvider(
            name="custom-anthropic",
            base_url="https://custom.api.com",
            timeout=60,
            api_key="sk-test123",
            max_retries=5,
            anthropic_version="2023-09-01",
        )

        assert provider.name == "custom-anthropic"
        assert provider.base_url == "https://custom.api.com"
        assert provider.timeout == 60
        assert provider.get_api_key() == "sk-test123"
        assert provider.max_retries == 5
        assert provider.anthropic_version == "2023-09-01"

    def test_base_url_trailing_slash_removal(self) -> None:
        """Test that trailing slashes are removed from base URL."""
        provider = AnthropicProvider(base_url="https://api.anthropic.com/")
        assert provider.base_url == "https://api.anthropic.com"

    def test_api_key_management(self) -> None:
        """Test API key getter and setter."""
        provider = AnthropicProvider(api_key="sk-initial")
        assert provider.get_api_key() == "sk-initial"

        provider.set_api_key("sk-updated")
        assert provider.get_api_key() == "sk-updated"

    def test_get_provider_name(self) -> None:
        """Test provider name retrieval."""
        provider = AnthropicProvider(name="test-provider")
        assert provider.get_provider_name() == "test-provider"


class TestAnthropicProviderChatCompletion:
    """Tests for AnthropicProvider chat completion functionality."""

    @pytest.mark.asyncio
    async def test_basic_chat_completion(self, respx_mock: respx.MockRouter) -> None:
        """Test basic chat completion request."""
        mock_response = {
            "id": "msg_0123456789",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "Hello! How can I help you?"}],
            "model": "claude-3-sonnet-20240229",
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 10, "output_tokens": 20},
        }

        respx_mock.post("https://api.anthropic.com/v1/messages").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        provider = AnthropicProvider(api_key="sk-test123")
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="Hello")],
            model="claude-3-sonnet-20240229",
        )

        response = await provider.chat_completion(request)

        assert response.content == "Hello! How can I help you?"
        assert response.model == "claude-3-sonnet-20240229"
        assert response.prompt_tokens == 10
        assert response.completion_tokens == 20
        assert response.total_tokens == 30
        assert response.finish_reason == "end_turn"

        await provider.close()

    @pytest.mark.asyncio
    async def test_chat_completion_with_system_prompt(
        self, respx_mock: respx.MockRouter
    ) -> None:
        """Test chat completion with system prompt."""
        mock_response = {
            "id": "msg_0123456789",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "I understand the context."}],
            "model": "claude-3-sonnet-20240229",
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 15, "output_tokens": 25},
        }

        route = respx_mock.post("https://api.anthropic.com/v1/messages")
        route.mock(return_value=httpx.Response(200, json=mock_response))

        provider = AnthropicProvider(api_key="sk-test123")
        request = ChatCompletionRequest(
            messages=[
                ChatMessage(role="system", content="You are a helpful assistant."),
                ChatMessage(role="user", content="Hello"),
            ],
            model="claude-3-sonnet-20240229",
        )

        response = await provider.chat_completion(request)

        # Verify system prompt was extracted
        assert route.calls.last is not None
        request_payload = json.loads(route.calls.last.request.content)
        assert "system" in request_payload
        assert request_payload["system"] == "You are a helpful assistant."
        assert "system" not in [m.get("role") for m in request_payload["messages"]]

        assert response.content == "I understand the context."
        await provider.close()

    @pytest.mark.asyncio
    async def test_chat_completion_with_parameters(
        self, respx_mock: respx.MockRouter
    ) -> None:
        """Test chat completion with custom parameters."""
        mock_response = {
            "id": "msg_0123456789",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "Response with params"}],
            "model": "claude-3-opus-20240229",
            "stop_reason": "stop_sequence",
            "usage": {"input_tokens": 12, "output_tokens": 18},
        }

        route = respx_mock.post("https://api.anthropic.com/v1/messages")
        route.mock(return_value=httpx.Response(200, json=mock_response))

        provider = AnthropicProvider(api_key="sk-test123")
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="Test")],
            model="claude-3-opus-20240229",
            temperature=0.5,
            max_tokens=500,
            top_p=0.9,
            stop=["END", "STOP"],
        )

        response = await provider.chat_completion(request)

        # Verify parameters were sent
        assert route.calls.last is not None
        request_payload = json.loads(route.calls.last.request.content)
        assert request_payload["temperature"] == 0.5
        assert request_payload["max_tokens"] == 500
        assert request_payload["top_p"] == 0.9
        assert request_payload["stop_sequences"] == ["END", "STOP"]

        assert response.content == "Response with params"
        await provider.close()

    @pytest.mark.asyncio
    async def test_chat_completion_without_api_key(self) -> None:
        """Test chat completion fails without API key."""
        provider = AnthropicProvider()
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="Hello")],
            model="claude-3-sonnet-20240229",
        )

        with pytest.raises(APIKeyError) as exc_info:
            await provider.chat_completion(request)

        assert "API key required" in str(exc_info.value)
        assert provider.name in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_chat_completion_empty_response(
        self, respx_mock: respx.MockRouter
    ) -> None:
        """Test handling of empty response."""
        mock_response = {
            "id": "msg_0123456789",
            "type": "message",
            "role": "assistant",
            "content": [],
            "model": "claude-3-sonnet-20240229",
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 10, "output_tokens": 0},
        }

        respx_mock.post("https://api.anthropic.com/v1/messages").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        provider = AnthropicProvider(api_key="sk-test123")
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="Hello")],
            model="claude-3-sonnet-20240229",
        )

        with pytest.raises(RemoteProviderError) as exc_info:
            await provider.chat_completion(request)

        assert "No content" in str(exc_info.value)
        await provider.close()

    @pytest.mark.asyncio
    async def test_chat_completion_multiple_content_blocks(
        self, respx_mock: respx.MockRouter
    ) -> None:
        """Test parsing response with multiple content blocks."""
        mock_response = {
            "id": "msg_0123456789",
            "type": "message",
            "role": "assistant",
            "content": [
                {"type": "text", "text": "First block"},
                {"type": "tool_use", "id": "tool1", "name": "calculator"},
                {"type": "text", "text": "Second block"},
            ],
            "model": "claude-3-sonnet-20240229",
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 10, "output_tokens": 30},
        }

        respx_mock.post("https://api.anthropic.com/v1/messages").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        provider = AnthropicProvider(api_key="sk-test123")
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="Calculate 2+2")],
            model="claude-3-sonnet-20240229",
        )

        response = await provider.chat_completion(request)

        # Should extract first text block
        assert response.content == "First block"
        await provider.close()


class TestAnthropicProviderErrorHandling:
    """Tests for AnthropicProvider error handling."""

    @pytest.mark.asyncio
    async def test_invalid_api_key(
        self, respx_mock: respx.MockRouter
    ) -> None:
        """Test handling of invalid API key."""
        respx_mock.post("https://api.anthropic.com/v1/messages").mock(
            return_value=httpx.Response(401, json={"error": {"type": "authentication_error"}})
        )

        provider = AnthropicProvider(api_key="sk-invalid")
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="Hello")],
            model="claude-3-sonnet-20240229",
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
        respx_mock.post("https://api.anthropic.com/v1/messages").mock(
            return_value=httpx.Response(
                429,
                json={"error": {"type": "rate_limit_error"}},
                headers={"Retry-After": "60"},
            )
        )

        provider = AnthropicProvider(api_key="sk-test123", max_retries=0)
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="Hello")],
            model="claude-3-sonnet-20240229",
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
        # First two calls fail, third succeeds
        respx_mock.post("https://api.anthropic.com/v1/messages").mock(
            side_effect=[
                httpx.Response(500, json={"error": "Internal server error"}),
                httpx.Response(503, json={"error": "Service unavailable"}),
                httpx.Response(200, json={
                    "id": "msg_0123456789",
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "text", "text": "Success after retry"}],
                    "model": "claude-3-sonnet-20240229",
                    "stop_reason": "end_turn",
                    "usage": {"input_tokens": 10, "output_tokens": 20},
                }),
            ]
        )

        provider = AnthropicProvider(api_key="sk-test123", max_retries=3)
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="Hello")],
            model="claude-3-sonnet-20240229",
        )

        response = await provider.chat_completion(request)

        assert response.content == "Success after retry"
        assert len(respx_mock.calls) == 3
        await provider.close()

    @pytest.mark.asyncio
    async def test_timeout_error(self) -> None:
        """Test handling of timeout errors."""
        with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = httpx.TimeoutException(
                "Request timed out", request=None
            )

            provider = AnthropicProvider(api_key="sk-test123", max_retries=0, timeout=5)
            request = ChatCompletionRequest(
                messages=[ChatMessage(role="user", content="Hello")],
                model="claude-3-sonnet-20240229",
            )

            with pytest.raises(RemoteProviderError) as exc_info:
                await provider.chat_completion(request)

            assert "timeout" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_connection_error(self) -> None:
        """Test handling of connection errors."""
        with patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = httpx.ConnectError(
                "Connection refused", request=None
            )

            provider = AnthropicProvider(api_key="sk-test123", max_retries=0)
            request = ChatCompletionRequest(
                messages=[ChatMessage(role="user", content="Hello")],
                model="claude-3-sonnet-20240229",
            )

            with pytest.raises(RemoteProviderError) as exc_info:
                await provider.chat_completion(request)

            assert "Request failed" in str(exc_info.value)


class TestAnthropicProviderEmbeddings:
    """Tests for AnthropicProvider embeddings functionality."""

    @pytest.mark.asyncio
    async def test_embeddings_not_implemented(self) -> None:
        """Test that embeddings raise NotImplementedError."""
        provider = AnthropicProvider()
        request = EmbeddingRequest(
            input="Test text",
            model="text-embedding-3-small",
        )

        with pytest.raises(NotImplementedError) as exc_info:
            await provider.embeddings(request)

        assert "does not support embeddings" in str(exc_info.value)


class TestAnthropicProviderHealthCheck:
    """Tests for AnthropicProvider health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_healthy(
        self, respx_mock: respx.MockRouter
    ) -> None:
        """Test health check when provider is healthy."""
        mock_response = {
            "id": "msg_0123456789",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "."}],
            "model": "claude-3-sonnet-20240229",
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 5, "output_tokens": 1},
        }

        respx_mock.post("https://api.anthropic.com/v1/messages").mock(
            return_value=httpx.Response(200, json=mock_response)
        )

        provider = AnthropicProvider(api_key="sk-test123")
        status = await provider.health_check()

        assert status.healthy is True
        assert "healthy" in status.message.lower()
        assert status.latency_ms is not None
        assert status.latency_ms >= 0

        await provider.close()

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(
        self, respx_mock: respx.MockRouter
    ) -> None:
        """Test health check when provider is unhealthy."""
        respx_mock.post("https://api.anthropic.com/v1/messages").mock(
            return_value=httpx.Response(503, json={"error": "Service unavailable"})
        )

        provider = AnthropicProvider(api_key="sk-test123")
        status = await provider.health_check()

        assert status.healthy is False
        assert "503" in status.message

        await provider.close()

    @pytest.mark.asyncio
    async def test_health_check_timeout(self) -> None:
        """Test health check timeout handling."""
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.TimeoutException(
                "Request timed out", request=None
            )

            provider = AnthropicProvider(api_key="sk-test123")
            status = await provider.health_check()

            assert status.healthy is False
            assert "timeout" in status.message.lower()

    @pytest.mark.asyncio
    async def test_health_check_connection_error(self) -> None:
        """Test health check connection error handling."""
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.ConnectError(
                "Connection refused", request=None
            )

            provider = AnthropicProvider(api_key="sk-test123")
            status = await provider.health_check()

            assert status.healthy is False
            assert "connect" in status.message.lower()


class TestAnthropicProviderRequestConversion:
    """Tests for AnthropicProvider request conversion logic."""

    def test_convert_request_basic(self) -> None:
        """Test basic request conversion."""
        provider = AnthropicProvider()
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="Hello")],
            model="claude-3-sonnet-20240229",
        )

        payload = provider._convert_request(request)

        assert payload["model"] == "claude-3-sonnet-20240229"
        assert len(payload["messages"]) == 1
        assert payload["messages"][0]["role"] == "user"
        assert payload["messages"][0]["content"] == "Hello"
        assert payload["max_tokens"] == 1024  # Default

    def test_convert_request_with_system(self) -> None:
        """Test request conversion with system prompt."""
        provider = AnthropicProvider()
        request = ChatCompletionRequest(
            messages=[
                ChatMessage(role="system", content="You are helpful"),
                ChatMessage(role="user", content="Hello"),
                ChatMessage(role="assistant", content="Hi there!"),
            ],
            model="claude-3-sonnet-20240229",
        )

        payload = provider._convert_request(request)

        assert payload["system"] == "You are helpful"
        assert len(payload["messages"]) == 2
        assert payload["messages"][0]["role"] == "user"
        assert payload["messages"][1]["role"] == "assistant"

    def test_convert_request_default_model(self) -> None:
        """Test request conversion uses default model when not specified."""
        provider = AnthropicProvider()
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="Hello")],
            model="",  # Empty model
        )

        payload = provider._convert_request(request)

        assert payload["model"] == "claude-3-sonnet-20240229"

    def test_convert_request_preserves_extra_kwargs(self) -> None:
        """Test request conversion preserves extra kwargs."""
        provider = AnthropicProvider()
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="Hello")],
            model="claude-3-sonnet-20240229",
            extra_kwargs={"metadata": {"user_id": "123"}},
        )

        payload = provider._convert_request(request)

        assert payload["metadata"] == {"user_id": "123"}


class TestAnthropicProviderResponseParsing:
    """Tests for AnthropicProvider response parsing."""

    def test_parse_response_standard(self) -> None:
        """Test parsing standard response."""
        provider = AnthropicProvider()
        response_data = {
            "id": "msg_0123456789",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "Hello!"}],
            "model": "claude-3-sonnet-20240229",
            "stop_reason": "end_turn",
            "usage": {"input_tokens": 10, "output_tokens": 20},
        }

        result = provider._parse_chat_completion_response(response_data)

        assert result.content == "Hello!"
        assert result.model == "claude-3-sonnet-20240229"
        assert result.prompt_tokens == 10
        assert result.completion_tokens == 20
        assert result.total_tokens == 30
        assert result.finish_reason == "end_turn"

    def test_parse_response_missing_usage(self) -> None:
        """Test parsing response with missing usage data."""
        provider = AnthropicProvider()
        response_data = {
            "id": "msg_0123456789",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "Hello!"}],
            "model": "claude-3-sonnet-20240229",
            "stop_reason": "end_turn",
        }

        result = provider._parse_chat_completion_response(response_data)

        assert result.prompt_tokens == 0
        assert result.completion_tokens == 0
        assert result.total_tokens == 0

    def test_parse_response_missing_content(self) -> None:
        """Test parsing response with missing content raises error."""
        provider = AnthropicProvider()
        response_data = {
            "id": "msg_0123456789",
            "type": "message",
            "role": "assistant",
            "content": [],
            "model": "claude-3-sonnet-20240229",
        }

        with pytest.raises(RemoteProviderError) as exc_info:
            provider._parse_chat_completion_response(response_data)

        assert "No content" in str(exc_info.value)


class TestAnthropicProviderRetryLogic:
    """Tests for AnthropicProvider retry logic."""

    @pytest.mark.asyncio
    async def test_retry_after_header_parsing(self) -> None:
        """Test Retry-After header parsing."""
        provider = AnthropicProvider(api_key="sk-test123")

        # Create mock response with Retry-After header
        response = httpx.Response(
            429,
            request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"),
            headers={"Retry-After": "30"},
        )

        retry_after = provider._parse_retry_after(response)
        assert retry_after == 30.0

    @pytest.mark.asyncio
    async def test_retry_after_header_invalid_format(self) -> None:
        """Test Retry-After header with invalid format."""
        provider = AnthropicProvider(api_key="sk-test123")

        response = httpx.Response(
            429,
            request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"),
            headers={"Retry-After": "invalid"},
        )

        retry_after = provider._parse_retry_after(response)
        assert retry_after is None

    @pytest.mark.asyncio
    async def test_retry_after_header_missing(self) -> None:
        """Test missing Retry-After header."""
        provider = AnthropicProvider(api_key="sk-test123")

        response = httpx.Response(
            429,
            request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"),
        )

        retry_after = provider._parse_retry_after(response)
        assert retry_after is None

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, respx_mock: respx.MockRouter) -> None:
        """Test max retries exceeded error."""
        respx_mock.post("https://api.anthropic.com/v1/messages").mock(
            return_value=httpx.Response(500, json={"error": "Server error"})
        )

        provider = AnthropicProvider(api_key="sk-test123", max_retries=2)
        request = ChatCompletionRequest(
            messages=[ChatMessage(role="user", content="Hello")],
            model="claude-3-sonnet-20240229",
        )

        with pytest.raises(RemoteProviderError) as exc_info:
            await provider.chat_completion(request)

        assert "All 3 attempts failed" in str(exc_info.value)
        assert len(respx_mock.calls) == 3

        await provider.close()


class TestAnthropicProviderCleanup:
    """Tests for AnthropicProvider cleanup."""

    @pytest.mark.asyncio
    async def test_close_method(self) -> None:
        """Test explicit close method."""
        provider = AnthropicProvider(api_key="sk-test123")

        # Trigger client creation
        client = await provider._get_client()
        assert client is not None
        assert not client.is_closed

        await provider.close()
        assert provider._client is None or provider._client.is_closed

    @pytest.mark.asyncio
    async def test_multiple_close_calls(self) -> None:
        """Test that multiple close calls don't cause errors."""
        provider = AnthropicProvider(api_key="sk-test123")

        await provider.close()
        await provider.close()  # Should not raise
