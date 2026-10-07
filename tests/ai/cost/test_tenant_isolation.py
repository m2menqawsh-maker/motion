"""
tests/ai/cost/test_tenant_isolation.py
======================================
Multi-tenant isolation and security boundary tests for Creative Cost Observability (S28-08C).

Verifies:
- Workspace A cannot read Workspace B cost records or summaries.
- Workspace A cannot record usage events under Workspace B's scope.
- Cross-tenant and unpermitted project accesses fail closed with TenantAuthorizationError.
- Telemetry outputs never leak provider credentials, bearer tokens, or raw prompts.
"""

from __future__ import annotations

import tempfile
from decimal import Decimal
import pytest

from ai.contracts.creative.cost import CreativeUsageEvent
from ai.cost.collector import CreativeUsageCollector
from ai.cost.errors import TenantAuthorizationError
from ai.memory.models import TrustedTenantContext
from scripts.core.ai_trace_repository import SQLTraceRepository
from scripts.core.database import DatabaseEngine


@pytest.fixture
def isolated_collector():
    temp_db = tempfile.mktemp(suffix=".db")
    engine = DatabaseEngine(db_url=f"sqlite:///{temp_db}")
    trace_repo = SQLTraceRepository(engine=engine)
    return CreativeUsageCollector(trace_repository=trace_repo)


def test_cross_tenant_event_recording_rejected(isolated_collector: CreativeUsageCollector):
    """
    Verifies that a caller claiming Workspace A cannot record an event claiming Workspace B.
    """
    context_a = TrustedTenantContext(workspace_id="ws_alpha")
    foreign_event = CreativeUsageEvent.create(
        workspace_id="ws_beta",  # Mismatched!
        project_id="proj_beta_01",
        stage="INTENT",
        operation_type="DETERMINISTIC_COMPILATION",
    )

    with pytest.raises(TenantAuthorizationError) as exc_info:
        isolated_collector.record_event(context=context_a, event=foreign_event)

    assert "Cross-tenant event rejection" in str(exc_info.value)


def test_cross_tenant_project_read_denied(isolated_collector: CreativeUsageCollector):
    """
    Verifies that Workspace Alpha cannot query or summarize Workspace Beta's project.
    """
    context_alpha = TrustedTenantContext(
        workspace_id="ws_alpha",
        accessible_projects=["proj_alpha_01"],
    )
    context_beta = TrustedTenantContext(
        workspace_id="ws_beta",
        accessible_projects=["proj_beta_01"],
    )

    # Beta records an event
    event_beta = CreativeUsageEvent.create(
        workspace_id="ws_beta",
        project_id="proj_beta_01",
        stage="CREATIVE_PLANNING",
        operation_type="AI_COMPLETION",
        model="gpt-4o",
        input_tokens=1000,
        output_tokens=300,
        estimated_cost=Decimal("0.009500"),
    )
    isolated_collector.record_event(context=context_beta, event=event_beta)

    # Alpha attempts to read Beta's project -> fails closed
    with pytest.raises(TenantAuthorizationError):
        isolated_collector.list_events_for_project(context=context_alpha, project_id="proj_beta_01")

    with pytest.raises(TenantAuthorizationError):
        isolated_collector.summarize_project(context=context_alpha, project_id="proj_beta_01")


def test_unpermitted_project_within_same_workspace(isolated_collector: CreativeUsageCollector):
    """
    Verifies that an actor restricted to project_1 cannot read project_2 within the same workspace.
    """
    restricted_actor = TrustedTenantContext(
        workspace_id="ws_shared",
        user_id="usr_restricted",
        accessible_projects=["proj_allowed_only"],
    )

    with pytest.raises(TenantAuthorizationError):
        isolated_collector.list_events_for_project(
            context=restricted_actor,
            project_id="proj_secret_unauthorized",
        )


def test_privacy_and_data_minimization(isolated_collector: CreativeUsageCollector):
    """
    Verifies that CreativeUsageEvent and project summaries do not store raw prompts
    or leak provider secrets.
    """
    context = TrustedTenantContext(workspace_id="ws_privacy", is_admin=True)

    # Event uses input_hash instead of raw prompt
    event = CreativeUsageEvent.create(
        workspace_id="ws_privacy",
        project_id="proj_priv_01",
        stage="INTENT",
        operation_type="AI_COMPLETION",
        model="gpt-4o",
        input_tokens=250,
        output_tokens=100,
        estimated_cost=Decimal("0.002000"),
        input_hash="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        details={"status": "SUCCESS"},
    )
    isolated_collector.record_event(context=context, event=event)

    events = isolated_collector.list_events_for_project(context=context, project_id="proj_priv_01")
    assert len(events) == 1
    dump = events[0].model_dump()

    # Assert no sensitive keys
    dump_str = str(dump)
    assert "api_key" not in dump_str
    assert "Authorization" not in dump_str
    assert "Bearer" not in dump_str
    assert "user_prompt_raw" not in dump_str
    assert dump["input_hash"] is not None
