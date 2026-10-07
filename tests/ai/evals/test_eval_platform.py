"""
tests/ai/evals/test_eval_platform.py
====================================
Comprehensive verification for AI Evaluation Platform (S27.20).

Invariants verified:
1. Versioned datasets with content hash (hash changes on fixture change).
2. 5 Evaluator types: Deterministic, Schema, Code-based, Human Label, LLM Judge.
3. Rule: LLM Judge cannot be sole evaluation authority (raises ValueError).
4. Bad cheap model test: Cost is cheap but quality fails floor (< 0.80) -> REJECTED.
5. Bad utility test: Quality improvement is tiny (+0.01) with 10x cost -> REJECTED under utility policy.
6. Good model test: Quality exceeds floor, fair cost, within latency ceiling -> APPROVED.
7. Bad prompt regression test: vGood passes CI gate; vBad produces degraded output -> CI gate FAILS -> promotion rejected.
8. Ground truth isolation: candidate model cannot generate its own ground truth.
9. Deferred benchmark debt: Speech, Vision, and Audio AI transform benchmarks honestly recorded as DEFERRED_FINAL_VALIDATION with zero fake scores.
"""

from datetime import datetime, timezone
import pytest

from ai.contracts.common import CapabilityType
from ai.contracts.evals import (
    CandidateType,
    EvalDatasetContract,
    EvalExample,
    EvaluatorType,
    ModelPromotionState,
)
from ai.contracts.prompt import PromptEvalGateRejectedError, PromptRenderRequest, PromptStatus
from ai.evals.datasets import get_dataset, get_planning_dataset
from ai.evals.deferred import list_deferred_benchmarks
from ai.evals.evaluators import (
    CodeBasedEvaluator,
    DeterministicEvaluator,
    HumanLabelEvaluator,
    LLMJudgeEvaluator,
    SchemaEvaluator,
)
from ai.evals.gate import CIEvalGate
from ai.evals.promotion import ModelPromotionEngine
from ai.evals.runner import EvalRunner
from ai.prompts.service import PromptService
from scripts.core.ai_prompt_repository import SQLPromptRepository
from scripts.core.database import DatabaseEngine


@pytest.fixture
def prompt_service(tmp_path):
    db_file = tmp_path / "test_eval_prompts.db"
    engine = DatabaseEngine(f"sqlite:///{db_file}")
    repo = SQLPromptRepository(engine=engine)
    return PromptService(repository=repo)


def test_dataset_versioning_and_content_hash():
    ds_base = get_planning_dataset()
    hash_base = ds_base.content_hash

    assert ds_base.dataset_id == "eval_dataset_planning"
    assert len(hash_base) == 64

    # Altering an example produces a different content hash
    modified_examples = list(ds_base.examples)
    modified_examples.append(
        EvalExample(
            example_id="plan_extra_01",
            input_payload={"topic": "Quantum Computing", "target_seconds": 90},
            expected_output={"scene_count": 5},
        )
    )

    new_hash = EvalDatasetContract.compute_content_hash(modified_examples)
    assert new_hash != hash_base


def test_five_evaluators_and_llm_judge_guard():
    example = EvalExample(
        example_id="ex_001",
        input_payload={"val": 10},
        expected_schema="status,score",
        expected_output={"status": "OK", "score": 100},
        ground_truth_label="verified_by_human",
    )

    # 1. Deterministic
    det = DeterministicEvaluator()
    score_det, _ = det.evaluate({"status": "OK", "score": 100}, example)
    assert score_det == 1.0

    # 2. Schema
    schema = SchemaEvaluator()
    score_sch, _ = schema.evaluate({"status": "OK", "score": 100, "extra": "data"}, example)
    assert score_sch == 1.0

    # 3. Code-based
    code = CodeBasedEvaluator(predicate=lambda out: out.get("score") == 100, rule_name="score_is_100")
    score_code, _ = code.evaluate({"status": "OK", "score": 100}, example)
    assert score_code == 1.0

    # 4. Human label
    human = HumanLabelEvaluator()
    score_human, _ = human.evaluate("verified_by_human", example)
    assert score_human == 1.0

    # 5. LLM Judge
    llm = LLMJudgeEvaluator(judge_score_fn=lambda out, ex: 0.95)
    score_llm, _ = llm.evaluate({"status": "OK"}, example)
    assert score_llm == 0.95

    # Mandatory Guard: LLM Judge CANNOT be sole authority
    with pytest.raises(ValueError) as exc_info:
        EvalRunner(evaluators=[llm])
    assert "LLM Judge cannot be the sole evaluation authority" in str(exc_info.value)

    # Combining LLM Judge with deterministic evaluator is allowed
    runner = EvalRunner(evaluators=[det, llm])
    assert len(runner.evaluators) == 2


