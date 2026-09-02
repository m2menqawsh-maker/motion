import os
import logging
from pathlib import Path
from PIL import Image, ImageChops

logger = logging.getLogger(__name__)

def resolve_output_path(input_path: str, provided_output: str | None, suffix: str) -> str:
    input_p = Path(input_path)
    if provided_output:
        out_p = Path(provided_output)
        if not out_p.suffix:
            # Inherit original extension if not provided
            out_p = out_p.with_suffix(input_p.suffix)
        return str(out_p.absolute())
    
    return str((input_p.parent / f"{input_p.stem}_{suffix}{input_p.suffix}").absolute())

def upscale_image_file(file_path: str, target_width: int = 0, target_height: int = 0, output_path: str | None = None) -> str:
    out_path = resolve_output_path(file_path, output_path, "upscaled")
    
    with Image.open(file_path) as img:
        orig_w, orig_h = img.size
        
        if target_width <= 0 and target_height <= 0:
            raise ValueError("At least one of target_width or target_height must be > 0.")
            
        final_w = target_width
        final_h = target_height
        
        # Maintain aspect ratio if one dimension is missing
        if target_width > 0 and target_height <= 0:
            ratio = target_width / orig_w
            final_h = int(orig_h * ratio)
        elif target_height > 0 and target_width <= 0:
            ratio = target_height / orig_h
            final_w = int(orig_w * ratio)
            
        # If both are provided, it will forcefully stretch to the exact dimensions.
        logger.info(f"Upscaling {file_path} from {orig_w}x{orig_h} to {final_w}x{final_h}")
        
        # Convert to RGB if saving to format that doesn't support alpha (like JPEG)
        out_ext = Path(out_path).suffix.lower()
        if out_ext in [".jpg", ".jpeg"] and img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")
            
        upscaled = img.resize((final_w, final_h), Image.Resampling.LANCZOS)
        upscaled.save(out_path, quality=95)
        
    return out_path

def crop_to_ratio_file(file_path: str, target_ratio: str, output_path: str | None = None) -> str:
    """
    target_ratio: e.g. "9:16" or "1:1"
    """
    out_path = resolve_output_path(file_path, output_path, "ratio")
    
    try:
        rw_str, rh_str = target_ratio.split(":")
        ratio_w = float(rw_str)
        ratio_h = float(rh_str)
        target_aspect = ratio_w / ratio_h
    except Exception:
        raise ValueError(f"Invalid target_ratio format: {target_ratio}. Must be like '9:16'")
        
    with Image.open(file_path) as img:
        orig_w, orig_h = img.size
        orig_aspect = orig_w / orig_h
        
        if abs(orig_aspect - target_aspect) < 0.01:
            logger.info("Image already matches target ratio. Saving a copy.")
            img.save(out_path)
            return out_path
            
        if orig_aspect > target_aspect:
            # Image is wider than target. Crop left/right.
            new_w = int(orig_h * target_aspect)
            new_h = orig_h
        else:
            # Image is taller than target. Crop top/bottom.
            new_w = orig_w
            new_h = int(orig_w / target_aspect)
            
        left = (orig_w - new_w) // 2
        top = (orig_h - new_h) // 2
        right = left + new_w
        bottom = top + new_h
        
        logger.info(f"Cropping {file_path} from {orig_w}x{orig_h} to {new_w}x{new_h}")
        
        # Convert to RGB if saving to format that doesn't support alpha (like JPEG)
        out_ext = Path(out_path).suffix.lower()
        if out_ext in [".jpg", ".jpeg"] and img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")
            
        cropped = img.crop((left, top, right, bottom))
        cropped.save(out_path, quality=95)
        
    return out_path

def auto_crop_content_file(file_path: str, background_color: str = "auto", background_threshold: int = 10, output_path: str | None = None) -> str:
    out_path = resolve_output_path(file_path, output_path, "autocrop")
    
    with Image.open(file_path) as img:
        # Convert to RGB if saving to format that doesn't support alpha (like JPEG)
        out_ext = Path(out_path).suffix.lower()
        if out_ext in [".jpg", ".jpeg"] and img.mode in ("RGBA", "P", "LA"):
            converted_img = img.convert("RGB")
            mode = "RGB"
        else:
            converted_img = img.convert("RGBA") if img.mode not in ("RGB", "RGBA") else img.copy()
            mode = converted_img.mode
            
        bbox = None
        
        if background_color == "auto":
            # If it has alpha and there are transparent pixels, use alpha as bound
            if mode == "RGBA":
                bbox = converted_img.getbbox()
                if bbox == (0, 0, img.width, img.height):
                    # It means the whole image is non-transparent, OR background is solid color.
                    # Fallback to corner pixel.
                    bg = converted_img.getpixel((0, 0))
                else:
                    bg = None # Successfully used alpha
            else:
                bg = converted_img.getpixel((0, 0))
        elif background_color.lower() == "transparent":
            if mode != "RGBA":
                converted_img = converted_img.convert("RGBA")
            bbox = converted_img.getbbox()
            bg = None
        elif background_color.lower() in ("white", "#ffffff"):
            bg = (255, 255, 255, 255) if mode == "RGBA" else (255, 255, 255)
        elif background_color.lower() in ("black", "#000000"):
            bg = (0, 0, 0, 255) if mode == "RGBA" else (0, 0, 0)
        else:
            # Try to parse hex or named color? 
            # Pillow ImageColor can do this, but to keep it simple we fall back to top-left pixel.
            logger.warning(f"Unknown background_color '{background_color}'. Falling back to corner pixel.")
            bg = converted_img.getpixel((0, 0))
            
        if bg is not None:
            # We need to subtract the background color from the image and find non-zero
            bg_image = Image.new(mode, converted_img.size, bg)
            diff = ImageChops.difference(converted_img, bg_image)
            # Add thresholding if needed. ImageChops gives abs difference.
            if background_threshold > 0:
                # Convert to grayscale to evaluate threshold
                diff_gray = diff.convert("L")
                diff = diff_gray.point(lambda p: 255 if p > background_threshold else 0)
                diff = diff.convert(mode)
            bbox = diff.getbbox()
            
        if bbox:
            logger.info(f"Auto-cropping {file_path} to bounding box: {bbox}")
            cropped = converted_img.crop(bbox)
            
            # Revert to original img's converted mode to avoid saving RGBA to JPG
            if out_ext in [".jpg", ".jpeg"] and cropped.mode == "RGBA":
                cropped = cropped.convert("RGB")
                
            cropped.save(out_path, quality=95)
        else:
            logger.info("Could not find a croppable background. Saving original.")
            img.save(out_path)
            
    return out_path
