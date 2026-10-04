"""
ai/mcp/adapters/__init__.py
===========================
Hardened adapters for retained MCP operations and parity validators (S27.10).
"""

from __future__ import annotations

from ai.mcp.adapters.base import BaseMCPAdapter, run_safe_subprocess
from ai.mcp.adapters.audio import (
    AudioTrimAdapter,
    AudioNormalizeAdapter,
    AudioSilenceAdapter,
    AudioExtendAdapter,
)
from ai.mcp.adapters.video import (
    VideoTrimAdapter,
    VideoResizeAdapter,
    VideoExtendAdapter,
    VideoBlackFramesAdapter,
)
from ai.mcp.adapters.image import (
    ImageUpscaleAdapter,
    ImageCropRatioAdapter,
    ImageAutoCropAdapter,
)
from ai.mcp.adapters.parity import (
    verify_cache_check_parity,
    verify_asset_status_parity,
    verify_save_cache_parity,
)

__all__ = [
    "BaseMCPAdapter",
    "run_safe_subprocess",
    "AudioTrimAdapter",
    "AudioNormalizeAdapter",
    "AudioSilenceAdapter",
    "AudioExtendAdapter",
    "VideoTrimAdapter",
    "VideoResizeAdapter",
    "VideoExtendAdapter",
    "VideoBlackFramesAdapter",
    "ImageUpscaleAdapter",
    "ImageCropRatioAdapter",
    "ImageAutoCropAdapter",
    "verify_cache_check_parity",
    "verify_asset_status_parity",
    "verify_save_cache_parity",
]
