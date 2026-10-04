"""
tests/ai/regression/test_retrieval_metrics.py
=============================================
Verification of information retrieval grading metrics: Precision@K, Recall@K, and MRR.
"""

import pytest

from ai.regression.retrieval_grader import (
    RetrievalGrader,
    calculate_precision_at_k,
    calculate_recall_at_k,
    calculate_mrr,
)


def test_precision_at_k_calculation():
    """Verifies Precision@K calculation across diverse ranking lists."""
    retrieved = ["doc_a", "doc_b", "doc_c", "doc_d"]
    acceptable = {"doc_a", "doc_c"}

    # k=2: doc_a (hit), doc_b (miss) -> 1/2 = 0.5
    assert calculate_precision_at_k(retrieved, acceptable, k=2) == 0.5

    # k=3: doc_a, doc_b, doc_c -> 2/3 ≈ 0.6667
    assert calculate_precision_at_k(retrieved, acceptable, k=3) == pytest.approx(0.6667, rel=1e-3)

    # Empty retrieved returns 0.0
    assert calculate_precision_at_k([], acceptable, k=3) == 0.0

    # Negative gate: acceptable is empty, returns 1.0 if retrieved is also empty
    assert calculate_precision_at_k([], set(), k=3) == 1.0


def test_recall_at_k_calculation():
    """Verifies Recall@K calculation."""
    retrieved = ["doc_a", "doc_b", "doc_c"]
    acceptable = {"doc_a", "doc_c", "doc_e", "doc_f"}  # Total 4 acceptable

    # k=3: doc_a and doc_c retrieved out of 4 acceptable -> 2/4 = 0.5
    assert calculate_recall_at_k(retrieved, acceptable, k=3) == 0.5

    # Perfect recall
    full_retrieved = ["doc_a", "doc_c", "doc_e", "doc_f"]
    assert calculate_recall_at_k(full_retrieved, acceptable, k=4) == 1.0

    # Empty acceptable returns 1.0 if retrieved is empty
    assert calculate_recall_at_k([], set(), k=3) == 1.0


def test_mrr_calculation():
    """Verifies Mean Reciprocal Rank (MRR) for first relevant hit."""
    acceptable = {"target_doc"}

    # Hit at rank 1 -> MRR = 1.0
    assert calculate_mrr(["target_doc", "other"], acceptable) == 1.0

    # Hit at rank 2 -> MRR = 0.5
    assert calculate_mrr(["other", "target_doc"], acceptable) == 0.5

    # Hit at rank 3 -> MRR = 1/3 ≈ 0.3333
    assert calculate_mrr(["other1", "other2", "target_doc"], acceptable) == pytest.approx(0.3333, rel=1e-3)

    # No hit -> MRR = 0.0
    assert calculate_mrr(["other1", "other2"], acceptable) == 0.0


def test_retrieval_grader_threshold_and_forbidden_checks():
    """Verifies RetrievalGrader fails when forbidden outputs are retrieved or thresholds not met."""
    grader = RetrievalGrader()

    # Successful retrieval meeting thresholds
    res = grader.grade_retrieval(
        retrieved=["doc_1", "doc_2", "doc_3"],
        acceptable=["doc_1", "doc_2"],
        unacceptable=["doc_bad"],
        k=3,
        min_precision=0.5,
        min_recall=0.5,
        min_mrr=0.5,
    )
    assert res["passed"]
    assert res["precision_at_k"] >= 0.5
    assert res["mrr"] == 1.0

    # Failure due to forbidden doc retrieved
    res_bad = grader.grade_retrieval(
        retrieved=["doc_1", "doc_bad", "doc_3"],
        acceptable=["doc_1"],
        unacceptable=["doc_bad"],
        k=3,
    )
    assert not res_bad["passed"]
    assert any("Incompatible items" in r and "doc_bad" in r for r in res_bad["reasons"])

    # Failure due to insufficient MRR
    res_low_mrr = grader.grade_retrieval(
        retrieved=["doc_3", "doc_4", "doc_1"],
        acceptable=["doc_1"],
        k=3,
        min_mrr=0.5,  # doc_1 is at rank 3, MRR = 0.333 < 0.5
    )
    assert not res_low_mrr["passed"]
    assert any("MRR" in r for r in res_low_mrr["reasons"])
