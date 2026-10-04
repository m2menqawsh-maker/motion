"""
ai/observability/__init__.py
============================
AI Observability, Tracing, Metrics, and Secret Redaction Subsystem (S27.19).
"""

from ai.contracts.observability import AITrace, SpanType, TraceSpanRecord
from ai.observability.metrics import AIMetricsCollector, HighCardinalityLabelError
from ai.observability.redaction import (
    is_raw_content_logging_allowed,
    redact_string,
    redact_telemetry_payload,
    scan_trace_for_secrets,
)
from ai.observability.repository import TraceRepository
from ai.observability.tracer import AITracer, SpanContext

__all__ = [
    "AITrace",
    "SpanType",
    "TraceSpanRecord",
    "AIMetricsCollector",
    "HighCardinalityLabelError",
    "is_raw_content_logging_allowed",
    "redact_string",
    "redact_telemetry_payload",
    "scan_trace_for_secrets",
    "TraceRepository",
    "AITracer",
    "SpanContext",
]
