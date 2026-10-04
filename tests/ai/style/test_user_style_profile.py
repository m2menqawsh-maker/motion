"""
tests/ai/style/test_user_style_profile.py
=========================================
Unit tests for UserStyleProfile contract and S27 Memory loading (S28-08A).

Guarantees:
- Strict contract validation: extra fields forbidden, models frozen.
- Optional fields default safely without requiring all dimensions.
- Provenance tracking: each dimension retains epistemic status, confidence, and source.
- Loading from canonical S27 MemoryService obeys tenant and user boundaries.
"""

from __future__ import annotations

from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from ai.contracts.creative.feedback import (
    StylePreferenceProvenance,
    UserStyleProfile,
)
from ai.memory.embeddings import DeterministicFakeEmbeddingProvider
from ai.memory.models import TrustedTenantContext
from ai.memory.policy import MemoryPolicy
from ai.memory.repository import InMemoryMemoryRepository
from ai.memory.service import MemoryService
from ai.memory.types import EpistemicStatus, MemoryScope, MemoryType, SourceType
from ai.style.resolver import UserStyleResolver


@pytest.fixture
def memory_env():
    repo = InMemoryMemoryRepository()
    policy = MemoryPolicy()
    embedder = DeterministicFakeEmbeddingProvider(dimension=64)
    service = MemoryService(repository=repo, embedding_provider=embedder, policy=policy)
    ctx = TrustedTenantContext(workspace_id="ws_style_test", user_id="usr_01")
    return service, ctx


class TestUserStyleProfileContract:

    def test_valid_profile_instantiation(self):
        """UserStyleProfile instantiates cleanly with sparse preferences."""
        now = datetime.now(timezone.utc)
        prof = UserStyleProfile(
            profile_id="prof_123",
            workspace_id="ws_1",
            user_id="usr_1",
            pacing_preference="fast",
            preferred_color_palette=["#FFFFFF", "#000000"],
            updated_at=now,
        )
        assert prof.profile_id == "prof_123"
        assert prof.pacing_preference == "fast"
        assert prof.motion_intensity is None
        assert prof.preferred_color_palette == ["#FFFFFF", "#000000"]
        assert prof.preferred_voices == []

    def test_extra_fields_forbidden(self):
        """Unexpected fields are strictly rejected per AIContractModel policy."""
        now = datetime.now(timezone.utc)
        with pytest.raises(ValidationError):
            UserStyleProfile(
                profile_id="prof_123",
                workspace_id="ws_1",
                updated_at=now,
                unauthorized_custom_field="malicious_payload",  # type: ignore
            )

    def test_profile_immutability(self):
        """UserStyleProfile is an immutable value object."""
        now = datetime.now(timezone.utc)
        prof = UserStyleProfile(
            profile_id="prof_123",
            workspace_id="ws_1",
            pacing_preference="fast",
            updated_at=now,
        )
        with pytest.raises(ValidationError):
            prof.pacing_preference = "slow"  # type: ignore

    def test_provenance_by_dimension_tracking(self):
        """Each preference dimension can record its epistemic provenance."""
        now = datetime.now(timezone.utc)
        prov = StylePreferenceProvenance(
            dimension="pacing",
            epistemic_status=EpistemicStatus.EXPLICIT,
            confidence=0.9,
            source_type=SourceType.USER_STATEMENT,
            evidence_count=2,
            last_observed_at=now,
            rationale="User explicitly requested fast pacing in prompt",
        )
        prof = UserStyleProfile(
            profile_id="prof_123",
            workspace_id="ws_1",
            pacing_preference="fast",
            provenance_by_dimension={"pacing": prov},
            updated_at=now,
        )
        assert "pacing" in prof.provenance_by_dimension
        assert prof.provenance_by_dimension["pacing"].epistemic_status == EpistemicStatus.EXPLICIT
        assert prof.provenance_by_dimension["pacing"].confidence == 0.9


