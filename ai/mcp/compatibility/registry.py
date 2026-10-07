"""
ai/mcp/compatibility/registry.py
==================================
Authoritative registry of all 34 legacy MCP tools mapped to canonical capabilities (S28-M09).

Invariants:
- Deterministic, complete mapping of all discovered repository MCP tools.
- Explicit canonical ownership for each tool (zero authority inside MCP).
- Explicit compatibility status: FULL, PARTIAL, DEPRECATED, BLOCKED.
- Explicit blocking of insecure tools (specifically concatenate_videos due to shell injection).
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple

from ai.contracts.common import CapabilityType
from ai.mcp.compatibility.contracts import (
    LegacyToolDescriptor,
    MCPCompatibilityStatus,
)
from ai.mcp.compatibility.mappers import (
    map_auto_crop_content_request,
    map_build_voiceover_timeline_request,
    map_cancel_job_request,
    map_change_asset_status_request,
    map_check_cache_request,
    map_check_cache_response,
    map_crop_to_ratio_request,
    map_default_output,
    map_detect_black_frames_request,
    map_download_direct_file_request,
    map_download_iconify_request,
    map_download_media_page_request,
    map_extend_audio_request,
    map_extend_video_request,
    map_extend_video_response,
    map_get_files_info_request,
    map_get_job_status_request,
    map_get_voiceover_manifest_request,
    map_iconify_search_request,
    map_increase_keyframes_request,
    map_normalize_loudness_request,
    map_resize_video_request,
    map_save_to_cache_request,
    map_save_to_cache_response,
    map_sound_effects_request,
    map_speed_up_video_request,
    map_split_voiceover_sentences_request,
    map_stock_audio_request,
    map_stock_images_request,
    map_stock_videos_request,
    map_trim_audio_request,
    map_trim_silence_request,
    map_trim_silence_response,
    map_trim_video_request,
    map_upscale_image_request,
)


class CompatibilityToolEntry:
    def __init__(
        self,
        descriptor: LegacyToolDescriptor,
        request_mapper: Optional[Callable[[Dict[str, Any], str], Dict[str, Any]]] = None,
        response_mapper: Optional[Callable[[Any], Any]] = None,
    ):
        self.descriptor = descriptor
        self.request_mapper = request_mapper or (lambda args, proj: args)
        self.response_mapper = response_mapper or map_default_output


def _build_authoritative_tool_entries() -> Dict[Tuple[str, str], CompatibilityToolEntry]:
    """Constructs the canonical 34 legacy MCP tool mappings."""
    entries: List[CompatibilityToolEntry] = [
        # ---------------------------------------------------------------------
        # 1. audio-tools-mcp (8 tools)
        # ---------------------------------------------------------------------
        CompatibilityToolEntry(
            descriptor=LegacyToolDescriptor(
                legacy_server_id="audio-tools-mcp",
                legacy_tool_name="trim_audio",
                capability_id=CapabilityType.TRIM_AUDIO,
                canonical_owner="MediaProcessingService",
                status=MCPCompatibilityStatus.FULL,
                description="Trims an audio file to a specified duration",
            ),
            request_mapper=map_trim_audio_request,
            response_mapper=map_default_output,
        ),
        CompatibilityToolEntry(
            descriptor=LegacyToolDescriptor(
                legacy_server_id="audio-tools-mcp",
                legacy_tool_name="extend_audio",
                capability_id=CapabilityType.EXTEND_AUDIO,
                canonical_owner="MediaProcessingService",
                status=MCPCompatibilityStatus.FULL,
                description="Extends audio to a target duration via looping or crossfade",
            ),
            request_mapper=map_extend_audio_request,
            response_mapper=map_default_output,
        ),
        CompatibilityToolEntry(
            descriptor=LegacyToolDescriptor(
                legacy_server_id="audio-tools-mcp",
                legacy_tool_name="normalize_loudness",
                capability_id=CapabilityType.NORMALIZE_AUDIO_LOUDNESS,
                canonical_owner="MediaProcessingService",
                status=MCPCompatibilityStatus.FULL,
                description="Normalizes audio loudness to target LUFS",
            ),
            request_mapper=map_normalize_loudness_request,
            response_mapper=map_default_output,
        ),
        CompatibilityToolEntry(
            descriptor=LegacyToolDescriptor(
                legacy_server_id="audio-tools-mcp",
                legacy_tool_name="detect_and_trim_silence",
                capability_id=CapabilityType.TRIM_AUDIO_SILENCE,
                canonical_owner="MediaProcessingService",
                status=MCPCompatibilityStatus.FULL,
                description="Detects and trims leading/trailing silence from audio",
            ),
            request_mapper=map_trim_silence_request,
            response_mapper=map_trim_silence_response,
        ),
        CompatibilityToolEntry(
            descriptor=LegacyToolDescriptor(
                legacy_server_id="audio-tools-mcp",
                legacy_tool_name="analyze_voiceover",
                capability_id=CapabilityType.SPEECH_TO_TEXT,
                canonical_owner="ModelRouter / LocalSTTProvider",
                status=MCPCompatibilityStatus.FULL,
                description="Transcribes and timestamps voiceover audio",
            ),
            request_mapper=lambda args, proj: {
                "project_id": args.get("project_id", proj),
                "audio_storage_key": args.get("audio_path", args.get("audio_storage_key", "")),
                "language": args.get("language"),
                "model_size": args.get("model_size"),
            },
            response_mapper=map_default_output,
        ),
        CompatibilityToolEntry(
            descriptor=LegacyToolDescriptor(
                legacy_server_id="audio-tools-mcp",
                legacy_tool_name="split_voiceover_sentences",
                capability_id=CapabilityType.SEGMENT_SPEECH_AUDIO,
                canonical_owner="SpeechPreparationService",
                status=MCPCompatibilityStatus.FULL,
                description="Splits voiceover words into sentence segments",
            ),
            request_mapper=map_split_voiceover_sentences_request,
            response_mapper=map_default_output,
        ),
        CompatibilityToolEntry(
            descriptor=LegacyToolDescriptor(
                legacy_server_id="audio-tools-mcp",
                legacy_tool_name="get_voiceover_manifest",
                capability_id=CapabilityType.GENERATE_SPEECH_MANIFEST,
                canonical_owner="SpeechManifestBuilder",
                status=MCPCompatibilityStatus.FULL,
                description="Aggregates STT analysis and sentence splits into manifest",
            ),
            request_mapper=map_get_voiceover_manifest_request,
            response_mapper=map_default_output,
        ),
        CompatibilityToolEntry(
            descriptor=LegacyToolDescriptor(
                legacy_server_id="audio-tools-mcp",
                legacy_tool_name="build_voiceover_timeline",
                capability_id=CapabilityType.BUILD_SPEECH_TIMELINE,
                canonical_owner="SpeechTimelineBuilder",
                status=MCPCompatibilityStatus.FULL,
                description="Builds chronological audio timeline for Remotion",
            ),
            request_mapper=map_build_voiceover_timeline_request,
            response_mapper=map_default_output,
        ),

        # ---------------------------------------------------------------------
        # 2. common-tools-mcp (2 tools)
        # ---------------------------------------------------------------------
        CompatibilityToolEntry(
            descriptor=LegacyToolDescriptor(
                legacy_server_id="common-tools-mcp",
                legacy_tool_name="check_cache",
                capability_id=CapabilityType.CHECK_MEDIA_CACHE,
                canonical_owner="AssetService",
                status=MCPCompatibilityStatus.FULL,
                description="Checks if a processed media variant exists in project cache",
            ),
            request_mapper=map_check_cache_request,
            response_mapper=map_check_cache_response,
        ),
        CompatibilityToolEntry(
            descriptor=LegacyToolDescriptor(
                legacy_server_id="common-tools-mcp",
                legacy_tool_name="save_to_cache",
                capability_id=CapabilityType.STORE_MEDIA_CACHE,
                canonical_owner="AssetService",
                status=MCPCompatibilityStatus.FULL,
                description="Saves a processed media variant to project cache",
            ),
            request_mapper=map_save_to_cache_request,
            response_mapper=map_save_to_cache_response,
        ),

        # ---------------------------------------------------------------------
        # 3. ffmpeg-mcp-server (6 tools)
        # ---------------------------------------------------------------------
        CompatibilityToolEntry(
            descriptor=LegacyToolDescriptor(
                legacy_server_id="ffmpeg-mcp-server",
                legacy_tool_name="speed_up_video",
                capability_id=CapabilityType.CHANGE_VIDEO_SPEED,
                canonical_owner="MediaProcessingService",
                status=MCPCompatibilityStatus.FULL,
                description="Changes playback speed of video asset",
            ),
            request_mapper=map_speed_up_video_request,
            response_mapper=map_default_output,
        ),
        CompatibilityToolEntry(
            descriptor=LegacyToolDescriptor(
                legacy_server_id="ffmpeg-mcp-server",
                legacy_tool_name="check_processing_status",
                capability_id=CapabilityType.GET_JOB_STATUS,
                canonical_owner="RunService",
                status=MCPCompatibilityStatus.FULL,
                description="Retrieves status and progress of an asynchronous processing job",
            ),
            request_mapper=map_get_job_status_request,
            response_mapper=map_default_output,
        ),
        CompatibilityToolEntry(
            descriptor=LegacyToolDescriptor(
                legacy_server_id="ffmpeg-mcp-server",
                legacy_tool_name="cancel_video_processing",
                capability_id=CapabilityType.CANCEL_PROCESSING_JOB,
                canonical_owner="RunService",
                status=MCPCompatibilityStatus.FULL,
                description="Cancels an active asynchronous processing job",
            ),
            request_mapper=map_cancel_job_request,
            response_mapper=map_default_output,
        ),
        CompatibilityToolEntry(
            descriptor=LegacyToolDescriptor(
                legacy_server_id="ffmpeg-mcp-server",
                legacy_tool_name="increase_keyframes",
                capability_id=CapabilityType.ENFORCE_KEYFRAME_INTERVAL,
                canonical_owner="MediaProcessingService",
                status=MCPCompatibilityStatus.PARTIAL,
                description="Enforces regular GOP keyframe intervals (legacy Node queue deprecated)",
                notes="Legacy Node background queue quarantined; native media processing handles keyframes.",
            ),
            request_mapper=map_increase_keyframes_request,
            response_mapper=map_default_output,
        ),
        CompatibilityToolEntry(
            descriptor=LegacyToolDescriptor(
                legacy_server_id="ffmpeg-mcp-server",
                legacy_tool_name="get_files_info",
                capability_id=CapabilityType.INSPECT_MEDIA,
                canonical_owner="MediaProcessingService",
                status=MCPCompatibilityStatus.FULL,
                description="Probes duration, streams, and codecs of media files",
            ),
            request_mapper=map_get_files_info_request,
            response_mapper=map_default_output,
        ),
        CompatibilityToolEntry(
            descriptor=LegacyToolDescriptor(
                legacy_server_id="ffmpeg-mcp-server",
                legacy_tool_name="concatenate_videos",
                capability_id=CapabilityType.CONCATENATE_VIDEOS,
                canonical_owner="MediaProcessingService / Remotion",
                status=MCPCompatibilityStatus.BLOCKED,
                is_security_blocked=True,
                block_reason="Verified shell injection vulnerability in legacy Node concat implementation; composition governed by Remotion React engine.",
                description="Concatenates video segments (SECURITY BLOCKED)",
            ),
            request_mapper=lambda args, proj: args,
            response_mapper=map_default_output,
        ),

        # ---------------------------------------------------------------------
        # 4. image-tools-mcp (3 tools)
        # ---------------------------------------------------------------------
        CompatibilityToolEntry(
            descriptor=LegacyToolDescriptor(
                legacy_server_id="image-tools-mcp",
                legacy_tool_name="upscale_image",
                capability_id=CapabilityType.RESIZE_IMAGE,
                canonical_owner="ImageProcessingService",
                status=MCPCompatibilityStatus.FULL,
                description="Scales or resizes an image with Lanczos resampling",
            ),
            request_mapper=map_upscale_image_request,
            response_mapper=map_default_output,
        ),
        CompatibilityToolEntry(
            descriptor=LegacyToolDescriptor(
                legacy_server_id="image-tools-mcp",
                legacy_tool_name="crop_to_ratio",
                capability_id=CapabilityType.CROP_IMAGE_TO_RATIO,
                canonical_owner="ImageProcessingService",
                status=MCPCompatibilityStatus.FULL,
                description="Crops an image to a target aspect ratio",
            ),
            request_mapper=map_crop_to_ratio_request,
            response_mapper=map_default_output,
        ),
        CompatibilityToolEntry(
            descriptor=LegacyToolDescriptor(
                legacy_server_id="image-tools-mcp",
                legacy_tool_name="auto_crop_content",
                capability_id=CapabilityType.AUTO_CROP_IMAGE,
                canonical_owner="ImageProcessingService",
                status=MCPCompatibilityStatus.FULL,
                description="Crops solid borders around image content",
            ),
            request_mapper=map_auto_crop_content_request,
            response_mapper=map_default_output,
        ),

        # ---------------------------------------------------------------------
        # 5. media-sources-mcp (11 tools)
        # ---------------------------------------------------------------------
        CompatibilityToolEntry(
            descriptor=LegacyToolDescriptor(
                legacy_server_id="media-sources-mcp",
                legacy_tool_name="download_direct_file",
                capability_id=CapabilityType.DOWNLOAD_REMOTE_MEDIA,
                canonical_owner="StockMediaService",
                status=MCPCompatibilityStatus.FULL,
                description="Downloads direct media file to project storage",
            ),
            request_mapper=map_download_direct_file_request,
            response_mapper=map_default_output,
        ),
        CompatibilityToolEntry(
            descriptor=LegacyToolDescriptor(
                legacy_server_id="media-sources-mcp",
                legacy_tool_name="download_media_page",
                capability_id=CapabilityType.EXTRACT_MEDIA_PAGE,
                canonical_owner="StockMediaService",
                status=MCPCompatibilityStatus.FULL,
                description="Extracts media from page URL via yt-dlp",
            ),
            request_mapper=map_download_media_page_request,
            response_mapper=map_default_output,
        ),
        CompatibilityToolEntry(
            descriptor=LegacyToolDescriptor(
                legacy_server_id="media-sources-mcp",
                legacy_tool_name="change_asset_status",
                capability_id=CapabilityType.MUTATE_ASSET_STATUS,
                canonical_owner="AssetService",
                status=MCPCompatibilityStatus.FULL,
                description="Updates asset lifecycle status in Manifest v2",
            ),
            request_mapper=map_change_asset_status_request,
            response_mapper=map_default_output,
        ),
        CompatibilityToolEntry(
            descriptor=LegacyToolDescriptor(
                legacy_server_id="media-sources-mcp",
                legacy_tool_name="pixabay_search_images",
                capability_id=CapabilityType.SEARCH_STOCK_IMAGES,
                canonical_owner="StockMediaService",
                status=MCPCompatibilityStatus.FULL,
                description="Searches stock images on Pixabay",
            ),
            request_mapper=map_stock_images_request,
            response_mapper=map_default_output,
        ),
        CompatibilityToolEntry(
            descriptor=LegacyToolDescriptor(
                legacy_server_id="media-sources-mcp",
                legacy_tool_name="pixabay_search_videos",
                capability_id=CapabilityType.SEARCH_STOCK_VIDEOS,
                canonical_owner="StockMediaService",
                status=MCPCompatibilityStatus.FULL,
                description="Searches stock videos on Pixabay",
            ),
            request_mapper=map_stock_videos_request,
            response_mapper=map_default_output,
        ),
        CompatibilityToolEntry(
            descriptor=LegacyToolDescriptor(
                legacy_server_id="media-sources-mcp",
                legacy_tool_name="pixabay_search_audio",
                capability_id=CapabilityType.SEARCH_STOCK_AUDIO,
                canonical_owner="StockMediaService",
                status=MCPCompatibilityStatus.FULL,
                description="Searches stock audio on Pixabay",
            ),
            request_mapper=map_stock_audio_request,
            response_mapper=map_default_output,
        ),
        CompatibilityToolEntry(
            descriptor=LegacyToolDescriptor(
                legacy_server_id="media-sources-mcp",
                legacy_tool_name="freesound_search",
                capability_id=CapabilityType.SEARCH_SOUND_EFFECTS,
                canonical_owner="StockMediaService",
                status=MCPCompatibilityStatus.FULL,
                description="Searches sound effects on Freesound",
            ),
            request_mapper=map_sound_effects_request,
            response_mapper=map_default_output,
        ),
        CompatibilityToolEntry(
            descriptor=LegacyToolDescriptor(
                legacy_server_id="media-sources-mcp",
                legacy_tool_name="pexels_search_images",
                capability_id=CapabilityType.SEARCH_STOCK_IMAGES,
                canonical_owner="StockMediaService",
                status=MCPCompatibilityStatus.FULL,
                description="Searches stock images on Pexels",
            ),
            request_mapper=map_stock_images_request,
            response_mapper=map_default_output,
        ),
        CompatibilityToolEntry(
            descriptor=LegacyToolDescriptor(
                legacy_server_id="media-sources-mcp",
                legacy_tool_name="pexels_search_videos",
                capability_id=CapabilityType.SEARCH_STOCK_VIDEOS,
                canonical_owner="StockMediaService",
                status=MCPCompatibilityStatus.FULL,
                description="Searches stock videos on Pexels",
            ),
            request_mapper=map_stock_videos_request,
            response_mapper=map_default_output,
        ),
        CompatibilityToolEntry(
            descriptor=LegacyToolDescriptor(
                legacy_server_id="media-sources-mcp",
                legacy_tool_name="iconify_search",
                capability_id=CapabilityType.SEARCH_ICONS,
                canonical_owner="StockMediaService",
                status=MCPCompatibilityStatus.FULL,
                description="Searches vector icons on Iconify",
            ),
            request_mapper=map_iconify_search_request,
            response_mapper=map_default_output,
        ),
        CompatibilityToolEntry(
            descriptor=LegacyToolDescriptor(
                legacy_server_id="media-sources-mcp",
                legacy_tool_name="download_iconify_icon",
                capability_id=CapabilityType.DOWNLOAD_ICON,
                canonical_owner="StockMediaService",
                status=MCPCompatibilityStatus.FULL,
                description="Downloads SVG icon from Iconify",
            ),
            request_mapper=map_download_iconify_request,
            response_mapper=map_default_output,
        ),

        # ---------------------------------------------------------------------
        # 6. video-tools-mcp (4 tools)
        # ---------------------------------------------------------------------
        CompatibilityToolEntry(
            descriptor=LegacyToolDescriptor(
                legacy_server_id="video-tools-mcp",
                legacy_tool_name="trim_video",
                capability_id=CapabilityType.TRIM_VIDEO,
                canonical_owner="MediaProcessingService",
                status=MCPCompatibilityStatus.FULL,
                description="Trims a video file to target duration",
            ),
            request_mapper=map_trim_video_request,
            response_mapper=map_default_output,
        ),
        CompatibilityToolEntry(
            descriptor=LegacyToolDescriptor(
                legacy_server_id="video-tools-mcp",
                legacy_tool_name="extend_video",
                capability_id=CapabilityType.EXTEND_VIDEO,
                canonical_owner="MediaProcessingService",
                status=MCPCompatibilityStatus.FULL,
                description="Extends video duration via looping or freeze-frame",
            ),
            request_mapper=map_extend_video_request,
            response_mapper=map_extend_video_response,
        ),
        CompatibilityToolEntry(
            descriptor=LegacyToolDescriptor(
                legacy_server_id="video-tools-mcp",
                legacy_tool_name="resize_video",
                capability_id=CapabilityType.RESIZE_VIDEO,
                canonical_owner="MediaProcessingService",
                status=MCPCompatibilityStatus.FULL,
                description="Resizes video dimensions with letterboxing",
            ),
            request_mapper=map_resize_video_request,
            response_mapper=map_default_output,
        ),
        CompatibilityToolEntry(
            descriptor=LegacyToolDescriptor(
                legacy_server_id="video-tools-mcp",
                legacy_tool_name="detect_and_trim_black_frames",
                capability_id=CapabilityType.TRIM_BLACK_FRAMES,
                canonical_owner="MediaProcessingService",
                status=MCPCompatibilityStatus.PARTIAL,
                description="Detects and trims black frames (known upstream ffmpeg filter edge case)",
                notes="PARTIALLY_WORKING: upstream ffmpeg blackdetect edge case for sub-second clips documented in M01.",
            ),
            request_mapper=map_detect_black_frames_request,
            response_mapper=map_default_output,
        ),
    ]

    return {(e.descriptor.legacy_server_id, e.descriptor.legacy_tool_name): e for e in entries}


class CompatibilityRegistry:
    """
    Authoritative registry and query interface for legacy MCP tool mappings.
    """
    def __init__(self) -> None:
        self._entries = _build_authoritative_tool_entries()

    def get_entry(self, server_id: str, tool_name: str) -> Optional[CompatibilityToolEntry]:
        return self._entries.get((server_id, tool_name))

    def get_descriptor(self, server_id: str, tool_name: str) -> Optional[LegacyToolDescriptor]:
        entry = self.get_entry(server_id, tool_name)
        return entry.descriptor if entry else None

    def list_descriptors(self, status: Optional[MCPCompatibilityStatus] = None) -> List[LegacyToolDescriptor]:
        descriptors = [e.descriptor for e in self._entries.values()]
        if status:
            descriptors = [d for d in descriptors if d.status == status]
        return sorted(descriptors, key=lambda d: (d.legacy_server_id, d.legacy_tool_name))

    def get_tools_by_server(self, server_id: str) -> List[LegacyToolDescriptor]:
        descriptors = [e.descriptor for e in self._entries.values() if e.descriptor.legacy_server_id == server_id]
        return sorted(descriptors, key=lambda d: d.legacy_tool_name)

    @property
    def total_count(self) -> int:
        return len(self._entries)

    def get_status_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {"FULL": 0, "PARTIAL": 0, "DEPRECATED": 0, "BLOCKED": 0}
        for e in self._entries.values():
            counts[e.descriptor.status.value] += 1
        return counts


default_compatibility_registry = CompatibilityRegistry()
