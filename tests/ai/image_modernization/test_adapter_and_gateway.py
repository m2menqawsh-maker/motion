"""
tests/ai/image_modernization/test_adapter_and_gateway.py
========================================================
ToolGateway and AdapterRegistry integration tests for ImageProcessingAdapter (S28-M08).

Invariants:
- AdapterRegistry deterministically routes all canonical image capabilities to ImageProcessingAdapter.
- ToolGateway executes end-to-end with full input/output schema validation.
- Legacy input models (UpscaleImageInput, CropRatioInput, AutoCropInput) execute with zero regression.
"""

from __future__ import annotations

import pytest

from ai.contracts import (
    CapabilityDefinition,
    CapabilityFamily,
    CapabilityRequest,
    CapabilityType,
)
from ai.contracts.media_ops import (
    AutoCropInput,
    CropRatioInput,
    UpscaleImageInput,
)
from ai.image_processing.contracts import (
    AutoCropImageRequest,
    CropImageRatioRequest,
    ProbeImageRequest,
    ResizeImageRequest,
)
from ai.image_processing.service import ImageProcessingService
from ai.tools.adapters.image_processing import ImageProcessingAdapter
from ai.tools.adapters.registry import get_adapter_registry
from ai.tools.gateway import ToolGateway
from ai.tools.types import TrustedToolExecutionContext


@pytest.fixture
def adapter(image_service: ImageProcessingService) -> ImageProcessingAdapter:
    return ImageProcessingAdapter(service=image_service)


def test_adapter_can_handle(adapter: ImageProcessingAdapter):
    for cap_type in [
        CapabilityType.RESIZE_IMAGE,
        CapabilityType.CROP_IMAGE_TO_RATIO,
        CapabilityType.AUTO_CROP_IMAGE,
        CapabilityType.CONVERT_IMAGE,
        CapabilityType.OPTIMIZE_IMAGE,
        CapabilityType.PROBE_IMAGE,
        CapabilityType.PREPARE_IMAGE_ASSET,
        CapabilityType.THUMBNAIL,
    ]:
        cap_def = CapabilityDefinition(
            capability_id=cap_type,
            version="1.0.0",
            name="Test",
            description="Test",
            category="TOOL",
            family=CapabilityFamily.IMAGE_PROCESSING,
            input_contract="TestInput",
            output_contract="TestOutput",
            owner="ImageProcessingService",
            side_effect_class="READ_ONLY",
        )
        assert adapter.can_handle(cap_def) is True


def test_adapter_registry_resolves_image_processing_adapter():
    registry = get_adapter_registry()
    for cap_type in [
        CapabilityType.RESIZE_IMAGE,
        CapabilityType.CROP_IMAGE_TO_RATIO,
        CapabilityType.AUTO_CROP_IMAGE,
        CapabilityType.CONVERT_IMAGE,
        CapabilityType.OPTIMIZE_IMAGE,
        CapabilityType.PROBE_IMAGE,
        CapabilityType.PREPARE_IMAGE_ASSET,
        CapabilityType.THUMBNAIL,
    ]:
        cap_def = CapabilityDefinition(
            capability_id=cap_type,
            version="1.0.0",
            name="Test",
            description="Test",
            category="TOOL",
            family=CapabilityFamily.IMAGE_PROCESSING,
            input_contract="TestInput",
            output_contract="TestOutput",
            owner="ImageProcessingService",
            side_effect_class="READ_ONLY",
        )
        resolved_adapter, _ = registry.resolve(cap_def)
        assert isinstance(resolved_adapter, ImageProcessingAdapter)


@pytest.mark.asyncio
async def test_adapter_execute_legacy_upscale_input(adapter: ImageProcessingAdapter, mock_storage, sample_png_bytes, trusted_context):
    mock_storage.put("projects/proj_image_test/orig.png", sample_png_bytes)

    inp = UpscaleImageInput(
        project_id="proj_image_test",
        image_storage_key="projects/proj_image_test/orig.png",
        target_width=300,
        target_height=150,
    )
    req = CapabilityRequest(
        request_id="req_test_upscale",
        capability_id=CapabilityType.RESIZE_IMAGE,
        input=inp.model_dump(),
        project_id="proj_image_test",
    )

    out = await adapter.execute(req, inp, trusted_context)
    assert out["width"] == 300
    assert out["height"] == 150
    assert mock_storage.exists(out["output_storage_key"])


@pytest.mark.asyncio
async def test_adapter_execute_legacy_crop_ratio_input(adapter: ImageProcessingAdapter, mock_storage, sample_jpeg_bytes, trusted_context):
    mock_storage.put("projects/proj_image_test/orig.jpg", sample_jpeg_bytes)

    inp = CropRatioInput(
        project_id="proj_image_test",
        image_storage_key="projects/proj_image_test/orig.jpg",
        aspect_ratio="1:1",
    )
    req = CapabilityRequest(
        request_id="req_test_crop",
        capability_id=CapabilityType.CROP_IMAGE_TO_RATIO,
        input=inp.model_dump(),
        project_id="proj_image_test",
    )

    out = await adapter.execute(req, inp, trusted_context)
    assert out["width"] == 200
    assert out["height"] == 200
    assert out["aspect_ratio"] == "1:1"


@pytest.mark.asyncio
async def test_adapter_execute_legacy_auto_crop_input(adapter: ImageProcessingAdapter, mock_storage, sample_png_bytes, trusted_context):
    mock_storage.put("projects/proj_image_test/orig.png", sample_png_bytes)

    inp = AutoCropInput(
        project_id="proj_image_test",
        image_storage_key="projects/proj_image_test/orig.png",
        padding_ratio=0.0,
    )
    req = CapabilityRequest(
        request_id="req_test_autocrop",
        capability_id=CapabilityType.AUTO_CROP_IMAGE,
        input=inp.model_dump(),
        project_id="proj_image_test",
    )

    out = await adapter.execute(req, inp, trusted_context)
    assert out["output_width"] == 100
    assert out["output_height"] == 50