class TestUserStyleLoader:

    def test_load_empty_profile(self, memory_env):
        """When no preferences exist, load_profile returns a clean default profile."""
        service, ctx = memory_env
        profile = UserStyleResolver.load_profile(ctx, service)

        assert profile.workspace_id == ctx.workspace_id
        assert profile.user_id == ctx.user_id
        assert profile.pacing_preference is None
        assert profile.motion_intensity is None
        assert profile.provenance_by_dimension == {}

    def test_load_profile_from_canonical_memory(self, memory_env):
        """Loads and synthesizes preferences stored in S27 Memory."""
        service, ctx = memory_env

        # 1. Store pacing preference
        service.store_memory(
            context=ctx,
            content="User preference for pacing: fast",
            memory_type=MemoryType.USER_PREFERENCE,
            scope=MemoryScope.USER,
            confidence=0.9,
            epistemic_status=EpistemicStatus.EXPLICIT,
            structured_payload={"dimension": "pacing", "value": "fast"},
            metadata={"dimension": "pacing", "value": "fast", "evidence_count": 1},
        )

        # 2. Store motion intensity preference
        service.store_memory(
            context=ctx,
            content="User preference for motion_intensity: low",
            memory_type=MemoryType.USER_PREFERENCE,
            scope=MemoryScope.USER,
            confidence=0.7,
            epistemic_status=EpistemicStatus.INFERRED,
            structured_payload={"dimension": "motion_intensity", "value": "low"},
            metadata={"dimension": "motion_intensity", "value": "low", "evidence_count": 2},
        )

        # 3. Store color palette
        service.store_memory(
            context=ctx,
            content="User preference for preferred_color_palette: #00FFCC",
            memory_type=MemoryType.USER_PREFERENCE,
            scope=MemoryScope.USER,
            confidence=0.95,
            epistemic_status=EpistemicStatus.CONFIRMED,
            structured_payload={"dimension": "preferred_color_palette", "value": "#00FFCC"},
            metadata={"dimension": "preferred_color_palette", "value": "#00FFCC"},
        )

        profile = UserStyleResolver.load_profile(ctx, service)

        assert profile.pacing_preference == "fast"
        assert profile.motion_intensity == "low"
        assert "#00FFCC" in profile.preferred_color_palette

        # Verify dimension provenance
        assert "pacing" in profile.provenance_by_dimension
        assert profile.provenance_by_dimension["pacing"].epistemic_status == EpistemicStatus.EXPLICIT
        assert profile.provenance_by_dimension["pacing"].confidence == 0.9

        assert "motion_intensity" in profile.provenance_by_dimension
        assert profile.provenance_by_dimension["motion_intensity"].epistemic_status == EpistemicStatus.INFERRED
        assert profile.provenance_by_dimension["motion_intensity"].confidence == 0.7

    def test_load_profile_enforces_user_and_tenant_isolation(self, memory_env):
        """User A's profile cannot see User B's preferences or Tenant B's preferences."""
        service, ctx_a = memory_env

        # Store preference for user A
        service.store_memory(
            context=ctx_a,
            content="User preference for pacing: fast",
            memory_type=MemoryType.USER_PREFERENCE,
            scope=MemoryScope.USER,
            user_id="usr_01",
            structured_payload={"dimension": "pacing", "value": "fast"},
            metadata={"dimension": "pacing", "value": "fast"},
        )

        # Context for User B in same workspace
        ctx_b = TrustedTenantContext(workspace_id=ctx_a.workspace_id, user_id="usr_02")

        profile_b = UserStyleResolver.load_profile(ctx_b, service)
        # User B should NOT see user A's pacing preference
        assert profile_b.pacing_preference is None
        assert "pacing" not in profile_b.provenance_by_dimension

        # Context for Tenant C (different workspace)
        ctx_c = TrustedTenantContext(workspace_id="ws_other_workspace", user_id="usr_01")
        profile_c = UserStyleResolver.load_profile(ctx_c, service)
        assert profile_c.pacing_preference is None
