"""
tests/ai/context/test_conflicts.py
==================================
Tests for authority-aware conflict resolution and source of truth enforcement (S27.8).
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


class TestConflictResolution:

    def test_domain_fps_30_beats_stale_memory_fps_24(self):
        """
        Canonical Domain: fps = 30 (DOMAIN_SOURCE_OF_TRUTH)
        Memory stale: fps = 24 (DERIVED)
        Expected: fps = 30 only, stale memory excluded with AUTHORITY_CONFLICT.
        """
        dedup = ContextDeduplicator()

        domain_item = ContextItem(
            id="fact_domain_fps",
            section=ContextSection.PROJECT,
            content="Project fps: 30",
            source_type=ContextSourceType.DOMAIN_SERVICE,
            authority=ContextAuthority.DOMAIN_SOURCE_OF_TRUTH,
            canonical_key="fact:project:fps",
            content_hash=ContextItem.compute_content_hash("Project fps: 30"),
        )
        memory_item = ContextItem(
            id="fact_stale_memory_fps",
            section=ContextSection.MEMORY,
            content="Project fps: 24",
            source_type=ContextSourceType.MEMORY,
            authority=ContextAuthority.DERIVED,
            canonical_key="fact:project:fps",
            content_hash=ContextItem.compute_content_hash("Project fps: 24"),
        )

        # Case 1: Domain item evaluated first
        kept, exclusions = dedup.deduplicate([domain_item, memory_item])
        assert len(kept) == 1
        assert kept[0].id == "fact_domain_fps"
        assert kept[0].content == "Project fps: 30"
        assert len(exclusions) == 1
        assert exclusions[0].reason == ExclusionReason.AUTHORITY_CONFLICT
        assert exclusions[0].candidate_id == "fact_stale_memory_fps"

        # Case 2: Memory item evaluated first (e.g. before sorting)
        dedup2 = ContextDeduplicator()
        kept2, exclusions2 = dedup2.deduplicate([memory_item, domain_item])
        assert len(kept2) == 1
        assert kept2[0].id == "fact_domain_fps"
        assert kept2[0].content == "Project fps: 30"
        assert len(exclusions2) == 1
        assert exclusions2[0].reason == ExclusionReason.AUTHORITY_CONFLICT
        assert exclusions2[0].candidate_id == "fact_stale_memory_fps"

    def test_domain_status_ready_beats_memory_draft(self):
        """
        DomainService says: status = READY
        Memory stale says: status = DRAFT
        Expected: READY wins, DRAFT excluded with AUTHORITY_CONFLICT.
        """
        dedup = ContextDeduplicator()

        domain_status = ContextItem(
            id="dom_status",
            section=ContextSection.PROJECT,
            content="Project status: READY",
            source_type=ContextSourceType.DOMAIN_SERVICE,
            authority=ContextAuthority.DOMAIN_SOURCE_OF_TRUTH,
            canonical_key="fact:project:status",
            content_hash=ContextItem.compute_content_hash("Project status: READY"),
        )
        memory_status = ContextItem(
            id="mem_status",
            section=ContextSection.MEMORY,
            content="Project status: DRAFT",
            source_type=ContextSourceType.MEMORY,
            authority=ContextAuthority.DERIVED,
            canonical_key="fact:project:status",
            content_hash=ContextItem.compute_content_hash("Project status: DRAFT"),
        )

        kept, exclusions = dedup.deduplicate([domain_status, memory_status])
        assert len(kept) == 1
        assert kept[0].id == "dom_status"
        assert kept[0].content == "Project status: READY"
        assert len(exclusions) == 1
        assert exclusions[0].reason == ExclusionReason.AUTHORITY_CONFLICT
