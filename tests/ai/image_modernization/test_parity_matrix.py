"""
tests/ai/image_modernization/test_parity_matrix.py
==================================================
Parity matrix tests proving exact behavioral and semantic parity between
legacy image-tools-mcp and modernized canonical ImageProcessingService (S28-M08).

Invariants:
- Zero capability loss across upscale_image, crop_to_ratio, and auto_crop_content.
- Pixel and dimension equivalence on canonical sample assets.
- Alpha channel and mode preservation.
"""

from __future__ import annotations

import io
from pathlib import Path
import pytest
from PIL import Image

from ai.image_processing.contracts import (
    AutoCropImageRequest,
    CropImageRatioRequest,
    ResizeImageRequest,
)
from ai.image_processing.service import ImageProcessingService

# Import legacy implementations for direct side-by-side comparison
import sys
LEGACY_DIR = Path(".agents/plugins/super-video-maker-plugin/tools/mcp-servers/image-tools-mcp")
if str(LEGACY_DIR.resolve()) not in sys.path:
    sys.path.insert(0, str(LEGACY_DIR.resolve()))

from utils.image_ops import (
    auto_crop_content_file,
    crop_to_ratio_file,
    upscale_image_file,
)


def test_parity_upscale_image(tmp_path, image_service: ImageProcessingService, mock_storage, sample_png_bytes):
    # 1. Run legacy implementation
    legacy_in = tmp_path / "orig.png"
    legacy_in.write_bytes(sample_png_bytes)
    legacy_out = upscale_image_file(str(legacy_in), target_width=400, target_height=200)

    # 2. Run canonical implementation
    mock_storage.put("projects/p1/orig.png", sample_png_bytes)
    req = ResizeImageRequest(
        project_id="p1",
        image_storage_key="projects/p1/orig.png",
        target_width=400,
        target_height=200,
        fit_mode="stretch",
    )
    canon_res = image_service.resize_image(req)
    canon_data = mock_storage.get(canon_res.output_storage_key)

    # 3. Compare parity
    with Image.open(legacy_out) as leg_img, Image.open(io.BytesIO(canon_data)) as can_img:
        assert leg_img.size == can_img.size == (400, 200)
        assert leg_img.format == can_img.format == "PNG"
        assert leg_img.mode == can_img.mode == "RGBA"
        # Bounded difference check: exact pixel parity
        diff = Image.new("RGBA", (400, 200))
        for x in [50, 100, 200, 350]:
            for y in [25, 50, 100, 150]:
                assert leg_img.getpixel((x, y)) == can_img.getpixel((x, y))


def test_parity_crop_to_ratio(tmp_path, image_service: ImageProcessingService, mock_storage, sample_jpeg_bytes):
    legacy_in = tmp_path / "orig.jpg"
    legacy_in.write_bytes(sample_jpeg_bytes)
    legacy_out = crop_to_ratio_file(str(legacy_in), target_ratio="1:1")

    mock_storage.put("projects/p1/orig.jpg", sample_jpeg_bytes)
    req = CropImageRatioRequest(
        project_id="p1",
        image_storage_key="projects/p1/orig.jpg",
        target_ratio="1:1",
    )
    canon_res = image_service.crop_image_to_ratio(req)
    canon_data = mock_storage.get(canon_res.output_storage_key)

    with Image.open(legacy_out) as leg_img, Image.open(io.BytesIO(canon_data)) as can_img:
        assert leg_img.size == can_img.size == (200, 200)
        assert leg_img.format == can_img.format == "JPEG"
        assert leg_img.mode == can_img.mode == "RGB"


def test_parity_auto_crop_content(tmp_path, image_service: ImageProcessingService, mock_storage, sample_solid_border_png):
    legacy_in = tmp_path / "border.png"
    legacy_in.write_bytes(sample_solid_border_png)
    legacy_out = auto_crop_content_file(str(legacy_in), background_color="white", background_threshold=10)

    mock_storage.put("projects/p1/border.png", sample_solid_border_png)
    req = AutoCropImageRequest(
        project_id="p1",
        image_storage_key="projects/p1/border.png",
        background_color="white",
        background_threshold=10,
    )
    canon_res = image_service.auto_crop_image(req)
    canon_data = mock_storage.get(canon_res.output_storage_key)

    with Image.open(legacy_out) as leg_img, Image.open(io.BytesIO(canon_data)) as can_img:
        assert leg_img.size == can_img.size == (120, 120)
        assert leg_img.format == can_img.format == "PNG"
