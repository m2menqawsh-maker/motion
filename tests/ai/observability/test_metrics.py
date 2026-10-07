"""
tests/ai/observability/test_metrics.py
=======================================
Tests for Standardized AI Subsystem Metrics & Cardinality Controls (S27.19).

Invariants verified:
1. Records all required metrics:
   - ai.cost.total, ai.cost.per_project
   - ai.request.count, ai.failure.rate
   - ai.cache.hit_rate
   - ai.router.escalation_rate, ai.router.fallback_rate
   - ai.provider.latency, ai.provider.error_rate
   - ai.budget.rejections
   - ai.retry.count
   - ai.quality.score
2. Bounded label cardinality enforcement:
   - Permitted bounded label keys (workspace_id, project_id, capability, provider, model, status, execution_class, reason_code).
   - Forbidden high-cardinality keys (url, prompt, text, body, query, input, output) raise HighCardinalityLabelError.
   - Values exceeding 64 characters raise HighCardinalityLabelError.
"""

from decimal import Decimal
import pytest

from ai.observability.metrics import (
    AIMetricsCollector,
    HighCardinalityLabelError,
)


@pytest.fixture
def collector():
    return AIMetricsCollector()


def test_cost_and_project_metrics(collector):
    collector.record_cost(Decimal("1.25"), workspace_id="ws_01", project_id="prj_100")
    collector.record_cost(Decimal("0.75"), workspace_id="ws_01", project_id="prj_100")
    collector.record_cost(Decimal("2.00"), workspace_id="ws_01", project_id="prj_200")

    summary = collector.get_summary()
    assert Decimal(summary["ai.cost.total"]) == Decimal("4.00")


def test_operational_rates(collector):
    # 3 successful requests, 1 failed request -> failure rate = 0.25
    collector.record_request("TEXT_GENERATION", "openai", "gpt-4o", "SUCCESS", "ws_01")
    collector.record_request("TEXT_GENERATION", "openai", "gpt-4o", "SUCCESS", "ws_01")
    collector.record_request("TEXT_GENERATION", "openai", "gpt-4o", "SUCCESS", "ws_01")
    collector.record_request("TEXT_GENERATION", "openai", "gpt-4o", "ERROR", "ws_01")

    # Cache: 3 lookups, 2 hits -> hit rate = 0.6667
    collector.record_cache_lookup(True, "TEXT_GENERATION", "ws_01")
    collector.record_cache_lookup(True, "TEXT_GENERATION", "ws_01")
    collector.record_cache_lookup(False, "TEXT_GENERATION", "ws_01")

    # Router: 4 events, 1 escalation, 1 fallback -> 0.25 each
    collector.record_router_event("route", "TEXT_GENERATION")
    collector.record_router_event("route", "TEXT_GENERATION")
    collector.record_router_event("escalation", "TEXT_GENERATION")
    collector.record_router_event("fallback", "TEXT_GENERATION")

    # Budget rejections: 2
    collector.record_budget_rejection("ws_01")
    collector.record_budget_rejection("ws_01")

    # Retries: 3
    collector.record_retry(3)

    summary = collector.get_summary()
    assert summary["ai.request.count"] == 4
    assert summary["ai.failure.rate"] == 0.25
    assert summary["ai.cache.hit_rate"] == 0.6667
    assert summary["ai.router.escalation_rate"] == 0.25
    assert summary["ai.router.fallback_rate"] == 0.25
    assert summary["ai.budget.rejections"] == 2
    assert summary["ai.retry.count"] == 3


def test_latency_and_quality_samples(collector):
    collector.record_latency("google", "gemini-2.5-flash", 120.5)
    collector.record_latency("google", "gemini-2.5-flash", 145.2)
    collector.record_quality_score(0.94, "TEXT_GENERATION", "gemini-2.5-flash")

    # Check that sample lists are populated
    latency_key = ("ai.provider.latency", (("model", "gemini-2.5-flash"), ("provider", "google")))
    assert len(collector._samples[latency_key]) == 2

    quality_key = ("ai.quality.score", (("capability", "TEXT_GENERATION"), ("model", "gemini-2.5-flash")))
    assert collector._samples[quality_key] == [0.94]


def test_forbidden_high_cardinality_labels(collector):
    # Attempting to use forbidden high-cardinality keys (prompt, url, text) must raise HighCardinalityLabelError
    with pytest.raises(HighCardinalityLabelError) as exc_prompt:
        collector._validate_and_freeze_labels({"prompt": "User raw input prompt"})
    assert "forbidden due to high cardinality" in str(exc_prompt.value)

    with pytest.raises(HighCardinalityLabelError) as exc_url:
        collector._validate_and_freeze_labels({"full_url": "https://storage.provider.com/file?sig=xyz"})
    assert "forbidden due to high cardinality" in str(exc_url.value)

    # Attempting to use label value > 64 chars on custom label
    with pytest.raises(HighCardinalityLabelError) as exc_len:
        collector._validate_and_freeze_labels({"custom_key": "a" * 65})
    assert "exceeds maximum 64 character" in str(exc_len.value)
