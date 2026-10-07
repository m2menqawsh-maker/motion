"""
tests/ai/context/test_ranking.py
================================
Tests for candidate ranking and authority weighting (S27.8).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest

from ai.context import (
    ContextAuthority,
    ContextItem,
    ContextRanker,
    ContextRankingPolicy,
    ContextSection,
    ContextSourceType,
    ExclusionReason,
)


class TestCandidateRanking:

    def test_authority_ordering(self):
        ranker = ContextRanker()

        item_sys = ContextItem(
            id="it_sys",
            section=ContextSection.SYSTEM,
            content="System policy",
            source_type=ContextSourceType.SYSTEM_POLICY,
            authority=ContextAuthority.SYSTEM_AUTHORITY,
            relevance_score=0.9,
            confidence=1.0,
            content_hash="h1",
        )
        item_dom = ContextItem(
            id="it_dom",
            section=ContextSection.PROJECT,
            content="Project status",
            source_type=ContextSourceType.DOMAIN_SERVICE,
            authority=ContextAuthority.DOMAIN_SOURCE_OF_TRUTH,
            relevance_score=0.9,
            confidence=1.0,
            content_hash="h2",
        )
        item_hum = ContextItem(
            id="it_hum",
            section=ContextSection.MEMORY,
            content="User confirmed decision",
            source_type=ContextSourceType.MEMORY,
            authority=ContextAuthority.HUMAN_CONFIRMED,
            relevance_score=0.9,
            confidence=1.0,
            content_hash="h3",
        )
        item_exp = ContextItem(
            id="it_exp",
            section=ContextSection.MEMORY,
            content="Explicit user preference",
            source_type=ContextSourceType.MEMORY,
            authority=ContextAuthority.EXPLICIT_USER,
            relevance_score=0.9,
            confidence=1.0,
            content_hash="h4",
        )
        item_der = ContextItem(
            id="it_der",
            section=ContextSection.MEMORY,
            content="Derived pattern",
            source_type=ContextSourceType.MEMORY,
            authority=ContextAuthority.DERIVED,
            relevance_score=0.9,
            confidence=1.0,
            content_hash="h5",
        )
        item_inf = ContextItem(
            id="it_inf",
            section=ContextSection.MEMORY,
            content="Low confidence inference",
            source_type=ContextSourceType.MEMORY,
            authority=ContextAuthority.INFERRED,
            relevance_score=0.9,
            confidence=1.0,
            content_hash="h6",
        )

        # Reverse order insertion
        items = [item_inf, item_der, item_exp, item_hum, item_dom, item_sys]
        ranked, exclusions = ranker.rank_items(items)

        assert len(exclusions) == 0
        ranked_ids = [it.id for it in ranked]
        assert ranked_ids == ["it_sys", "it_dom", "it_hum", "it_exp", "it_der", "it_inf"]

    def test_confirmed_preference_beats_low_confidence_inference(self):
        ranker = ContextRanker()

        confirmed = ContextItem(
            id="it_confirmed",
            section=ContextSection.MEMORY,
            content="User explicitly requested 30 fps",
            source_type=ContextSourceType.MEMORY,
            authority=ContextAuthority.HUMAN_CONFIRMED,
            relevance_score=0.9,
            confidence=1.0,
            content_hash="h_conf",
        )
        inference = ContextItem(
            id="it_inference",
            section=ContextSection.MEMORY,
            content="User might want 60 fps",
            source_type=ContextSourceType.MEMORY,
            authority=ContextAuthority.INFERRED,
            relevance_score=0.9,
            confidence=0.4,
            content_hash="h_inf",
        )

        ranked, _ = ranker.rank_items([inference, confirmed])
        assert ranked[0].id == "it_confirmed"
        assert ranked[1].id == "it_inference"

    def test_recency_impacts_score(self):
        ranker = ContextRanker()
        now = datetime.now(timezone.utc)

        fresh = ContextItem(
            id="it_fresh",
            section=ContextSection.MEMORY,
            content="Recent edit",
            source_type=ContextSourceType.MEMORY,
            authority=ContextAuthority.DERIVED,
            relevance_score=0.8,
            confidence=0.9,
            recency_timestamp=now - timedelta(minutes=5),
            content_hash="h_fresh",
        )
        old = ContextItem(
            id="it_old",
            section=ContextSection.MEMORY,
            content="Old edit",
            source_type=ContextSourceType.MEMORY,
            authority=ContextAuthority.DERIVED,
            relevance_score=0.8,
            confidence=0.9,
            recency_timestamp=now - timedelta(days=30),
            content_hash="h_old",
        )

        ranked, _ = ranker.rank_items([old, fresh], reference_time=now)
        assert ranked[0].id == "it_fresh"
        assert ranked[1].id == "it_old"

    def test_below_threshold_exclusion(self):
        policy = ContextRankingPolicy(minimum_score_threshold=Decimal("0.50"))
        ranker = ContextRanker(policy=policy)

        low_item = ContextItem(
            id="it_very_low",
            section=ContextSection.MEMORY,
            content="Unrelated noise",
            source_type=ContextSourceType.MEMORY,
            authority=ContextAuthority.INFERRED,
            relevance_score=0.1,
            confidence=0.1,
            content_hash="h_low",
        )

        ranked, exclusions = ranker.rank_items([low_item])
        assert len(ranked) == 0
        assert len(exclusions) == 1
        assert exclusions[0].reason == ExclusionReason.LOW_CONFIDENCE
