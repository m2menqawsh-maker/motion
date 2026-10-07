"""
tests/ai/evals/test_knowledge_and_skill_evals.py
================================================
Evaluation gate and benchmark metric runner for Knowledge Retrieval & Skill Routing (S28-02).

Evaluates:
- Knowledge Retrieval: Precision@k, Recall@k, Irrelevant Retrieval Rate (forbidden documents)
- Skill Routing: Correct Activation Rate, False Activation Rate, Missing Activation Rate
- Produces machine-readable JSON evaluation report.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List
import pytest

from ai.evals.creative_datasets import (
    KnowledgeEvalCase,
    SkillRoutingEvalCase,
    get_knowledge_retrieval_dataset,
    get_skill_routing_dataset,
)
from ai.knowledge.contracts import KnowledgeRetrievalQuery, RetrievalMode
from ai.knowledge.indexer import KnowledgeIndexer
from ai.knowledge.loader import KnowledgeLoader
from ai.knowledge.registry import KnowledgeRegistry
from ai.knowledge.retriever import KnowledgeRetriever
from ai.knowledge.router import KnowledgeRouter
from ai.skills.contracts import SkillRoutingContext
from ai.skills.loader import SkillLoader
from ai.skills.registry import SkillRegistry
from ai.skills.router import SkillRouter

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent
EVAL_REPORT_PATH = WORKSPACE_ROOT / "documentation" / "audits" / "s28_02_eval_report.json"


@pytest.fixture(scope="module")
def knowledge_router():
    registry = KnowledgeRegistry()
    loader = KnowledgeLoader(workspace_root=WORKSPACE_ROOT)
    indexer = KnowledgeIndexer()
    router = KnowledgeRouter(
        registry=registry,
        indexer=indexer,
        loader=loader,
        workspace_root=WORKSPACE_ROOT,
    )
    router.initialize_canonical_catalog(verify_hash=True)
    return router


@pytest.fixture(scope="module")
def skill_router():
    registry = SkillRegistry()
    loader = SkillLoader(workspace_root=WORKSPACE_ROOT)
    loader.load_canonical_catalog(registry=registry)
    return SkillRouter(registry=registry)


# =========================================================================
# 1. Knowledge Retrieval Evaluation & Ablation Suite
# =========================================================================

def _run_knowledge_eval_for_mode(
    knowledge_router: KnowledgeRouter,
    dataset: List[KnowledgeEvalCase],
    mode: RetrievalMode,
) -> Dict[str, Any]:
    """Runs the knowledge evaluation dataset under a specific retrieval channel mode."""
    case_results: List[Dict[str, Any]] = []
    precisions: List[float] = []
    recalls: List[float] = []
    irrelevant_rates: List[float] = []
    total_forbidden_violations = 0

    for case in dataset:
        query = KnowledgeRetrievalQuery(
            query=case.query,
            video_type=case.video_type,
            platform=case.platform,
            audio_mode=case.audio_mode,
            language=case.language,
            tags=case.tags,
            category=case.category,
            version=case.version,
            limit_chunks=4,
            retrieval_mode=mode,
        )
        res = knowledge_router.retriever.retrieve(query)
        retrieved_doc_ids = set(res.selected_documents)
        expected_set = set(case.expected_documents)
        forbidden_set = set(case.forbidden_documents)

        # Precision@k & Recall@k
        if expected_set:
            tp = len(retrieved_doc_ids.intersection(expected_set))
            prec = tp / max(1, len(retrieved_doc_ids))
            rec = tp / max(1, len(expected_set))
        else:
            prec = 1.0
            rec = 1.0

        # Irrelevant / Forbidden rate
        forbidden_hits = retrieved_doc_ids.intersection(forbidden_set)
        irr_rate = len(forbidden_hits) / max(1, len(retrieved_doc_ids))
        if forbidden_hits:
            total_forbidden_violations += len(forbidden_hits)

        precisions.append(prec)
        recalls.append(rec)
        irrelevant_rates.append(irr_rate)

        case_results.append({
            "case_id": case.case_id,
            "description": case.description,
            "retrieved_documents": list(retrieved_doc_ids),
            "expected_documents": list(expected_set),
            "forbidden_documents": list(forbidden_set),
            "forbidden_hits": list(forbidden_hits),
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "irrelevant_rate": round(irr_rate, 4),
            "total_tokens": res.total_tokens_estimated,
        })

    avg_precision = sum(precisions) / len(precisions)
    avg_recall = sum(recalls) / len(recalls)
    avg_irrelevant_rate = sum(irrelevant_rates) / len(irrelevant_rates)

    return {
        "mode": mode.value,
        "mean_precision_at_k": round(avg_precision, 4),
        "mean_recall_at_k": round(avg_recall, 4),
        "irrelevant_retrieval_rate": round(avg_irrelevant_rate, 4),
        "forbidden_document_violations": total_forbidden_violations,
        "cases": case_results,
    }


def test_knowledge_retrieval_evaluation_suite(knowledge_router):
    dataset = get_knowledge_retrieval_dataset()
    assert len(dataset) >= 12

    # 1. Run Ablation on Lexical Only
    ablation_lexical = _run_knowledge_eval_for_mode(
        knowledge_router, dataset, RetrievalMode.LEXICAL_ONLY
    )

    # 2. Run Ablation on Semantic Only
    ablation_semantic = _run_knowledge_eval_for_mode(
        knowledge_router, dataset, RetrievalMode.SEMANTIC_ONLY
    )

    # 3. Run Primary Hybrid Mode
    hybrid_results = _run_knowledge_eval_for_mode(
        knowledge_router, dataset, RetrievalMode.HYBRID
    )

    # Invariants for Primary Hybrid Mode
    assert hybrid_results["forbidden_document_violations"] == 0, (
        f"Hybrid retrieval had forbidden violations: {hybrid_results['forbidden_document_violations']}"
    )
    assert hybrid_results["mean_precision_at_k"] >= 0.70, (
        f"Average Precision@k ({hybrid_results['mean_precision_at_k']}) below threshold 0.70"
    )
    assert hybrid_results["mean_recall_at_k"] >= 0.85, (
        f"Average Recall@k ({hybrid_results['mean_recall_at_k']}) below threshold 0.85"
    )
    assert hybrid_results["irrelevant_retrieval_rate"] == 0.0, (
        f"Average Irrelevant Rate ({hybrid_results['irrelevant_retrieval_rate']}) must be 0.0"
    )

    # Store for combined report
    pytest.s28_02_knowledge_eval_summary = {
        "total_cases": len(dataset),
        "mean_precision_at_k": hybrid_results["mean_precision_at_k"],
        "mean_recall_at_k": hybrid_results["mean_recall_at_k"],
        "irrelevant_retrieval_rate": hybrid_results["irrelevant_retrieval_rate"],
        "cases": hybrid_results["cases"],
        "ablation_evaluation": {
            "lexical_only": {
                "mean_precision_at_k": ablation_lexical["mean_precision_at_k"],
                "mean_recall_at_k": ablation_lexical["mean_recall_at_k"],
                "irrelevant_retrieval_rate": ablation_lexical["irrelevant_retrieval_rate"],
                "forbidden_document_violations": ablation_lexical["forbidden_document_violations"],
            },
            "semantic_only": {
                "mean_precision_at_k": ablation_semantic["mean_precision_at_k"],
                "mean_recall_at_k": ablation_semantic["mean_recall_at_k"],
                "irrelevant_retrieval_rate": ablation_semantic["irrelevant_retrieval_rate"],
                "forbidden_document_violations": ablation_semantic["forbidden_document_violations"],
            },
            "hybrid": {
                "mean_precision_at_k": hybrid_results["mean_precision_at_k"],
                "mean_recall_at_k": hybrid_results["mean_recall_at_k"],
                "irrelevant_retrieval_rate": hybrid_results["irrelevant_retrieval_rate"],
                "forbidden_document_violations": hybrid_results["forbidden_document_violations"],
            },
        },
    }


# =========================================================================
# 2. Skill Routing Evaluation Gate
# =========================================================================

def test_skill_routing_evaluation_suite(skill_router):
    dataset = get_skill_routing_dataset()
    assert len(dataset) >= 10

    case_results: List[Dict[str, Any]] = []
    correct_activations = 0
    false_activations = 0
    missing_activations = 0

    for case in dataset:
        ctx = SkillRoutingContext(
            intent=case.intent,
            audio_mode=case.audio_mode,
            video_type=case.video_type,
            task_type=case.task_type,
            platform=case.platform,
            available_capabilities=case.available_capabilities,
            max_skills=case.max_skills,
        )
        res = skill_router.route_skills(ctx)
        selected_ids = {s.skill_id for s in res.selected_skills}
        expected_set = set(case.expected_skills)
        forbidden_set = set(case.forbidden_skills)

        # Check expected
        if expected_set:
            is_correct = expected_set.issubset(selected_ids)
            has_missing = not is_correct
        else:
            is_correct = len(selected_ids) == 0
            has_missing = False

        if is_correct:
            correct_activations += 1
        if has_missing:
            missing_activations += 1

        # Check forbidden
        forbidden_hits = selected_ids.intersection(forbidden_set)
        if forbidden_hits:
            false_activations += 1

        # Invariant: Forbidden skills MUST NEVER activate
        assert len(forbidden_hits) == 0, (
            f"Case '{case.case_id}' activated forbidden skills: {forbidden_hits}"
        )

        case_results.append({
            "case_id": case.case_id,
            "description": case.description,
            "selected_skills": list(selected_ids),
            "expected_skills": list(expected_set),
            "forbidden_skills": list(forbidden_set),
            "forbidden_hits": list(forbidden_hits),
            "is_correct": is_correct,
            "has_missing": has_missing,
        })

    total_cases = len(dataset)
    correct_rate = correct_activations / total_cases
    false_activation_rate = false_activations / total_cases
    missing_activation_rate = missing_activations / total_cases

    # Threshold assertions
    assert correct_rate >= 0.90, f"Correct Activation Rate ({correct_rate:.2f}) below threshold 0.90"
    assert false_activation_rate == 0.0, f"False Activation Rate ({false_activation_rate}) must be 0.0"
    assert missing_activation_rate <= 0.10, f"Missing Activation Rate ({missing_activation_rate:.2f}) above tolerance 0.10"

    skill_summary = {
        "total_cases": total_cases,
        "correct_activation_rate": round(correct_rate, 4),
        "false_activation_rate": round(false_activation_rate, 4),
        "missing_activation_rate": round(missing_activation_rate, 4),
        "cases": case_results,
    }

    # Write combined machine-readable evaluation report
    k_summary = getattr(pytest, "s28_02_knowledge_eval_summary", {})
    combined_report = {
        "suite": "S28-02 Knowledge + Skills Platform Evaluation Gate",
        "status": "PASS",
        "knowledge_retrieval_benchmark": k_summary,
        "skill_routing_benchmark": skill_summary,
    }
    EVAL_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    EVAL_REPORT_PATH.write_text(json.dumps(combined_report, indent=2), encoding="utf-8")
    assert EVAL_REPORT_PATH.exists()