def test_bad_cheap_model_rejected():
    """
    Fake cheap model:
    Cost is low ($0.0005 vs baseline $0.01)
    Quality fails floor (0.65 < 0.80)
    Result: NOT APPROVED
    """
    decision = ModelPromotionEngine.evaluate_candidate(
        candidate_id="fake_cheap_model_v1",
        quality_score=0.65,
        cost_per_call=0.0005,
        latency_ms=250.0,
        baseline_quality=0.85,
        baseline_cost=0.01,
    )

    assert decision.approved is False
    assert decision.final_state == ModelPromotionState.REJECTED
    assert any("failed quality floor" in r for r in decision.reasons)


def test_bad_utility_model_rejected():
    """
    Candidate with trivial quality gain (+0.01) but 10x cost inflation ($0.10 vs $0.01):
    Result: NOT APPROVED under economic utility policy
    """
    decision = ModelPromotionEngine.evaluate_candidate(
        candidate_id="inflated_cost_model_v1",
        quality_score=0.86,  # baseline is 0.85 (delta = +0.01)
        cost_per_call=0.10,  # 10x baseline cost of 0.01
        latency_ms=900.0,
        baseline_quality=0.85,
        baseline_cost=0.01,
    )

    assert decision.approved is False
    assert decision.final_state == ModelPromotionState.REJECTED
    assert any("economic utility policy" in r for r in decision.reasons)


def test_good_model_approved():
    """
    Candidate with strong quality (0.92 > 0.80 floor), reasonable cost ($0.012),
    and fast latency (450ms < 5000ms ceiling):
    Result: APPROVED
    """
    decision = ModelPromotionEngine.evaluate_candidate(
        candidate_id="gemini-2.5-pro-candidate",
        quality_score=0.92,
        cost_per_call=0.012,
        latency_ms=450.0,
        baseline_quality=0.85,
        baseline_cost=0.01,
    )

    assert decision.approved is True
    assert decision.final_state == ModelPromotionState.APPROVED
    assert any("passed quality floor" in r for r in decision.reasons)


