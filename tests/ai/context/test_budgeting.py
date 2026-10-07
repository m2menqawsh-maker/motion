"""
tests/ai/context/test_budgeting.py
==================================
Tests for token budgeting, output reserve, and ceiling enforcement (S27.8).
"""

from __future__ import annotations

import pytest

from ai.context import (
    BudgetExceededError,
    ContextAuthority,
    ContextBudgetManager,
    ContextBudgetPolicy,
    ContextItem,
    ContextSection,
    ContextSourceType,
    DeterministicTokenEstimator,
    ExclusionReason,
)


class TestTokenBudgeting:

    def test_token_ceiling_hard_enforcement(self):
        """
        Total budget = 4000, output reserve = 1000 -> maximum input = 3000.
        Candidate payload contains 5000 tokens.
        Final assembled input tokens must be <= 3000.
        """
        policy = ContextBudgetPolicy(total_budget=4000, output_reserve=1000)
        manager = ContextBudgetManager(policy=policy)
        estimator = DeterministicTokenEstimator()

        items = []
        # Add 20 items of ~300 tokens each (total ~6000 tokens)
        for i in range(20):
            content = f"Fact {i}: " + ("substantialword " * 100)
            items.append(
                ContextItem(
                    id=f"item_{i:02d}",
                    section=ContextSection.MEMORY,
                    content=content,
                    source_type=ContextSourceType.MEMORY,
                    authority=ContextAuthority.DERIVED,
                    relevance_score=1.0 - (i * 0.04),  # decreasing score
                    estimated_tokens=estimator.estimate_tokens(content),
                    content_hash=f"h_{i}",
                )
            )

        final_items, exclusions, tokens_by_sec = manager.apply_budget(items)

        total_final_tokens = sum(it.estimated_tokens for it in final_items)
        assert total_final_tokens <= 3000
        assert len(final_items) < len(items)
        assert len(exclusions) > 0

        for exc in exclusions:
            assert exc.reason == ExclusionReason.TOKEN_BUDGET

    def test_important_fact_preservation_under_pressure(self):
        """
        Under budget pressure:
        - SYSTEM policy
        - REQUEST payload
        - DOMAIN_SOURCE_OF_TRUTH core status
        must NOT be dropped ahead of low-priority memory.
        """
        policy = ContextBudgetPolicy(total_budget=500, output_reserve=100)  # max input = 400
        manager = ContextBudgetManager(policy=policy)
        estimator = DeterministicTokenEstimator()

        sys_content = "SYSTEM DIRECTIVE: Obey taste gates."
        sys_item = ContextItem(
            id="sys_crit",
            section=ContextSection.SYSTEM,
            content=sys_content,
            source_type=ContextSourceType.SYSTEM_POLICY,
            authority=ContextAuthority.SYSTEM_AUTHORITY,
            estimated_tokens=estimator.estimate_tokens(sys_content),
            content_hash="h_sys",
        )

        stat_content = "Project status: PLAN_READY"
        status_item = ContextItem(
            id="proj_stat",
            section=ContextSection.PROJECT,
            content=stat_content,
            source_type=ContextSourceType.DOMAIN_SERVICE,
            authority=ContextAuthority.DOMAIN_SOURCE_OF_TRUTH,
            canonical_key="fact:project:status",
            estimated_tokens=estimator.estimate_tokens(stat_content),
            content_hash="h_stat",
        )

        req_content = "REQUEST: Build the video plan."
        req_item = ContextItem(
            id="req_crit",
            section=ContextSection.REQUEST,
            content=req_content,
            source_type=ContextSourceType.REQUEST_PAYLOAD,
            authority=ContextAuthority.EXPLICIT_USER,
            estimated_tokens=estimator.estimate_tokens(req_content),
            content_hash="h_req",
        )

        mem_items = []
        for i in range(10):
            c = f"Memory observation {i}: " + ("filler " * 50)
            mem_items.append(
                ContextItem(
                    id=f"mem_filler_{i}",
                    section=ContextSection.MEMORY,
                    content=c,
                    source_type=ContextSourceType.MEMORY,
                    authority=ContextAuthority.INFERRED,
                    relevance_score=0.4,
                    estimated_tokens=estimator.estimate_tokens(c),
                    content_hash=f"h_mem_{i}",
                )
            )

        all_items = [sys_item, status_item, req_item] + mem_items
        final_items, exclusions, _ = manager.apply_budget(all_items)

        final_ids = {it.id for it in final_items}
        # Critical items MUST be preserved
        assert "sys_crit" in final_ids
        assert "proj_stat" in final_ids
        assert "req_crit" in final_ids

        # Total tokens must not exceed 400
        assert sum(it.estimated_tokens for it in final_items) <= 400

    def test_budget_policy_validation(self):
        with pytest.raises(ValueError, match="output_reserve.*must be strictly less than"):
            ContextBudgetPolicy(total_budget=1000, output_reserve=1000)

        with pytest.raises(ValueError, match="output_reserve.*must be strictly less than"):
            ContextBudgetPolicy(total_budget=1000, output_reserve=1200)
