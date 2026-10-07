"""
tests/ai/context/test_deduplication.py
======================================
Tests for candidate deduplication and exact match elimination (S27.8).
"""

from __future__ import annotations

import pytest

from ai.context import (
    ContextAuthority,
    ContextDeduplicator,
    ContextItem,
    ContextSection,
    ContextSourceType,
    ExclusionReason,
)


class TestCandidateDeduplication:

    def test_exact_content_hash_deduplication(self):
        dedup = ContextDeduplicator()

        # Same content across 3 sources: ProjectService, Memory, Knowledge
        content = "Video resolution is 1080x1920 portrait."
        h = ContextItem.compute_content_hash(content)

        item_proj = ContextItem(
            id="proj_fact_1",
            section=ContextSection.PROJECT,
            content=content,
            source_type=ContextSourceType.DOMAIN_SERVICE,
            authority=ContextAuthority.DOMAIN_SOURCE_OF_TRUTH,
            content_hash=h,
        )
        item_mem = ContextItem(
            id="mem_fact_1",
            section=ContextSection.MEMORY,
            content=content,
            source_type=ContextSourceType.MEMORY,
            authority=ContextAuthority.DERIVED,
            content_hash=h,
        )
        item_know = ContextItem(
            id="know_fact_1",
            section=ContextSection.KNOWLEDGE,
            content=content,
            source_type=ContextSourceType.KNOWLEDGE,
            authority=ContextAuthority.DERIVED,
            content_hash=h,
        )

        kept, exclusions = dedup.deduplicate([item_proj, item_mem, item_know])

        assert len(kept) == 1
        assert kept[0].id == "proj_fact_1"
        assert kept[0].authority == ContextAuthority.DOMAIN_SOURCE_OF_TRUTH

        assert len(exclusions) == 2
        for exc in exclusions:
            assert exc.reason == ExclusionReason.DUPLICATE

    def test_canonical_key_identical_content_deduplication(self):
        dedup = ContextDeduplicator()

        item1 = ContextItem(
            id="item1",
            section=ContextSection.PROJECT,
            content="Project status: PLAN_READY",
            source_type=ContextSourceType.DOMAIN_SERVICE,
            authority=ContextAuthority.DOMAIN_SOURCE_OF_TRUTH,
            canonical_key="fact:project:status",
            content_hash="h1",
        )
        item2 = ContextItem(
            id="item2",
            section=ContextSection.MEMORY,
            content="Project status: PLAN_READY",
            source_type=ContextSourceType.MEMORY,
            authority=ContextAuthority.DERIVED,
            canonical_key="fact:project:status",
            content_hash="h2",
        )

        kept, exclusions = dedup.deduplicate([item1, item2])
        assert len(kept) == 1
        assert kept[0].id == "item1"
        assert len(exclusions) == 1
        assert exclusions[0].reason == ExclusionReason.DUPLICATE
