"""
tests/ai/memory/test_100_messages.py
====================================
100-Message Mandatory Gate Test for S27.7.

Feeds 100 diverse conversation messages into the Memory system:
- 25 Greetings and small talk -> 0 memories
- 30 Ephemeral requests -> 0 memories
- 15 Ungrounded model speculations -> 0 memories
- 5 Accidental secret/credential leaks -> 0 memories
- 10 Repeated identical preferences -> 1 active memory (reinforced)
- 5 Progressive contradictory preference updates -> 1 active memory (superseded)
- 5 Unique explicit user preferences -> 5 active memories
- 5 Unique project decisions -> 5 active memories

Strict Deterministic Assertion:
Expected active long-term memories created: EXACTLY 12 (NOT 100).
"""

import pytest

from ai.memory.embeddings import DeterministicFakeEmbeddingProvider
from ai.memory.models import (
    MemoryCandidate,
    MemoryFilter,
    TrustedTenantContext,
)
from ai.memory.policy import MemoryPolicy
from ai.memory.repository import InMemoryMemoryRepository
from ai.memory.service import MemoryService
from ai.memory.types import (
    MemoryScope,
    MemoryStatus,
    MemoryType,
    SourceType,
)


class Test100MessagesGate:

    @pytest.fixture
    def setup_system(self):
        repo = InMemoryMemoryRepository()
        policy = MemoryPolicy()
        embedder = DeterministicFakeEmbeddingProvider(dimension=64)
        service = MemoryService(repository=repo, embedding_provider=embedder, policy=policy)
        ctx = TrustedTenantContext(workspace_id="ws_100_msgs", user_id="usr_producer")
        return service, repo, ctx

    def test_100_messages_produces_deterministic_12_memories(self, setup_system):
        """
        Feeds exactly 100 structured candidate proposals.
        Asserts that trivial chatter, secrets, ephemeral requests, and speculations
        are rejected, duplicates are merged, contradictions are superseded,
        resulting in exactly 12 active canonical memories.
        """
        service, repo, ctx = setup_system

        messages = []

        # 1. 25 Greetings and small talk
        greetings = [
            "Hello there", "مرحبا بك", "Good morning", "صباح النور والسرور",
            "Hey", "How are you doing?", "كيف حالك يا باشا", "Thanks a lot",
            "شكرا جزيلا", "OK", "تمام", "Cool", "Nice job", "Got it", "مع السلامة",
            "Bye", "Yes", "نعم", "No", "لا", "Sure thing", "ماشي يا غالي",
            "Thank you very much", "تسلم ايدك", "Good evening",
        ]
        assert len(greetings) == 25
        for g in greetings:
            messages.append(
                MemoryCandidate(
                    proposed_type=MemoryType.CONVERSATION,
                    proposed_scope=MemoryScope.SESSION,
                    content=g,
                    source_type=SourceType.USER_STATEMENT,
                )
            )

        # 2. 30 Ephemeral execution requests
        ephemerals = [
            f"render now item #{i}" for i in range(10)
        ] + [
            f"show me the preview of frame {i}" for i in range(10)
        ] + [
            f"أرني المعاينة للمشهد {i}" for i in range(10)
        ]
        assert len(ephemerals) == 30
        for ep in ephemerals:
            messages.append(
                MemoryCandidate(
                    proposed_type=MemoryType.WORKING,
                    proposed_scope=MemoryScope.SESSION,
                    content=ep,
                    source_type=SourceType.USER_STATEMENT,
                )
            )

        # 3. 15 Ungrounded model speculations
        speculations = [
            f"Maybe the user wants 3D rotation effects on title #{i}" for i in range(8)
        ] + [
            f"ربما يفضل المستخدم موسيقى صاخبة في المقطع {i}" for i in range(7)
        ]
        assert len(speculations) == 15
        for sp in speculations:
            messages.append(
                MemoryCandidate(
                    proposed_type=MemoryType.USER_PREFERENCE,
                    proposed_scope=MemoryScope.USER,
                    content=sp,
                    source_type=SourceType.AI_INFERENCE,
                    evidence=[],  # Ungrounded!
                )
            )

        # 4. 5 Accidental secret/credential leaks
        secrets = [
            "OpenAI API token: sk-proj99887766554433221100aabbccdd",  # pragma: allowlist
            "Google Cloud key: AIzaSyD9876543210zyxwvutsrqponmlkjihgfedcba",
            "Auth header: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.dummy_token_data",
            "Server Key: -----BEGIN RSA PRIVATE KEY----- MIICXAIBAAKCAQEA0...",  # pragma: allowlist
            "Database config: password=SuperSecretRootPassword99!",
        ]
        assert len(secrets) == 5
        for sec in secrets:
            messages.append(
                MemoryCandidate(
                    proposed_type=MemoryType.KNOWLEDGE,
                    proposed_scope=MemoryScope.WORKSPACE,
                    content=sec,
                    source_type=SourceType.USER_STATEMENT,
                )
            )

        # 5. 10 Repeated identical preferences (same preference repeated 10 times)
        for i in range(10):
            messages.append(
                MemoryCandidate(
                    proposed_type=MemoryType.USER_PREFERENCE,
                    proposed_scope=MemoryScope.USER,
                    content="Always use Cairo font for main headings and titles",
                    source_type=SourceType.USER_STATEMENT,
                    user_id=ctx.user_id,
                )
            )

        # 6. 5 Progressive contradictory preference updates
        contradictory_cuts = [
            "I prefer fast cuts of 1.0 second per scene",
            "I prefer fast cuts of 1.2 seconds per scene",
            "I prefer cuts of 2.0 seconds per scene",
            "I prefer slow cuts of 3.0 seconds per scene",
            "I now prefer slow cinematic cuts of 4.5 seconds per scene",
        ]
        assert len(contradictory_cuts) == 5
        for c in contradictory_cuts:
            messages.append(
                MemoryCandidate(
                    proposed_type=MemoryType.USER_PREFERENCE,
                    proposed_scope=MemoryScope.USER,
                    content=c,
                    source_type=SourceType.USER_STATEMENT,
                    user_id=ctx.user_id,
                )
            )

        # 7. 5 Unique explicit user preferences
        explicit_prefs = [
            "Primary brand accent color is #FF6B00 amber orange",
            "Default subtitle size should be 28px with semi-transparent black pill box",
            "Default aspect ratio for social exports is 9:16 vertical",
            "Pacing should emphasize high energy in the first 3 seconds",
            "All primary voiceovers should be in Modern Standard Arabic (الفصحى)",
        ]
        assert len(explicit_prefs) == 5
        for ep in explicit_prefs:
            messages.append(
                MemoryCandidate(
                    proposed_type=MemoryType.USER_PREFERENCE,
                    proposed_scope=MemoryScope.USER,
                    content=ep,
                    source_type=SourceType.USER_STATEMENT,
                    user_id=ctx.user_id,
                )
            )

        # 8. 5 Unique confirmed project decisions
        project_decisions = [
            "Decision: Master export resolution is locked to 1080x1920 at 30 fps",
            "Decision: Dialog audio track must be normalized to -16 LUFS integrated",
            "Decision: Hook scene duration must be strictly 3.5 seconds",
            "Decision: Outro logo sting duration must be exactly 2.0 seconds with sound mark",
            "Decision: Deliverable container format is MP4 with H.264 video and AAC audio",
        ]
        assert len(project_decisions) == 5
        for pd in project_decisions:
            messages.append(
                MemoryCandidate(
                    proposed_type=MemoryType.DECISION,
                    proposed_scope=MemoryScope.PROJECT,
                    project_id="prj_main",
                    content=pd,
                    source_type=SourceType.DECISION,
                )
            )

        # TOTAL MESSAGE COUNT ASSERTION: EXACTLY 100
        assert len(messages) == 100, f"Expected 100 test messages, got {len(messages)}"

        # PROCESS ALL 100 MESSAGES THROUGH MEMORY SERVICE & POLICY
        decisions = []
        for msg in messages:
            d = service.propose_candidate(ctx, msg)
            decisions.append(d)

        assert len(decisions) == 100

        # RETRIEVE ACTIVE LONG-TERM MEMORIES
        active_entries = repo.query_structured(
            MemoryFilter(
                workspace_id=ctx.workspace_id,
                limit=100,
            )
        )

        # STRICT DETERMINISTIC ASSERTIONS
        # 1. Must NOT be 100 memories
        assert len(active_entries) != 100

        # 2. Must be EXACTLY 12 active memories:
        # - 1 repeated preference (reinforced)
        # - 1 contradictory preference (superseded to latest)
        # - 5 explicit brand preferences
        # - 5 confirmed project decisions
        # Total = 1 + 1 + 5 + 5 = 12
        assert len(active_entries) == 12, (
            f"Expected exactly 12 active canonical memories from 100 messages, "
            f"but found {len(active_entries)}: {[e.content for e in active_entries]}"
        )

        # Verify old superseded memories are kept for audit history
        all_entries = repo.query_structured(
            MemoryFilter(
                workspace_id=ctx.workspace_id,
                include_inactive=True,
                limit=100,
            )
        )
        superseded = [e for e in all_entries if e.status == MemoryStatus.SUPERSEDED]
        assert len(superseded) == 4, f"Expected 4 superseded cut preferences, got {len(superseded)}"
