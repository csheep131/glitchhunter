"""
Unit tests for Base Provider types and interface.

Tests cover data classes and abstract base class functionality.
"""

import pytest

from inference.remote.base_provider import (
    BaseProvider,
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    EmbeddingRequest,
    EmbeddingResponse,
    HealthStatus,
)


class TestChatMessage:
    """Tests for ChatMessage dataclass."""

    def test_basic_message(self) -> None:
        """Test creating a basic chat message."""
        msg = ChatMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.name is None

    def test_message_with_name(self) -> None:
        """Test creating a message with name."""
        msg = ChatMessage(role="user", content="Hello", name="Alice")
        assert msg.name == "Alice"

    def test_to_dict(self) -> None:
        """Test converting message to dictionary."""
        msg = ChatMessage(role="user", content="Hello", name="Alice")
        result = msg.to_dict()

        assert result == {
            "role": "user",
            "content": "Hello",
            "name": "Alice",
        }

    def test_to_dict_without_name(self) -> None:
        """Test converting message without name."""
        msg = ChatMessage(role="system", content="You are helpful")
        result = msg.to_dict()

        assert result == {
            "role": "system",
            "content": "You are helpful",
        }
        assert "name" not in result


class TestChatCompletionRequest:
    """Tests for ChatCompletionRequest dataclass."""

    def test_basic_request(self) -> None:
        """Test creating a basic request."""
        messages = [ChatMessage(role="user", content="Hello")]
        req = ChatCompletionRequest(messages=messages, model="gpt-4")

        assert req.model == "gpt-4"
        assert req.temperature == 0.7
        assert req.max_tokens is None
        assert req.stream is False
        assert req.n == 1

    def test_request_with_all_params(self) -> None:
        """Test creating a request with all parameters."""
        messages = [
            ChatMessage(role="system", content="You are helpful"),
            ChatMessage(role="user", content="Hello"),
        ]
        req = ChatCompletionRequest(
            messages=messages,
            model="gpt-4",
            temperature=0.5,
            max_tokens=100,
            top_p=0.9,
            frequency_penalty=0.1,
            presence_penalty=0.2,
            stop=["END", "STOP"],
            stream=True,
            n=2,
        )

        assert req.temperature == 0.5
        assert req.max_tokens == 100
        assert req.top_p == 0.9
        assert req.frequency_penalty == 0.1
        assert req.presence_penalty == 0.2
        assert req.stop == ["END", "STOP"]
        assert req.stream is True
        assert req.n == 2

    def test_to_dict(self) -> None:
        """Test converting request to dictionary."""
        messages = [
            ChatMessage(role="system", content="Be helpful"),
            ChatMessage(role="user", content="Hi"),
        ]
        req = ChatCompletionRequest(
            messages=messages,
            model="gpt-4",
            temperature=0.8,
            max_tokens=50,
            stop=["END"],
            n=1,
        )

        result = req.to_dict()

        assert result["model"] == "gpt-4"
        assert result["temperature"] == 0.8
        assert result["max_tokens"] == 50
        assert result["stop"] == ["END"]
        assert len(result["messages"]) == 2
        assert result["messages"][0]["role"] == "system"
        assert result["messages"][1]["role"] == "user"

    def test_to_dict_with_extra_kwargs(self) -> None:
        """Test converting request with extra kwargs."""
        messages = [ChatMessage(role="user", content="Hello")]
        req = ChatCompletionRequest(
            messages=messages,
            model="gpt-4",
            extra_kwargs={"user": "user123", "metadata": {"key": "value"}},
        )

        result = req.to_dict()
        assert result["user"] == "user123"
        assert result["metadata"] == {"key": "value"}


class TestChatCompletionResponse:
    """Tests for ChatCompletionResponse dataclass."""

    def test_basic_response(self) -> None:
        """Test creating a basic response."""
        resp = ChatCompletionResponse(
            content="Hello there!",
            model="gpt-4",
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            finish_reason="stop",
        )

        assert resp.content == "Hello there!"
        assert resp.model == "gpt-4"
        assert resp.finish_reason == "stop"
        assert resp.index == 0

    def test_usage_properties(self) -> None:
        """Test usage property accessors."""
        resp = ChatCompletionResponse(
            content="Test",
            model="gpt-4",
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            finish_reason="stop",
        )

        assert resp.prompt_tokens == 10
        assert resp.completion_tokens == 5
        assert resp.total_tokens == 15

    def test_usage_with_missing_keys(self) -> None:
        """Test usage with missing keys returns 0."""
        resp = ChatCompletionResponse(
            content="Test",
            model="gpt-4",
            usage={},
            finish_reason="stop",
        )

        assert resp.prompt_tokens == 0
        assert resp.completion_tokens == 0
        assert resp.total_tokens == 0

    def test_with_raw_response(self) -> None:
        """Test response with raw response data."""
        raw = {
            "id": "chatcmpl-123",
            "choices": [{"message": {"content": "Hello"}}],
        }
        resp = ChatCompletionResponse(
            content="Hello",
            model="gpt-4",
            usage={},
            finish_reason="stop",
            raw_response=raw,
        )

        assert resp.raw_response == raw


