"""
ai/mcp/compatibility/mappers.py
=================================
Bidirectional contract mappers translating between legacy MCP tool invocations
and canonical CapabilityRequest / CapabilityResult models (S28-M09).

Invariants:
- Never exposes host filesystem paths as canonical product identities.
- Translates legacy untyped/loosely typed arguments into strictly validated Pydantic models.
- Preserves machine-readable error codes and failure contexts.
- Rejects path traversal and parameter injection before reaching domain services.
"""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, Optional, Tuple

from ai.contracts import (
    AIContractModel,
    CapabilityRequest,
    CapabilityResult,
    CapabilityType,
)
from ai.contracts.media_ops import (
    AutoCropInput,
    CancelJobInput,
    ChangeVideoSpeedInput,
    CheckCacheInput,
    CropRatioInput,
    DetectBlackFramesInput,
    DownloadIconInput,
    DownloadRemoteMediaInput,
    EnforceKeyframesInput,
    ExtendAudioInput,
    ExtendVideoInput,
    ExtractMediaPageInput,
    GetJobStatusInput,
    InspectMediaInput,
    MutateAssetStatusInput,
    NormalizeAudioInput,
    NormalizeLoudnessInput,
    ResizeVideoInput,
    SearchIconsInput,
    SearchSoundEffectsInput,
    SearchStockAudioInput,
    SearchStockImagesInput,
    SearchStockVideosInput,
    SegmentSpeechInput,
    SpeechManifestInput,
    SpeechTimelineInput,
    StoreCacheInput,
    TrimAudioInput,
    TrimSilenceInput,
    TrimVideoInput,
    UpscaleImageInput,
)
from ai.image_processing.contracts import (
    AutoCropImageRequest,
    CropImageRatioRequest,
    ResizeImageRequest,
)


def _sanitize_path(val: Optional[str]) -> Optional[str]:
    """Rejects traversal tokens and normalizes path representation."""
    if not val or not isinstance(val, str):
        return val
    if ".." in val or "%2e%2e" in val.lower():
        raise ValueError(f"Path traversal detected: {val}")
    return val.replace("\\", "/").strip()


# =============================================================================
# Request Mappers: Legacy dict -> Canonical input dict
# =============================================================================

def map_check_cache_request(args: Dict[str, Any], project_id: str) -> Dict[str, Any]:
    return {
        "project_id": args.get("project_id", project_id),
        "asset_id": str(args.get("asset_id", "")),
        "transformation_hash": str(args.get("specs_hash", args.get("transformation_hash", ""))),
    }

def map_save_to_cache_request(args: Dict[str, Any], project_id: str) -> Dict[str, Any]:
    src = _sanitize_path(args.get("file_path", args.get("source_storage_key", "")))
    return {
        "project_id": args.get("project_id", project_id),
        "asset_id": str(args.get("asset_id", "")),
        "transformation_hash": str(args.get("specs_hash", args.get("transformation_hash", ""))),
        "source_storage_key": src,
    }

def map_trim_audio_request(args: Dict[str, Any], project_id: str) -> Dict[str, Any]:
    return {
        "project_id": args.get("project_id", project_id),
        "source_audio_key": _sanitize_path(args.get("file_path", args.get("source_audio_key", ""))),
        "target_duration_seconds": float(args.get("target_duration", args.get("target_duration_seconds", 0.0))),
        "output_audio_key": _sanitize_path(args.get("output_path", args.get("output_audio_key"))),
    }

def map_extend_audio_request(args: Dict[str, Any], project_id: str) -> Dict[str, Any]:
    return {
        "project_id": args.get("project_id", project_id),
        "source_audio_key": _sanitize_path(args.get("file_path", args.get("source_audio_key", ""))),
        "target_duration_seconds": float(args.get("target_duration", args.get("target_duration_seconds", 0.0))),
        "method": str(args.get("method", "loop")),
        "output_audio_key": _sanitize_path(args.get("output_path", args.get("output_audio_key"))),
        "crossfade_duration_seconds": float(args.get("crossfade_duration_seconds", 0.5)),
    }

