"""
AI Communication Logger for GlitchHunter.

Logs all LLM requests and responses for debugging purposes.
Can be enabled via config (ai_logging.enabled).
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.config import AILoggingConfig

logger = logging.getLogger(__name__)


class AICommunicationLogger:
    """
    Logger for AI/LLM communication.

    Logs requests and responses to files in the ai_logs directory.
    Each request/response pair gets its own timestamped file.
    """

    def __init__(self, config: AILoggingConfig):
        """
        Initialize AI communication logger.

        Args:
            config: AI logging configuration
        """
        self.config = config
        self.enabled = config.enabled
        self.directory = Path(config.directory)
        self.request_counter = 0

        if self.enabled:
            self._setup_directory()
            logger.info(f"AI Communication logging enabled: {self.directory}")

    def _setup_directory(self) -> None:
        """Create the ai_logs directory if it doesn't exist."""
        self.directory.mkdir(parents=True, exist_ok=True)

        # Cleanup old files if max_files exceeded
        if self.config.max_files > 0:
            self._cleanup_old_files()

    def _cleanup_old_files(self) -> None:
        """Remove old log files if exceeding max_files limit."""
        try:
            files = sorted(
                self.directory.glob("ai_comm_*.json"),
                key=lambda f: f.stat().st_mtime,
                reverse=True
            )

            if len(files) > self.config.max_files:
                for old_file in files[self.config.max_files:]:
                    old_file.unlink()
                    logger.debug(f"Removed old AI log: {old_file}")
        except Exception as e:
            logger.warning(f"Failed to cleanup old AI logs: {e}")

    def _get_timestamp(self) -> str:
        """Get current timestamp for filenames."""
        return datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    def _sanitize_content(self, content: str, max_length: Optional[int] = None) -> str:
        """
        Sanitize content for logging.

        Args:
            content: Content to sanitize
            max_length: Maximum length (if None, use full content)

        Returns:
            Sanitized content
        """
        if max_length and len(content) > max_length:
            return content[:max_length] + f"\n... [{len(content) - max_length} chars truncated]"
        return content

    def log_request(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        Log an LLM request.

        Args:
            model: Model name
            messages: List of messages
            temperature: Temperature parameter
            max_tokens: Max tokens parameter
            **kwargs: Additional parameters

        Returns:
            Request ID for correlating with response
        """
        if not self.enabled:
            return ""

        self.request_counter += 1
        request_id = f"req_{self.request_counter}_{self._get_timestamp()}"

        # Prepare log entry
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id,
            "type": "request",
            "model": model,
        }

        if self.config.log_requests:
            log_entry["parameters"] = {
                "temperature": temperature,
                "max_tokens": max_tokens,
                **kwargs
            }

        if self.config.log_prompts:
            # Sanitize messages
            sanitized_messages = []
            for msg in messages:
                content = msg.get("content", "")
                # Truncate very long prompts
                sanitized_content = self._sanitize_content(content, max_length=10000)
                sanitized_messages.append({
                    "role": msg.get("role", "user"),
                    "content": sanitized_content
                })
            log_entry["messages"] = sanitized_messages
        else:
            log_entry["message_count"] = len(messages)

        # Write to file
        self._write_log(request_id, log_entry)

        return request_id

    def log_response(
        self,
        request_id: str,
        response_content: str,
        model: str,
        usage: Optional[Dict[str, Any]] = None,
        finish_reason: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Log an LLM response.

        Args:
            request_id: Request ID from log_request
            response_content: Response content
            model: Model name
            usage: Token usage information
            finish_reason: Finish reason
            **kwargs: Additional response data
        """
        if not self.enabled or not self.config.log_responses:
            return

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id,
            "type": "response",
            "model": model,
        }

        if self.config.log_full_response:
            log_entry["content"] = self._sanitize_content(response_content, max_length=50000)
        else:
            # Log summary only
            log_entry["content_preview"] = response_content[:500] if response_content else ""
            log_entry["content_length"] = len(response_content)

        if usage:
            log_entry["usage"] = usage

        if finish_reason:
            log_entry["finish_reason"] = finish_reason

        # Write to file
        self._write_log(f"{request_id}_response", log_entry)

    def log_error(
        self,
        request_id: str,
        error: Exception,
        model: str
    ) -> None:
        """
        Log an LLM error.

        Args:
            request_id: Request ID from log_request
            error: Exception that occurred
            model: Model name
        """
        if not self.enabled:
            return

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "request_id": request_id,
            "type": "error",
            "model": model,
            "error_type": type(error).__name__,
            "error_message": str(error),
        }

        self._write_log(f"{request_id}_error", log_entry)

    def _write_log(self, filename: str, data: Dict[str, Any]) -> None:
        """
        Write log entry to file.

        Args:
            filename: Filename (without extension)
            data: Data to write
        """
        try:
            filepath = self.directory / f"ai_comm_{filename}.json"
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to write AI log: {e}")


# Global instance (initialized by Config)
_ai_logger: Optional[AICommunicationLogger] = None


def init_ai_logger(config: AILoggingConfig) -> None:
    """
    Initialize global AI logger.

    Args:
        config: AI logging configuration
    """
    global _ai_logger
    _ai_logger = AICommunicationLogger(config)


def get_ai_logger() -> Optional[AICommunicationLogger]:
    """
    Get global AI logger instance.

    Returns:
        AICommunicationLogger instance or None if not initialized/disabled
    """
    return _ai_logger


def log_request(*args, **kwargs) -> str:
    """Convenience function to log a request."""
    if _ai_logger:
        return _ai_logger.log_request(*args, **kwargs)
    return ""


def log_response(*args, **kwargs) -> None:
    """Convenience function to log a response."""
    if _ai_logger:
        _ai_logger.log_response(*args, **kwargs)


def log_error(*args, **kwargs) -> None:
    """Convenience function to log an error."""
    if _ai_logger:
        _ai_logger.log_error(*args, **kwargs)
