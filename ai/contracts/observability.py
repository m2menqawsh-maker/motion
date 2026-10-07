"""
ai/contracts/observability.py
=============================
Canonical typed contracts for AI Observability & Tracing (S27.19).

Invariants:
- Typed trace spans with hierarchical correlation:
  run_id -> step_id -> activity_id -> trace_id -> span_id -> parent_span_id.
- Captures capability, model, prompt_version, token usage, cost, latency, cache, fallback, retry.
- Telemetry is NOT source of truth; never replaces transactional DB state.
- Strictly sanitized: secrets, bearer tokens, signed URLs, and raw prompts are forbidden by default.
- No dict[str, Any] at boundaries.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional
from pydantic import Field, JsonValue

from ai.contracts.base import AIContractModel, StrictDecimal, TzAwareDatetime, strict_enum


class SpanType(str, Enum):
    """Categorical classification of AI execution spans."""
    AI_RUN = "AI_RUN"
    CONTEXT_BUILD = "CONTEXT_BUILD"
    MEMORY_RETRIEVAL = "MEMORY_RETRIEVAL"
    MODEL_ROUTE = "MODEL_ROUTE"
    CACHE_LOOKUP = "CACHE_LOOKUP"
    PROVIDER_CALL = "PROVIDER_CALL"
    TOOL_CALL = "TOOL_CALL"
    VALIDATION = "VALIDATION"
    ARTIFACT_PERSISTENCE = "ARTIFACT_PERSISTENCE"


SpanTypeEnum = strict_enum(SpanType)


class TraceSpanRecord(AIContractModel):
    """
    Authoritative record for a single correlated execution span in an AI trace.
    """
    trace_id: str = Field(min_length=1, description="Root distributed trace identifier")
    span_id: str = Field(min_length=1, description="Unique span identifier")
    parent_span_id: Optional[str] = Field(default=None, description="Parent span identifier in hierarchy")
    span_type: SpanTypeEnum = Field(description="Architectural layer or operation type")
    name: str = Field(min_length=1, description="Human-readable span operation name")
    run_id: str = Field(min_length=1, description="Correlated AIRun identifier")
    step_id: Optional[str] = Field(default=None, description="Correlated AIStep identifier")
    activity_id: Optional[str] = Field(default=None, description="Correlated durable activity identifier")
    workspace_id: str = Field(min_length=1, description="Tenant workspace isolation key")
    project_id: Optional[str] = Field(default=None, description="Associated project identifier")
    capability: Optional[str] = Field(default=None, description="AI capability exercised")
    provider: Optional[str] = Field(default=None, description="Provider adapter invoked")
    model: Optional[str] = Field(default=None, description="Model identifier used")
    prompt_id: Optional[str] = Field(default=None, description="Prompt identifier resolved")
    prompt_version: Optional[str] = Field(default=None, description="Prompt version resolved")
    started_at: TzAwareDatetime = Field(description="Span start timestamp")
    ended_at: Optional[TzAwareDatetime] = Field(default=None, description="Span end timestamp")
    duration_ms: Optional[float] = Field(default=None, ge=0.0, description="Execution duration in milliseconds")
    input_tokens: Optional[int] = Field(default=None, ge=0, description="Prompt / input tokens consumed")
    output_tokens: Optional[int] = Field(default=None, ge=0, description="Completion / output tokens generated")
    cache_hit: Optional[bool] = Field(default=None, description="Whether operation was served from cache")
    retry_count: int = Field(default=0, ge=0, description="Number of retry attempts executed")
    fallback: bool = Field(default=False, description="Whether fallback model or provider was engaged")
    estimated_cost: Optional[StrictDecimal] = Field(default=None, description="Estimated cost of span execution")
    actual_cost: Optional[StrictDecimal] = Field(default=None, description="Settled actual cost of span execution")
    quality_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Observed quality score if evaluated")
    status: str = Field(default="SUCCESS", description="Execution outcome (SUCCESS, ERROR, CANCELLED)")
    error_code: Optional[str] = Field(default=None, description="Standardized error code if status is ERROR")
    attributes: Dict[str, JsonValue] = Field(default_factory=dict, description="Sanitized, low-cardinality metadata attributes")


class AITrace(AIContractModel):
    """
    Complete correlated trace document aggregating all spans for an AIRun.
    """
    trace_id: str = Field(min_length=1, description="Trace identifier")
    run_id: str = Field(min_length=1, description="Associated AIRun identifier")
    workspace_id: str = Field(min_length=1, description="Tenant boundary")
    spans: List[TraceSpanRecord] = Field(default_factory=list, description="Ordered execution spans")
