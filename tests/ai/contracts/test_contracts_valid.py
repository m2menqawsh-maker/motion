"""
tests/ai/contracts/test_contracts_valid.py
==========================================
Verifies that all valid fixtures successfully instantiate canonical Pydantic contracts
and achieve 100% deterministic JSON roundtrip serialization.
"""

from __future__ import annotations

import pytest
from ai.contracts import (
    AIError,
    AIRequest,
    AIResponse,
    AIRun,
    AIStep,
    AITrace,
    BenchmarkDebtContract,
    CapabilityRequest,
    CapabilityResult,
    CostEstimate,
    EvalDatasetContract,
    EvalResultContract,
    MediaIntelligenceRef,
    MemoryQuery,
    MemoryResult,
    ModelRequirement,
    ModelSelection,
    PromptContract,
    PromptRenderRequest,
    PromptRenderResult,
    ProvenanceRecord,
    ToolCall,
    ToolResult,
    TraceSpanRecord,
    UsageRecord,
)
from tests.ai.contracts.fixtures import get_valid_fixtures


class TestValidContracts:

    def test_usage_record_valid(self):
        f = get_valid_fixtures()["UsageRecord_full"]
        record = UsageRecord.model_validate(f)
        assert record.input_tokens == 100
        assert record.total_tokens == 300
        assert len(record.reported_units) == 1

        # Test JSON roundtrip
        json_data = record.model_dump_json()
        reloaded = UsageRecord.model_validate_json(json_data)
        assert reloaded == record

    def test_cost_estimate_valid(self):
        f = get_valid_fixtures()["CostEstimate_full"]
        cost = CostEstimate.model_validate(f)
        assert str(cost.estimated_cost) == "0.1000"
        assert cost.currency == "USD"

        # JSON roundtrip
        json_data = cost.model_dump_json()
        reloaded = CostEstimate.model_validate_json(json_data)
        assert reloaded == cost

    def test_ai_error_valid(self):
        f = get_valid_fixtures()["AIError_full"]
        err = AIError.model_validate(f)
        assert err.code.value == "RATE_LIMITED"
        assert err.retryable is True
        assert err.details["limit"] == 100

        json_data = err.model_dump_json()
        reloaded = AIError.model_validate_json(json_data)
        assert reloaded == err

    def test_provenance_record_valid(self):
        f = get_valid_fixtures()["ProvenanceRecord_valid"]
        prov = ProvenanceRecord.model_validate(f)
        assert prov.source == "provider_adapter"
        assert prov.latency_ms == 250

        json_data = prov.model_dump_json()
        reloaded = ProvenanceRecord.model_validate_json(json_data)
        assert reloaded == prov

    def test_model_requirement_valid(self):
        f = get_valid_fixtures()["ModelRequirement_full"]
        req = ModelRequirement.model_validate(f)
        assert req.capability.value == "TEXT_TO_SPEECH"
        assert req.quality_target.value == "HIGH"
        assert "streaming" in req.required_features

        json_data = req.model_dump_json()
        reloaded = ModelRequirement.model_validate_json(json_data)
        assert reloaded == req

    def test_model_selection_valid(self):
        f = get_valid_fixtures()["ModelSelection_valid"]
        sel = ModelSelection.model_validate(f)
        assert sel.primary_model == "model_tts_neural_v1"
        assert "model_tts_standard_v2" in sel.fallback_candidates

        json_data = sel.model_dump_json()
        reloaded = ModelSelection.model_validate_json(json_data)
        assert reloaded == sel

    def test_capability_request_valid(self):
        f = get_valid_fixtures()["CapabilityRequest_valid"]
        cap_req = CapabilityRequest.model_validate(f)
        assert cap_req.capability.value == "TEXT_TO_SPEECH"
        assert cap_req.input_data["text"] == "Hello world"

        json_data = cap_req.model_dump_json()
        reloaded = CapabilityRequest.model_validate_json(json_data)
        assert reloaded == cap_req

    def test_capability_result_valid(self):
        f_succ = get_valid_fixtures()["CapabilityResult_success"]
        res_succ = CapabilityResult.model_validate(f_succ)
        assert res_succ.status.value == "SUCCESS"
        assert res_succ.confidence == 0.95
        assert res_succ.error is None

        f_fail = get_valid_fixtures()["CapabilityResult_failed"]
        res_fail = CapabilityResult.model_validate(f_fail)
        assert res_fail.status.value == "FAILED"
        assert res_fail.error is not None
        assert res_fail.error.code.value == "PROVIDER_UNAVAILABLE"

    def test_tool_call_valid(self):
        f = get_valid_fixtures()["ToolCall_valid"]
        tc = ToolCall.model_validate(f)
        assert tc.tool_name == "crop_video"
        assert tc.parameters["width"] == 1080

        json_data = tc.model_dump_json()
        reloaded = ToolCall.model_validate_json(json_data)
        assert reloaded == tc

    def test_tool_result_valid(self):
        f_succ = get_valid_fixtures()["ToolResult_success"]
        tr_succ = ToolResult.model_validate(f_succ)
        assert tr_succ.status.value == "SUCCESS"
        assert tr_succ.duration_ms == 5000

        f_err = get_valid_fixtures()["ToolResult_error"]
        tr_err = ToolResult.model_validate(f_err)
        assert tr_err.status.value == "ERROR"
        assert tr_err.error is not None

    def test_memory_query_valid(self):
        f = get_valid_fixtures()["MemoryQuery_valid"]
        mq = MemoryQuery.model_validate(f)
        assert mq.workspace_id == "ws_alpha"
        assert mq.limit == 5

        json_data = mq.model_dump_json()
        reloaded = MemoryQuery.model_validate_json(json_data)
        assert reloaded == mq

    def test_memory_result_valid(self):
        f = get_valid_fixtures()["MemoryResult_valid"]
        mr = MemoryResult.model_validate(f)
        assert mr.total_found == 1
        assert len(mr.entries) == 1
        assert mr.entries[0].confidence == 0.92

        json_data = mr.model_dump_json()
        reloaded = MemoryResult.model_validate_json(json_data)
        assert reloaded == mr

    def test_media_intelligence_ref_valid(self):
        f = get_valid_fixtures()["MediaIntelligenceRef_valid"]
        ref = MediaIntelligenceRef.model_validate(f)
        assert ref.artifact_id == "art_analysis_99"
        assert "storage_key" in f

        json_data = ref.model_dump_json()
        reloaded = MediaIntelligenceRef.model_validate_json(json_data)
        assert reloaded == ref

    def test_ai_request_valid(self):
        f_min = get_valid_fixtures()["AIRequest_minimal"]
        req_min = AIRequest.model_validate(f_min)
        assert req_min.request_id == "req_001"
        assert req_min.execution_class.value == "INTERACTIVE"

        f_full = get_valid_fixtures()["AIRequest_full"]
        req_full = AIRequest.model_validate(f_full)
        assert req_full.capability.value == "VIDEO_GENERATION"
        assert req_full.execution_class.value == "BATCH"
        assert req_full.privacy_requirement.value == "ZERO_DATA_RETENTION"

        json_data = req_full.model_dump_json()
        reloaded = AIRequest.model_validate_json(json_data)
        assert reloaded == req_full

    def test_ai_response_valid(self):
        f_succ = get_valid_fixtures()["AIResponse_success"]
        resp_succ = AIResponse.model_validate(f_succ)
        assert resp_succ.status.value == "SUCCEEDED"
        assert resp_succ.error is None

        f_fail = get_valid_fixtures()["AIResponse_failed"]
        resp_fail = AIResponse.model_validate(f_fail)
        assert resp_fail.status.value == "FAILED"
        assert resp_fail.error is not None
        assert resp_fail.error.code.value == "BUDGET_EXCEEDED"

    def test_ai_run_valid(self):
        f = get_valid_fixtures()["AIRun_valid"]
        run = AIRun.model_validate(f)
        assert run.run_id == "run_001"
        assert run.status.value == "RUNNING"
        assert run.started_at is not None

        json_data = run.model_dump_json()
        reloaded = AIRun.model_validate_json(json_data)
        assert reloaded == run

    def test_ai_step_valid(self):
        f = get_valid_fixtures()["AIStep_valid"]
        step = AIStep.model_validate(f)
        assert step.step_id == "step_001"
        assert step.status.value == "SUCCEEDED"
        assert step.attempt == 1

        json_data = step.model_dump_json()
        reloaded = AIStep.model_validate_json(json_data)
        assert reloaded == step

    def test_prompt_contract_valid(self):
        f = get_valid_fixtures()["PromptContract_valid"]
        prompt = PromptContract.model_validate(f)
        assert prompt.prompt_id == "prompt_translator"
        assert prompt.version == 1
        assert prompt.status.value == "DRAFT"

        json_data = prompt.model_dump_json()
        reloaded = PromptContract.model_validate_json(json_data)
        assert reloaded == prompt

    def test_prompt_render_contracts_valid(self):
        req_f = get_valid_fixtures()["PromptRenderRequest_valid"]
        req = PromptRenderRequest.model_validate(req_f)
        assert req.prompt_id == "prompt_translator"

        res_f = get_valid_fixtures()["PromptRenderResult_valid"]
        res = PromptRenderResult.model_validate(res_f)
        assert res.prompt_id == "prompt_translator"
        assert res.version == 1

    def test_trace_span_record_valid(self):
        f = get_valid_fixtures()["TraceSpanRecord_valid"]
        span = TraceSpanRecord.model_validate(f)
        assert span.trace_id == "trc_12345"
        assert span.span_type.value == "MODEL_ROUTE"

        json_data = span.model_dump_json()
        reloaded = TraceSpanRecord.model_validate_json(json_data)
        assert reloaded == span

    def test_ai_trace_valid(self):
        f = get_valid_fixtures()["AITrace_valid"]
        trace = AITrace.model_validate(f)
        assert trace.trace_id == "trc_12345"

    def test_eval_contracts_valid(self):
        ds_f = get_valid_fixtures()["EvalDatasetContract_valid"]
        ds = EvalDatasetContract.model_validate(ds_f)
        assert ds.dataset_id == "dataset_test_routing"

        res_f = get_valid_fixtures()["EvalResultContract_valid"]
        res = EvalResultContract.model_validate(res_f)
        assert res.passed is True
        assert res.quality_score == 0.92

        debt_f = get_valid_fixtures()["BenchmarkDebtContract_valid"]
        debt = BenchmarkDebtContract.model_validate(debt_f)
        assert debt.status == "DEFERRED_FINAL_VALIDATION"
        assert debt.fake_scores_injected is False