class TestEmbeddingRequest:
    """Tests for EmbeddingRequest dataclass."""

    def test_single_input(self) -> None:
        """Test request with single input."""
        req = EmbeddingRequest(input="Hello world", model="text-embedding-3-small")
        assert req.input == "Hello world"
        assert req.model == "text-embedding-3-small"

    def test_multiple_inputs(self) -> None:
        """Test request with multiple inputs."""
        req = EmbeddingRequest(
            input=["Hello", "World"], model="text-embedding-3-small"
        )
        assert req.input == ["Hello", "World"]

    def test_to_dict(self) -> None:
        """Test converting request to dictionary."""
        req = EmbeddingRequest(
            input="Hello",
            model="text-embedding-3-small",
            encoding_format="float",
            dimensions=512,
        )

        result = req.to_dict()
        assert result["input"] == "Hello"
        assert result["model"] == "text-embedding-3-small"
        assert result["encoding_format"] == "float"
        assert result["dimensions"] == 512

    def test_to_dict_without_dimensions(self) -> None:
        """Test converting request without dimensions."""
        req = EmbeddingRequest(
            input="Hello",
            model="text-embedding-3-small",
        )

        result = req.to_dict()
        assert "dimensions" not in result


class TestEmbeddingResponse:
    """Tests for EmbeddingResponse dataclass."""

    def test_basic_response(self) -> None:
        """Test creating a basic response."""
        resp = EmbeddingResponse(
            embeddings=[[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
            model="text-embedding-3-small",
            usage={"prompt_tokens": 10, "total_tokens": 10},
        )

        assert len(resp.embeddings) == 2
        assert resp.embeddings[0] == [0.1, 0.2, 0.3]
        assert resp.model == "text-embedding-3-small"

    def test_usage_properties(self) -> None:
        """Test usage property accessors."""
        resp = EmbeddingResponse(
            embeddings=[[0.1, 0.2]],
            model="text-embedding-3-small",
            usage={"prompt_tokens": 5, "total_tokens": 5},
        )

        assert resp.prompt_tokens == 5
        assert resp.total_tokens == 5


class TestHealthStatus:
    """Tests for HealthStatus dataclass."""

    def test_healthy_status(self) -> None:
        """Test creating healthy status."""
        status = HealthStatus(
            healthy=True,
            message="All good",
            latency_ms=50.5,
        )

        assert status.healthy is True
        assert status.message == "All good"
        assert status.latency_ms == 50.5

    def test_unhealthy_status(self) -> None:
        """Test creating unhealthy status."""
        status = HealthStatus(
            healthy=False,
            message="Connection failed",
            details={"error": "timeout"},
        )

        assert status.healthy is False
        assert status.message == "Connection failed"
        assert status.details == {"error": "timeout"}


class TestBaseProvider:
    """Tests for BaseProvider abstract class."""

    def test_cannot_instantiate_abstract(self) -> None:
        """Test that BaseProvider cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseProvider(name="test", base_url="http://test.com")

    def test_concrete_implementation(self) -> None:
        """Test creating a concrete implementation."""

        class TestProvider(BaseProvider):
            async def chat_completion(self, request):
                return None

            async def embeddings(self, request):
                return None

            async def health_check(self):
                return HealthStatus(healthy=True, message="OK")

            def get_provider_name(self):
                return self.name

        provider = TestProvider(name="test", base_url="http://test.com", timeout=60)

        assert provider.name == "test"
        assert provider.base_url == "http://test.com"
        assert provider.timeout == 60
        assert provider.get_provider_name() == "test"

    def test_api_key_management(self) -> None:
        """Test API key getter/setter."""

        class TestProvider(BaseProvider):
            async def chat_completion(self, request):
                return None

            async def embeddings(self, request):
                return None

            async def health_check(self):
                return HealthStatus(healthy=True, message="OK")

            def get_provider_name(self):
                return self.name

        provider = TestProvider(
            name="test", base_url="http://test.com", api_key="sk-test123"
        )

        assert provider.get_api_key() == "sk-test123"

        provider.set_api_key("sk-new456")
        assert provider.get_api_key() == "sk-new456"

    def test_build_url(self) -> None:
        """Test URL building."""

        class TestProvider(BaseProvider):
            async def chat_completion(self, request):
                return None

            async def embeddings(self, request):
                return None

            async def health_check(self):
                return HealthStatus(healthy=True, message="OK")

            def get_provider_name(self):
                return self.name

        provider = TestProvider(name="test", base_url="http://test.com/api")

        assert provider._build_url("/v1/chat") == "http://test.com/api/v1/chat"
        assert (
            provider._build_url("/v1/embeddings") == "http://test.com/api/v1/embeddings"
        )

    def test_build_url_trailing_slash(self) -> None:
        """Test URL building with trailing slash in base."""

        class TestProvider(BaseProvider):
            async def chat_completion(self, request):
                return None

            async def embeddings(self, request):
                return None

            async def health_check(self):
                return HealthStatus(healthy=True, message="OK")

            def get_provider_name(self):
                return self.name

        provider = TestProvider(name="test", base_url="http://test.com/api/")

        # Should not double the slash
        assert provider._build_url("/v1/chat") == "http://test.com/api/v1/chat"

    def test_repr(self) -> None:
        """Test string representation."""

        class TestProvider(BaseProvider):
            async def chat_completion(self, request):
                return None

            async def embeddings(self, request):
                return None

            async def health_check(self):
                return HealthStatus(healthy=True, message="OK")

            def get_provider_name(self):
                return self.name

        provider = TestProvider(name="openai", base_url="https://api.openai.com")
        repr_str = repr(provider)

        assert "TestProvider" in repr_str
        assert "openai" in repr_str
        assert "https://api.openai.com" in repr_str