def map_normalize_loudness_request(args: Dict[str, Any], project_id: str) -> Dict[str, Any]:
    return {
        "project_id": args.get("project_id", project_id),
        "source_audio_key": _sanitize_path(args.get("file_path", args.get("source_audio_key", ""))),
        "target_lufs": float(args.get("target_lufs", -16.0)),
        "output_audio_key": _sanitize_path(args.get("output_path", args.get("output_audio_key"))),
    }

def map_trim_silence_request(args: Dict[str, Any], project_id: str) -> Dict[str, Any]:
    return {
        "project_id": args.get("project_id", project_id),
        "source_audio_key": _sanitize_path(args.get("file_path", args.get("source_audio_key", ""))),
        "threshold_db": float(args.get("threshold_db", -40.0)),
        "min_silence_duration_seconds": float(args.get("min_silence_duration", args.get("min_silence_duration_seconds", 0.1))),
        "trim_start": bool(args.get("trim_start", True)),
        "trim_end": bool(args.get("trim_end", True)),
        "output_audio_key": _sanitize_path(args.get("output_path", args.get("output_audio_key"))),
    }

def map_split_voiceover_sentences_request(args: Dict[str, Any], project_id: str) -> Dict[str, Any]:
    return {
        "project_id": args.get("project_id", project_id),
        "source_audio_key": _sanitize_path(args.get("audio_path", args.get("source_audio_key", ""))),
        "analysis_storage_key": _sanitize_path(args.get("analysis_path", args.get("analysis_storage_key"))),
        "output_directory_key": _sanitize_path(args.get("output_dir", args.get("output_directory_key"))),
        "min_sentence_duration_seconds": float(args.get("min_sentence_duration", 2.0)),
        "max_sentence_duration_seconds": float(args.get("max_sentence_duration", 10.0)),
        "silence_threshold_seconds": float(args.get("silence_threshold", 0.3)),
    }

def map_get_voiceover_manifest_request(args: Dict[str, Any], project_id: str) -> Dict[str, Any]:
    return {
        "project_id": args.get("project_id", project_id),
        "audio_storage_key": _sanitize_path(args.get("audio_path", args.get("audio_storage_key", ""))),
        "analysis_data": args.get("analysis", {}),
        "split_sentences": args.get("split_result", {}).get("sentences", []) if isinstance(args.get("split_result"), dict) else [],
        "output_manifest_key": _sanitize_path(args.get("output_path", args.get("output_manifest_key"))),
    }

def map_build_voiceover_timeline_request(args: Dict[str, Any], project_id: str) -> Dict[str, Any]:
    return {
        "project_id": args.get("project_id", project_id),
        "manifest_data": args.get("manifest", {}),
        "fps": float(args.get("fps", 30.0)),
        "output_timeline_key": _sanitize_path(args.get("output_path", args.get("output_timeline_key"))),
    }

def map_trim_video_request(args: Dict[str, Any], project_id: str) -> Dict[str, Any]:
    return {
        "project_id": args.get("project_id", project_id),
        "source_video_key": _sanitize_path(args.get("file_path", args.get("source_video_key", ""))),
        "target_duration_seconds": float(args.get("target_duration", args.get("target_duration_seconds", 0.0))),
        "output_video_key": _sanitize_path(args.get("output_path", args.get("output_video_key"))),
    }

def map_extend_video_request(args: Dict[str, Any], project_id: str) -> Dict[str, Any]:
    return {
        "project_id": args.get("project_id", project_id),
        "source_video_key": _sanitize_path(args.get("file_path", args.get("source_video_key", ""))),
        "target_duration_seconds": float(args.get("target_duration", args.get("target_duration_seconds", 0.0))),
        "method": str(args.get("method", "loop")),
        "output_video_key": _sanitize_path(args.get("output_path", args.get("output_video_key"))),
    }

