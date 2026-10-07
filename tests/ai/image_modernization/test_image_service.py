"""
tests/ai/image_modernization/test_image_service.py
==================================================
Functional tests for canonical ImageProcessingService (S28-M08).

Invariants:
- All operations preserve legacy capability semantics with typed contracts.
- Alpha preservation / safe composite onto background when converting to JPEG.
- Full AssetService registration and StorageService publication.
"""

from __future__ import annotations

import io
import pytest
from PIL import Image

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
from ai.image_processing.service import ImageProcessingService


def test_probe_image_read_only(image_service: ImageProcessingService, mock_storage, sample_png_bytes):
    mock_storage.put("projects/proj_1/images/source.png", sample_png_bytes)

    req = ProbeImageRequest(project_id="proj_1", image_storage_key="projects/proj_1/images/source.png")
    res = image_service.probe_image(req)

    assert res.project_id == "proj_1"
    assert res.width == 200
    assert res.height == 100
    assert res.format == "PNG"
    assert res.has_alpha is True
    assert res.frame_count == 1
    assert res.file_size_bytes == len(sample_png_bytes)


def test_resize_image_aspect_ratio_preservation(image_service: ImageProcessingService, mock_storage, sample_png_bytes):
    mock_storage.put("projects/proj_1/images/source.png", sample_png_bytes)

    # 200x100 source, target width 400 with maintain_aspect_ratio=True -> 400x200
    req = ResizeImageRequest(
        project_id="proj_1",
        image_storage_key="projects/proj_1/images/source.png",
        target_width=400,
        maintain_aspect_ratio=True,
    )
    res = image_service.resize_image(req)

    assert res.width == 400
    assert res.height == 200
    assert mock_storage.exists(res.output_storage_key)


def test_resize_image_stretch(image_service: ImageProcessingService, mock_storage, sample_png_bytes):
    mock_storage.put("projects/proj_1/images/source.png", sample_png_bytes)

    # Forceful stretch to 300x300
    req = ResizeImageRequest(
        project_id="proj_1",
        image_storage_key="projects/proj_1/images/source.png",
        target_width=300,
        target_height=300,
        fit_mode="stretch",
    )
    res = image_service.resize_image(req)

    assert res.width == 300
    assert res.height == 300


def test_crop_image_to_ratio(image_service: ImageProcessingService, mock_storage, sample_jpeg_bytes):
    # 300x200 source (aspect 1.5). Target 1:1 -> center cropped to 200x200
    mock_storage.put("projects/proj_1/images/source.jpg", sample_jpeg_bytes)

    req = CropImageRatioRequest(
        project_id="proj_1",
        image_storage_key="projects/proj_1/images/source.jpg",
        target_ratio="1:1",
    )
    res = image_service.crop_image_to_ratio(req)

    assert res.width == 200
    assert res.height == 200
    assert res.applied_ratio == "1:1"
    assert mock_storage.exists(res.output_storage_key)


def test_auto_crop_content_alpha(image_service: ImageProcessingService, mock_storage, sample_png_bytes):
    # Sample PNG has 200x100 canvas, but content is strictly from x:50..150, y:25..75 (100x50 content)
    mock_storage.put("projects/proj_1/images/transparent_content.png", sample_png_bytes)

    req = AutoCropImageRequest(
        project_id="proj_1",
        image_storage_key="projects/proj_1/images/transparent_content.png",
        background_color="auto",
    )
    res = image_service.auto_crop_image(req)

    assert res.output_width == 100
    assert res.output_height == 50
    assert res.cropped_box == [50, 25, 150, 75]
    assert mock_storage.exists(res.output_storage_key)


def test_auto_crop_content_solid_border(image_service: ImageProcessingService, mock_storage, sample_solid_border_png):
    # 200x200 canvas with solid white border, center content 40..160 (120x120 content)
    mock_storage.put("projects/proj_1/images/solid_border.png", sample_solid_border_png)

    req = AutoCropImageRequest(
        project_id="proj_1",
        image_storage_key="projects/proj_1/images/solid_border.png",
        background_color="white",
        background_threshold=10,
    )
    res = image_service.auto_crop_image(req)

    assert res.output_width == 120
    assert res.output_height == 120
    assert res.cropped_box == [40, 40, 160, 160]


def test_convert_image_rgba_to_jpeg_with_background(image_service: ImageProcessingService, mock_storage, sample_png_bytes):
    mock_storage.put("projects/proj_1/images/source.png", sample_png_bytes)

    req = ConvertImageRequest(
        project_id="proj_1",
        image_storage_key="projects/proj_1/images/source.png",
        target_format="JPEG",
        background_color="#ffffff",
    )
    res = image_service.convert_image(req)

    assert res.target_format == "JPEG"
    assert res.source_format == "PNG"
    assert mock_storage.exists(res.output_storage_key)

    # Verify decoded output has no alpha and is valid JPEG
    out_data = mock_storage.get(res.output_storage_key)
    with Image.open(io.BytesIO(out_data)) as decoded:
        assert decoded.format == "JPEG"
        assert decoded.mode == "RGB"


def test_optimize_image_metrics(image_service: ImageProcessingService, mock_storage, sample_jpeg_bytes):
    mock_storage.put("projects/proj_1/images/source.jpg", sample_jpeg_bytes)

    req = OptimizeImageRequest(
        project_id="proj_1",
        image_storage_key="projects/proj_1/images/source.jpg",
        quality=60,
    )
    res = image_service.optimize_image(req)

    assert res.input_bytes == len(sample_jpeg_bytes)
    assert res.output_bytes > 0
    assert res.compression_ratio > 0.0
    assert mock_storage.exists(res.output_storage_key)


def test_generate_thumbnail(image_service: ImageProcessingService, mock_storage, sample_jpeg_bytes):
    mock_storage.put("projects/proj_1/images/source.jpg", sample_jpeg_bytes)

    req = ThumbnailRequest(
        project_id="proj_1",
        image_storage_key="projects/proj_1/images/source.jpg",
        width=128,
        height=128,
        output_format="webp",
    )
    res = image_service.generate_thumbnail(req)

    assert res.width <= 128
    assert res.height <= 128
    assert res.format == "WEBP"
    assert mock_storage.exists(res.output_storage_key)


def test_prepare_image_asset_full_orchestration(image_service: ImageProcessingService, mock_storage, mock_asset_service, sample_png_bytes):
    mock_storage.put("projects/proj_1/images/source.png", sample_png_bytes)

    req = PrepareImageAssetRequest(
        project_id="proj_1",
        image_storage_key="projects/proj_1/images/source.png",
        asset_id="ast_hero_image",
        generate_thumbnail=True,
        thumbnail_size=128,
    )
    res = image_service.prepare_image_asset(req)

    assert res.asset_id == "ast_hero_image"
    assert res.manifest_registered is True
    assert mock_storage.exists(res.primary_storage_key)
    assert res.thumbnail_storage_key is not None
    assert mock_storage.exists(res.thumbnail_storage_key)

    # Verify registered in AssetService
    assert "ast_hero_image" in mock_asset_service.uploaded_assets
    rec = mock_asset_service.uploaded_assets["ast_hero_image"]
    assert rec["kind"] == "IMAGE"
    assert rec["status"] == "ready"
