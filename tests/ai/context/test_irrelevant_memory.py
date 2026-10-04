"""
tests/ai/context/test_irrelevant_memory.py
==========================================
Test for Section 54: 100 Memories (90 irrelevant, 10 relevant).
Verifies that only the relevant subset enters context by checking content IDs.
"""

from __future__ import annotations

from datetime import datetime, timezone
import pytest

from ai.contracts.common import CapabilityType
from ai.contracts.memory import MemoryType
from ai.context import (
    ContextBuilder,
    ContextPackage,
    ContextRequest,
    ContextSection,
)
from ai.memory.models import TrustedTenantContext
from ai.memory.types import MemoryScope
from tests.ai.context.conftest import (
    MockLifecycleDTO,
    MockProjectService,
    make_test_memory_service,
)


class TestIrrelevantMemoryFiltering:

    def test_90_unrelated_10_relevant_memories(self):
        """
        Section 54 Gate:
        Populate 100 memories:
        - 90 unrelated (e.g. typography, visual styling, color codes, serif fonts)
        - 10 relevant (e.g. audio loudness, speech pacing, voiceover clarity, denoise preference)
        Request capability is SPEECH_TO_TEXT.
        Expected:
        - Only the 10 relevant audio memories are included.
        - None of the 90 irrelevant memories enter context.
        - Verified by exact content IDs.
        """
        ctx = TrustedTenantContext(workspace_id="ws_1", user_id="u1")
        mem_svc = make_test_memory_service()

        relevant_contents = [
            f"Relevant Audio Preference {i}: Ensure vocal isolation at -16 LUFS and clear denoise."
            for i in range(10)
        ]

        irrelevant_contents = [
            f"Irrelevant Visual Preference {j}: Use serif font typography and pastel color palette."
            for j in range(90)
        ]

        relevant_stored_ids = []
        for rc in relevant_contents:
            ent = mem_svc.store_memory(
                context=ctx,
                content=rc,
                memory_type=MemoryType.USER_PREFERENCE,
                scope=MemoryScope.USER,
                confidence=0.9,
                metadata={"domain": "audio"},
            )
            relevant_stored_ids.append(ent.id)

        irrelevant_stored_ids = []
        for ic in irrelevant_contents:
            ent = mem_svc.store_memory(
                context=ctx,
                content=ic,
                memory_type=MemoryType.USER_PREFERENCE,
                scope=MemoryScope.USER,
                confidence=0.9,
                metadata={"domain": "visual"},
            )
            irrelevant_stored_ids.append(ent.id)

        proj_svc = MockProjectService({
            "prj_1": MockLifecycleDTO(project_id="prj_1", lifecycle_state="ASSETS_READY")
        })

        builder = ContextBuilder(
            project_service=proj_svc,
            memory_service=mem_svc,
        )

        req = ContextRequest(
            request_id="req_audio_filter_test",
            trusted_context=ctx,
            capability=CapabilityType.SPEECH_TO_TEXT,
            project_id="prj_1",
            query_text="Transcribe audio tracks with optimal voice clarity",
            created_at=datetime.now(timezone.utc),
        )

        pkg: ContextPackage = builder.build(req)

        # Audit memory items in context package
        included_memory_source_ids = {it.source_id for it in pkg.memory_context.items}

        # Check 1: All 10 relevant memory IDs are present
        for rel_id in relevant_stored_ids:
            assert rel_id in included_memory_source_ids, f"Expected relevant memory {rel_id} to be included"

        # Check 2: NONE of the 90 irrelevant memory IDs are present
        for irrel_id in irrelevant_stored_ids:
            assert irrel_id not in included_memory_source_ids, f"Irrelevant memory {irrel_id} leaked into context!"

        assert len(pkg.memory_context.items) == 10
