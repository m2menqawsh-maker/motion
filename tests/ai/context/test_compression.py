"""
tests/ai/context/test_compression.py
====================================
Tests for bounded deterministic context compression (S27.8).
"""

from __future__ import annotations

import pytest

from ai.context import (
    ContextAuthority,
    ContextItem,
    ContextSection,
    ContextSourceType,
    DeterministicContextCompressor,
    DeterministicTokenEstimator,
)


class TestContextCompression:

    def test_compression_of_large_knowledge_item(self):
        compressor = DeterministicContextCompressor(default_max_chars=300)
        estimator = DeterministicTokenEstimator()

        long_content = (
            "This is a comprehensive playbook for video editing and storytelling. "
            "Pacing must be tight in the first 3 seconds with a high energy visual hook. "
            "Transitions should be seamless and use motion blur. Audio normalization must strictly "
            "adhere to -16 LUFS for voiceover and -24 LUFS for background music and effects. "
            "Typography must never cover the speaker's mouth or overlap other text elements. "
            "Color grading should be cinematic with high contrast."
        )
        assert len(long_content) > 400

        item = ContextItem(
            id="know_large",
            section=ContextSection.KNOWLEDGE,
            content=long_content,
            source_type=ContextSourceType.KNOWLEDGE,
            authority=ContextAuthority.DERIVED,
            content_hash=ContextItem.compute_content_hash(long_content),
            estimated_tokens=estimator.estimate_tokens(long_content),
        )

        compressed = compressor.compress_item(item, max_chars=250, estimator=estimator)

        assert compressed.compressed is True
        assert len(compressed.content) < len(long_content)
        assert "[Compressed: trimmed from" in compressed.content
        assert compressed.estimated_tokens < item.estimated_tokens
        assert compressed.content_hash != item.content_hash

    def test_protected_items_never_compressed(self):
        compressor = DeterministicContextCompressor(default_max_chars=100)

        # 1. System policy
        sys_item = ContextItem(
            id="sys_1",
            section=ContextSection.SYSTEM,
            content="A " * 200,
            source_type=ContextSourceType.SYSTEM_POLICY,
            authority=ContextAuthority.SYSTEM_AUTHORITY,
            content_hash="h_sys",
        )
        assert compressor.is_compressible(sys_item) is False
        res_sys = compressor.compress_item(sys_item, max_chars=50)
        assert res_sys.compressed is False

        # 2. Current request
        req_item = ContextItem(
            id="req_1",
            section=ContextSection.REQUEST,
            content="B " * 200,
            source_type=ContextSourceType.REQUEST_PAYLOAD,
            authority=ContextAuthority.EXPLICIT_USER,
            content_hash="h_req",
        )
        assert compressor.is_compressible(req_item) is False
        res_req = compressor.compress_item(req_item, max_chars=50)
        assert res_req.compressed is False

        # 3. Core project status
        proj_item = ContextItem(
            id="proj_status",
            section=ContextSection.PROJECT,
            content="Project status: " + ("READY " * 50),
            source_type=ContextSourceType.DOMAIN_SERVICE,
            authority=ContextAuthority.DOMAIN_SOURCE_OF_TRUTH,
            canonical_key="fact:project:status",
            content_hash="h_stat",
        )
        assert compressor.is_compressible(proj_item) is False
        res_proj = compressor.compress_item(proj_item, max_chars=50)
        assert res_proj.compressed is False