def map_resize_video_request(args: Dict[str, Any], project_id: str) -> Dict[str, Any]:
    return {
        "project_id": args.get("project_id", project_id),
        "source_video_key": _sanitize_path(args.get("file_path", args.get("source_video_key", ""))),
        "target_width": int(args.get("target_width", 1080)),
        "target_height": int(args.get("target_height", 1920)),
        "maintain_aspect_ratio": bool(args.get("maintain_aspect_ratio", True)),
        "output_video_key": _sanitize_path(args.get("output_path", args.get("output_video_key"))),
    }

def map_detect_black_frames_request(args: Dict[str, Any], project_id: str) -> Dict[str, Any]:
    return {
        "project_id": args.get("project_id", project_id),
        "source_video_key": _sanitize_path(args.get("file_path", args.get("source_video_key", ""))),
        "threshold": float(args.get("threshold", 0.1)),
        "min_duration_seconds": float(args.get("min_duration", args.get("min_duration_seconds", 0.1))),
        "trim_start": bool(args.get("trim_start", True)),
        "trim_end": bool(args.get("trim_end", True)),
        "output_video_key": _sanitize_path(args.get("output_path", args.get("output_video_key"))),
    }

def map_speed_up_video_request(args: Dict[str, Any], project_id: str) -> Dict[str, Any]:
    return {
        "project_id": args.get("project_id", project_id),
        "source_video_key": _sanitize_path(args.get("input_path", args.get("file_path", args.get("source_video_key", "")))),
        "speed_factor": float(args.get("speed_factor", 1.0)),
        "output_video_key": _sanitize_path(args.get("output_path", args.get("output_video_key"))),
    }

def map_get_job_status_request(args: Dict[str, Any], project_id: str) -> Dict[str, Any]:
    return {
        "project_id": args.get("project_id", project_id),
        "job_id": str(args.get("job_id", "")),
    }

def map_cancel_job_request(args: Dict[str, Any], project_id: str) -> Dict[str, Any]:
    return {
        "project_id": args.get("project_id", project_id),
        "job_id": str(args.get("job_id", "")),
        "reason": str(args.get("reason", "Cancelled by MCP client")),
    }

def map_increase_keyframes_request(args: Dict[str, Any], project_id: str) -> Dict[str, Any]:
    return {
        "project_id": args.get("project_id", project_id),
        "source_video_key": _sanitize_path(args.get("input_path", args.get("file_path", args.get("source_video_key", "")))),
        "keyframe_interval": int(args.get("keyframe_interval", 1)),
        "output_video_key": _sanitize_path(args.get("output_path", args.get("output_video_key"))),
    }

def map_get_files_info_request(args: Dict[str, Any], project_id: str) -> Dict[str, Any]:
    files = args.get("file_paths", [args.get("file_path", "")])
    first_file = _sanitize_path(files[0] if files else "")
    return {
        "project_id": args.get("project_id", project_id),
        "media_storage_key": first_file,
    }

def map_upscale_image_request(args: Dict[str, Any], project_id: str) -> Dict[str, Any]:
    tw = args.get("target_width")
    th = args.get("target_height")
    res: Dict[str, Any] = {
        "project_id": args.get("project_id", project_id),
        "image_storage_key": _sanitize_path(args.get("file_path", args.get("image_storage_key", ""))),
    }
    if tw and int(tw) > 0:
        res["target_width"] = int(tw)
    if th and int(th) > 0:
        res["target_height"] = int(th)
    return res

def map_crop_to_ratio_request(args: Dict[str, Any], project_id: str) -> Dict[str, Any]:
    return {
        "project_id": args.get("project_id", project_id),
        "image_storage_key": _sanitize_path(args.get("file_path", args.get("image_storage_key", ""))),
        "target_ratio": str(args.get("target_ratio", "9:16")),
    }

def map_auto_crop_content_request(args: Dict[str, Any], project_id: str) -> Dict[str, Any]:
    return {
        "project_id": args.get("project_id", project_id),
        "image_storage_key": _sanitize_path(args.get("file_path", args.get("image_storage_key", ""))),
        "background_color": str(args.get("background_color", "auto")),
        "background_threshold": int(args.get("background_threshold", 10)),
    }

