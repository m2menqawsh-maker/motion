"""
tests/ai/image_modernization/conftest.py
========================================
Fixtures for S28-M08 Image Processing Modernization tests.
"""

from __future__ import annotations

import io
from typing import Any, Dict, Optional
import pytest
from PIL import Image

from ai.image_processing.service import ImageProcessingService
from ai.tools.types import TrustedToolExecutionContext
from scripts.core.storage.storage_service import LocalStorageBackend, StorageService


class MockAssetService:
    """Mock AssetService recording asset registrations."""

    def __init__(self) -> None:
        self.uploaded_assets: Dict[str, Dict[str, Any]] = {}
        self.should_fail_upload: bool = False

    def upload_asset(
        self,
        project_id: str,
        content: bytes,
        filename: str,
        asset_id: Optional[str] = None,
        kind: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        if self.should_fail_upload:
            raise RuntimeError("Injected AssetService upload failure")

        aid = asset_id or f"mock_{filename}"
        record = {
            "project_id": project_id,
            "asset_id": aid,
            "filename": filename,
            "kind": kind,
            "status": status,
            "size_bytes": len(content),
        }
        self.uploaded_assets[aid] = record
        return record


@pytest.fixture
def mock_storage(tmp_path) -> StorageService:
    return LocalStorageBackend(root_dir=tmp_path / "storage")


@pytest.fixture
def mock_asset_service() -> MockAssetService:
    return MockAssetService()


@pytest.fixture
def sample_png_bytes() -> bytes:
    """Creates a 200x100 RGBA PNG image with transparent corners and red center."""
    img = Image.new("RGBA", (200, 100), (0, 0, 0, 0))
    # Fill middle area with red
    for x in range(50, 150):
        for y in range(25, 75):
            img.putpixel((x, y), (255, 0, 0, 255))
    bio = io.BytesIO()
    img.save(bio, format="PNG")
    return bio.getvalue()


@pytest.fixture
def sample_jpeg_bytes() -> bytes:
    """Creates a 300x200 RGB JPEG image."""
    img = Image.new("RGB", (300, 200), (0, 128, 255))
    bio = io.BytesIO()
    img.save(bio, format="JPEG", quality=90)
    return bio.getvalue()


@pytest.fixture
def sample_solid_border_png() -> bytes:
    """Creates a 200x200 image with solid white border and blue center."""
    img = Image.new("RGB", (200, 200), (255, 255, 255))
    for x in range(40, 160):
        for y in range(40, 160):
            img.putpixel((x, y), (0, 0, 255))
    bio = io.BytesIO()
    img.save(bio, format="PNG")
    return bio.getvalue()


@pytest.fixture
def image_service(mock_storage: StorageService, mock_asset_service: MockAssetService) -> ImageProcessingService:
    return ImageProcessingService(storage=mock_storage, asset_service=mock_asset_service)


@pytest.fixture
def trusted_context() -> TrustedToolExecutionContext:
    return TrustedToolExecutionContext(
        workspace_id="ws_default",
        actor_id="user_test",
        roles=["editor"],
        permissions=["editor"],
        accessible_projects=["proj_image_test"],
    )
