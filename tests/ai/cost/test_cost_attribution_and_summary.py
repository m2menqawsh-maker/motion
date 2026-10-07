"""
tests/ai/cost/test_cost_attribution_and_summary.py
==================================================
Unit tests for CreativeUsageCollector and CreativeProjectCostSummary (S28-08C).

Verifies:
- Project-level aggregation and multi-dimensional breakdown.
- Strict epistemic separation between actual billed cost and estimated cost.
- Attribution of planning tokens, retrieval volume, AI calls, generation calls, and latency.
- Tier rate and average cost calculation (REUSE, COMPOSE, CREATE).
- Accounting for failed runs and retries without dropping telemetry.
"""

from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from decimal import Decimal
import pytest

from ai.contracts.creative.cost import (
    CostProvenance,
    CreativeUsageEvent,
)
from ai.cost.collector import CreativeUsageCollector
from ai.memory.models import TrustedTenantContext
from scripts.core.ai_trace_repository import SQLTraceRepository
from scripts.core.database import DatabaseEngine


@pytest.fixture
def isolated_collector():
    temp_db = tempfile.mktemp(suffix=".db")
    engine = DatabaseEngine(db_url=f"sqlite:///{temp_db}")
    trace_repo = SQLTraceRepository(engine=engine)
    return CreativeUsageCollector(trace_repository=trace_repo)


def test_project_cost_summary_aggregation(isolated_collector: CreativeUsageCollector):
    """
    Verifies that all events for a project are accurately aggregated and attributed.
    """
    context = TrustedTenantContext(workspace_id="ws_acme", is_admin=True)
    project_id = "proj_super_ad"
    now = datetime.now(timezone.utc)

    # 1. Planning call
    isolated_collector.record_event(
        context=context,
        event=CreativeUsageEvent.create(
            workspace_id="ws_acme",
            project_id=project_id,
            run_id="run_01",
            stage="CREATIVE_PLANNING",
            subsystem="creative_planner",
            operation_type="AI_COMPLETION",
            provider="openai",
            model="gpt-4o",
            input_tokens=1500,
            output_tokens=500,
            latency_ms=850.0,
            cost_provenance=CostProvenance.ESTIMATED,
            estimated_cost=Decimal("0.015000"),
            pricing_version="2026.09.v1",
            details={"status": "SUCCESS"},
        ),
    )

    # 2. Knowledge Retrieval
    isolated_collector.record_event(
        context=context,
        event=CreativeUsageEvent.create(
            workspace_id="ws_acme",
            project_id=project_id,
            run_id="run_01",
            stage="KNOWLEDGE_RETRIEVAL",
            subsystem="knowledge_router",
            operation_type="RETRIEVAL",
            retrieval_items=4,
            latency_ms=60.0,
            cost_provenance=CostProvenance.ESTIMATED,
            estimated_cost=Decimal("0.000000"),
            details={"retrieved_ids": ["doc_1", "doc_2", "doc_3", "doc_4"]},
        ),
    )

    # 3. Tier decisions: 2 scenes REUSE, 1 scene COMPOSE
    isolated_collector.record_event(
        context=context,
        event=CreativeUsageEvent.create(
            workspace_id="ws_acme",
            project_id=project_id,
            run_id="run_01",
            stage="TIER_DECISION",
            subsystem="reuse_engine",
            operation_type="DETERMINISTIC_COMPILATION",
            latency_ms=10.0,
            cost_provenance=CostProvenance.ESTIMATED,
            estimated_cost=Decimal("0.000000"),
            details={"tier": "REUSE", "template_id": "tmpl_counter"},
        ),
    )
    isolated_collector.record_event(
        context=context,
        event=CreativeUsageEvent.create(
            workspace_id="ws_acme",
            project_id=project_id,
            run_id="run_01",
            stage="TIER_DECISION",
            subsystem="reuse_engine",
            operation_type="DETERMINISTIC_COMPILATION",
            latency_ms=8.0,
            cost_provenance=CostProvenance.ESTIMATED,
            estimated_cost=Decimal("0.000000"),
            details={"tier": "REUSE", "template_id": "tmpl_header"},
        ),
    )
    isolated_collector.record_event(
        context=context,
        event=CreativeUsageEvent.create(
            workspace_id="ws_acme",
            project_id=project_id,
            run_id="run_01",
            stage="TIER_DECISION",
            subsystem="compose_engine",
            operation_type="DETERMINISTIC_COMPILATION",
            latency_ms=15.0,
            cost_provenance=CostProvenance.ESTIMATED,
            estimated_cost=Decimal("0.000000"),
            details={"tier": "COMPOSE", "components": ["title", "graphic"]},
        ),
    )

    # 4. Generate summary
    summary = isolated_collector.summarize_project(context=context, project_id=project_id)

    assert summary.workspace_id == "ws_acme"
    assert summary.project_id == project_id
    assert summary.run_count == 1
    assert summary.ai_calls == 1
    assert summary.planning_tokens == 2000  # 1500 + 500
    assert summary.retrieval_tokens == 4
    assert summary.reuse_count == 2
    assert summary.compose_count == 1
    assert summary.create_count == 0
    assert summary.estimated_cost == Decimal("0.015000")
    assert summary.actual_cost == Decimal("0.000000")
    assert summary.total_latency_ms == 943.0

    # Tier breakdown
    tb = summary.tier_breakdown
    assert tb["REUSE"]["count"] == 2
    assert tb["REUSE"]["rate"] == round(2 / 3, 4)
    assert tb["COMPOSE"]["count"] == 1
    assert tb["COMPOSE"]["rate"] == round(1 / 3, 4)
    assert tb["CREATE"]["count"] == 0

    # Model and stage breakdown
    assert "gpt-4o" in summary.model_breakdown
    assert summary.model_breakdown["gpt-4o"]["calls"] == 1
    assert "CREATIVE_PLANNING" in summary.stage_breakdown
    assert summary.stage_breakdown["CREATIVE_PLANNING"]["input_tokens"] == 1500


