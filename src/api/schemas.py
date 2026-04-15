"""
Pydantic schemas for GlitchHunter API.

Defines request and response models for all API endpoints.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# =============================================================================
# Request Models
# =============================================================================


class AnalyzeRequest(BaseModel):
    """Request to start code analysis."""

    repo_path: str = Field(..., description="Path to repository or URL")
    languages: Optional[List[str]] = Field(
        None, description="Languages to analyze (auto-detect if None)"
    )
    scan_security: bool = Field(True, description="Run security scans")
    scan_correctness: bool = Field(True, description="Run correctness scans")
    generate_patches: bool = Field(True, description="Generate patches for issues")
    index_mcp: bool = Field(False, description="Index project with SocratiCode before scan")
    max_iterations: int = Field(5, description="Maximum patch iterations")

    model_config = {
        "json_schema_extra": {
            "example": {
                "repo_path": "/path/to/repo",
                "languages": ["python", "javascript"],
                "scan_security": True,
                "scan_correctness": True,
                "generate_patches": True,
                "max_iterations": 5,
            }
        }
    }


class EscalationRequest(BaseModel):
    """Request to escalate an issue."""

    issue_id: str = Field(..., description="ID of the issue to escalate")
    level: int = Field(..., ge=1, le=4, description="Escalation level (1-4)")
    reason: str = Field(..., description="Reason for escalation")
    context: Optional[Dict[str, Any]] = Field(
        None, description="Additional context for escalation"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "issue_id": "issue-123",
                "level": 2,
                "reason": "Patch verification failed after 3 attempts",
                "context": {"attempts": 3, "error": "Verification timeout"},
            }
        }
    }


# =============================================================================
# Response Models
# =============================================================================


class AnalyzeResponse(BaseModel):
    """Response from analysis request."""

    analysis_id: str = Field(..., description="Unique analysis ID")
    status: str = Field(..., description="Analysis status")
    repo_path: str = Field(..., description="Repository path")
    started_at: datetime = Field(..., description="Analysis start time")
    estimated_duration_seconds: Optional[int] = Field(
        None, description="Estimated duration"
    )
    message: str = Field(..., description="Status message")

    model_config = {
        "json_schema_extra": {
            "example": {
                "analysis_id": "analysis-abc123",
                "status": "running",
                "repo_path": "/path/to/repo",
                "started_at": "2026-04-14T10:30:00Z",
                "estimated_duration_seconds": 600,
                "message": "Analysis started successfully",
            }
        }
    }


class StatusResponse(BaseModel):
    """Response from status endpoint."""

    analysis_id: str = Field(..., description="Analysis ID")
    status: str = Field(..., description="Current status")
    current_state: Optional[str] = Field(None, description="Current workflow state")
    progress_percent: float = Field(..., description="Progress percentage (0-100)")
    findings_count: int = Field(0, description="Number of findings so far")
    patches_generated: int = Field(0, description="Number of patches generated")
    patches_verified: int = Field(0, description="Number of patches verified")
    errors: List[str] = Field(default_factory=list, description="Errors encountered")
    started_at: Optional[datetime] = Field(None, description="Start time")
    completed_at: Optional[datetime] = Field(None, description="Completion time")
    result_url: Optional[str] = Field(None, description="URL to fetch results")

    model_config = {
        "json_schema_extra": {
            "example": {
                "analysis_id": "analysis-abc123",
                "status": "running",
                "current_state": "patch_loop",
                "progress_percent": 65.0,
                "findings_count": 12,
                "patches_generated": 5,
                "patches_verified": 3,
                "errors": [],
                "started_at": "2026-04-14T10:30:00Z",
                "completed_at": None,
                "result_url": "/api/analyze/analysis-abc123/result",
            }
        }
    }


class HardwareInfo(BaseModel):
    """Hardware information response."""

    detected_stack: str = Field(..., description="Detected hardware stack")
    gpu_name: Optional[str] = Field(None, description="GPU name")
    vram_total_gb: int = Field(..., description="Total VRAM in GB")
    vram_available_gb: float = Field(..., description="Available VRAM in GB")
    cuda_compute: Optional[str] = Field(None, description="CUDA compute capability")
    execution_mode: str = Field(..., description="Execution mode (sequential/parallel)")
    features: Dict[str, bool] = Field(..., description="Enabled features")

    model_config = {
        "json_schema_extra": {
            "example": {
                "detected_stack": "stack_b",
                "gpu_name": "NVIDIA GeForce RTX 3090",
                "vram_total_gb": 24,
                "vram_available_gb": 22.5,
                "cuda_compute": "8.6",
                "execution_mode": "parallel",
                "features": {
                    "parallel_inference": True,
                    "deep_security_scan": True,
                    "multi_model_consensus": True,
                },
            }
        }
    }


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Health status")
    version: str = Field(..., description="Application version")
    timestamp: datetime = Field(..., description="Response timestamp")
    components: Dict[str, str] = Field(
        ..., description="Component health status"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "healthy",
                "version": "0.1.0",
                "timestamp": "2026-04-14T10:30:00Z",
                "components": {
                    "api": "healthy",
                    "inference": "healthy",
                    "mcp": "healthy",
                    "database": "healthy",
                },
            }
        }
    }


class ErrorResponse(BaseModel):
    """Error response."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Error details")
    code: Optional[str] = Field(None, description="Error code")

    model_config = {
        "json_schema_extra": {
            "example": {
                "error": "ValidationError",
                "message": "Repository not found",
                "details": {"repo_path": "/invalid/path"},
                "code": "REPO_NOT_FOUND",
            }
        }
    }


