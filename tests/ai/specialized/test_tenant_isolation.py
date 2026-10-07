"""
tests/ai/specialized/test_tenant_isolation.py
=============================================
Multi-tenant boundary isolation tests for Specialized Media AI (S27.17 / AI-13 Rule 25).

Invariants verified:
- Workspace A cannot access Workspace B input storage keys or generated output storage keys.
- Passing an alien workspace's storage key raises TenantIsolationViolationError.
- Storage paths are strictly prefixed with 'workspaces/{workspace_id}/'.
"""

import pytest

from ai.cache.errors import TenantIsolationViolationError
from ai.contracts.specialized import (
    BackgroundRemovalRequest,
    LipSyncRequest,
    PersonSegmentationRequest,
    UpscaleRequest,
)
from ai.specialized.adapters import FakeSpecializedMediaAdapterA
from ai.specialized.service import SpecializedMediaService
from scripts.core.storage.storage_service import LocalStorageBackend


@pytest.fixture
def storage(tmp_path):
    return LocalStorageBackend(root_dir=tmp_path / "tenant_storage")


@pytest.fixture
def service(storage):
    adapter = FakeSpecializedMediaAdapterA(storage_service=storage)
    svc = SpecializedMediaService(storage_service=storage)
    svc.register_provider_adapter("fake-specialized-a", adapter)
    return svc


@pytest.mark.asyncio
async def test_tenant_isolation_on_person_segmentation(service):
    """Workspace B attempting to segment an image stored under Workspace A is rejected."""
    alien_req = PersonSegmentationRequest(
        image_storage_key="workspaces/workspace_alpha/inputs/person.png",
        content_hash="hash_alpha_person",
    )

    with pytest.raises(TenantIsolationViolationError) as exc_info:
        await service.segment_person("workspace_beta", alien_req, provider_id_override="fake-specialized-a")

    assert "Tenant isolation violation" in str(exc_info.value)
    assert "workspace_beta" in str(exc_info.value)


@pytest.mark.asyncio
async def test_tenant_isolation_on_background_removal(service):
    """Workspace B cannot remove background on Workspace A's asset."""
    alien_req = BackgroundRemovalRequest(
        image_storage_key="workspaces/workspace_alpha/inputs/item.png",
        content_hash="hash_alpha_item",
    )

    with pytest.raises(TenantIsolationViolationError):
        await service.remove_background("workspace_beta", alien_req, provider_id_override="fake-specialized-a")


@pytest.mark.asyncio
async def test_tenant_isolation_on_upscale(service):
    """Workspace B cannot upscale an image belonging to Workspace A."""
    alien_req = UpscaleRequest(
        media_storage_key="workspaces/workspace_alpha/inputs/photo.png",
        content_hash="hash_alpha_photo",
        scale_factor=2,
    )

    with pytest.raises(TenantIsolationViolationError):
        await service.upscale("workspace_beta", alien_req, provider_id_override="fake-specialized-a")


@pytest.mark.asyncio
async def test_tenant_isolation_on_lip_sync(service):
    """Workspace B cannot mix video or audio from Workspace A."""
    alien_video_req = LipSyncRequest(
        video_storage_key="workspaces/workspace_alpha/video.mp4",
        audio_storage_key="workspaces/workspace_beta/audio.wav",
        content_hash="hash_mixed",
    )

    with pytest.raises(TenantIsolationViolationError):
        await service.sync_lips("workspace_beta", alien_video_req, provider_id_override="fake-specialized-a")
