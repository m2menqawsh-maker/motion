"""
tests/ai/memory/test_write_policy.py
===================================
Unit tests for MemoryPolicy write governance, epistemic classification,
worth-remembering filter, sensitive credential rejection, and dedup (S27.7).
"""

from datetime import datetime, timezone
import pytest

from ai.memory.embeddings import DeterministicFakeEmbeddingProvider
from ai.memory.models import (
    MemoryCandidate,
    MemoryFilter,
    TrustedTenantContext,
)
from ai.memory.policy import MemoryPolicy, MemoryPolicyConfig
from ai.memory.repository import InMemoryMemoryRepository
from ai.memory.service import MemoryService
from ai.memory.types import (
    ConfidenceLevel,
    EpistemicStatus,
    MemoryScope,
    MemoryStatus,
    MemoryType,
    SourceType,
    WriteDecisionType,
)


class TestMemoryWritePolicy:

    @pytest.fixture
    def setup_policy_env(self):
        repo = InMemoryMemoryRepository()
        policy = MemoryPolicy()
        embedder = DeterministicFakeEmbeddingProvider(dimension=64)
        service = MemoryService(repository=repo, embedding_provider=embedder, policy=policy)
        ctx = TrustedTenantContext(workspace_id="ws_policy_test", user_id="usr_01")
        return service, repo, policy, ctx

    def test_explicit_preference_approved_for_storage(self, setup_policy_env):
        """User explicit preference is classified as EXPLICIT, HIGH confidence, and STORED."""
        service, repo, policy, ctx = setup_policy_env

        cand = MemoryCandidate(
            proposed_type=MemoryType.USER_PREFERENCE,
            proposed_scope=MemoryScope.USER,
            content="لا تستخدم transitions مزعجة معي واعتمد الـ Cut المباشر فقط",
            source_type=SourceType.USER_STATEMENT,
            user_id="usr_01",
        )

        decision = service.propose_candidate(ctx, cand)

        assert decision.decision_type == WriteDecisionType.STORE
        assert decision.epistemic_status == EpistemicStatus.EXPLICIT
        assert decision.final_confidence == 0.9
        assert decision.final_confidence_level == ConfidenceLevel.HIGH
        assert decision.target_entry_id is not None

        # Verify entry exists in repository
        stored = repo.get(decision.target_entry_id, ctx.workspace_id)
        assert stored is not None
        assert stored.status == MemoryStatus.ACTIVE

    def test_single_inferred_action_requires_confirmation(self, setup_policy_env):
        """Single inferred behavior does NOT become permanent memory without confirmation."""
        service, repo, policy, ctx = setup_policy_env

        cand = MemoryCandidate(
            proposed_type=MemoryType.USER_PREFERENCE,
            proposed_scope=MemoryScope.USER,
            content="User prefers 1.5x playback speed based on one timeline adjustment",
            source_type=SourceType.AI_INFERENCE,
            evidence=["Single timeline speed slider adjustment"],
            user_id="usr_01",
        )

        decision = service.propose_candidate(ctx, cand)

        assert decision.decision_type == WriteDecisionType.REQUIRE_CONFIRMATION
        assert decision.epistemic_status == EpistemicStatus.INFERRED
        assert decision.final_confidence == 0.4
        assert decision.target_entry_id is None

        # Verify nothing was persisted in repository
        entries = repo.query_structured(MemoryFilter(workspace_id=ctx.workspace_id))
        assert len(entries) == 0

    def test_inferred_preference_with_sufficient_evidence_approved(self, setup_policy_env):
        """Inference with >= 3 distinct evidence items meets the promotion threshold."""
        service, repo, policy, ctx = setup_policy_env

        cand = MemoryCandidate(
            proposed_type=MemoryType.USER_PREFERENCE,
            proposed_scope=MemoryScope.USER,
            content="User prefers dark theme canvas background",
            source_type=SourceType.AI_INFERENCE,
            evidence=[
                "Session 1: switched to dark mode",
                "Session 2: set background to #121212",
                "Session 3: rejected light theme template",
            ],
            user_id="usr_01",
        )

        decision = service.propose_candidate(ctx, cand)
        assert decision.decision_type == WriteDecisionType.STORE

    def test_human_confirmed_preference_approved(self, setup_policy_env):
        """Human confirmation grants CONFIRMED epistemic status and HIGH confidence."""
        service, repo, policy, ctx = setup_policy_env

        cand = MemoryCandidate(
            proposed_type=MemoryType.USER_PREFERENCE,
            proposed_scope=MemoryScope.USER,
            content="Confirmed: Subtitle font must be Amiri with yellow highlight",
            source_type=SourceType.HUMAN_CONFIRMATION,
            user_id="usr_01",
        )

        decision = service.propose_candidate(ctx, cand)

        assert decision.decision_type == WriteDecisionType.STORE
        assert decision.epistemic_status == EpistemicStatus.CONFIRMED
        assert decision.final_confidence == 0.95
        assert decision.final_confidence_level == ConfidenceLevel.HIGH

    def test_small_talk_and_greetings_rejected(self, setup_policy_env):
        """Greetings, filler, and trivial small talk are rejected as not worth remembering."""
        service, repo, policy, ctx = setup_policy_env

        trivial_inputs = [
            "Hello",
            "مرحبا",
            "صباح الخير",
            "How are you today?",
            "شكرا لك",
            "ok",
            "تمام يا بطل",
            "Bye!",
        ]

        for text in trivial_inputs:
            cand = MemoryCandidate(
                proposed_type=MemoryType.CONVERSATION,
                proposed_scope=MemoryScope.SESSION,
                content=text,
                source_type=SourceType.USER_STATEMENT,
            )
            decision = service.propose_candidate(ctx, cand)
            assert decision.decision_type == WriteDecisionType.REJECT
            assert decision.reason_code == "NOT_WORTH_REMEMBERING_TRIVIAL"

    def test_ephemeral_execution_requests_rejected(self, setup_policy_env):
        """Temporary requests are not long-term memories and must be rejected."""
        service, repo, policy, ctx = setup_policy_env

        ephemeral_inputs = [
            "render now please",
            "show me the preview",
            "display status of run",
            "أرني المعاينة الآن",
            "ابدأ الرندر فورا",
        ]

        for text in ephemeral_inputs:
            cand = MemoryCandidate(
                proposed_type=MemoryType.WORKING,
                proposed_scope=MemoryScope.SESSION,
                content=text,
                source_type=SourceType.USER_STATEMENT,
            )
            decision = service.propose_candidate(ctx, cand)
            assert decision.decision_type == WriteDecisionType.REJECT
            assert decision.reason_code == "NOT_WORTH_REMEMBERING_EPHEMERAL"

    def test_ai_speculation_without_evidence_rejected(self, setup_policy_env):
        """Ungrounded model speculation is rejected."""
        service, repo, policy, ctx = setup_policy_env

        cand = MemoryCandidate(
            proposed_type=MemoryType.USER_PREFERENCE,
            proposed_scope=MemoryScope.USER,
            content="Maybe the user likes aggressive 3D transitions and loud music",
            source_type=SourceType.AI_INFERENCE,
            evidence=[],  # No evidence!
        )

        decision = service.propose_candidate(ctx, cand)
        assert decision.decision_type == WriteDecisionType.REJECT
        assert decision.reason_code == "NOT_WORTH_REMEMBERING_SPECULATION"

    def test_sensitive_credentials_rejected(self, setup_policy_env):
        """API keys, bearer tokens, passwords, and private keys are rejected."""
        service, repo, policy, ctx = setup_policy_env

        secret_candidates = [
            "My OpenAI key is sk-proj1234567890abcdef1234567890",  # pragma: allowlist
            "Connect using Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.secrettoken",
            "Google API key: AIzaSyA1234567890abcdef1234567890abcdef",
            "Server RSA key: -----BEGIN RSA PRIVATE KEY----- MIIEowIBAAKCAQEA...",  # pragma: allowlist
            "DB password: password=supersecretpass123",
        ]

        for secret_text in secret_candidates:
            cand = MemoryCandidate(
                proposed_type=MemoryType.KNOWLEDGE,
                proposed_scope=MemoryScope.WORKSPACE,
                content=secret_text,
                source_type=SourceType.USER_STATEMENT,
            )
            decision = service.propose_candidate(ctx, cand)
            assert decision.decision_type == WriteDecisionType.REJECT
            assert decision.reason_code == "SENSITIVE_DATA_DETECTED"

    def test_global_scope_rejection_for_tenant_content(self, setup_policy_env):
        """Tenant proposing scope = GLOBAL is rejected by policy."""
        service, repo, policy, ctx = setup_policy_env

        cand = MemoryCandidate(
            proposed_type=MemoryType.USER_PREFERENCE,
            proposed_scope=MemoryScope.GLOBAL,  # Illegal!
            content="User prefers 4K exports for all projects across the platform",
            source_type=SourceType.USER_STATEMENT,
        )

        decision = service.propose_candidate(ctx, cand)
        assert decision.decision_type == WriteDecisionType.REJECT
        assert decision.reason_code == "GLOBAL_SCOPE_RESTRICTED"

    def test_repeated_preference_merged_and_reinforced(self, setup_policy_env):
        """Repeating the exact same preference 5 times merges into 1 memory, reinforcing confidence."""
        service, repo, policy, ctx = setup_policy_env

        pref_text = "Always use Cairo font for all project titles"

        cand1 = MemoryCandidate(
            proposed_type=MemoryType.USER_PREFERENCE,
            proposed_scope=MemoryScope.USER,
            content=pref_text,
            source_type=SourceType.USER_STATEMENT,
            user_id="usr_01",
            suggested_confidence=0.85,
        )

        # 1st time: STORE
        d1 = service.propose_candidate(ctx, cand1)
        assert d1.decision_type == WriteDecisionType.STORE
        target_id = d1.target_entry_id

        # 2nd through 5th time: MERGE
        for _ in range(4):
            cand_repeat = MemoryCandidate(
                proposed_type=MemoryType.USER_PREFERENCE,
                proposed_scope=MemoryScope.USER,
                content=f"  {pref_text}  \n",  # slight whitespace variance
                source_type=SourceType.USER_STATEMENT,
                user_id="usr_01",
            )
            d_repeat = service.propose_candidate(ctx, cand_repeat)
            assert d_repeat.decision_type == WriteDecisionType.MERGE
            assert d_repeat.target_entry_id == target_id

        # Assert only 1 active memory exists in the repository
        entries = repo.query_structured(MemoryFilter(workspace_id=ctx.workspace_id))
        assert len(entries) == 1
        assert entries[0].id == target_id
        assert entries[0].metadata["evidence_count"] == 5

    def test_contradictory_preference_superseded(self, setup_policy_env):
        """New contradictory preference supersedes the old one, preserving audit history."""
        service, repo, policy, ctx = setup_policy_env

        # 1. Old preference: fast cuts
        cand_old = MemoryCandidate(
            proposed_type=MemoryType.USER_PREFERENCE,
            proposed_scope=MemoryScope.USER,
            content="I prefer fast cuts of 1 second per scene",
            source_type=SourceType.USER_STATEMENT,
            user_id="usr_01",
        )
        d_old = service.propose_candidate(ctx, cand_old)
        assert d_old.decision_type == WriteDecisionType.STORE
        old_id = d_old.target_entry_id

        # 2. New preference: slow cuts
        cand_new = MemoryCandidate(
            proposed_type=MemoryType.USER_PREFERENCE,
            proposed_scope=MemoryScope.USER,
            content="I now prefer slow cuts of 4 seconds per scene",
            source_type=SourceType.USER_STATEMENT,
            user_id="usr_01",
        )
        d_new = service.propose_candidate(ctx, cand_new)

        assert d_new.decision_type == WriteDecisionType.SUPERSEDE
        assert d_new.supersedes_id == old_id

        # 3. Check repository state:
        # Normal query returns ONLY the active new preference
        active_entries = repo.query_structured(MemoryFilter(workspace_id=ctx.workspace_id))
        assert len(active_entries) == 1
        assert active_entries[0].id == d_new.target_entry_id
        assert active_entries[0].version == 2
        assert active_entries[0].supersedes_id == old_id

        # Old entry is retained as SUPERSEDED for auditability
        old_entry = repo.get(old_id, ctx.workspace_id)
        assert old_entry.status == MemoryStatus.SUPERSEDED