class FindingSummary(BaseModel):
    """Summary of a security/correctness finding."""

    id: str = Field(..., description="Finding ID")
    type: str = Field(..., description="Finding type (security/correctness)")
    severity: str = Field(..., description="Severity level")
    file_path: str = Field(..., description="File path")
    line_start: int = Field(..., description="Start line")
    line_end: int = Field(..., description="End line")
    message: str = Field(..., description="Finding message")
    rule_id: Optional[str] = Field(None, description="Rule ID that matched")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "finding-001",
                "type": "security",
                "severity": "HIGH",
                "file_path": "src/auth.py",
                "line_start": 42,
                "line_end": 45,
                "message": "SQL injection vulnerability detected",
                "rule_id": "python.lang.security.sql-injection",
            }
        }
    }


class PatchInfo(BaseModel):
    """Information about a generated patch."""

    id: str = Field(..., description="Patch ID")
    finding_id: str = Field(..., description="Associated finding ID")
    file_path: str = Field(..., description="File to patch")
    diff: str = Field(..., description="Unified diff")
    verified: bool = Field(..., description="Whether patch is verified")
    applied: bool = Field(..., description="Whether patch is applied")
    verification_attempts: int = Field(0, description="Verification attempts")

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "patch-001",
                "finding_id": "finding-001",
                "file_path": "src/auth.py",
                "diff": "@@ -42,4 +42,6 @@\n- query = f'SELECT * FROM users...",
                "verified": True,
                "applied": False,
                "verification_attempts": 1,
            }
        }
    }


class AnalysisResult(BaseModel):
    """Complete analysis result."""

    analysis_id: str = Field(..., description="Analysis ID")
    repo_path: str = Field(..., description="Repository path")
    status: str = Field(..., description="Final status")
    findings: List[FindingSummary] = Field(..., description="All findings")
    patches: List[PatchInfo] = Field(..., description="Generated patches")
    statistics: Dict[str, Any] = Field(..., description="Analysis statistics")
    started_at: datetime = Field(..., description="Start time")
    completed_at: datetime = Field(..., description="Completion time")
    duration_seconds: float = Field(..., description="Total duration")

    model_config = {
        "json_schema_extra": {
            "example": {
                "analysis_id": "analysis-abc123",
                "repo_path": "/path/to/repo",
                "status": "completed",
                "findings": [],
                "patches": [],
                "statistics": {"files_analyzed": 50, "lines_analyzed": 10000},
                "started_at": "2026-04-14T10:30:00Z",
                "completed_at": "2026-04-14T10:40:00Z",
                "duration_seconds": 600.0,
            }
        }
    }


# =============================================================================
# Event Models (for WebSocket streaming)
# =============================================================================


class AnalysisEvent(BaseModel):
    """Analysis progress event for WebSocket."""

    event_type: str = Field(..., description="Event type")
    analysis_id: str = Field(..., description="Analysis ID")
    data: Dict[str, Any] = Field(..., description="Event data")
    timestamp: datetime = Field(..., description="Event timestamp")

    model_config = {
        "json_schema_extra": {
            "example": {
                "event_type": "state_change",
                "analysis_id": "analysis-abc123",
                "data": {"from_state": "shield", "to_state": "hypothesis"},
                "timestamp": "2026-04-14T10:35:00Z",
            }
        }
    }


# =============================================================================
# TUI Data Models
# =============================================================================


class StackInfo(BaseModel):
    """Information about current hardware stack."""
    stack_type: str = Field(..., description="Stack type (stack_a/stack_b)")
    gpu_name: str = Field(..., description="GPU name")
    vram_gb: int = Field(..., description="VRAM in GB")
    mode: str = Field(..., description="Execution mode (sequential/parallel)")
    available: bool = Field(True, description="Whether stack is available")


class ModelInfo(BaseModel):
    """Information about an AI model."""
    name: str = Field(..., description="Model name")
    role: str = Field(..., description="Model role (analyzer/verifier)")
    path: str = Field(..., description="Path to model file")
    available: bool = Field(..., description="Whether model is downloaded")
    size_gb: Optional[float] = Field(None, description="Model size in GB")


class LlamaStatus(BaseModel):
    """Llama.cpp server status."""
    running: bool = Field(..., description="Whether server is running")
    response_time_ms: Optional[int] = Field(None, description="Last response time")
    load_percent: Optional[int] = Field(None, description="Server load")
    port: int = Field(8000, description="Server port")


class SystemResources(BaseModel):
    """System resource usage."""
    cpu_percent: float = Field(..., description="CPU usage percentage")
    ram_used_gb: float = Field(..., description="RAM used in GB")
    ram_total_gb: float = Field(..., description="RAM total in GB")
    gpu_temp_c: Optional[int] = Field(None, description="GPU temperature")
    vram_used_gb: Optional[float] = Field(None, description="VRAM used in GB")
    vram_total_gb: Optional[float] = Field(None, description="VRAM total in GB")


class SocratiCodeStatus(BaseModel):
    """SocratiCode MCP integration status."""
    enabled: bool = Field(..., description="Integration enabled")
    connected: bool = Field(..., description="Connected to MCP server")
    server_url: str = Field(..., description="MCP server URL")
    indexed_projects: int = Field(0, description="Number of indexed projects")
    features: List[str] = Field(default_factory=list, description="Available features")


class CompleteStatus(BaseModel):
    """Complete system status for TUI."""
    api_online: bool = Field(..., description="API is online")
    current_stack: StackInfo = Field(..., description="Current stack info")
    available_stacks: List[StackInfo] = Field(..., description="All available stacks")
    models: List[ModelInfo] = Field(..., description="Available models")
    llama: LlamaStatus = Field(..., description="Llama server status")
    socraticode: SocratiCodeStatus = Field(..., description="SocratiCode MCP status")
    system: SystemResources = Field(..., description="System resources")
    uptime_seconds: int = Field(..., description="API uptime in seconds")
