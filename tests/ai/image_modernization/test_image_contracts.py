"""
tests/ai/image_modernization/test_image_contracts.py
====================================================
Tests verifying strict typed contracts for S28-M08 image capabilities.

Invariants:
- Extra fields forbidden (extra="forbid").
- Dimension limits (1-8192) enforced.
- Ratio strings strictly validated.
- Quality bounded between 1 and 100.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ai.image_processing.contracts import (
    AutoCropImageRequest,
    ConvertImageRequest,
    CropImageRatioRequest,
    OptimizeImageRequest,
    PrepareImageAssetRequest,
    ProbeImageRequest,
    ResizeImageRequest,
    ThumbnailRequest,
)


def test_probe_image_contract_valid():
    req = ProbeImageRequest(project_id="proj_1", image_storage_key="images/test.png")
    assert req.project_id == "proj_1"
    assert req.image_storage_key == "images/test.png"
    assert req.extract_metadata is True


def test_probe_image_contract_extra_forbidden():
    with pytest.raises(ValidationError):
        ProbeImageRequest(project_id="proj_1", image_storage_key="images/test.png", random_extra=123)


def test_resize_image_contract_bounds():
    # Valid explicit width
    req = ResizeImageRequest(project_id="proj_1", image_storage_key="images/test.png", target_width=1920)
    assert req.target_width == 1920

    # Invalid dimension (> 8192)
    with pytest.raises(ValidationError):
        ResizeImageRequest(project_id="proj_1", image_storage_key="images/test.png", target_width=99999)

    # Invalid dimension (< 1)
    with pytest.raises(ValidationError):
        ResizeImageRequest(project_id="proj_1", image_storage_key="images/test.png", target_width=0)

    # Invalid quality (> 100)
    with pytest.raises(ValidationError):
        ResizeImageRequest(project_id="proj_1", image_storage_key="images/test.png", target_width=100, quality=101)

    # Missing all targets
    with pytest.raises(ValidationError):
        ResizeImageRequest(project_id="proj_1", image_storage_key="images/test.png")


def test_crop_ratio_contract():
    req = CropImageRatioRequest(project_id="proj_1", image_storage_key="images/test.png", target_ratio="16:9")
    assert req.target_ratio == "16:9"

    # Invalid ratio formats
    with pytest.raises(ValidationError):
        CropImageRatioRequest(project_id="proj_1", image_storage_key="images/test.png", target_ratio="invalid")

    with pytest.raises(ValidationError):
        CropImageRatioRequest(project_id="proj_1", image_storage_key="images/test.png", target_ratio="-16:9")


def test_auto_crop_contract():
    req = AutoCropImageRequest(project_id="proj_1", image_storage_key="images/test.png", background_threshold=15)
    assert req.background_threshold == 15

    # Threshold > 255 rejected
    with pytest.raises(ValidationError):
        AutoCropImageRequest(project_id="proj_1", image_storage_key="images/test.png", background_threshold=300)


def test_convert_image_contract():
    req = ConvertImageRequest(project_id="proj_1", image_storage_key="images/test.png", target_format="WEBP")
    assert req.target_format == "WEBP"

    # Unsupported target format
    with pytest.raises(ValidationError):
        ConvertImageRequest(project_id="proj_1", image_storage_key="images/test.png", target_format="TIFF")


def test_optimize_image_contract():
    req = OptimizeImageRequest(project_id="proj_1", image_storage_key="images/test.png", quality=80)
    assert req.quality == 80


def test_thumbnail_contract():
    req = ThumbnailRequest(project_id="proj_1", image_storage_key="images/test.png", width=128, height=128)
    assert req.width == 128
    assert req.height == 128

    # Width > 1024 rejected
    with pytest.raises(ValidationError):
        ThumbnailRequest(project_id="proj_1", image_storage_key="images/test.png", width=2000)


def test_prepare_image_asset_contract():
    req = PrepareImageAssetRequest(
        project_id="proj_1",
        image_storage_key="images/test.png",
        asset_id="ast_custom1",
        generate_thumbnail=True,
    )
    assert req.asset_id == "ast_custom1"
    assert req.generate_thumbnail is True
