"""
ai/tools/adapters/image_processing.py
=====================================
Canonical ToolGateway adapter for ImageProcessingService (S28-M08).

Invariants:
- AI callers submit provider-neutral CapabilityRequest objects to ToolGateway.
- Calls are dispatched strictly to canonical ImageProcessingService.
- AI callers never supply arbitrary shell commands, raw host filesystem paths, or flags.
- Translates canonical ImageProcessingService results into strongly-typed output dictionaries.
- Preserves full backward compatibility with legacy M02/M03 contracts (UpscaleImageInput, CropRatioInput, AutoCropInput).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, Set

from ai.contracts import (
    CapabilityDefinition,
    CapabilityFamily,
    CapabilityRequest,
    CapabilityType,
    ImplementationDescriptor,
)
from ai.contracts.errors import AIError, AIErrorCode
from ai.contracts.media_ops import (
    AutoCropInput,
    CropRatioInput,
    UpscaleImageInput,
)
from ai.image_processing.contracts import (
    AutoCropImageRequest,
    AutoCropImageResult,
    ConvertImageRequest,
    ConvertImageResult,
    CropImageRatioRequest,
    CropImageRatioResult,
    OptimizeImageRequest,
    OptimizeImageResult,
    PrepareImageAssetRequest,
    PrepareImageAssetResult,
    ProbeImageRequest,
    ProbeImageResult,
    ResizeImageRequest,
    ResizeImageResult,
    ThumbnailRequest,
    ThumbnailResult,
)
from ai.image_processing.errors import ImageProcessingError
from ai.image_processing.service import ImageProcessingService, get_image_processing_service
from ai.tools.adapters.base import CapabilityAdapter
from ai.tools.types import TrustedToolExecutionContext

logger = logging.getLogger("ai.tools.adapters.image_processing")


class ImageProcessingAdapter(CapabilityAdapter):
    """
    Adapter executing image processing capabilities via ImageProcessingService.
    """

    HANDLED_CAPABILITY_TYPES: Set[str] = {
        # Canonical S28-M08 Capabilities
        CapabilityType.RESIZE_IMAGE.value,
        CapabilityType.CROP_IMAGE_TO_RATIO.value,
        CapabilityType.AUTO_CROP_IMAGE.value,
        CapabilityType.CONVERT_IMAGE.value,
        CapabilityType.OPTIMIZE_IMAGE.value,
        CapabilityType.PROBE_IMAGE.value,
        CapabilityType.PREPARE_IMAGE_ASSET.value,
        CapabilityType.THUMBNAIL.value,
    }

    def __init__(self, service: Optional[ImageProcessingService] = None) -> None:
        super().__init__(name="canonical_image_processing_adapter", adapter_kind="IMAGE_PROCESSING")
        self._service: Optional[ImageProcessingService] = service

    @property
    def service(self) -> ImageProcessingService:
        if self._service is not None:
            return self._service
        return get_image_processing_service()

    def can_handle(
        self,
        capability: CapabilityDefinition,
        implementation: Optional[ImplementationDescriptor] = None,
    ) -> bool:
        cap_val = capability.capability_id.value if hasattr(capability.capability_id, "value") else str(capability.capability_id)
        return cap_val in self.HANDLED_CAPABILITY_TYPES

    async def execute(
        self,
        request: CapabilityRequest,
        validated_input: Any,
        context: TrustedToolExecutionContext,
    ) -> Dict[str, Any]:
        """
        Executes image capability through ImageProcessingService.
        """
        context.assert_not_timed_out()
        cap_val = request.capability_id.value if hasattr(request.capability_id, "value") else str(request.capability_id)

        try:
            if cap_val == CapabilityType.RESIZE_IMAGE.value:
                return self._execute_resize_image(validated_input)
            elif cap_val == CapabilityType.CROP_IMAGE_TO_RATIO.value:
                return self._execute_crop_image_ratio(validated_input)
            elif cap_val == CapabilityType.AUTO_CROP_IMAGE.value:
                return self._execute_auto_crop_image(validated_input)
            elif cap_val == CapabilityType.CONVERT_IMAGE.value:
                return self._execute_convert_image(validated_input)
            elif cap_val == CapabilityType.OPTIMIZE_IMAGE.value:
                return self._execute_optimize_image(validated_input)
            elif cap_val == CapabilityType.PROBE_IMAGE.value:
                return self._execute_probe_image(validated_input)
            elif cap_val == CapabilityType.PREPARE_IMAGE_ASSET.value:
                return self._execute_prepare_image_asset(validated_input)
            elif cap_val == CapabilityType.THUMBNAIL.value:
                return self._execute_thumbnail(validated_input)
            else:
                raise NotImplementedError(f"Image capability '{cap_val}' not supported by ImageProcessingAdapter.")
        except ImageProcessingError as e:
            raise e.to_ai_error()
        except Exception as e:
            logger.error(f"ImageProcessingAdapter execution failed: {e}", exc_info=True)
            raise AIError(
                code=AIErrorCode.INTERNAL_ERROR,
                message=f"Image operation failed: {e}",
                category="IMAGE_PROCESSING",
                retryable=False,
                details={"capability_id": cap_val},
            )

    def _execute_resize_image(self, inp: Any) -> Dict[str, Any]:
        if isinstance(inp, UpscaleImageInput):
            # Backward compatibility translation
            req = ResizeImageRequest(
                project_id=inp.project_id,
                image_storage_key=inp.image_storage_key,
                target_width=inp.target_width,
                target_height=inp.target_height,
                scale_factor=inp.scale_factor if not (inp.target_width or inp.target_height) else None,
            )
            res = self.service.resize_image(req)
            return {
                "project_id": res.project_id,
                "output_storage_key": res.output_storage_key,
                "width": res.width,
                "height": res.height,
            }
        elif isinstance(inp, ResizeImageRequest):
            res = self.service.resize_image(inp)
            return res.model_dump()
        else:
            raise ValueError(f"Unsupported input type for RESIZE_IMAGE: {type(inp).__name__}")

    def _execute_crop_image_ratio(self, inp: Any) -> Dict[str, Any]:
        if isinstance(inp, CropRatioInput):
            req = CropImageRatioRequest(
                project_id=inp.project_id,
                image_storage_key=inp.image_storage_key,
                target_ratio=inp.aspect_ratio,
            )
            res = self.service.crop_image_to_ratio(req)
            return {
                "project_id": res.project_id,
                "output_storage_key": res.output_storage_key,
                "width": res.width,
                "height": res.height,
                "aspect_ratio": res.applied_ratio,
            }
        elif isinstance(inp, CropImageRatioRequest):
            res = self.service.crop_image_to_ratio(inp)
            return res.model_dump()
        else:
            raise ValueError(f"Unsupported input type for CROP_IMAGE_TO_RATIO: {type(inp).__name__}")

    def _execute_auto_crop_image(self, inp: Any) -> Dict[str, Any]:
        if isinstance(inp, AutoCropInput):
            req = AutoCropImageRequest(
                project_id=inp.project_id,
                image_storage_key=inp.image_storage_key,
                padding_ratio=inp.padding_ratio,
            )
            res = self.service.auto_crop_image(req)
            return {
                "project_id": res.project_id,
                "output_storage_key": res.output_storage_key,
                "cropped_box": res.cropped_box,
                "original_width": res.original_width,
                "original_height": res.original_height,
                "output_width": res.output_width,
                "output_height": res.output_height,
            }
        elif isinstance(inp, AutoCropImageRequest):
            res = self.service.auto_crop_image(inp)
            return res.model_dump()
        else:
            raise ValueError(f"Unsupported input type for AUTO_CROP_IMAGE: {type(inp).__name__}")

    def _execute_convert_image(self, inp: Any) -> Dict[str, Any]:
        if not isinstance(inp, ConvertImageRequest):
            raise ValueError(f"Expected ConvertImageRequest, got {type(inp).__name__}")
        res = self.service.convert_image(inp)
        return res.model_dump()

    def _execute_optimize_image(self, inp: Any) -> Dict[str, Any]:
        if not isinstance(inp, OptimizeImageRequest):
            raise ValueError(f"Expected OptimizeImageRequest, got {type(inp).__name__}")
        res = self.service.optimize_image(inp)
        return res.model_dump()

    def _execute_probe_image(self, inp: Any) -> Dict[str, Any]:
        if not isinstance(inp, ProbeImageRequest):
            raise ValueError(f"Expected ProbeImageRequest, got {type(inp).__name__}")
        res = self.service.probe_image(inp)
        return res.model_dump()

    def _execute_prepare_image_asset(self, inp: Any) -> Dict[str, Any]:
        if not isinstance(inp, PrepareImageAssetRequest):
            raise ValueError(f"Expected PrepareImageAssetRequest, got {type(inp).__name__}")
        res = self.service.prepare_image_asset(inp)
        return res.model_dump()

    def _execute_thumbnail(self, inp: Any) -> Dict[str, Any]:
        if not isinstance(inp, ThumbnailRequest):
            raise ValueError(f"Expected ThumbnailRequest, got {type(inp).__name__}")
        res = self.service.generate_thumbnail(inp)
        return res.model_dump()
