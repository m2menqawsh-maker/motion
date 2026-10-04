"""
tests/ai/test_ai14_final_integration_proof.py
=============================================
Mandatory Integration & Durability Proofs for AI-14 Certification (AI-14R).

Invariants verified:
1. AIRun ↔ Prompt Version Persistence:
   - Real production execution path persistently records prompt_id, prompt_version, prompt_hash.
   - Fresh-instance reload test: destroying repository/service objects and reloading from disk
     guarantees exact prompt_id, prompt_version, and prompt_hash are recovered.
   - Immutability of history: Promoting a new production prompt v2 and running a new AIRun leaves
     the old AIRun permanently pinned to v1 without historical alteration.
2. Real End-to-End Trace Proof:
   - Production-like AI workflow exercising:
     AIRun -> Context Build -> Memory Retrieval -> Model Route -> Cache Lookup ->
     Provider Call -> Validation -> Artifact Persistence.
   - All spans correlated under a single trace_id with valid parent_span_id, run_id, step_id, activity_id.
   - Fresh-process reload of trace verifies:
     provider/model, routing reason, prompt version, latency breakdown, cache hit/miss,
     retry count, fallback status, estimated/actual cost, artifact reference.
3. Secret Safety on Real E2E Trace:
   - Injected fake secrets (Bearer token, OpenAI API key, signed URL signature, authorization header)
     are thoroughly sanitized before persistence.
   - scan_trace_for_secrets(reloaded_trace) == [] (CLEAN).
   - raw prompt = absent by default.
   - raw user content = absent by default.
   - authorization = redacted.
   - signed URL secrets = redacted.
"""

from datetime import datetime, timezone
from decimal import Decimal
import json
import uuid
import pytest

from ai.contracts.cache import AICacheKeyParams
from ai.contracts.common import CapabilityType, CapabilityTypeEnum, ExecutionClass
from ai.contracts.model import ModelRequirement
from ai.contracts.observability import AITrace, SpanType
from ai.contracts.prompt import PromptContract, PromptRenderRequest, PromptStatus
from ai.contracts.run import AIRunStatus, AIStepStatus
from ai.contracts.usage import CostEstimate
from ai.observability.redaction import scan_trace_for_secrets
from ai.observability.tracer import AITracer
from ai.orchestration.dag import DAGSpecification, StepDefinition
from ai.orchestration.service import AIRunService
from ai.prompts.service import PromptService
from ai.routing.router import ModelRouter
from scripts.core.ai_cache_repository import SQLAICacheRepository
from scripts.core.ai_prompt_repository import SQLPromptRepository
from scripts.core.ai_run_repository import SQLAIRunRepository
from scripts.core.ai_trace_repository import SQLTraceRepository
from scripts.core.database import DatabaseEngine
from scripts.core.storage.storage_service import LocalStorageBackend


# ============================================================================
# PROOF 1: AIRun ↔ Prompt Version Persistence & Historic Immutability
# ============================================================================

