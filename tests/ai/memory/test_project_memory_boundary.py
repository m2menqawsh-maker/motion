"""
tests/ai/memory/test_project_memory_boundary.py
===============================================
Tests verifying Project Memory does NOT shadow or duplicate Project DB (S27.6).
"""

from unittest.mock import MagicMock
import pytest

from ai.memory.embeddings import DeterministicFakeEmbeddingProvider
from ai.memory.facade import (
    ProjectAccessDeniedError,
    ProjectMemoryFacade,
    ProjectNotFoundError,
)
from ai.memory.models import TrustedTenantContext
from ai.memory.repository import InMemoryMemoryRepository
from ai.memory.service import MemoryService
from ai.memory.types import MemoryScope, MemoryType, SourceType


class TestProjectMemoryBoundary:

    @pytest.fixture
    def setup_facade(self):
        embedder = DeterministicFakeEmbeddingProvider(dimension=64)
        repo = InMemoryMemoryRepository()
        service = MemoryService(repository=repo, embedding_provider=embedder)

        # Mock Domain ProjectService
        mock_proj_service = MagicMock()
        facade = ProjectMemoryFacade(
            memory_service=service,
            project_service=mock_proj_service,
        )
        return facade, service, mock_proj_service

    def test_project_memory_facade_separates_facts_from_learned_insights(self, setup_facade):
        """Verifies domain facts come from ProjectService while learned insights come from MemoryService."""
        facade, service, mock_proj_service = setup_facade

        ctx = TrustedTenantContext(
            workspace_id="ws_demo",
            user_id="usr_editor",
            accessible_projects=["prj_101"],
        )

        # 1. Domain service returns canonical facts
        mock_proj_service.get_lifecycle_dto.return_value = {
            "project_id": "prj_101",
            "lifecycle_state": "READY_FOR_RENDER",
            "revision": 3,
            "render_fps": 30,
        }

        # 2. Store learned decision in MemoryService
        service.store_memory(
            context=ctx,
            content="Color grading decision: Warm tint applied to intro scene.",
            memory_type=MemoryType.DECISION,
            scope=MemoryScope.PROJECT,
            project_id="prj_101",
            source_type=SourceType.DECISION,
        )

        # 3. Retrieve through Facade
        bundle = facade.get_project_context(ctx, "prj_101")

        assert bundle["project_id"] == "prj_101"
        # Domain facts come from ProjectService
        assert bundle["domain_facts"]["lifecycle_state"] == "READY_FOR_RENDER"
        assert bundle["domain_facts"]["render_fps"] == 30

        # Learned memories come from MemoryService
        assert len(bundle["learned_memories"]) == 1
        assert "Warm tint" in bundle["learned_memories"][0]["content"]

    def test_deleted_project_raises_project_not_found(self, setup_facade):
        """If a project is deleted in ProjectService, facade refuses to expose stale memories."""
        facade, service, mock_proj_service = setup_facade

        ctx = TrustedTenantContext(
            workspace_id="ws_demo",
            user_id="usr_editor",
            accessible_projects=["prj_deleted"],
        )

        # ProjectService reports project not found / None
        mock_proj_service.get_lifecycle_dto.return_value = None

        with pytest.raises(ProjectNotFoundError, match="deleted"):
            facade.get_project_context(ctx, "prj_deleted")

    def test_unauthorized_project_raises_access_denied(self, setup_facade):
        """If user lacks permission for the project, access is immediately denied."""
        facade, service, mock_proj_service = setup_facade

        ctx = TrustedTenantContext(
            workspace_id="ws_demo",
            user_id="usr_unauthorized",
            accessible_projects=["prj_other"],
        )

        with pytest.raises(ProjectAccessDeniedError, match="does not have access"):
            facade.get_project_context(ctx, "prj_forbidden")
