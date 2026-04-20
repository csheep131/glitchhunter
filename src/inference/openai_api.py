"""
OpenAI-compatible API wrapper for GlitchHunter.

Provides OpenAI API-compatible interface for llama-cpp-server, enabling
integration with tools and libraries that expect OpenAI API format.
"""

import logging
from typing import Any, Dict, List, Optional

import httpx

from core.exceptions import InferenceError
from core.ai_logger import log_request, log_response, log_error

logger = logging.getLogger(__name__)

# Default API endpoints
DEFAULT_CHAT_COMPLETION_ENDPOINT = "/v1/chat/completions"
DEFAULT_EMBEDDINGS_ENDPOINT = "/v1/embeddings"
DEFAULT_MODELS_ENDPOINT = "/v1/models"


class OpenAIAPI:
    """
    OpenAI-compatible API client for llama-cpp-server.

    Wraps HTTP calls to an OpenAI-compatible server endpoint, providing
    type-safe methods for chat completion and embeddings.

    Attributes:
        base_url: Base URL of the API server
        api_key: API key for authentication (optional)
        timeout: Request timeout in seconds
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        api_key: Optional[str] = None,
        timeout: int = 120,
    ) -> None:
        """
        Initialize OpenAI API client.

        Args:
            base_url: Base URL of the API server
            api_key: API key for authentication (optional)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

        # Build headers
        self._headers = {"Content-Type": "application/json"}
        if api_key:
            self._headers["Authorization"] = f"Bearer {api_key}"

        logger.debug(f"OpenAIAPI initialized for {base_url}")

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "default",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        top_p: float = 1.0,
        stream: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Create a chat completion.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model name/alias
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            top_p: Top-p sampling parameter
            stream: Enable streaming (not yet implemented)
            **kwargs: Additional OpenAI API parameters

        Returns:
            Chat completion response dict

        Raises:
            InferenceError: If request fails
        """
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": top_p,
            "stream": stream,
            **kwargs,
        }

        url = f"{self.base_url}{DEFAULT_CHAT_COMPLETION_ENDPOINT}"

        logger.debug(f"Sending chat completion request to {url}")

        # Log request if AI logging enabled
        request_id = log_request(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            **kwargs
        )

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self._headers,
                )
                response.raise_for_status()
                result = response.json()

                # Log response if AI logging enabled
                if result and "choices" in result:
                    content = result["choices"][0].get("message", {}).get("content", "")
                    usage = result.get("usage")
                    finish_reason = result["choices"][0].get("finish_reason")
                    log_response(
                        request_id=request_id,
                        response_content=content,
                        model=model,
                        usage=usage,
                        finish_reason=finish_reason
                    )

                return result

        except httpx.HTTPError as e:
            raise InferenceError(
                f"Chat completion request failed: {e}",
                model_name=model,
                details={
                    "url": url,
                    "status_code": getattr(e, "status_code", None),
                    "error": str(e),
                },
            )

        except Exception as e:
            raise InferenceError(
                f"Unexpected error in chat completion: {e}",
                model_name=model,
                details={"error": str(e)},
            )

    async def embeddings(
        self,
        input: List[str],
        model: str = "default",
        encoding_format: str = "float",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Generate embeddings.

        Args:
            input: List of texts to embed
            model: Model name/alias
            encoding_format: Output format ("float" or "base64")
            **kwargs: Additional OpenAI API parameters

        Returns:
            Embeddings response dict

        Raises:
            InferenceError: If request fails
        """
        payload = {
            "model": model,
            "input": input,
            "encoding_format": encoding_format,
            **kwargs,
        }

        url = f"{self.base_url}{DEFAULT_EMBEDDINGS_ENDPOINT}"

        logger.debug(f"Sending embeddings request to {url}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self._headers,
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPError as e:
            raise InferenceError(
                f"Embeddings request failed: {e}",
                model_name=model,
                details={
                    "url": url,
                    "status_code": getattr(e, "status_code", None),
                    "error": str(e),
                },
            )

        except Exception as e:
            raise InferenceError(
                f"Unexpected error in embeddings: {e}",
                model_name=model,
                details={"error": str(e)},
            )

    async def list_models(self) -> List[Dict[str, Any]]:
        """
        List available models.

        Returns:
            List of model dicts

        Raises:
            InferenceError: If request fails
        """
        url = f"{self.base_url}{DEFAULT_MODELS_ENDPOINT}"

        logger.debug(f"Fetching model list from {url}")

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    url,
                    headers=self._headers,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("data", [])

        except httpx.HTTPError as e:
            raise InferenceError(
                f"Model list request failed: {e}",
                details={
                    "url": url,
                    "status_code": getattr(e, "status_code", None),
                    "error": str(e),
                },
            )

        except Exception as e:
            raise InferenceError(
                f"Unexpected error fetching models: {e}",
                details={"error": str(e)},
            )

    async def health_check(self) -> bool:
        """
        Check if API server is healthy.

        Returns:
            True if server is healthy
        """
        url = f"{self.base_url}/health"

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(url)
                return response.status_code == 200

        except Exception:
            return False

    def health_check_sync(self) -> bool:
        """
        Synchronous health check for API server.

        Returns:
            True if server is healthy
        """
        url = f"{self.base_url}/health"

        try:
            with httpx.Client(timeout=10) as client:
                response = client.get(url)
                return response.status_code == 200

        except Exception:
            return False

    def chat_completion_sync(
        self,
        messages: List[Dict[str, str]],
        model: str = "default",
        temperature: float = 0.7,
        max_tokens: int = 2048,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Synchronous chat completion.

        Args:
            messages: List of message dicts
            model: Model name/alias
            temperature: Temperature for generation
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters

        Returns:
            Chat completion response dict
        """
        import httpx

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs,
        }

        url = f"{self.base_url}{DEFAULT_CHAT_COMPLETION_ENDPOINT}"

        # Log request if AI logging enabled
        request_id = log_request(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    url,
                    json=payload,
                    headers=self._headers,
                )
                response.raise_for_status()
                result = response.json()

                # Log response if AI logging enabled
                if result and "choices" in result:
                    content = result["choices"][0].get("message", {}).get("content", "")
                    usage = result.get("usage")
                    finish_reason = result["choices"][0].get("finish_reason")
                    log_response(
                        request_id=request_id,
                        response_content=content,
                        model=model,
                        usage=usage,
                        finish_reason=finish_reason
                    )

                return result

        except httpx.HTTPError as e:
            log_error(request_id, e, model)
            raise InferenceError(
                f"Chat completion request failed: {e}",
                model_name=model,
                details={"error": str(e)},
            )

    def embeddings_sync(
        self,
        input: List[str],
        model: str = "default",
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Synchronous embeddings generation.

        Args:
            input: List of texts to embed
            model: Model name/alias
            **kwargs: Additional parameters

        Returns:
            Embeddings response dict
        """
        import httpx

        payload = {
            "model": model,
            "input": input,
            **kwargs,
        }

        url = f"{self.base_url}{DEFAULT_EMBEDDINGS_ENDPOINT}"

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    url,
                    json=payload,
                    headers=self._headers,
                )
                response.raise_for_status()
                return response.json()

        except httpx.HTTPError as e:
            raise InferenceError(
                f"Embeddings request failed: {e}",
                model_name=model,
                details={"error": str(e)},
            )

    def set_base_url(self, base_url: str) -> None:
        """
        Update the base URL.

        Args:
            base_url: New base URL
        """
        self.base_url = base_url.rstrip("/")
        logger.debug(f"Base URL updated to {self.base_url}")

    def get_status(self) -> Dict[str, Any]:
        """
        Get API client status.

        Returns:
            Dictionary with status information
        """
        return {
            "base_url": self.base_url,
            "api_key_configured": self.api_key is not None,
            "timeout": self.timeout,
        }
