"""
tests/ai/observability/test_tracer.py
======================================
Tests for Hierarchical Trace Model & E2E Diagnostic Observability (S27.19).

Invariants verified:
1. Hierarchical span relationship: parent_span_id properly tracked across stack.
2. Correlation across run_id, step_id, activity_id, trace_id, and span_id.
3. Structured metadata captured: capability, provider, model, prompt_id/version, tokens, cost, latency, retries, fallback.
4. E2E Proof: Tracer summary answers all 9 diagnostic questions:
   - Run cost
   - Capability requested
   - Model selection & routing reason
   - Cache hit status
   - Fallback status
   - Retry count
   - Time spent breakdown
   - Prompt version used
   - Output artifact reference
5. Persistence to SQLTraceRepository.
"""

from decimal import Decimal
import pytest

from ai.contracts.observability import SpanType
from ai.observability.tracer import AITracer
from scripts.core.ai_trace_repository import SQLTraceRepository
from scripts.core.database import DatabaseEngine


@pytest.fixture
def tracer_and_repo(tmp_path):
    db_file = tmp_path / "test_traces.db"
    engine = DatabaseEngine(f"sqlite:///{db_file}")
    repo = SQLTraceRepository(engine=engine)
    tracer = AITracer(
        run_id="run_e2e_observability_proof_001",
        workspace_id="ws_observability_test",
        project_id="prj_alpha",
        repository=repo,
    )
    return tracer, repo


def test_hierarchical_spans_and_correlation(tracer_and_repo):
    tracer, repo = tracer_and_repo

    # Root span: AIRun
    with tracer.start_span("orchestration_run", SpanType.AI_RUN) as root_span:
        root_span_id = root_span.span_id
        root_span.set_capability("VIDEO_PLANNING")

        # Child 1: Context Build
        with tracer.start_span("build_context", SpanType.CONTEXT_BUILD, step_id="step_01") as ctx_span:
            assert ctx_span.parent_span_id == root_span_id
            ctx_span.set_attribute("context_items_count", 5)

        # Child 2: Memory Retrieval
        with tracer.start_span("retrieve_memory", SpanType.MEMORY_RETRIEVAL, step_id="step_01") as mem_span:
            assert mem_span.parent_span_id == root_span_id
            mem_span.set_attribute("recalled_memories", 2)

        # Child 3: Model Routing
        with tracer.start_span("route_candidate", SpanType.MODEL_ROUTE, step_id="step_02") as route_span:
            assert route_span.parent_span_id == root_span_id
            route_span.set_model("google", "gemini-2.5-flash")
            route_span.set_attribute("routing_reason", "Lowest cost tier satisfying quality floor 0.85")

        # Child 4: Cache Lookup
        with tracer.start_span("lookup_cache", SpanType.CACHE_LOOKUP, step_id="step_02") as cache_span:
            assert cache_span.parent_span_id == root_span_id
            cache_span.set_cache_hit(False)

        # Child 5: Provider Execution (with retry & fallback demonstration)
        with tracer.start_span("call_provider", SpanType.PROVIDER_CALL, step_id="step_02") as prov_span:
            assert prov_span.parent_span_id == root_span_id
            prov_span.set_capability("VIDEO_PLANNING")
            prov_span.set_model("google", "gemini-2.5-flash")
            prov_span.set_prompt(prompt_id="prompt_video_planner", prompt_version="2.1.0")
            prov_span.set_tokens(input_tokens=150, output_tokens=320)
            prov_span.set_retry(1)
            prov_span.set_fallback(False)
            prov_span.set_cost(estimated=Decimal("0.0045"), actual=Decimal("0.0042"))
            prov_span.set_quality(0.92)

        # Child 6: Artifact Persistence
        with tracer.start_span("persist_blueprint", SpanType.ARTIFACT_PERSISTENCE, step_id="step_03") as art_span:
            assert art_span.parent_span_id == root_span_id
            art_span.set_attribute("artifact_ref", "storage/blueprints/blueprint_001.json")

    # Verify spans persisted in database
    persisted_spans = repo.list_spans_for_run(tracer.run_id, tracer.workspace_id)
    assert len(persisted_spans) == 7

    # Verify correlation
    for span in persisted_spans:
        assert span.run_id == "run_e2e_observability_proof_001"
        assert span.workspace_id == "ws_observability_test"
        assert span.trace_id == tracer.trace_id
        assert span.duration_ms is not None
        assert span.duration_ms >= 0.0


def test_trace_answers_9_diagnostic_questions(tracer_and_repo):
    tracer, _ = tracer_and_repo

    # Simulate workflow execution
    with tracer.start_span("execute_workflow", SpanType.AI_RUN) as root:
        root.set_capability("SPEECH_TO_TEXT")

        with tracer.start_span("route_speech", SpanType.MODEL_ROUTE) as route:
            route.set_model("openai", "whisper-large-v3")
            route.set_attribute("routing_reason", "Arabic dialect specialist selected for speech accuracy")

        with tracer.start_span("check_cache", SpanType.CACHE_LOOKUP) as cache:
            cache.set_cache_hit(True)

        with tracer.start_span("transcribe_audio", SpanType.PROVIDER_CALL) as call:
            call.set_capability("SPEECH_TO_TEXT")
            call.set_model("openai", "whisper-large-v3")
            call.set_prompt("speech_canonical_prompt", "1.0.0")
            call.set_retry(2)
            call.set_fallback(True)
            call.set_cost(estimated=Decimal("0.015"), actual=Decimal("0.012"))

        with tracer.start_span("save_transcript", SpanType.ARTIFACT_PERSISTENCE) as art:
            art.set_attribute("artifact_ref", "storage/transcripts/tr_8892.json")

    summary = tracer.summarize()

    # 1. How much did the run cost?
    assert summary["run_cost"]["actual_cost"] == "0.012"
    assert summary["run_cost"]["estimated_cost"] == "0.015"

    # 2. What capability was requested?
    assert summary["requested_capability"] == "SPEECH_TO_TEXT"

    # 3. Why was Model X selected?
    assert summary["model_selection"]["model"] == "whisper-large-v3"
    assert "Arabic dialect specialist" in summary["model_selection"]["reason"]

    # 4. Did a cache hit occur?
    assert summary["cache_hit"] is True

    # 5. Did a fallback occur?
    assert summary["fallback_occurred"] is True

    # 6. How many retries occurred?
    assert summary["retry_count"] == 2

    # 7. Where was time spent?
    assert summary["time_spent_ms"]["total_duration_ms"] >= 0.0
    assert "execute_workflow" in summary["time_spent_ms"]["spans"]
    assert "transcribe_audio" in summary["time_spent_ms"]["spans"]

    # 8. Which prompt version was used?
    assert summary["prompt_used"]["prompt_id"] == "speech_canonical_prompt"
    assert summary["prompt_used"]["prompt_version"] == "1.0.0"

    # 9. Which artifact was produced?
    assert summary["artifact_produced"] == "storage/transcripts/tr_8892.json"
