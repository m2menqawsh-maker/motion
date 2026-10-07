"""
tests/ai/context/test_builder.py
================================
Unit and integration tests for ContextBuilder facade (S27.8).
"""

from __future__ import annotations

from datetime import datetime, timezone
import pytest

from ai.contracts.common import CapabilityType
from ai.context import (
    ContextBuilder,
    ContextPackage,
    ContextRequest,
    ContextSection,
    DeterministicKnowledgeRetriever,
    KnowledgeDocument,
)
from ai.memory.models import TrustedTenantContext
from tests.ai.context.conftest import (
    MockLifecycleDTO,
    MockProjectService,
    MockAssetService,
    MockReviewService,
    make_test_memory_service,
)


class TestContextBuilder:

    def test_basic_context_build(self):
        ctx = TrustedTenantContext(
            workspace_id="ws_alpha",
            user_id="usr_alice",
            accessible_projects=["prj_100"],
        )
        proj_service = MockProjectService({
            "prj_100": MockLifecycleDTO(
                project_id="prj_100",
                lifecycle_state="PLAN_READY",
                revision=2,
                allowed_actions=["blueprint:edit", "run:execute"],
            )
        })
        asset_service = MockAssetService({
            "prj_100": [
                {"asset_id": "ast_01", "filename": "voice.mp3", "kind": "AUDIO", "status": "READY"}
            ]
        })
        review_service = MockReviewService()
        memory_service = make_test_memory_service()

        knowledge_retriever = DeterministicKnowledgeRetriever([
            KnowledgeDocument(
                doc_id="playbook_video_flow",
                title="Video Production Playbook",
                content="Standard cinematic pacing rules for 9:16 portrait reels.",
                tags=["planning", "workflow"],
            )
        ])

        builder = ContextBuilder(
            project_service=proj_service,
            asset_service=asset_service,
            review_service=review_service,
            memory_service=memory_service,
            knowledge_retriever=knowledge_retriever,
        )

        request = ContextRequest(
            request_id="req_001",
            trusted_context=ctx,
            capability=CapabilityType.PLANNING,
            project_id="prj_100",
            query_text="Build the scene composition plan for this reel",
            created_at=datetime.now(timezone.utc),
        )

        package: ContextPackage = builder.build(request)

        assert isinstance(package, ContextPackage)
        assert package.request_id == "req_001"
        assert package.context_hash is not None
        assert len(package.context_hash) == 64

        # Verify all 9 canonical sections exist
        assert package.system_policy.section == ContextSection.SYSTEM
        assert len(package.system_policy.items) >= 1

        assert package.tool_schema_context.section == ContextSection.TOOLS
        assert len(package.tool_schema_context.items) == 0  # S27.9 placeholder

        assert package.shared_context.section == ContextSection.SHARED
        assert len(package.shared_context.items) >= 1

        assert package.project_context.section == ContextSection.PROJECT
        assert len(package.project_context.items) >= 2  # status, revision, allowed_actions

        assert package.knowledge_context.section == ContextSection.KNOWLEDGE
        assert len(package.knowledge_context.items) >= 1

        assert package.current_request.section == ContextSection.REQUEST
        assert len(package.current_request.items) == 1

        # Check diagnostics
        diag = package.diagnostics
        assert diag.total_candidates_retrieved > 0
        assert diag.total_items_included > 0
        assert diag.total_estimated_tokens > 0
        assert diag.budget_ceiling > 0
        assert diag.total_estimated_tokens <= diag.budget_ceiling

        # Check all_items ordering
        all_items = package.all_items()
        assert len(all_items) == diag.total_items_included

        # Verify prompt representations
        prompt_text = package.to_prompt_text()
        assert "=== SYSTEM POLICY & DIRECTIVES ===" in prompt_text
        assert "=== CANONICAL PROJECT FACTS (AUTHORITATIVE) ===" in prompt_text
        assert "Project status: PLAN_READY" in prompt_text
        assert "=== CURRENT REQUEST ===" in prompt_text

        messages = package.to_messages()
        assert len(messages) >= 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert "Build the scene composition plan" in messages[1]["content"]

    def test_item_provenance_tracking(self):
        ctx = TrustedTenantContext(
            workspace_id="ws_alpha",
            user_id="usr_alice",
            accessible_projects=["prj_100"],
        )
        proj_service = MockProjectService({
            "prj_100": MockLifecycleDTO(project_id="prj_100", lifecycle_state="DRAFT")
        })
        builder = ContextBuilder(project_service=proj_service)

        request = ContextRequest(
            request_id="req_002",
            trusted_context=ctx,
            capability=CapabilityType.TEXT_GENERATION,
            project_id="prj_100",
            query_text="Write headline",
            created_at=datetime.now(timezone.utc),
        )

        package = builder.build(request)

        for item in package.all_items():
            assert item.id
            assert item.section
            assert item.content
            assert item.source_type
            assert item.authority
            assert item.content_hash
            assert item.estimated_tokens > 0
