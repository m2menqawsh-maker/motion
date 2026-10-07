"""
ai/regression/retrieval_grader.py
=================================
Retrieval evaluation metrics engine for Knowledge and Template retrieval (S28-08B).

Computes:
- Precision@K
- Recall@K
- Mean Reciprocal Rank (MRR)
- Incompatible items rejection
- Empty-set correctness for negative retrieval cases
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple


def calculate_precision_at_k(
    retrieved: List[str],
    acceptable: List[str],
    k: int = 3,
) -> float:
    """Calculates Precision@K = (hits in top K) / min(k, len(top K))."""
    top_k = retrieved[:k]
    if not acceptable:
        # Negative case: expecting nothing
        return 1.0 if len(top_k) == 0 else 0.0

    if not top_k:
        return 0.0

    acc_set = set(acceptable)
    hits = sum(1 for item in top_k if item in acc_set)
    return round(hits / len(top_k), 4)


def calculate_recall_at_k(
    retrieved: List[str],
    acceptable: List[str],
    k: int = 3,
) -> float:
    """Calculates Recall@K = (hits in top K) / len(acceptable)."""
    top_k = retrieved[:k]
    if not acceptable:
        return 1.0 if len(top_k) == 0 else 0.0

    acc_set = set(acceptable)
    hits = sum(1 for item in top_k if item in acc_set)
    return round(hits / len(acceptable), 4)


def calculate_mrr(
    retrieved: List[str],
    acceptable: List[str],
    k: int = 3,
) -> float:
    """Calculates Reciprocal Rank of the first acceptable item in top K."""
    top_k = retrieved[:k]
    if not acceptable:
        return 1.0 if len(top_k) == 0 else 0.0

    acc_set = set(acceptable)
    for rank, item in enumerate(top_k, start=1):
        if item in acc_set:
            return round(1.0 / rank, 4)
    return 0.0


class RetrievalGrader:
    """
    Evaluates retrieval quality against acceptable and unacceptable ground truth sets.
    """

    def grade_retrieval(
        self,
        retrieved: List[str],
        acceptable: List[str],
        unacceptable: Optional[List[str]] = None,
        k: int = 3,
        min_precision: Optional[float] = None,
        min_recall: Optional[float] = None,
        min_mrr: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Grades retrieved items against expectations.
        Returns a dict containing metrics and passed flag.
        """
        top_k = retrieved[:k]
        prec = calculate_precision_at_k(retrieved, acceptable, k=k)
        rec = calculate_recall_at_k(retrieved, acceptable, k=k)
        mrr = calculate_mrr(retrieved, acceptable, k=k)

        unacc_set = set(unacceptable or [])
        incompatible_retrieved = [item for item in top_k if item in unacc_set]

        reasons = []
        passed = True

        if incompatible_retrieved:
            passed = False
            reasons.append(
                f"Incompatible items retrieved in top {k}: {incompatible_retrieved}"
            )

        if min_precision is not None and prec < min_precision:
            passed = False
            reasons.append(
                f"Precision@{k} ({prec}) below threshold ({min_precision})"
            )

        if min_recall is not None and rec < min_recall:
            passed = False
            reasons.append(
                f"Recall@{k} ({rec}) below threshold ({min_recall})"
            )

        if min_mrr is not None and mrr < min_mrr:
            passed = False
            reasons.append(
                f"MRR ({mrr}) below threshold ({min_mrr})"
            )

        return {
            "passed": passed,
            "precision_at_k": prec,
            "recall_at_k": rec,
            "mrr": mrr,
            "k": k,
            "top_k": top_k,
            "acceptable": acceptable,
            "incompatible_retrieved": incompatible_retrieved,
            "reasons": reasons,
        }
