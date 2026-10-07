"""
ai/image_processing/adapter.py
==============================
Typed, isolated Pillow backend adapter for ImageProcessingService (S28-M08).

Invariants:
- All transformations execute strictly in-memory (io.BytesIO) without writing to host filesystem.
- Safe color mode & alpha handling: converts RGBA/LA/P to RGB with configurable background when saving to JPEG.
- Normalizes EXIF orientation cleanly using ImageOps.exif_transpose.
- Uses high-quality Lanczos resampling (Image.Resampling.LANCZOS) for all resizing.
- Does not invoke subprocesses or execute shell commands.
"""

from __future__ import annotations

import io
import math
from typing import Any, Dict, List, Optional, Tuple
from PIL import Image, ImageChops, ImageColor, ImageOps

from ai.image_processing.errors import InvalidImageRequestError
from ai.image_processing.security import (
    detect_image_format_from_magic,
    safe_open_image,
    validate_dimensions,
)


class PillowImageAdapter:
    """
    In-memory image processing adapter wrapping Pillow safely.
    """

    @classmethod
    def _parse_color(cls, color_str: Optional[str], default: Tuple[int, int, int] = (255, 255, 255)) -> Tuple[int, int, int]:
        if not color_str:
            return default
        try:
            return ImageColor.getrgb(color_str)
        except Exception:
            return default

    @classmethod
    def _composite_alpha_to_rgb(cls, img: Image.Image, background_color: Optional[str] = "#ffffff") -> Image.Image:
        """Composites an image with alpha channel onto a solid background for formats without alpha support."""
        bg_rgb = cls._parse_color(background_color, (255, 255, 255))
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            rgba = img.convert("RGBA")
            bg = Image.new("RGBA", rgba.size, bg_rgb + (255,))
            alpha_composite = Image.alpha_composite(bg, rgba)
            return alpha_composite.convert("RGB")
        return img.convert("RGB")

    @classmethod
    def probe(cls, data: bytes, extract_metadata: bool = True) -> Dict[str, Any]:
        """
        Extracts technical properties from raw image bytes in a strictly read-only manner.
        """
        img = safe_open_image(data)
        w, h = img.size
        fmt = (img.format or detect_image_format_from_magic(data)).upper()
        mode = img.mode
        has_alpha = mode in ("RGBA", "LA") or (mode == "P" and "transparency" in img.info)

        # Detect frame count for animated formats
        frame_count = 1
        is_animated = getattr(img, "is_animated", False)
        if is_animated and hasattr(img, "n_frames"):
            frame_count = img.n_frames

        # Extract orientation
        orientation = None
        metadata_summary = {}
        if extract_metadata:
            try:
                exif = img.getexif()
                if exif:
                    # 0x0112 is standard Orientation tag
                    orientation = exif.get(0x0112)
                    for tag_id, val in list(exif.items())[:15]:
                        metadata_summary[str(tag_id)] = str(val)[:100]
            except Exception:
                pass

        return {
            "format": fmt,
            "width": w,
            "height": h,
            "mode": mode,
            "has_alpha": has_alpha,
            "frame_count": frame_count,
            "orientation": orientation,
            "file_size_bytes": len(data),
            "is_animated": is_animated,
            "metadata_summary": metadata_summary,
        }

    @classmethod
    def resize(
        cls,
        data: bytes,
        target_width: Optional[int] = None,
        target_height: Optional[int] = None,
        scale_factor: Optional[float] = None,
        fit_mode: str = "contain",
        maintain_aspect_ratio: bool = True,
        output_format: Optional[str] = None,
        quality: int = 95,
    ) -> Tuple[bytes, str, int, int]:
        """
        Resizes an image according to target bounds, fit mode, and scale factor.
        Returns: (output_bytes, format, width, height)
        """
        img = safe_open_image(data)
        # Normalize orientation first
        img = ImageOps.exif_transpose(img) or img
        orig_w, orig_h = img.size

        # Determine target dimensions
        if scale_factor is not None and target_width is None and target_height is None:
            final_w = max(1, int(orig_w * scale_factor))
            final_h = max(1, int(orig_h * scale_factor))
        elif target_width is not None and target_height is None:
            final_w = target_width
            final_h = max(1, int(orig_h * (target_width / orig_w))) if maintain_aspect_ratio else orig_h
        elif target_height is not None and target_width is None:
            final_h = target_height
            final_w = max(1, int(orig_w * (target_height / orig_h))) if maintain_aspect_ratio else orig_w
        elif target_width is not None and target_height is not None:
            tw, th = target_width, target_height
            if fit_mode in ("stretch", "exact") or not maintain_aspect_ratio:
                final_w, final_h = tw, th
            elif fit_mode == "contain":
                ratio = min(tw / orig_w, th / orig_h)
                final_w = max(1, int(orig_w * ratio))
                final_h = max(1, int(orig_h * ratio))
            elif fit_mode == "cover":
                ratio = max(tw / orig_w, th / orig_h)
                final_w = max(1, int(orig_w * ratio))
                final_h = max(1, int(orig_h * ratio))
            else:
                final_w, final_h = tw, th
        else:
            final_w, final_h = orig_w, orig_h

        validate_dimensions(final_w, final_h)

        # Resample
        resized = img.resize((final_w, final_h), Image.Resampling.LANCZOS)

        # If fit_mode == "cover" and exact dimensions requested, center-crop to exact (tw, th)
        if fit_mode == "cover" and target_width is not None and target_height is not None:
            if final_w > target_width or final_h > target_height:
                left = (final_w - target_width) // 2
                top = (final_h - target_height) // 2
                resized = resized.crop((left, top, left + target_width, top + target_height))
                final_w, final_h = target_width, target_height

        # Determine output format
        orig_fmt = (img.format or detect_image_format_from_magic(data)).upper()
        fmt = (output_format.strip().upper() if output_format else orig_fmt)
        if fmt == "JPG":
            fmt = "JPEG"

        # Safe alpha handling if outputting to JPEG
        if fmt == "JPEG" and resized.mode in ("RGBA", "LA", "P"):
            resized = cls._composite_alpha_to_rgb(resized)

        bio = io.BytesIO()
        resized.save(bio, format=fmt, quality=quality)
        return bio.getvalue(), fmt, final_w, final_h

    @classmethod
    def crop_to_ratio(
        cls,
        data: bytes,
        target_ratio: str,
        output_format: Optional[str] = None,
        quality: int = 95,
    ) -> Tuple[bytes, str, int, int, str]:
        """
        Crops an image to a target aspect ratio using center crop.
        Returns: (output_bytes, format, width, height, applied_ratio)
        """
        img = safe_open_image(data)
        img = ImageOps.exif_transpose(img) or img
        orig_w, orig_h = img.size

        parts = target_ratio.split(":")
        ratio_w, ratio_h = float(parts[0]), float(parts[1])
        target_aspect = ratio_w / ratio_h
        current_aspect = orig_w / orig_h

        if abs(current_aspect - target_aspect) < 0.005:
            cropped = img
            new_w, new_h = orig_w, orig_h
        elif current_aspect > target_aspect:
            # Too wide: crop left & right
            new_w = max(1, int(orig_h * target_aspect))
            new_h = orig_h
            left = (orig_w - new_w) // 2
            cropped = img.crop((left, 0, left + new_w, orig_h))
        else:
            # Too tall: crop top & bottom
            new_w = orig_w
            new_h = max(1, int(orig_w / target_aspect))
            top = (orig_h - new_h) // 2
            cropped = img.crop((0, top, orig_w, top + new_h))

        orig_fmt = (img.format or detect_image_format_from_magic(data)).upper()
        fmt = (output_format.strip().upper() if output_format else orig_fmt)
        if fmt == "JPG":
            fmt = "JPEG"

        if fmt == "JPEG" and cropped.mode in ("RGBA", "LA", "P"):
            cropped = cls._composite_alpha_to_rgb(cropped)

        bio = io.BytesIO()
        cropped.save(bio, format=fmt, quality=quality)
        return bio.getvalue(), fmt, new_w, new_h, target_ratio

    @classmethod
    def auto_crop_content(
        cls,
        data: bytes,
        background_color: str = "auto",
        background_threshold: int = 10,
        padding_ratio: float = 0.0,
        output_format: Optional[str] = None,
        quality: int = 95,
    ) -> Tuple[bytes, str, int, int, int, int, List[int]]:
        """
        Automatically detects and strips outer solid or transparent borders.
        Returns: (output_bytes, format, orig_w, orig_h, output_w, output_h, [left, top, right, bottom])
        """
        img = safe_open_image(data)
        img = ImageOps.exif_transpose(img) or img
        orig_w, orig_h = img.size

        # Convert to RGBA for consistent bounding box detection
        rgba = img.convert("RGBA") if img.mode != "RGBA" else img.copy()
        bbox = None

        if background_color == "auto":
            # Check alpha channel transparency first
            alpha_bbox = rgba.getbbox()
            if alpha_bbox and alpha_bbox != (0, 0, orig_w, orig_h):
                bbox = alpha_bbox
            else:
                # Solid background: sample top-left pixel
                bg_pixel = rgba.getpixel((0, 0))
                bg_img = Image.new("RGBA", rgba.size, bg_pixel)
                diff = ImageChops.difference(rgba, bg_img)
                if background_threshold > 0:
                    diff_gray = diff.convert("L").point(lambda p: 255 if p > background_threshold else 0)
                    bbox = diff_gray.getbbox()
                else:
                    bbox = diff.getbbox()
        elif background_color.lower() == "transparent":
            bbox = rgba.getbbox()
        else:
            bg_rgb = cls._parse_color(background_color)
            bg_img = Image.new("RGBA", rgba.size, bg_rgb + (255,))
            diff = ImageChops.difference(rgba, bg_img)
            if background_threshold > 0:
                diff_gray = diff.convert("L").point(lambda p: 255 if p > background_threshold else 0)
                bbox = diff_gray.getbbox()
            else:
                bbox = diff.getbbox()

        if bbox is None:
            bbox = (0, 0, orig_w, orig_h)
            cropped = img
        else:
            left, top, right, bottom = bbox
            if padding_ratio > 0.0:
                pad_x = int((right - left) * padding_ratio)
                pad_y = int((bottom - top) * padding_ratio)
                left = max(0, left - pad_x)
                top = max(0, top - pad_y)
                right = min(orig_w, right + pad_x)
                bottom = min(orig_h, bottom + pad_y)
                bbox = (left, top, right, bottom)
            cropped = img.crop(bbox)

        out_w, out_h = cropped.size
        orig_fmt = (img.format or detect_image_format_from_magic(data)).upper()
        fmt = (output_format.strip().upper() if output_format else orig_fmt)
        if fmt == "JPG":
            fmt = "JPEG"

        if fmt == "JPEG" and cropped.mode in ("RGBA", "LA", "P"):
            cropped = cls._composite_alpha_to_rgb(cropped)

        bio = io.BytesIO()
        cropped.save(bio, format=fmt, quality=quality)
        return bio.getvalue(), fmt, orig_w, orig_h, out_w, out_h, list(bbox)

    @classmethod
    def convert(
        cls,
        data: bytes,
        target_format: str,
        quality: int = 95,
        background_color: Optional[str] = "#ffffff",
        strip_metadata: bool = False,
    ) -> Tuple[bytes, str, str, int, int]:
        """
        Converts image to another format with safe alpha handling.
        Returns: (output_bytes, source_format, target_format, width, height)
        """
        img = safe_open_image(data)
        img = ImageOps.exif_transpose(img) or img
        source_fmt = (img.format or detect_image_format_from_magic(data)).upper()
        target_fmt = target_format.strip().upper()
        if target_fmt == "JPG":
            target_fmt = "JPEG"

        if target_fmt == "JPEG" and img.mode in ("RGBA", "LA", "P"):
            img = cls._composite_alpha_to_rgb(img, background_color)

        bio = io.BytesIO()
        save_kwargs: Dict[str, Any] = {"format": target_fmt, "quality": quality}
        if not strip_metadata and hasattr(img, "info") and "exif" in img.info:
            save_kwargs["exif"] = img.info["exif"]

        img.save(bio, **save_kwargs)
        return bio.getvalue(), source_fmt, target_fmt, img.width, img.height

    @classmethod
    def optimize(
        cls,
        data: bytes,
        quality: int = 85,
        strip_metadata: bool = True,
        max_width: Optional[int] = None,
        max_height: Optional[int] = None,
    ) -> Tuple[bytes, str, int, int]:
        """
        Optimizes an image via quality tuning, metadata stripping, and optional bounding.
        Returns: (output_bytes, format, width, height)
        """
        img = safe_open_image(data)
        img = ImageOps.exif_transpose(img) or img
        w, h = img.size

        # Constrain dimensions if requested
        if max_width or max_height:
            mw = max_width or w
            mh = max_height or h
            if w > mw or h > mh:
                ratio = min(mw / w, mh / h)
                w = max(1, int(w * ratio))
                h = max(1, int(h * ratio))
                img = img.resize((w, h), Image.Resampling.LANCZOS)

        fmt = (img.format or detect_image_format_from_magic(data)).upper()
        if fmt == "JPG":
            fmt = "JPEG"

        bio = io.BytesIO()
        save_kwargs: Dict[str, Any] = {"format": fmt, "quality": quality, "optimize": True}
        if not strip_metadata and hasattr(img, "info") and "exif" in img.info:
            save_kwargs["exif"] = img.info["exif"]

        img.save(bio, **save_kwargs)
        return bio.getvalue(), fmt, w, h

    @classmethod
    def generate_thumbnail(
        cls,
        data: bytes,
        width: int = 256,
        height: int = 256,
        fit_mode: str = "contain",
        output_format: str = "webp",
        quality: int = 85,
    ) -> Tuple[bytes, str, int, int]:
        """
        Generates a deterministic thumbnail.
        Returns: (output_bytes, format, width, height)
        """
        return cls.resize(
            data=data,
            target_width=width,
            target_height=height,
            fit_mode=fit_mode,
            maintain_aspect_ratio=True,
            output_format=output_format,
            quality=quality,
        )
