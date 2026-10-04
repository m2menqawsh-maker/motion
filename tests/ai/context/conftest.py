"""
tests/ai/context/conftest.py
============================
Shared test fixtures and mock domain services for Context Builder tests (S27.8).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional
from pydantic import BaseModel

from ai.contracts.common import CapabilityType
from ai.contracts.memory import MemoryType
from ai.context.types import (
    ContextAuthority,
    ContextItem,
    ContextRequest,
    ContextSection,
    ContextSourceType,
)
from ai.context.retrieval import KnowledgeDocument
from ai.memory.embeddings import EmbeddingProvider
from ai.memory.models import TrustedTenantContext
from ai.memory.repository import InMemoryMemoryRepository
from ai.memory.service import MemoryService
from ai.memory.types import EpistemicStatus, MemoryScope, SourceType


class MockLifecycleDTO(BaseModel):
    project_id: str
    lifecycle_state: str = "PLAN_READY"
    revision: int = 1
    allowed_actions: List[str] = ["blueprint:edit", "run:execute"]
    blocked_reason: Optional[str] = None
    review: Dict[str, str] = {}
    latest_run: Optional[Dict[str, str]] = None
    artifacts_status: Dict[str, str] = {}


class MockReviewStatusDTO(BaseModel):
    project_id: str
    lifecycle_state: str = "PLAN_READY"
    active_bundle_id: Optional[str] = "bundle_001"
    active_decision: Optional[str] = "APPROVED"
    decision_id: Optional[str] = "dec_001"
    is_stale: bool = False
    blocking_reason: Optional[str] = None


class MockProjectService:
    def __init__(self, projects: Optional[Dict[str, MockLifecycleDTO]] = None):
        self.projects = projects or {}

    def get_lifecycle_dto(self, project_id: str) -> Optional[MockLifecycleDTO]:
        if project_id not in self.projects:
            raise LookupError(f"Project '{project_id}' not found.")
        return self.projects[project_id]


class MockAssetService:
    def __init__(self, assets: Optional[Dict[str, List[Dict[str, str]]]] = None):
        self.assets = assets or {}

    def list_assets(self, project_id: str) -> List[Dict[str, str]]:
        return self.assets.get(project_id, [])


class MockReviewService:
    def __init__(self, reviews: Optional[Dict[str, MockReviewStatusDTO]] = None):
        self.reviews = reviews or {}

    def get_review_status(self, project_id: str) -> MockReviewStatusDTO:
        if project_id in self.reviews:
            return self.reviews[project_id]
        return MockReviewStatusDTO(project_id=project_id)


from ai.memory.embeddings import DeterministicFakeEmbeddingProvider


def make_test_memory_service() -> MemoryService:
    repo = InMemoryMemoryRepository()
    emb = DeterministicFakeEmbeddingProvider(dimension=16)
    return MemoryService(repository=repo, embedding_provider=emb)
