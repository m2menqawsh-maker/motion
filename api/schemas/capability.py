"""
api/schemas/capability.py — Schemas for Capability Execution and Discovery.
Governs typed requests and responses for authorized capability invocations via CapabilityRouter (S28-M03 / REALITY-015).
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ExecuteCapabilityRequest(BaseModel):
    """Client request to execute an authorized domain or tool capability."""
    capability_id: str = Field(..., description="Canonical capability identifier (e.g. GENERATE_SPEECH_MANIFEST, TRIM_VIDEO)")
    input: Dict[str, Any] = Field(default_factory=dict, description="Typed input payload for the capability")
    idempotency_key: Optional[str] = Field(default=None, description="Optional client idempotency key")
    requested_timeout: Optional[float] = Field(default=30.0, ge=1.0, le=300.0, description="Execution timeout in seconds")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Safe caller metadata")


class CapabilityErrorDetail(BaseModel):
    """Structured error details from capability execution."""
    code: str = Field(description="Structured AI error code")
    message: str = Field(description="Sanitized human-readable error explanation")
    retryable: bool = Field(default=False, description="Whether the operation may be retried safely")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional error context")


class ExecuteCapabilityResponse(BaseModel):
    """Response returned upon capability execution."""
    request_id: str = Field(description="Unique request identifier")
    capability_id: str = Field(description="Requested capability identifier")
    status: str = Field(description="Execution lifecycle status (SUCCESS, FAILED, PARTIAL)")
    output: Optional[Dict[str, Any]] = Field(default=None, description="Typed capability output dictionary")
    duration_ms: int = Field(description="Execution duration in milliseconds")
    error: Optional[CapabilityErrorDetail] = Field(default=None, description="Error details if execution failed")
    execution_metadata: Dict[str, Any] = Field(default_factory=dict, description="Execution topology and adapter metadata")


class CapabilityDescriptorResponse(BaseModel):
    """Summary descriptor for a capability in the capability catalog."""
    capability_id: str
    category: str
    family: str
    description: str
    cost_class: str
    latency_class: str
    is_allowlisted: bool