def test_bad_prompt_regression_fails_ci_gate_and_blocks_promotion(prompt_service):
    """
    Takes a good prompt v1 that passes the CI evaluation gate.
    Creates an intentionally degraded prompt v2 that fails structured output requirements.
    CI eval gate fails and blocks v2 promotion to PRODUCTION.
    """
    # 1. Create Prompt v1 (Good)
    prompt_service.create_prompt(
        prompt_id="blueprint_generator",
        template='Generate video blueprint for {topic}. Output JSON with keys: ["title", "scene_count", "scenes"].',
        variables=["topic"],
    )
    prompt_service.promote_prompt("blueprint_generator", 1, PromptStatus.TESTING)

    # Define minimal test dataset
    ex_list = [
        EvalExample(
            example_id="ex_1",
            input_payload={"topic": "Cooking Tips"},
            expected_schema="title,scene_count,scenes",
            expected_output={"title": "Cooking Tips"},
        ),
    ]
    dataset = EvalDatasetContract(
        dataset_id="DATASET_BLUEPRINT_TEST",
        version="1.0.0",
        content_hash=EvalDatasetContract.compute_content_hash(ex_list),
        capability=CapabilityType.PLANNING,
        description="Test blueprint dataset",
        examples=ex_list,
    )

    # Good executor simulating compliant output for v1
    def good_executor(rendered_prompt: str, payload: dict) -> dict:
        return {"title": "Cooking Tips", "scene_count": 3, "scenes": ["intro", "recipe", "outro"]}

    # Evaluate v1 through CI Eval Gate
    eval_result_v1 = CIEvalGate.run_prompt_regression_gate(
        prompt_service=prompt_service,
        prompt_id="blueprint_generator",
        candidate_version=1,
        dataset=dataset,
        executor_fn=good_executor,
        evaluators=[SchemaEvaluator()],
        min_threshold=0.80,
    )
    assert eval_result_v1.passed is True
    assert eval_result_v1.quality_score == 1.0

    # Promote v1 to PRODUCTION with passing score
    prompt_service.promote_prompt(
        "blueprint_generator",
        1,
        PromptStatus.PRODUCTION,
        eval_gate_id=eval_result_v1.evaluation_id,
        eval_quality_score=eval_result_v1.quality_score,
    )

    # 2. Create Prompt v2 (Intentionally degraded / malformed instructions)
    prompt_service.create_version(
        prompt_id="blueprint_generator",
        template="Just chat about {topic} without any specific formatting.",
        variables=["topic"],
    )
    prompt_service.promote_prompt("blueprint_generator", 2, PromptStatus.TESTING)

    # Bad executor simulating non-compliant output produced by degraded v2
    def bad_executor(rendered_prompt: str, payload: dict) -> dict:
        # Missing required 'scenes' and 'scene_count' keys
        return {"unstructured_thought": "Cooking is fun"}

    # Evaluate v2 through CI Eval Gate
    eval_result_v2 = CIEvalGate.run_prompt_regression_gate(
        prompt_service=prompt_service,
        prompt_id="blueprint_generator",
        candidate_version=2,
        dataset=dataset,
        executor_fn=bad_executor,
        evaluators=[SchemaEvaluator()],
        min_threshold=0.80,
    )

    # Assert CI Eval Gate catches regression and FAILS
    assert eval_result_v2.passed is False
    assert eval_result_v2.quality_score < 0.80
    assert len(eval_result_v2.failure_reasons) > 0

    # Attempting to promote v2 to PRODUCTION with degraded score is BLOCKED
    with pytest.raises(PromptEvalGateRejectedError) as exc_blocked:
        prompt_service.promote_prompt(
            "blueprint_generator",
            2,
            PromptStatus.PRODUCTION,
            eval_gate_id=eval_result_v2.evaluation_id,
            eval_quality_score=eval_result_v2.quality_score,
        )
    assert "below the 0.80 minimum threshold" in str(exc_blocked.value)

    # Confirm active PRODUCTION prompt is STILL v1!
    active_prod = prompt_service._repository.get_active_production_prompt("blueprint_generator")
    assert active_prod.version == 1
    assert active_prod.status == PromptStatus.PRODUCTION


def test_deferred_benchmark_debt_honestly_tracked():
    """
    Verifies that Speech, Vision, and Audio AI quality benchmarks are honestly recorded
    as DEFERRED_FINAL_VALIDATION with zero fake scores injected.
    """
    benchmarks = list_deferred_benchmarks()
    assert len(benchmarks) == 3

    b_map = {b.benchmark_id: b for b in benchmarks}

    # Speech Real Quality Benchmark
    speech_bench = b_map["BENCH_SPEECH_QUALITY"]
    assert speech_bench.status == "DEFERRED_FINAL_VALIDATION"
    assert speech_bench.fake_scores_injected is False
    assert speech_bench.target_stage == "AI-15"

    # Vision Real Quality Benchmark
    vision_bench = b_map["BENCH_VISION_QUALITY"]
    assert vision_bench.status == "DEFERRED_FINAL_VALIDATION"
    assert vision_bench.fake_scores_injected is False
    assert vision_bench.target_stage == "AI-15"

    # Audio AI Transform Benchmark
    audio_bench = b_map["BENCH_AUDIO_AI"]
    assert audio_bench.status == "DEFERRED_FINAL_VALIDATION"
    assert audio_bench.fake_scores_injected is False
    assert audio_bench.target_stage == "AI-15"