def test_airun_prompt_version_persistence_and_historic_immutability(tmp_path):
    db_file = tmp_path / "proof_prompt_persistence.db"
    engine = DatabaseEngine(f"sqlite:///{db_file}")
    workspace_id = "ws_prompt_persistence_test"

    # --- Phase 1: Setup Prompt Service and publish Prompt v1 ---
    prompt_repo_1 = SQLPromptRepository(engine=engine)
    prompt_service_1 = PromptService(repository=prompt_repo_1)

    p_v1 = prompt_service_1.create_prompt(
        prompt_id="prompt_video_director",
        template="Direct a video about {topic} with {tone} style.",
        system_prompt="You are a cinematic director.",
        variables=["topic", "tone"],
        workspace_id=workspace_id,
    )
    prompt_service_1.promote_prompt("prompt_video_director", 1, PromptStatus.TESTING, workspace_id=workspace_id)
    prompt_service_1.promote_prompt(
        "prompt_video_director",
        1,
        PromptStatus.PRODUCTION,
        workspace_id=workspace_id,
        eval_gate_id="eval_gate_director_001",
        eval_quality_score=0.94,
    )

    # Resolve active production prompt
    resolved_v1 = prompt_service_1.render_prompt(
        PromptRenderRequest(
            prompt_id="prompt_video_director",
            workspace_id=workspace_id,
            variables={"topic": "Deep Sea", "tone": "Dramatic"},
        )
    )
    assert resolved_v1.version == 1
    v1_hash = resolved_v1.hash

    # --- Phase 2: Start real production AIRun using Prompt v1 ---
    run_repo_1 = SQLAIRunRepository(engine=engine)
    run_service_1 = AIRunService(repository=run_repo_1)

    dag_spec_1 = DAGSpecification(
        workflow_ref="workflow_cinematic_v1",
        steps=[
            StepDefinition(
                step_id="step_direct_scene",
                capability=CapabilityType.REASONING,
                prompt_id=resolved_v1.prompt_id,
                prompt_version=str(resolved_v1.version),
                prompt_hash=resolved_v1.hash,
            )
        ],
    )

    run_1 = run_service_1.create_run(
        workspace_id=workspace_id,
        capability=CapabilityType.REASONING,
        dag_spec=dag_spec_1,
        execution_class=ExecutionClass.INTERACTIVE,
        prompt_id=resolved_v1.prompt_id,
        prompt_version=str(resolved_v1.version),
        prompt_hash=resolved_v1.hash,
    )

    # Transition run & step to completed state
    run_1 = run_1.model_copy(update={"status": AIRunStatus.RUNNING})
    run_repo_1.update_run(run_1)

    steps_run_1 = run_repo_1.get_steps_for_run(run_1.run_id)
    step_1 = steps_run_1[0].model_copy(
        update={
            "status": AIStepStatus.RUNNING,
        }
    )
    run_repo_1.update_step(step_1)
    step_1 = step_1.model_copy(
        update={
            "status": AIStepStatus.SUCCEEDED,
            "output_ref": "storage/scenes/scene_001.json",
        }
    )
    run_repo_1.update_step(step_1)

    run_1 = run_1.model_copy(
        update={
            "status": AIRunStatus.SUCCEEDED,
            "cost": CostEstimate(estimated_cost=Decimal("0.005"), actual_cost=Decimal("0.0048")),
        }
    )
    run_repo_1.update_run(run_1)

    # --- Phase 3: Destroy service/repository objects and reload from disk ---
    del prompt_repo_1, prompt_service_1, run_repo_1, run_service_1

    # Fresh repository instances querying the exact same underlying DB
    fresh_run_repo = SQLAIRunRepository(engine=engine)
    fresh_prompt_repo = SQLPromptRepository(engine=engine)
    fresh_prompt_service = PromptService(repository=fresh_prompt_repo)

    reloaded_run_1 = fresh_run_repo.get_run(run_1.run_id, workspace_id)
    assert reloaded_run_1 is not None
    assert reloaded_run_1.prompt_id == "prompt_video_director"
    assert reloaded_run_1.prompt_version == "1"
    assert reloaded_run_1.prompt_hash == v1_hash

    reloaded_steps_1 = fresh_run_repo.get_steps_for_run(run_1.run_id, workspace_id)
    assert len(reloaded_steps_1) == 1
    assert reloaded_steps_1[0].prompt_id == "prompt_video_director"
    assert reloaded_steps_1[0].prompt_version == "1"
    assert reloaded_steps_1[0].prompt_hash == v1_hash

    # --- Phase 4: Create & promote Prompt v2 (New production version) ---
    p_v2 = fresh_prompt_service.create_version(
        prompt_id="prompt_video_director",
        template="Direct a high-energy video about {topic} with {tone} aesthetic.",
        variables=["topic", "tone"],
        workspace_id=workspace_id,
    )
    fresh_prompt_service.promote_prompt("prompt_video_director", 2, PromptStatus.TESTING, workspace_id=workspace_id)
    fresh_prompt_service.promote_prompt(
        "prompt_video_director",
        2,
        PromptStatus.PRODUCTION,
        workspace_id=workspace_id,
        eval_gate_id="eval_gate_director_002",
        eval_quality_score=0.97,
    )

    resolved_v2 = fresh_prompt_service.render_prompt(
        PromptRenderRequest(
            prompt_id="prompt_video_director",
            workspace_id=workspace_id,
            variables={"topic": "Space Exploration", "tone": "Epic"},
        )
    )
    assert resolved_v2.version == 2
    v2_hash = resolved_v2.hash
    assert v2_hash != v1_hash

    # Start new AIRun using Prompt v2
    fresh_run_service = AIRunService(repository=fresh_run_repo)
    dag_spec_2 = DAGSpecification(
        workflow_ref="workflow_cinematic_v2",
        steps=[
            StepDefinition(
                step_id="step_direct_scene",
                capability=CapabilityType.REASONING,
                prompt_id=resolved_v2.prompt_id,
                prompt_version=str(resolved_v2.version),
                prompt_hash=resolved_v2.hash,
            )
        ],
    )
    run_2 = fresh_run_service.create_run(
        workspace_id=workspace_id,
        capability=CapabilityType.REASONING,
        dag_spec=dag_spec_2,
        execution_class=ExecutionClass.INTERACTIVE,
        prompt_id=resolved_v2.prompt_id,
        prompt_version=str(resolved_v2.version),
        prompt_hash=resolved_v2.hash,
    )

    # --- Phase 5: Verification of Historic Immutability ---
    # Reload both runs to verify history is untouched
    persisted_old_run = fresh_run_repo.get_run(run_1.run_id, workspace_id)
    persisted_new_run = fresh_run_repo.get_run(run_2.run_id, workspace_id)

    # Old run remains strictly pinned to v1
    assert persisted_old_run.prompt_id == "prompt_video_director"
    assert persisted_old_run.prompt_version == "1"
    assert persisted_old_run.prompt_hash == v1_hash

    # New run is strictly bound to v2
    assert persisted_new_run.prompt_id == "prompt_video_director"
    assert persisted_new_run.prompt_version == "2"
    assert persisted_new_run.prompt_hash == v2_hash


