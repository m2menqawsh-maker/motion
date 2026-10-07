"""
tests/ai/memory/test_large_artifacts.py
======================================
Tests verifying large artifact handling via StorageService boundary (S27.6).
"""

import hashlib
import tempfile
from pathlib import Path
import pytest

from ai.memory.embeddings import DeterministicFakeEmbeddingProvider
from ai.memory.facade import ProjectMemoryFacade
from ai.memory.models import TrustedTenantContext
from ai.memory.repository import InMemoryMemoryRepository
from ai.memory.service import MemoryService
from ai.memory.types import MemoryType
from scripts.core.storage.storage_service import LocalStorageBackend


class TestLargeArtifacts:

    @pytest.fixture
    def setup_storage_facade(self):
        temp_dir = tempfile.mkdtemp()
        storage = LocalStorageBackend(root_dir=temp_dir)
        embedder = DeterministicFakeEmbeddingProvider(dimension=64)
        repo = InMemoryMemoryRepository()
        service = MemoryService(repository=repo, embedding_provider=embedder)
        facade = ProjectMemoryFacade(memory_service=service, storage_service=storage)
        return facade, service, storage

    def test_heavy_media_artifact_stored_in_storage_service(self, setup_storage_facade):
        """
        Verifies large video/audio/analysis blobs are written to StorageService,
        leaving MemoryEntry with only canonical storage_ref, sha256, and metadata.
        """
        facade, service, storage = setup_storage_facade

        ctx = TrustedTenantContext(
            workspace_id="ws_media_prod",
            user_id="usr_producer",
            accessible_projects=["prj_ep01"],
        )

        # Create dummy 1MB heavy payload
        raw_video_bytes = b"MOCK_HEAVY_VIDEO_FRAME_BYTES_" * 35000
        expected_sha256 = hashlib.sha256(raw_video_bytes).hexdigest()

        # Store through Facade
        entry = facade.store_heavy_artifact_memory(
            context=ctx,
            project_id="prj_ep01",
            category="transcripts",
            item_id="item_scene_01",
            filename="full_analysis.json",
            content_bytes=raw_video_bytes,
            content_type="application/json",
            summary="Scene 01 deep multi-modal analysis summary: 4 speakers identified, sentiment neutral.",
            memory_type=MemoryType.MEDIA_INTELLIGENCE,
            metadata={"duration_sec": 45.2, "speaker_count": 4},
        )

        # 1. Assert MemoryEntry holds only metadata and reference, NOT raw payload
        assert entry.storage_ref is not None
        assert entry.storage_ref.startswith("workspaces/ws_media_prod/projects/prj_ep01/transcripts/item_scene_01/full_analysis.json")
        assert entry.metadata["size_bytes"] == len(raw_video_bytes)
        assert entry.metadata["sha256"] == expected_sha256
        assert entry.content.startswith("Scene 01 deep multi-modal analysis")

        # 2. Retrieve actual heavy payload directly from StorageService
        read_bytes = storage.get(entry.storage_ref)
        assert read_bytes == raw_video_bytes
        assert hashlib.sha256(read_bytes).hexdigest() == expected_sha256
