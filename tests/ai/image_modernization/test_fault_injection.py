"""
tests/ai/image_modernization/test_fault_injection.py
====================================================
Fault injection and transactional atomicity tests for ImageProcessingService (S28-M08).

Invariants:
- Storage read or write failures fail closed without leaving persistent garbage.
- AssetService registration failure triggers storage rollback to prevent orphan payloads.
- Output validation failure aborts publication.
"""

from __future__ import annotations

import io
import pytest
from PIL import Image

from ai.image_processing.contracts import PrepareImageAssetRequest, ResizeImageRequest
from ai.image_processing.errors import ImageProcessingError, OutputValidationError
from ai.image_processing.service import ImageProcessingService
from ai.image_processing.validator import validate_image_output
from pathlib import Path
from scripts.core.storage.storage_service import LocalStorageBackend, StorageService


class FaultyStorage(LocalStorageBackend):
    """Storage backend simulating network and filesystem outages."""

    def __init__(self, root_dir: Path) -> None:
        super().__init__(root_dir=root_dir)
        self.fail_get = False
        self.fail_put = False

    def get(self, key: str) -> bytes:
        if self.fail_get:
            raise IOError("Injected storage read outage")
        return super().get(key)

    def put(self, key: str, val: bytes) -> str:
        if self.fail_put:
            raise IOError("Injected storage write outage")
        return super().put(key, val)


def test_storage_read_failure_fails_closed(tmp_path, sample_png_bytes, mock_asset_service):
    storage = FaultyStorage(tmp_path / "storage")
    storage.put("projects/p1/img.png", sample_png_bytes)
    storage.fail_get = True

    svc = ImageProcessingService(storage=storage, asset_service=mock_asset_service)
    req = ResizeImageRequest(project_id="p1", image_storage_key="projects/p1/img.png", target_width=100)

    with pytest.raises(Exception) as exc_info:
        svc.resize_image(req)
    assert "Injected storage read outage" in str(exc_info.value)


def test_storage_put_failure_fails_closed(tmp_path, sample_png_bytes, mock_asset_service):
    storage = FaultyStorage(tmp_path / "storage")
    storage.put("projects/p1/img.png", sample_png_bytes)
    storage.fail_put = True

    svc = ImageProcessingService(storage=storage, asset_service=mock_asset_service)
    req = ResizeImageRequest(project_id="p1", image_storage_key="projects/p1/img.png", target_width=100)

    with pytest.raises(Exception):
        svc.resize_image(req)


def test_storage_put_failure_prevents_asset_registration_and_leaves_no_corrupt_state(tmp_path, sample_png_bytes, mock_asset_service):
    """
    Explicitly verifies requirement §4:
    - Processing succeeds, but StorageService.put FAILS.
    - Expected: no AssetService registration, no success, no corrupt state.
    """
    storage = FaultyStorage(tmp_path / "storage")
    storage.put("projects/p1/img.png", sample_png_bytes)
    storage.fail_put = True

    svc = ImageProcessingService(storage=storage, asset_service=mock_asset_service)
    req = PrepareImageAssetRequest(
        project_id="p1",
        image_storage_key="projects/p1/img.png",
        asset_id="ast_put_fail",
        generate_thumbnail=True,
    )

    with pytest.raises(ImageProcessingError) as exc_info:
        svc.prepare_image_asset(req)

    assert exc_info.value.code == "STORAGE_ERROR"
    # Zero registrations in AssetService
    assert len(mock_asset_service.uploaded_assets) == 0
    assert "ast_put_fail" not in mock_asset_service.uploaded_assets


def test_asset_registration_failure_triggers_storage_cleanup(sample_png_bytes, mock_storage, mock_asset_service):
    """
    Explicitly verifies requirement §4:
    - Image processing succeeds
    - Output validation succeeds
    - StorageService.put succeeds
    - AssetService registration FAILS
    - Expected:
      - operation != success (raises ImageProcessingError)
      - uploaded candidate objects cleaned up / compensated (rollback)
      - no orphan canonical asset in AssetService
      - no false-success response
    """
    mock_storage.put("projects/p1/img.png", sample_png_bytes)
    mock_asset_service.should_fail_upload = True

    svc = ImageProcessingService(storage=mock_storage, asset_service=mock_asset_service)
    req = PrepareImageAssetRequest(
        project_id="p1",
        image_storage_key="projects/p1/img.png",
        asset_id="ast_failing_registration",
        generate_thumbnail=True,
    )

    with pytest.raises(ImageProcessingError) as exc_info:
        svc.prepare_image_asset(req)

    assert exc_info.value.code == "ASSET_REGISTRATION_FAILED"

    # Assert that rollback occurred: candidate primary and thumbnail files purged
    primary_key = "projects/p1/assets/ready/ast_failing_registration.png"
    thumb_key = "projects/p1/assets/cache/ast_failing_registration_thumb.webp"
    assert not mock_storage.exists(primary_key)
    assert not mock_storage.exists(thumb_key)

    # Assert zero registrations in AssetService
    assert len(mock_asset_service.uploaded_assets) == 0
    assert "ast_failing_registration" not in mock_asset_service.uploaded_assets


def test_output_validation_failure_on_corrupt_data():
    with pytest.raises(OutputValidationError):
        validate_image_output(b"")

    with pytest.raises(OutputValidationError):
        validate_image_output(b"CORRUPTED_BYTES")


def test_output_validation_failure_on_dimension_mismatch(sample_png_bytes):
    # Sample PNG is 200x100; expected width 500 must fail validation
    with pytest.raises(OutputValidationError):
        validate_image_output(sample_png_bytes, expected_width=500, tolerance=2)