def map_change_asset_status_request(args: Dict[str, Any], project_id: str) -> Dict[str, Any]:
    return {
        "project_id": args.get("project_id", project_id),
        "asset_id": str(args.get("asset_id", "")),
        "new_status": str(args.get("to_status", args.get("new_status", "ready"))),
    }

def map_download_direct_file_request(args: Dict[str, Any], project_id: str) -> Dict[str, Any]:
    return {
        "project_id": args.get("project_id", project_id),
        "remote_url": str(args.get("url", args.get("remote_url", ""))),
        "asset_type": str(args.get("asset_type", "video")),
        "source_provider": str(args.get("source", args.get("source_provider", "direct"))),
        "target_asset_id": str(args.get("asset_id", args.get("target_asset_id", ""))),
    }

def map_download_media_page_request(args: Dict[str, Any], project_id: str) -> Dict[str, Any]:
    return {
        "project_id": args.get("project_id", project_id),
        "page_url": str(args.get("url", args.get("page_url", ""))),
        "asset_type": str(args.get("asset_type", "video")),
        "source_provider": str(args.get("source", args.get("source_provider", "ytdlp"))),
        "target_asset_id": str(args.get("asset_id", args.get("target_asset_id", ""))),
    }

def map_iconify_search_request(args: Dict[str, Any], project_id: str) -> Dict[str, Any]:
    return {
        "project_id": args.get("project_id", project_id),
        "query": str(args.get("query", "")),
        "limit": int(args.get("limit", 20)),
    }

def map_download_iconify_request(args: Dict[str, Any], project_id: str) -> Dict[str, Any]:
    return {
        "project_id": args.get("project_id", project_id),
        "icon_name": str(args.get("icon_name", "")),
        "target_asset_id": str(args.get("asset_id", args.get("target_asset_id", ""))),
    }

def map_stock_images_request(args: Dict[str, Any], project_id: str) -> Dict[str, Any]:
    return {
        "project_id": args.get("project_id", project_id),
        "query": str(args.get("query", "")),
        "per_page": int(args.get("per_page", 15)),
        "orientation": str(args.get("orientation", "all")),
    }

def map_stock_videos_request(args: Dict[str, Any], project_id: str) -> Dict[str, Any]:
    return {
        "project_id": args.get("project_id", project_id),
        "query": str(args.get("query", "")),
        "per_page": int(args.get("per_page", 15)),
        "orientation": str(args.get("orientation", "all")),
    }

def map_stock_audio_request(args: Dict[str, Any], project_id: str) -> Dict[str, Any]:
    return {
        "project_id": args.get("project_id", project_id),
        "query": str(args.get("query", "")),
        "per_page": int(args.get("max_results", args.get("per_page", 10))),
    }

def map_sound_effects_request(args: Dict[str, Any], project_id: str) -> Dict[str, Any]:
    return {
        "project_id": args.get("project_id", project_id),
        "query": str(args.get("query", "")),
        "per_page": int(args.get("page_size", args.get("per_page", 15))),
    }


# =============================================================================
# Response Mappers: Canonical output dict -> Legacy return value
# =============================================================================

def map_default_output(res: CapabilityResult) -> Any:
    out = res.output or {}
    for key in ("output_audio_key", "output_video_key", "output_storage_key", "cached_storage_key"):
        if key in out and out[key]:
            return str(out[key])
    return out

def map_check_cache_response(res: CapabilityResult) -> Optional[str]:
    out = res.output or {}
    if out.get("cache_hit"):
        return str(out.get("cached_storage_key", ""))
    return None

def map_save_to_cache_response(res: CapabilityResult) -> str:
    out = res.output or {}
    return str(out.get("cached_storage_key", ""))

def map_trim_silence_response(res: CapabilityResult) -> Dict[str, Any]:
    out = res.output or {}
    return {
        "output_path": out.get("output_audio_key", ""),
        "trimmed_start_seconds": out.get("trimmed_start_seconds", 0.0),
        "trimmed_end_seconds": out.get("trimmed_end_seconds", 0.0),
    }

def map_extend_video_response(res: CapabilityResult) -> str:
    out = res.output or {}
    key = out.get("output_video_key", "")
    return f"Success: Extended file saved to {key}"
