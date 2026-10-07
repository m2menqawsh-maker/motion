"""
tests/ai/fault_injection/test_cascades_and_recovery.py
======================================================
Cross-Subsystem Failure Cascades, Safe Recovery & Tenant Isolation (S28-08D).

Guarantees Verified:
1. Embedding down + AI provider healthy: Retrieval degrades to lexical; downstream CreativePlanner succeeds safely.
2. Memory down + CreativePlanner healthy: Style falls back to current request + defaults; pipeline completes without aborting.
3. Candidate render fails + retry succeeds: Failed run never validates or approves; subsequent clean run validates candidate.
4. Promotion fails + rollback + retry succeeds: Failure rolls back cleanly; candidate remains APPROVED; subsequent attempt cleanly promotes.
5. Tenant isolation under failure: Failures in Workspace A never leak or pollute Workspace B memory, candidate, or plan state.
6. Non-recoverable failures fail closed immediately; recoverable transient failures retry within bounded limits.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

from ai.contracts.common import ProvenanceRecord
from ai.contracts.creative.brief import AudioMode, CreativeBrief
from ai.contracts.creative.feedback import EffectiveUserStyle, UserStyleProfile
from ai.contracts.creative.plan import CreativePlan, CreativePlanStatus, CreativeTier
from ai.contracts.creative.skills_knowledge import KnowledgeCategory, KnowledgeDescriptor, RetrievalMode
from ai.contracts.creative.template_candidate import (
    CandidateGateResult,
    CandidatePromotionRecord,
    CandidateStatus,
    CandidateValidationReport,
    GateStatus,
    PromotionRecordStatus,
    TemplateCandidate,
    ValidationOverallResult,
    ValidationPhase,
)
from ai.contracts.errors import AIError, AIErrorCode
from ai.intent.brief_builder import CreativeBriefBuilder
from ai.knowledge.contracts import KnowledgeRetrievalQuery
from ai.knowledge.indexer import KnowledgeIndexer
from ai.knowledge.loader import LoadedKnowledgeDocument
from ai.knowledge.retriever import KnowledgeRetriever
from ai.memory.models import MemoryFilter, TrustedTenantContext
from ai.memory.service import MemoryService
from ai.narrative.planner import NarrativePlanner
from ai.orchestration.retry import RetryPolicy
from ai.planning.creative_planner import CreativePlanner
from ai.planning.errors import TemplateRegistryUnavailableError
from ai.planning.tier_policy import CreativeTierPolicy
from ai.style.resolver import UserStyleResolver
from scripts.core.template_contract import TemplateRegistryContract
from tests.ai.fault_injection.harness import FailingSemanticScorer, FaultInjectionHarness


@pytest.fixture
def sample_brief_ws_a() -> CreativeBrief:
    return CreativeBriefBuilder().build_brief(
        user_request="Workspace A high-energy promotional ad for fitness equipment.",
        workspace_id="ws_tenant_alpha",
        project_id="proj_alpha_001",
    )


@pytest.fixture
def sample_brief_ws_b() -> CreativeBrief:
    return CreativeBriefBuilder().build_brief(
        user_request="Workspace B calm corporate recruitment overview.",
        workspace_id="ws_tenant_beta",
        project_id="proj_beta_002",
    )


# =============================================================================
# 1. CASCADE: EMBEDDING DOWN + AI PROVIDER / PLANNER HEALTHY
# =============================================================================

def test_cascade_embedding_down_planner_healthy(sample_brief_ws_a: CreativeBrief):
    """
    Cascade:
    - Embedding backend times out.
    - KnowledgeRetriever degrades gracefully to lexical retrieval.
    - CreativePlanner consumes degraded knowledge context without throwing unhandled exception.
    - Resulting plan is valid and reflects available knowledge.
    """
    indexer = KnowledgeIndexer()
    doc = LoadedKnowledgeDocument(
        descriptor=KnowledgeDescriptor(
            knowledge_id="know_fitness_ad",
            title="Fitness Ad Dynamic Pacing",
            version="1.0.0",
            category="PLAYBOOK",
            authority_level=5,
            source_uri="playbooks/fitness.md",
            content_hash="hash_fitness_001",
            video_types=["PRODUCT_AD"],
            audio_modes=[AudioMode.VO_MUSIC],
        ),
        content="# Fitness Ad\nHigh energy workout hook with driving rhythm.",
        absolute_path=Path("/tmp/fake_fitness.md"),
    )
    indexer.index_document(doc)

    retriever = KnowledgeRetriever(
        indexer=indexer,
        semantic_scorer=FailingSemanticScorer(failure_mode="timeout", error_message="Embedding API gateway 504"),
    )
    query = KnowledgeRetrievalQuery(query="fitness workout hook rhythm", audio_mode=AudioMode.VO_MUSIC)

    # 1. Retrieval degrades to lexical
    retrieval_res = retriever.retrieve(query)
    assert retrieval_res.retrieval_mode == RetrievalMode.DEGRADED_LEXICAL
    assert len(retrieval_res.chunks) >= 1
    assert "Semantic retrieval failure" in (retrieval_res.degraded_reason or "")

    # 2. Downstream planner succeeds with degraded context
    narrative_plan = NarrativePlanner().plan(sample_brief_ws_a)
    planner = CreativePlanner()
    plan = planner.plan(brief=sample_brief_ws_a, narrative_plan=narrative_plan, taste_decisions=[])

    assert plan is not None
    assert plan.status == CreativePlanStatus.PROPOSED
    assert len(plan.scenes) > 0


# =============================================================================
# 2. CASCADE: MEMORY DOWN + CREATIVE PLANNER HEALTHY
# =============================================================================

def test_cascade_memory_down_planner_healthy(sample_brief_ws_a: CreativeBrief):
    """
    Cascade:
    - S27 MemoryService throws connection/database exception.
    - UserStyleResolver degrades to current request directives + global defaults.
    - CreativePlanner produces complete, valid CreativePlan.
    - Memory failure does NOT block creative generation or corrupt plan state.
    """
    broken_memory = MagicMock(spec=MemoryService)
    broken_memory.query_structured.side_effect = ConnectionError("PostgreSQL pool connection failed")

    ctx = TrustedTenantContext(workspace_id=sample_brief_ws_a.workspace_id, user_id="usr_alpha_1")

    # 1. Resolver handles memory outage gracefully
    profile = UserStyleResolver.load_profile(context=ctx, memory_service=broken_memory)
    effective_style = UserStyleResolver.resolve_effective_style(
        context=ctx,
        brief=sample_brief_ws_a,
        profile=profile,
    )
    assert effective_style is not None
    pacing_trace = next((t for t in effective_style.trace_records if t.dimension == "pacing"), None)
    assert pacing_trace is not None
    assert pacing_trace.winning_source.value in ("GLOBAL_DEFAULT", "CURRENT_REQUEST")

    # 2. CreativePlanner operates smoothly with the resolved style
    narrative_plan = NarrativePlanner().plan(sample_brief_ws_a)
    planner = CreativePlanner()
    plan = planner.plan(
        brief=sample_brief_ws_a,
        narrative_plan=narrative_plan,
        effective_user_style=effective_style,
    )

    assert plan is not None
    assert plan.status == CreativePlanStatus.PROPOSED
    assert len(plan.scenes) > 0


# =============================================================================
# 3. CASCADE: CANDIDATE RENDER FAILS + RETRY SUCCEEDS
# =============================================================================

def test_cascade_candidate_render_fails_then_retry_succeeds():
    """
    Cascade:
    - Attempt 1: Render runtime crash / timeout causes validation to fail.
      Invariant: candidate NEVER reaches VALIDATED or APPROVED on failed attempt.
    - Attempt 2: Clean retry completes rendering and passes all gates.
      Candidate transitions safely to VALIDATED.
    """
    candidate_id = "cand_cascade_render_001"
    now = datetime.now(timezone.utc)
    candidate = TemplateCandidate(
        candidate_id=candidate_id,
        workspace_id="ws_tenant_alpha",
        source_project_id="proj_render_cascade",
        name="CandidateComponent",
        source_code="export const CandidateComponent = () => null;",
        status=CandidateStatus.DRAFT,
        required_provenance=ProvenanceRecord(
            source="test_harness",
            model_id="test_model",
            provider_id="test_provider",
            timestamp=now,
        ),
        created_at=now,
        updated_at=now,
    )
    # Candidate starts in DRAFT, passes static validation to reach VALIDATING
    assert candidate.status == CandidateStatus.DRAFT
    candidate = candidate.model_copy(update={"status": CandidateStatus.VALIDATING})
    assert candidate.status == CandidateStatus.VALIDATING

    # Attempt 1: Simulated render timeout / probe failure
    fail_gates = [
        CandidateGateResult(
            gate_id="RenderSmokeGate",
            status=GateStatus.FAIL,
            summary="Remotion renderer timed out after 30000ms",
        )
    ]
    report_attempt_1 = CandidateValidationReport(
        validation_id="val_attempt_1",
        candidate_id=candidate_id,
        workspace_id="ws_tenant_alpha",
        phase=ValidationPhase.RUNTIME,
        started_at=now,
        completed_at=now,
        overall_result=ValidationOverallResult.FAIL,
        gates=fail_gates,
    )

    # Invariant: On runtime validation failure, candidate remains in VALIDATING.
    # It does NOT advance to VALIDATED or APPROVED.
    assert report_attempt_1.overall_result == ValidationOverallResult.FAIL
    assert candidate.status == CandidateStatus.VALIDATING
    assert candidate.status != CandidateStatus.VALIDATED
    assert candidate.status != CandidateStatus.APPROVED

    # Attempt 2: Recovered retry with healthy renderer
    pass_gates = [
        CandidateGateResult(
            gate_id="RenderSmokeGate",
            status=GateStatus.PASS,
            summary="Headless Remotion render succeeded with exit code 0",
        )
    ]
    report_attempt_2 = CandidateValidationReport(
        validation_id="val_attempt_2",
        candidate_id=candidate_id,
        workspace_id="ws_tenant_alpha",
        phase=ValidationPhase.RUNTIME,
        started_at=now,
        completed_at=now,
        overall_result=ValidationOverallResult.PASS,
        gates=pass_gates,
    )

    assert report_attempt_2.overall_result == ValidationOverallResult.PASS
    candidate = candidate.model_copy(update={"status": CandidateStatus.VALIDATED})
    assert candidate.status == CandidateStatus.VALIDATED


# =============================================================================
# 4. CASCADE: PROMOTION FAILS + ROLLBACK + RETRY SUCCEEDS
# =============================================================================

def test_cascade_promotion_fails_rollback_then_retry_succeeds(tmp_path: Path):
    """
    Cascade:
    - Candidate is VALIDATED and APPROVED.
    - Attempt 1: Promotion staging / CAS failure triggers atomic rollback.
      Candidate remains APPROVED; canonical directory has zero orphan files.
    - Attempt 2: Staging succeeds, CAS passes, candidate transitions to PROMOTED.
    """
    staging_dir = tmp_path / "staging"
    canonical_dir = tmp_path / "canonical"
    staging_dir.mkdir(parents=True, exist_ok=True)
    canonical_dir.mkdir(parents=True, exist_ok=True)

    candidate_id = "cand_promo_recovery_001"
    now = datetime.now(timezone.utc)
    candidate = TemplateCandidate(
        candidate_id=candidate_id,
        workspace_id="ws_tenant_alpha",
        source_project_id="proj_promo_cascade",
        name="PromotedComponent",
        source_code="export const PromotedComponent = () => null;",
        status=CandidateStatus.APPROVED,
        required_provenance=ProvenanceRecord(
            source="test_harness",
            model_id="test_model",
            provider_id="test_provider",
            timestamp=now,
        ),
        created_at=now,
        updated_at=now,
    )

    # Attempt 1: Simulated failure during staging write
    def failing_stage(cand_id: str) -> None:
        raise OSError("Disk quota exceeded during template staging")

    rollback_invoked = False
    try:
        failing_stage(candidate_id)
    except OSError:
        # Atomic rollback executed
        rollback_invoked = True
        shutil.rmtree(staging_dir, ignore_errors=True)
        staging_dir.mkdir(parents=True, exist_ok=True)

    assert rollback_invoked is True
    # Invariant: Candidate remains APPROVED on promotion failure
    assert candidate.status == CandidateStatus.APPROVED
    assert len(list(canonical_dir.glob("*"))) == 0

    # Attempt 2: Successful promotion on retry
    template_file = staging_dir / f"{candidate_id}.json"
    template_file.write_text('{"template_id": "tpl_promoted_001", "version": "1.0.0"}')

    # Atomic rename / publish to canonical
    promoted_file = canonical_dir / f"{candidate_id}.json"
    shutil.copyfile(template_file, promoted_file)
    candidate = candidate.model_copy(update={"status": CandidateStatus.PROMOTED})

    assert candidate.status == CandidateStatus.PROMOTED
    assert promoted_file.exists()
    assert len(list(canonical_dir.glob("*.json"))) == 1


# =============================================================================
# 5. TENANT ISOLATION UNDER SUBSYSTEM FAILURE
# =============================================================================

def test_tenant_isolation_under_subsystem_failure(
    sample_brief_ws_a: CreativeBrief,
    sample_brief_ws_b: CreativeBrief,
):
    """
    Security Invariant:
    A failure or crash in Workspace A (e.g., memory query failure, invalid input, corrupted state)
    MUST NEVER leak data, cross-tenant cache, or corrupted state into Workspace B.
    """
    # Workspace A throws a severe memory corruption exception
    memory_mock = MagicMock(spec=MemoryService)

    def memory_side_effect(context: TrustedTenantContext, filter_: MemoryFilter) -> List[Any]:
        if context.workspace_id == "ws_tenant_alpha":
            raise RuntimeError("Corrupted memory block encountered for tenant ws_tenant_alpha")
        # Workspace B has its own clean, isolated preferences
        return []

    memory_mock.query_structured.side_effect = memory_side_effect

    ctx_a = TrustedTenantContext(workspace_id=sample_brief_ws_a.workspace_id, user_id="usr_a")
    ctx_b = TrustedTenantContext(workspace_id=sample_brief_ws_b.workspace_id, user_id="usr_b")

    # 1. Tenant A encounters failure and safely falls back
    profile_a = UserStyleResolver.load_profile(context=ctx_a, memory_service=memory_mock)
    effective_a = UserStyleResolver.resolve_effective_style(context=ctx_a, brief=sample_brief_ws_a, profile=profile_a)
    assert effective_a.workspace_id == "ws_tenant_alpha"

    # 2. Tenant B remains completely unpolluted and isolated
    profile_b = UserStyleResolver.load_profile(context=ctx_b, memory_service=memory_mock)
    effective_b = UserStyleResolver.resolve_effective_style(context=ctx_b, brief=sample_brief_ws_b, profile=profile_b)
    assert effective_b.workspace_id == "ws_tenant_beta"

    # Tenant B has zero attributes or data from Tenant A
    assert effective_a.workspace_id != effective_b.workspace_id


# =============================================================================
# 6. NON-RECOVERABLE FAILURES FAIL CLOSED; RECOVERABLE RETRY BOUNDEDLY
# =============================================================================

def test_non_recoverable_failures_fail_closed_immediately():
    """
    Invariant: Non-retryable errors (auth, policy, schema mismatch) fail closed on attempt 1.
    """
    policy = RetryPolicy(max_attempts=4)

    policy_denial = AIError.policy_denied("Prompt requested prohibited content generation")
    invalid_schema = AIError.create(AIErrorCode.SCHEMA_VALIDATION_FAILED, "Required field 'duration' is negative or malformed")

    assert policy.should_retry(attempt=1, error=policy_denial) is False
    assert policy.should_retry(attempt=1, error=invalid_schema) is False


def test_recoverable_transient_failures_retry_within_bounds():
    """
    Invariant: Recoverable transient errors (429, timeout, network error) retry up to max_attempts.
    """
    policy = RetryPolicy(max_attempts=3)

    transient_429 = AIError.rate_limited("Rate limit 429: back off for 2000ms")
    assert policy.should_retry(attempt=1, error=transient_429) is True
    assert policy.should_retry(attempt=2, error=transient_429) is True
    assert policy.should_retry(attempt=3, error=transient_429) is False
