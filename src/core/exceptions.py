"""
Custom exceptions for GlitchHunter.

Defines a hierarchy of exception classes for proper error handling
throughout the application.
"""

from typing import Any, Dict, Optional


class GlitchHunterException(Exception):
    """
    Base exception for all GlitchHunter errors.

    All custom exceptions inherit from this class to enable
    centralized error handling.

    Attributes:
        message: Human-readable error message
        code: Optional error code for programmatic handling
        details: Optional dictionary with additional context
    """

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Initialize the exception.

        Args:
            message: Human-readable error message
            code: Optional error code
            details: Optional additional context
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

    def __str__(self) -> str:
        """String representation of the exception."""
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary for logging/API responses.

        Returns:
            Dictionary with exception information
        """
        return {
            "type": self.__class__.__name__,
            "message": self.message,
            "code": self.code,
            "details": self.details,
        }


class HardwareDetectionError(GlitchHunterException):
    """
    Raised when hardware detection fails.

    Examples:
        - pynvml not available
        - GPU not detected
        - VRAM query failed
    """

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message=message,
            code="HARDWARE_DETECTION_ERROR",
            details=details,
        )


class ModelLoadError(GlitchHunterException):
    """
    Raised when model loading fails.

    Examples:
        - Model file not found
        - Invalid model format
        - Insufficient VRAM
        - CUDA initialization failed
    """

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(
            message=message,
            code="MODEL_LOAD_ERROR",
            details=details,
        )


class PatchApplyError(GlitchHunterException):
    """
    Raised when patch application fails.

    Examples:
        - Patch format invalid
        - Target file not found
        - Patch conflicts with existing code
        - Syntax error in patched code
    """

    def __init__(
        self,
        message: str,
        file_path: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        details = details or {}
        if file_path:
            details["file_path"] = file_path
        super().__init__(
            message=message,
            code="PATCH_APPLY_ERROR",
            details=details,
        )


class EscalationError(GlitchHunterException):
    """
    Raised when escalation process fails.

    Examples:
        - All escalation levels exhausted
        - Escalation handler not found
        - Human review timeout
    """

    def __init__(
        self,
        message: str,
        level: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        details = details or {}
        if level is not None:
            details["escalation_level"] = level
        super().__init__(
            message=message,
            code="ESCALATION_ERROR",
            details=details,
        )


class MCPConnectionError(GlitchHunterException):
    """
    Raised when MCP (Model Context Protocol) connection fails.

    Examples:
        - MCP server not reachable
        - Connection timeout
        - Protocol error
        - Authentication failed
    """

    def __init__(
        self,
        message: str,
        server_url: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        details = details or {}
        if server_url:
            details["server_url"] = server_url
        super().__init__(
            message=message,
            code="MCP_CONNECTION_ERROR",
            details=details,
        )


class ConfigError(GlitchHunterException):
    """
    Raised when configuration loading or validation fails.

    Examples:
        - Config file not found
        - Invalid YAML syntax
        - Missing required fields
        - Invalid field values
    """

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        details = details or {}
        if field:
            details["field"] = field
        super().__init__(
            message=message,
            code="CONFIG_ERROR",
            details=details,
        )


class InferenceError(GlitchHunterException):
    """
    Raised when model inference fails.

    Examples:
        - Model not loaded
        - Context length exceeded
        - Generation timeout
        - CUDA out of memory
    """

    def __init__(
        self,
        message: str,
        model_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        details = details or {}
        if model_name:
            details["model_name"] = model_name
        super().__init__(
            message=message,
            code="INFERENCE_ERROR",
            details=details,
        )


class SecurityScanError(GlitchHunterException):
    """
    Raised when security scan fails.

    Examples:
        - Semgrep not available
        - Rule file not found
        - Scan timeout
        - Invalid scan result format
    """

    def __init__(
        self,
        message: str,
        scanner: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        details = details or {}
        if scanner:
            details["scanner"] = scanner
        super().__init__(
            message=message,
            code="SECURITY_SCAN_ERROR",
            details=details,
        )


class GraphAnalysisError(GlitchHunterException):
    """
    Raised when graph analysis fails.

    Examples:
        - Symbol graph not built
        - Circular dependency detected
        - Invalid graph structure
        - Path not found
    """

    def __init__(
        self,
        message: str,
        graph_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        details = details or {}
        if graph_type:
            details["graph_type"] = graph_type
        super().__init__(
            message=message,
            code="GRAPH_ANALYSIS_ERROR",
            details=details,
        )


class ValidationError(GlitchHunterException):
    """
    Raised when input validation fails.

    Examples:
        - Invalid repository path
        - Missing required parameters
        - Invalid file format
        - Schema validation failed
    """

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        details = details or {}
        if field:
            details["field"] = field
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            details=details,
        )
