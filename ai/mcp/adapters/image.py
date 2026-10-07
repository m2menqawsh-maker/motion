"""
ai/mcp/adapters/image.py
========================
Hardened adapters for retained image MCP operations (S27.10).

Invariants:
- Uses Pillow (PIL) in-process without shell or external subprocess execution.
- Server-side path validation via MCPSecurityPolicy.validate_safe_path.
- Strict bounded execution timeouts.
- Structured error handling and audit tracking.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional
from PIL import Image

from ai.mcp.adapters.base import BaseMCPAdapter
from ai.mcp.contracts import (
    AutoCropInput,
    AutoCropOutput,
    CropRatioInput,
    CropRatioOutput,
    UpscaleImageInput,
    UpscaleImageOutput,
)
from ai.mcp.policy import MCPSecurityPolicy
from ai.tools.types import TrustedToolExecutionContext


class ImageUpscaleAdapter(BaseMCPAdapter[UpscaleImageInput, UpscaleImageOutput]):
    """Hardened adapter for image resizing and upscaling."""
    def __init__(self):
        super().__init__("image-tools-mcp", "upscale_image")

    async def _execute_internal(
        self,
        input_data: UpscaleImageInput,
        context: TrustedToolExecutionContext,
    ) -> UpscaleImageOutput:
        src = MCPSecurityPolicy.validate_safe_path(input_data.file_path, must_exist=True)

        if input_data.output_path:
            dst = MCPSecurityPolicy.validate_safe_path(input_data.output_path)
        else:
            dst = src.with_name(f"{src.stem}_upscaled{src.suffix}")

        with Image.open(src) as img:
            orig_w, orig_h = img.size
            tw, th = input_data.target_width, input_data.target_height

            if tw > 0 and th > 0:
                final_w, final_h = tw, th
            elif tw > 0:
                final_w = tw
                final_h = int(orig_h * (tw / orig_w))
            elif th > 0:
                final_h = th
                final_w = int(orig_w * (th / orig_h))
            else:
                final_w, final_h = orig_w, orig_h

            resampled = img.resize((final_w, final_h), Image.Resampling.LANCZOS)
            resampled.save(dst)

        return UpscaleImageOutput(output_path=str(dst), width=final_w, height=final_h)


class ImageCropRatioAdapter(BaseMCPAdapter[CropRatioInput, CropRatioOutput]):
    """Hardened adapter for aspect ratio center-cropping."""
    def __init__(self):
        super().__init__("image-tools-mcp", "crop_to_ratio")

    async def _execute_internal(
        self,
        input_data: CropRatioInput,
        context: TrustedToolExecutionContext,
    ) -> CropRatioOutput:
        src = MCPSecurityPolicy.validate_safe_path(input_data.file_path, must_exist=True)

        if input_data.output_path:
            dst = MCPSecurityPolicy.validate_safe_path(input_data.output_path)
        else:
            dst = src.with_name(f"{src.stem}_cropped{src.suffix}")

        num_str, den_str = input_data.target_ratio.split(":")
        target_aspect = float(num_str) / float(den_str)

        with Image.open(src) as img:
            w, h = img.size
            current_aspect = w / h

            if current_aspect > target_aspect:
                new_w = int(h * target_aspect)
                left = (w - new_w) // 2
                box = (left, 0, left + new_w, h)
            else:
                new_h = int(w / target_aspect)
                top = (h - new_h) // 2
                box = (0, top, w, top + new_h)

            cropped = img.crop(box)
            cropped.save(dst)

        return CropRatioOutput(output_path=str(dst), ratio=input_data.target_ratio)


class ImageAutoCropAdapter(BaseMCPAdapter[AutoCropInput, AutoCropOutput]):
    """Hardened adapter for auto-cropping borders."""
    def __init__(self):
        super().__init__("image-tools-mcp", "auto_crop_content")

    async def _execute_internal(
        self,
        input_data: AutoCropInput,
        context: TrustedToolExecutionContext,
    ) -> AutoCropOutput:
        src = MCPSecurityPolicy.validate_safe_path(input_data.file_path, must_exist=True)

        if input_data.output_path:
            dst = MCPSecurityPolicy.validate_safe_path(input_data.output_path)
        else:
            dst = src.with_name(f"{src.stem}_autocrop{src.suffix}")

        with Image.open(src) as img:
            orig_size = [img.size[0], img.size[1]]
            bbox = img.getbbox()
            if bbox:
                cropped = img.crop(bbox)
                cropped.save(dst)
                cropped_size = [cropped.size[0], cropped.size[1]]
            else:
                img.save(dst)
                cropped_size = list(orig_size)

        return AutoCropOutput(
            output_path=str(dst),
            original_size=orig_size,
            cropped_size=cropped_size,
        )