def test_failed_run_and_retry_accounting(isolated_collector: CreativeUsageCollector):
    """
    Verifies that costs from failed and retried runs are tracked and distinguished.
    """
    context = TrustedTenantContext(workspace_id="ws_beta", is_admin=True)
    project_id = "proj_flaky"

    # Attempt 1: Failed call ($0.010000)
    isolated_collector.record_event(
        context=context,
        event=CreativeUsageEvent.create(
            workspace_id="ws_beta",
            project_id=project_id,
            run_id="run_fail_01",
            stage="CREATIVE_PLANNING",
            operation_type="AI_COMPLETION",
            model="gpt-4o",
            input_tokens=1000,
            output_tokens=0,
            cost_provenance=CostProvenance.ESTIMATED,
            estimated_cost=Decimal("0.005000"),
            details={"status": "FAILED", "error": "TimeoutError"},
        ),
    )

    # Attempt 2: Retry call ($0.015000)
    isolated_collector.record_event(
        context=context,
        event=CreativeUsageEvent.create(
            workspace_id="ws_beta",
            project_id=project_id,
            run_id="run_fail_01",
            stage="CREATIVE_PLANNING",
            operation_type="AI_COMPLETION",
            model="gpt-4o",
            input_tokens=1000,
            output_tokens=400,
            cost_provenance=CostProvenance.ESTIMATED,
            estimated_cost=Decimal("0.011000"),
            details={"status": "SUCCESS", "is_retry": True, "retry_count": 1},
        ),
    )

    # Succeeded run 02 ($0.020000)
    isolated_collector.record_event(
        context=context,
        event=CreativeUsageEvent.create(
            workspace_id="ws_beta",
            project_id=project_id,
            run_id="run_ok_02",
            stage="CREATIVE_PLANNING",
            operation_type="AI_COMPLETION",
            model="gpt-4o",
            input_tokens=1500,
            output_tokens=500,
            cost_provenance=CostProvenance.ESTIMATED,
            estimated_cost=Decimal("0.015000"),
            details={"status": "SUCCESS"},
        ),
    )

    summary = isolated_collector.summarize_project(context=context, project_id=project_id)
    sb = summary.status_breakdown

    assert Decimal(sb["failed_runs_cost"]) == Decimal("0.005000")
    assert Decimal(sb["retried_runs_cost"]) == Decimal("0.011000")
    assert Decimal(sb["successful_runs_cost"]) == Decimal("0.015000")
    assert summary.estimated_cost == Decimal("0.031000")