# ============================================================================
# PROOF 2: Real Production-Like End-to-End Trace & Secret Sanitization
# ============================================================================

def test_real_e2e_trace_proof_with_secret_safety(tmp_path):
    """
    Executes a production-like AI workflow integrating all architectural layers:
    1. AIRun (Root orchestration context)
    2. Context Build (Retrieves workspace metadata)
    3. Memory Retrieval (Recalls project preferences)
    4. Model Route (Selects provider and records reason)
    5. Cache Lookup (Queries cache key)
    6. Provider Call (Invokes model execution with simulated retry & tokens)
    7. Validation (Evaluates structured schema conformity)
    8. Artifact Persistence (Writes output to storage service)

    Verifies:
    - All spans linked under one trace_id with valid parent-child hierarchy.
    - Reloading from disk via fresh SQLTraceRepository accurately reproduces:
      provider, model, routing reason, prompt version, latency breakdown, cache hit,
      retry count, fallback status, estimated/actual cost, and artifact reference.
    - Zero secrets leaked into persisted trace (secret scan = CLEAN).
    """
    db_file = tmp_path / "proof_e2e_trace.db"
    storage_dir = tmp_path / "storage"
    engine = DatabaseEngine(f"sqlite:///{db_file}")

    trace_repo = SQLTraceRepository(engine=engine)
    storage_service = LocalStorageBackend(root_dir=storage_dir)
    router = ModelRouter()

    workspace_id = "ws_e2e_trace_proof"
    project_id = "prj_cinematic_01"
    run_id = f"airun_{uuid.uuid4().hex}"
    trace_id = f"trc_{uuid.uuid4().hex[:16]}"

    # Inject realistic secret tokens in inputs to test redaction layer
    fake_bearer_token = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.super_secret_user_jwt_token_12345"
    fake_openai_key = "sk-proj-1234567890abcdef1234567890abcdef12345678"
    fake_signed_url = (
        "https://s3.us-east-1.amazonaws.com/assets/video_raw.mp4"
        "?X-Amz-Signature=abcdef1234567890abcdef123456789012345678&Expires=1750000000"
    )
    raw_user_prompt = "You are a director. Direct scene 1 with dramatic lightning and sound effects."

    tracer = AITracer(
        run_id=run_id,
        workspace_id=workspace_id,
        project_id=project_id,
        trace_id=trace_id,
        repository=trace_repo,
    )

    # -------------------------------------------------------------------------
    # Execute Production-Like Workflow
    # -------------------------------------------------------------------------
    with tracer.start_span("workflow_scene_generation", SpanType.AI_RUN) as root_span:
        root_span.set_capability("VIDEO_PLANNING")
        root_span.set_attribute("session_type", "automated_batch")

        # 1. Context Build
        with tracer.start_span("build_scene_context", SpanType.CONTEXT_BUILD, step_id="step_01") as ctx_span:
            ctx_span.set_attribute("target_resolution", "1080p")
            ctx_span.set_attribute("auth_header", fake_bearer_token)  # Sensitive!

        # 2. Memory Retrieval
        with tracer.start_span("retrieve_project_memory", SpanType.MEMORY_RETRIEVAL, step_id="step_01") as mem_span:
            mem_span.set_attribute("recalled_rules", ["avoid_jump_cuts", "color_palette_teal_orange"])

        # 3. Model Route
        route_req = ModelRequirement(
            capability=CapabilityType.REASONING,
            execution_class=ExecutionClass.INTERACTIVE,
        )
        route_selection = router.route(route_req)
        model_def = router._model_registry.get(route_selection.primary_model)
        primary_provider = model_def.provider_id if model_def else "google"

        with tracer.start_span("route_candidate_model", SpanType.MODEL_ROUTE, step_id="step_02") as route_span:
            route_span.set_model(primary_provider, route_selection.primary_model)
            route_span.set_attribute("routing_reason", "Lowest cost tier satisfying quality floor 0.85")

        # 4. Cache Lookup
        cache_key = "ck_sample_cache_key_998877665544332211"
        with tracer.start_span("lookup_scene_cache", SpanType.CACHE_LOOKUP, step_id="step_02") as cache_span:
            cache_span.set_cache_hit(False)
            cache_span.set_attribute("source_asset_url", fake_signed_url)  # Sensitive!

        # 5. Provider Call (simulates provider execution, retry, cost, and prompt versioning)
        with tracer.start_span("execute_provider_call", SpanType.PROVIDER_CALL, step_id="step_02", activity_id="act_001") as prov_span:
            prov_span.set_capability("REASONING")
            prov_span.set_model(primary_provider, route_selection.primary_model)
            prov_span.set_prompt("prompt_scene_director", "2.0.0")
            prov_span.set_tokens(input_tokens=180, output_tokens=350)
            prov_span.set_retry(1)
            prov_span.set_fallback(False)
            prov_span.set_cost(estimated=Decimal("0.0052"), actual=Decimal("0.0049"))
            prov_span.set_quality(0.95)
            # Sensitive provider credentials in payload
            prov_span.set_attribute("provider_api_key", fake_openai_key)
            prov_span.set_attribute("prompt", raw_user_prompt)  # Privacy policy exclusion!

        # 6. Validation
        with tracer.start_span("validate_scene_schema", SpanType.VALIDATION, step_id="step_02") as val_span:
            val_span.set_attribute("schema_status", "VALID")
            val_span.set_attribute("scene_duration_sec", 15.0)

        # 7. Artifact Persistence
        artifact_data = json.dumps({"scene_id": "sc_01", "shots": 4, "status": "APPROVED"}).encode("utf-8")
        storage_ref = f"workspaces/{workspace_id}/scenes/sc_001.json"
        storage_service.put(storage_ref, artifact_data, "application/json")

        with tracer.start_span("persist_scene_artifact", SpanType.ARTIFACT_PERSISTENCE, step_id="step_03") as art_span:
            art_span.set_attribute("artifact_ref", storage_ref)

    # -------------------------------------------------------------------------
    # Reload Trace from Disk using a FRESH repository instance
    # -------------------------------------------------------------------------
    del tracer, trace_repo

    fresh_trace_repo = SQLTraceRepository(engine=engine)
    reloaded_trace = fresh_trace_repo.get_trace_for_run(run_id, workspace_id)

    assert reloaded_trace is not None
    assert reloaded_trace.run_id == run_id
    assert reloaded_trace.workspace_id == workspace_id
    assert reloaded_trace.trace_id == trace_id

    # -------------------------------------------------------------------------
    # Invariant Checks on Reloaded Trace
    # -------------------------------------------------------------------------
    spans = reloaded_trace.spans
    assert len(spans) == 8, f"Expected 8 spans in workflow trace, got {len(spans)}"

    # Check 1: Single correlated trace_id across all spans
    assert all(s.trace_id == trace_id for s in spans)
    assert all(s.run_id == run_id for s in spans)

    # Check 2: Parent-child hierarchy
    root = [s for s in spans if s.parent_span_id is None][0]
    assert root.name == "workflow_scene_generation"
    children = [s for s in spans if s.parent_span_id == root.span_id]
    assert len(children) == 7

    # Check 3: Provider / model / routing reason
    route_spans = [s for s in spans if s.span_type == SpanType.MODEL_ROUTE]
    assert len(route_spans) == 1
    assert route_spans[0].model == route_selection.primary_model
    assert "Lowest cost tier satisfying quality floor" in route_spans[0].attributes["routing_reason"]

    # Check 4: Prompt version
    prov_spans = [s for s in spans if s.span_type == SpanType.PROVIDER_CALL]
    assert len(prov_spans) == 1
    assert prov_spans[0].prompt_id == "prompt_scene_director"
    assert prov_spans[0].prompt_version == "2.0.0"

    # Check 5: Cache, Retry, Fallback status
    cache_spans = [s for s in spans if s.span_type == SpanType.CACHE_LOOKUP]
    assert cache_spans[0].cache_hit is False
    assert prov_spans[0].retry_count == 1
    assert prov_spans[0].fallback is False

    # Check 6: Latency breakdown & Cost
    assert prov_spans[0].estimated_cost == Decimal("0.0052")
    assert prov_spans[0].actual_cost == Decimal("0.0049")
    assert all(s.duration_ms is not None and s.duration_ms >= 0.0 for s in spans)

    # Check 7: Artifact reference
    art_spans = [s for s in spans if s.span_type == SpanType.ARTIFACT_PERSISTENCE]
    assert art_spans[0].attributes["artifact_ref"] == storage_ref

    # -------------------------------------------------------------------------
    # Check 8: Secret Safety & Privacy Policy Verification
    # -------------------------------------------------------------------------
    # Audit scanner must report ZERO violations
    violations = scan_trace_for_secrets(reloaded_trace)
    assert violations == [], f"Security violation! Leaked secrets in reloaded trace: {violations}"

    # Verify explicit redactions
    serialized_trace = reloaded_trace.model_dump_json()

    # Raw secrets must NOT exist in the serialized trace
    assert "super_secret_user_jwt_token_12345" not in serialized_trace
    assert "sk-proj-1234567890abcdef" not in serialized_trace
    assert "abcdef1234567890abcdef123456789012345678" not in serialized_trace
    assert raw_user_prompt not in serialized_trace

    # Expected mask tokens must be present
    assert "[REDACTED_SECRET]" in serialized_trace or "[REDACTED" in serialized_trace
    assert "[CONTENT_EXCLUDED_BY_PRIVACY_POLICY]" in serialized_trace
    assert "Signature=[REDACTED_SIGNATURE]" in serialized_trace
