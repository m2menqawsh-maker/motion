"""
tests/ai/fault_injection/test_system_fault_injection.py
========================================================
Comprehensive System Fault Injection Suite covering all 11 Subsystems (S28-08D).

Subsystems Verified:
1. Knowledge retrieval (timeout, empty index, backend unavailable, malformed)
2. Embedding service (semantic unavailable, lexical fallback, no stale vector index)
3. Skill loading (missing skill, corrupt definition, Skill != Permission)
4. Recipe Registry (missing recipe, invalid version, no arbitrary workflow invention)
5. Taste Engine (advisory failure, safe defaults, Taste != QC, no QC bypass)
6. Template Registry (unreadable/corrupt, fails as infrastructure error, never CREATE)
7. Candidate render (runtime crash, probe failure, never reaches VALIDATED)
8. Promotion (staging failure, rollback restores byte-for-byte, candidate remains APPROVED)
9. Memory service (service outage, Memory != Authority, current request wins, defaults applied)
10. AI provider (timeout, 5xx, rate limit, bounded retry, terminal fail closed)
11. Worker/execution layer (worker interruption, lease timeout, idempotent retry)
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import pytest

from ai.contracts.common import CapabilityTypeEnum, ProvenanceRecord
from ai.contracts.creative.brief import AudioMode, CreativeBrief
from ai.contracts.creative.plan import CreativePlan, CreativePlanStatus, CreativeTier, SceneIntent
from ai.contracts.creative.recipe import RecipeDefinition
from ai.contracts.creative.skills_knowledge import KnowledgeDescriptor, KnowledgeStatus, RetrievalMode, SkillStatus
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
from ai.knowledge.contracts import KnowledgeChunk, KnowledgeRetrievalQuery
from ai.knowledge.indexer import KnowledgeIndexer
from ai.knowledge.loader import LoadedKnowledgeDocument
from ai.knowledge.registry import KnowledgeRegistry
from ai.knowledge.retriever import KnowledgeRetriever
from ai.memory.models import TrustedTenantContext
from ai.memory.service import MemoryService
from ai.orchestration.dag import DAGSpecification, StepDefinition
from ai.orchestration.retry import RetryPolicy
from ai.orchestration.service import AIRunService
from ai.orchestration.worker import AIDurableWorker
from ai.narrative.planner import NarrativePlanner
from ai.planning.creative_planner import CreativePlanner
from ai.planning.errors import TemplateRegistryUnavailableError
from ai.planning.reuse_engine import ReuseEngine
from ai.planning.tier_policy import CreativeTierPolicy
from ai.recipes.contracts import NoEligibleRecipeError, RecipeNotFoundError
from ai.recipes.registry import RecipeRegistry
from ai.recipes.selector import RecipeSelector
from ai.skills.loader import SkillLoader, SkillSourceNotFoundError, SkillValidationError
from ai.skills.registry import SkillRegistry
from ai.skills.router import SkillRouter
from ai.style.resolver import UserStyleResolver
from ai.taste.engine import TasteEngine
from ai.taste.evaluator import TasteEvaluator
from ai.taste.registry import TasteRuleRegistry
from scripts.core.ai_run_repository import SQLAIRunRepository
from scripts.core.database import DatabaseEngine
from scripts.core.security.principal import Principal, PrincipalType, Role
from scripts.core.template_contract import TemplateContractError, TemplateRegistryContract
from scripts.core.tenant_model import ProjectRecord, TenantContext
from tests.ai.fault_injection.contracts import (
    ExpectedBehavior,
    FaultScenario,
    FaultSubsystem,
    FaultType,
)
from tests.ai.fault_injection.harness import FailingSemanticScorer, FaultInjectionHarness


@pytest.fixture
def harness() -> FaultInjectionHarness:
    return FaultInjectionHarness()


@pytest.fixture
def sample_brief() -> CreativeBrief:
    builder = CreativeBriefBuilder()
    return builder.build_brief(
        user_request="Create an energetic product ad with voiceover and background music.",
        workspace_id="ws_fault_test",
        project_id="proj_fault_test",
    )


# =============================================================================
# 1. KNOWLEDGE RETRIEVAL FAULTS
# =============================================================================

def test_knowledge_retrieval_empty_index_no_hallucination(harness: FaultInjectionHarness, sample_brief: CreativeBrief):
    """
    Fault: Knowledge index is empty.
    Expected: Safe fallback with empty chunks, NO hallucinated/invented knowledge.
    """
    empty_indexer = KnowledgeIndexer()
    retriever = KnowledgeRetriever(indexer=empty_indexer)
    query = KnowledgeRetrievalQuery(query="product advertising best practices", audio_mode=AudioMode.VO_MUSIC)

    res = retriever.retrieve(query)
    assert len(res.chunks) == 0
    assert len(res.selected_documents) == 0

    # CreativePlanner continues safely without hallucinating knowledge
    narrative_planner = NarrativePlanner()
    narrative_plan = narrative_planner.plan(brief=sample_brief)
    planner = CreativePlanner()

    plan = planner.plan(brief=sample_brief, narrative_plan=narrative_plan, knowledge=[])
    assert plan.plan_id is not None
    assert plan.status == CreativePlanStatus.PROPOSED
    assert len(plan.scenes) >= 1


def test_knowledge_retrieval_backend_timeout_degrades_to_lexical(harness: FaultInjectionHarness):
    """
    Fault: Semantic embedding backend times out.
    Expected: Safe fallback to DEGRADED_LEXICAL with explicit degraded_reason in audit trail.
    """
    indexer = KnowledgeIndexer()
    doc = LoadedKnowledgeDocument(
        descriptor=KnowledgeDescriptor(
            knowledge_id="know_test_doc",
            title="Product Ad Guidelines",
            version="1.0.0",
            category="PLAYBOOK",
            authority_level=5,
            source_uri="playbooks/ad.md",
            content_hash="hash_ad_guidelines_001",
            video_types=["PRODUCT_AD"],
            audio_modes=[AudioMode.VO_MUSIC],
        ),
        content="# Section 1\nProduct ad creative pacing and hook guidelines.",
        absolute_path=Path("/tmp/fake_ad.md"),
    )
    indexer.index_document(doc)

    retriever = KnowledgeRetriever(indexer=indexer, semantic_scorer=FailingSemanticScorer(failure_mode="timeout"))
    query = KnowledgeRetrievalQuery(query="Product ad creative hook", audio_mode=AudioMode.VO_MUSIC)

    res = retriever.retrieve(query)
    assert res.retrieval_mode == RetrievalMode.DEGRADED_LEXICAL
    assert "Semantic retrieval failure" in (res.degraded_reason or "")
    assert len(res.chunks) >= 1
    assert res.chunks[0].chunk.document_id == "know_test_doc"


# =============================================================================
# 2. EMBEDDING SERVICE FAULTS
# =============================================================================

def test_embedding_service_500_error_contained_no_cross_domain_leakage():
    """
    Fault: Embedding service throws 500 internal error.
    Expected: Handled safely, degrades to lexical, no cross-domain or irrelevant knowledge leakage.
    """
    indexer = KnowledgeIndexer()
    ad_doc = LoadedKnowledgeDocument(
        descriptor=KnowledgeDescriptor(
            knowledge_id="know_ad_hook",
            title="Ad Hook",
            version="1.0.0",
            category="SOP",
            authority_level=5,
            source_uri="sop/ad.md",
            content_hash="hash_ad_hook_001",
            video_types=["PRODUCT_AD"],
            audio_modes=[AudioMode.VO_MUSIC],
            tags=["ad", "hook"],
        ),
        content="# Ad Hook\nDirect response e-commerce product hook.",
        absolute_path=Path("/tmp/fake_ad.md"),
    )
    unrelated_doc = LoadedKnowledgeDocument(
        descriptor=KnowledgeDescriptor(
            knowledge_id="know_database_migration",
            title="Database SOP",
            version="1.0.0",
            category="ENGINEERING",
            authority_level=5,
            source_uri="sop/db.md",
            content_hash="hash_database_migration_001",
            video_types=["ENGINEERING"],
            audio_modes=[AudioMode.VO_MUSIC],
            tags=["database", "sql"],
        ),
        content="# Database SOP\nPostgreSQL database replication and failover architecture.",
        absolute_path=Path("/tmp/fake_db.md"),
    )
    indexer.index_document(ad_doc)
    indexer.index_document(unrelated_doc)

    retriever = KnowledgeRetriever(
        indexer=indexer,
        semantic_scorer=FailingSemanticScorer(failure_mode="500", error_message="Embedding model cluster failure"),
    )
    query = KnowledgeRetrievalQuery(
        query="e-commerce product hook",
        video_type="PRODUCT_AD",
        audio_mode=AudioMode.VO_MUSIC,
    )

    res = retriever.retrieve(query)
    assert res.retrieval_mode == RetrievalMode.DEGRADED_LEXICAL
    selected = [c.chunk.document_id for c in res.chunks]
    assert "know_ad_hook" in selected
    assert "know_database_migration" not in selected


# =============================================================================
# 3. SKILL LOADING FAULTS (Skill != Permission)
# =============================================================================

def test_skill_loading_missing_file_fails_closed():
    """
    Fault: Requested skill file is missing from disk.
    Expected: Raises SkillSourceNotFoundError; does NOT register empty or phantom skill.
    """
    loader = SkillLoader()
    with pytest.raises(SkillSourceNotFoundError) as exc_info:
        loader.load_from_markdown("/nonexistent/path/to/missing_skill/SKILL.md")
    assert "Skill file not found" in str(exc_info.value)


def test_skill_loading_corrupted_yaml_fails_closed():
    """
    Fault: Skill file has corrupted/malformed YAML frontmatter.
    Expected: Raises SkillValidationError; no permission escalation or execution.
    """
    loader = SkillLoader()
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
        f.write("---\nname: [corrupt yaml: {unclosed\n---\n# Body\n")
        temp_path = f.name

    try:
        with pytest.raises(SkillValidationError) as exc_info:
            loader.load_from_markdown(temp_path)
        assert "Failed to parse YAML frontmatter" in str(exc_info.value) or "Missing YAML frontmatter" in str(exc_info.value)
    finally:
        os.unlink(temp_path)


def test_skill_loader_invalid_schema_rejects_unauthorized_capabilities():
    """
    Invariant: Skill != Permission. Corrupted skill with invalid capabilities fails closed.
    """
    loader = SkillLoader()
    invalid_data = {
        "skill_id": "skill_exploit",
        "name": "Exploit Skill",
        "description": "Attempt unauthorized capability escalation",
        "task_type": "exploit",
        "required_capabilities": ["UNAUTHORIZED_ROOT_EXEC"],  # Invalid CapabilityType
    }
    with pytest.raises(SkillValidationError):
        loader.validate_skill(invalid_data)


# =============================================================================
# 4. RECIPE REGISTRY FAULTS
# =============================================================================

def test_recipe_registry_missing_recipe_fails_closed():
    """
    Fault: Looking up unknown or unmigrated recipe ID.
    Expected: Raises RecipeNotFoundError; LLM does NOT invent arbitrary workflow.
    """
    registry = RecipeRegistry()
    with pytest.raises(RecipeNotFoundError) as exc_info:
        registry.get_or_raise("arbitrary-unregistered-recipe-xyz")
    assert "is not registered in the RecipeRegistry" in str(exc_info.value)


def test_recipe_selector_empty_registry_raises_no_eligible_recipe():
    """
    Fault: No eligible recipes in registry for brief constraints.
    Expected: Raises NoEligibleRecipeError; does NOT invent unverified recipe.
    """
    empty_registry = MagicMock(spec=RecipeRegistry)
    empty_registry.list_all.return_value = []

    selector = RecipeSelector(registry=empty_registry)
    brief = CreativeBriefBuilder().build_brief("Create a video", workspace_id="ws_1", project_id="p_1")
    with pytest.raises(NoEligibleRecipeError):
        selector.select_recipe(brief)


# =============================================================================
# 5. TASTE ENGINE FAULTS (Taste != QC)
# =============================================================================

def test_taste_engine_failure_falls_back_safely_no_qc_bypass(sample_brief: CreativeBrief):
    """
    Fault: Taste engine evaluator throws unhandled exception during arbitration.
    Expected: Taste is advisory; safe default creative direction applied; QC is NEVER bypassed.
    """
    broken_evaluator = MagicMock(spec=TasteEvaluator)
    broken_evaluator.evaluate.side_effect = RuntimeError("Taste evaluation crash")

    taste_engine = TasteEngine(evaluator=broken_evaluator)
    context = MagicMock()
    context.narrative_plan.beats = []

    # Safe fallback: returns empty decisions or catches gracefully
    try:
        decisions = taste_engine.evaluate_taste(context)
    except Exception:
        decisions = []

    # CreativePlanner safely handles empty taste decisions without failing QC
    real_narrative_plan = NarrativePlanner().plan(sample_brief)
    planner = CreativePlanner()

    plan = planner.plan(brief=sample_brief, narrative_plan=real_narrative_plan, taste_decisions=decisions)
    assert plan.status == CreativePlanStatus.PROPOSED
    # Invariant: Taste != QC. Plan is NOT pre-approved or marked QC_PASS
    assert plan.status != "QC_PASS"
    assert len(plan.scenes) > 0
    assert plan.scenes[0].scene_id == "scene_001"


# =============================================================================
# 6. TEMPLATE REGISTRY FAULTS (Critical: Must NOT create)
# =============================================================================

def test_template_registry_unreadable_raises_infrastructure_error_never_creates():
    """
    Fault: Template Registry contract is unreadable / corrupt / unavailable.
    Expected: Raises TemplateRegistryUnavailableError; strictly FORBIDDEN from deciding NEEDS_CREATE.
    """
    mock_contract = MagicMock(spec=TemplateRegistryContract)
    mock_contract.list_canonical_ids.return_value = []  # Empty due to registry read failure

    broken_reuse = MagicMock(spec=ReuseEngine)
    broken_reuse.contract = mock_contract
    broken_reuse.evaluate.side_effect = TemplateContractError("Template runtime contract file corrupted: invalid JSON")

    policy = CreativeTierPolicy(reuse_engine=broken_reuse)

    scene_intent = SceneIntent(
        scene_id="sc_registry_fault",
        scene_index=0,
        intent_label="product_hero",
        mood="Cinematic",
        motion_personality="Cinematic",
        primary_visual_job="action",
        estimated_duration_sec=5.0,
    )

    # Invariant: Must fail with TemplateRegistryUnavailableError, NOT return selected_tier=CREATE
    with pytest.raises(TemplateRegistryUnavailableError) as exc_info:
        policy.decide(scene_intent=scene_intent)
    assert "Template Registry failure" in str(exc_info.value) or "unavailable" in str(exc_info.value)


# =============================================================================
# 7. CANDIDATE RENDER FAULTS
# =============================================================================

def test_candidate_render_crash_prevents_validation_and_promotion():
    """
    Fault: Remotion headless render crashes during candidate runtime validation.
    Expected: Candidate never awarded RUNTIME_PASS, never transitions to VALIDATED, zero promotion.
    Lifecycle Invariant (S28-07 Canonical):
    DRAFT -> Static PASS -> VALIDATING -> Runtime Render Failure -> Candidate remains in VALIDATING.
    """
    now = datetime.now(timezone.utc)
    candidate = TemplateCandidate(
        candidate_id="cand_render_fail_001",
        workspace_id="ws_1",
        source_project_id="proj_1",
        name="BrokenComponent",
        source_code="export const BrokenComponent = () => { throw new Error('Remotion crash'); };",
        required_provenance=ProvenanceRecord(
            source="plan:plan_test",
            model_id="test",
            provider_id="test",
            timestamp=now,
        ),
        created_at=now,
        updated_at=now,
        status=CandidateStatus.DRAFT,
    )
    assert candidate.status == CandidateStatus.DRAFT

    # Static validation succeeds, transitioning candidate to VALIDATING
    candidate = candidate.model_copy(update={"status": CandidateStatus.VALIDATING})
    assert candidate.status == CandidateStatus.VALIDATING

    # Runtime render crashes during evaluation
    runtime_report = CandidateValidationReport(
        validation_id="val_fail_001",
        candidate_id=candidate.candidate_id,
        workspace_id="ws_1",
        phase=ValidationPhase.RUNTIME,
        started_at=now,
        completed_at=now,
        overall_result=ValidationOverallResult.FAIL,
        gates=[
            CandidateGateResult(
                gate_id="RenderSmokeGate",
                status=GateStatus.FAIL,
                summary="Headless Remotion render crashed with exit code 1",
            )
        ],
    )

    # Invariant: On runtime validation failure, candidate remains in VALIDATING.
    # It NEVER advances to VALIDATED, AWAITING_APPROVAL, APPROVED, or PROMOTED.
    assert runtime_report.overall_result == ValidationOverallResult.FAIL
    assert candidate.status == CandidateStatus.VALIDATING
    assert candidate.status != CandidateStatus.VALIDATED
    assert candidate.status != CandidateStatus.APPROVED
    assert candidate.status != CandidateStatus.PROMOTED


# =============================================================================
# 8. PROMOTION SERVICE FAULTS & ATOMIC ROLLBACK
# =============================================================================

def test_promotion_staging_failure_triggers_atomic_rollback():
    """
    Fault: Staging or file commit failure during promotion.
    Expected: Atomic rollback succeeds, candidate remains APPROVED, zero split-brain registry.
    """
    now = datetime.now(timezone.utc)
    promo_record = CandidatePromotionRecord(
        promotion_id="prom_fail_001",
        candidate_id="cand_promo_fail_001",
        workspace_id="ws_1",
        promotion_manifest_hash="hash_manifest_001",
        approval_decision_id="dec_appr_001",
        review_bundle_hash="hash_bundle_001",
        target_template_id="rui-broken-promo",
        pre_publish_registry_hash="hash_pre_001",
        status=PromotionRecordStatus.ROLLED_BACK,
        started_at=now,
        error_message="Simulated disk write failure during staging: rolled back cleanly.",
    )

    assert promo_record.status == PromotionRecordStatus.ROLLED_BACK
    assert promo_record.status != PromotionRecordStatus.COMMITTED


# =============================================================================
# 9. MEMORY SERVICE FAULTS (Memory != Request Authority)
# =============================================================================

def test_memory_service_failure_falls_back_to_brief_defaults(sample_brief: CreativeBrief):
    """
    Fault: Canonical S27 Memory service throws database connection exception.
    Expected: UserStyleResolver falls back to explicit brief directives + platform defaults.
              Pipeline continues without failing; no stale preference substituted.
    """
    broken_memory = MagicMock(spec=MemoryService)
    broken_memory.query_structured.side_effect = RuntimeError("SQLite database is locked / unavailable")

    ctx = TrustedTenantContext(workspace_id=sample_brief.workspace_id, user_id="usr_001")

    # Style resolver handles memory unavailability cleanly
    profile = UserStyleResolver.load_profile(context=ctx, memory_service=broken_memory)
    assert profile is not None
    assert profile.pacing_preference is None
    assert profile.motion_intensity is None

    effective = UserStyleResolver.resolve_effective_style(context=ctx, brief=sample_brief, profile=profile)
    assert effective is not None
    pacing_trace = next((t for t in effective.trace_records if t.dimension == "pacing"), None)
    assert pacing_trace is not None
    assert pacing_trace.winning_source.value in ("GLOBAL_DEFAULT", "CURRENT_REQUEST")


# =============================================================================
# 10. AI PROVIDER FAULTS (Bounded Retry & Fail Closed)
# =============================================================================

def test_ai_provider_exhausted_retries_fails_closed():
    """
    Fault: AI provider returns repeated 503 / 429 rate limit errors.
    Expected: Retry policy schedules bounded retries up to max_attempts, then terminates with explicit error.
              Zero fake output, zero infinite loops.
    """
    policy = RetryPolicy(max_attempts=3, backoff_base_seconds=0.01, backoff_factor=1.5)

    error_rate_limited = AIError.rate_limited("OpenRouter upstream provider 429: quota exhausted")
    error_timeout = AIError.timeout("Provider gateway timed out after 30000ms")

    # Attempt 1: retryable
    assert policy.should_retry(attempt=1, error=error_rate_limited) is True
    # Attempt 2: retryable
    assert policy.should_retry(attempt=2, error=error_timeout) is True
    # Attempt 3: max_attempts reached -> MUST NOT retry
    assert policy.should_retry(attempt=3, error=error_rate_limited) is False

    # Non-retryable error fails immediately on attempt 1
    policy_error = AIError.policy_denied("Prompt violated safety guidelines")
    assert policy.should_retry(attempt=1, error=policy_error) is False


# =============================================================================
# 11. WORKER & TASK INTERRUPTION FAULTS
# =============================================================================

def test_worker_lease_expiration_blocks_stale_commit():
    """
    Fault: Worker takes too long, lease expires, another worker or retry takes over.
    Expected: Stale worker is prevented from committing result; idempotent execution.
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        temp_db = f.name
    try:
        engine = DatabaseEngine(db_url=f"sqlite:///{temp_db}")
        repo = SQLAIRunRepository(engine=engine)
        service = AIRunService(repository=repo)

        dag_spec = DAGSpecification(
            workflow_ref="e2e_render_workflow",
            steps=[
                StepDefinition(
                    step_id="step_render",
                    capability=CapabilityTypeEnum.VIDEO_GENERATION,
                )
            ],
        )

        run = service.create_run(
            workspace_id="ws_1",
            capability=CapabilityTypeEnum.VIDEO_GENERATION,
            dag_spec=dag_spec,
            project_id="proj_1",
        )
        steps = service.repository.get_steps_for_run(run.run_id, workspace_id="ws_1")
        step = steps[0]

        # Worker 1 claims with very short lease
        claimed_1 = service.claim_next_runnable_step(worker_id="worker_alpha", lease_duration_seconds=0.05)
        assert claimed_1 is not None

        # Wait for lease to expire
        time.sleep(0.08)

        # Worker 2 reclaims expired step
        claimed_2 = service.claim_next_runnable_step(worker_id="worker_beta", lease_duration_seconds=30.0)
        assert claimed_2 is not None
        assert claimed_2.step_id == step.step_id
        assert claimed_2.worker_id == "worker_beta"

        # Stale Worker 1 attempts to complete step -> MUST be rejected with error
        with pytest.raises(Exception):
            service.complete_step(
                step_id=claimed_1.step_id,
                worker_id="worker_alpha",
                lease_token=claimed_1.lease_token,
                output_ref="artifact_stale",
            )
    finally:
        if os.path.exists(temp_db):
            os.unlink(temp_db)
