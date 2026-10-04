"""
ai/mcp/catalog.py
=================
Authoritative Catalog of MCP Servers and Operations (S27.10).

Invariants:
- Exhaustive registry of all discovered repository MCP servers.
- Explicit ownership classification (DEV_ONLY, RUNTIME_CONTROL, OBSOLETE, SHARED_INVARIANT).
- Explicit disposition classification (KEEP_AS_MCP, CONVERT_TO_DOMAIN_SERVICE, CONVERT_TO_CAPABILITY_ADAPTER, DEPRECATE, DELETE).
- Production gate: Servers with allowed_for_production=False cannot be executed by production AI.
- Deterministic order and immutable definitions.
"""

from __future__ import annotations

import threading
from typing import Dict, List, Optional

from ai.mcp.contracts import (
    AutoCropInput,
    AutoCropOutput,
    CropRatioInput,
    CropRatioOutput,
    DetectBlackFramesInput,
    DetectBlackFramesOutput,
    ExtendAudioInput,
    ExtendAudioOutput,
    ExtendVideoInput,
    ExtendVideoOutput,
    MCPDisposition,
    MCPOperationCategory,
    MCPOperationDefinition,
    MCPOwnershipClass,
    MCPServerDefinition,
    NormalizeLoudnessInput,
    NormalizeLoudnessOutput,
    ResizeVideoInput,
    ResizeVideoOutput,
    TrimAudioInput,
    TrimAudioOutput,
    TrimSilenceInput,
    TrimSilenceOutput,
    TrimVideoInput,
    TrimVideoOutput,
    UpscaleImageInput,
    UpscaleImageOutput,
)


def _build_canonical_mcp_servers() -> Dict[str, MCPServerDefinition]:
    """Builds the authoritative definitions for all 6 repository MCP servers."""

    # 1. audio-tools-mcp
    audio_ops = {
        "trim_audio": MCPOperationDefinition(
            name="trim_audio",
            description="Trims an audio file to a specified duration",
            category=MCPOperationCategory.AUDIO_PROCESSING,
            input_contract=TrimAudioInput,
            output_contract=TrimAudioOutput,
            timeout_seconds=30.0,
            allow_shell=False,
            allow_arbitrary_fs=False,
            requires_tenant_scope=True,
        ),
        "normalize_loudness": MCPOperationDefinition(
            name="normalize_loudness",
            description="Normalizes audio integrated loudness to target LUFS",
            category=MCPOperationCategory.AUDIO_PROCESSING,
            input_contract=NormalizeLoudnessInput,
            output_contract=NormalizeLoudnessOutput,
            timeout_seconds=30.0,
            allow_shell=False,
            allow_arbitrary_fs=False,
            requires_tenant_scope=True,
        ),
        "detect_and_trim_silence": MCPOperationDefinition(
            name="detect_and_trim_silence",
            description="Detects and trims leading/trailing silence from audio",
            category=MCPOperationCategory.AUDIO_PROCESSING,
            input_contract=TrimSilenceInput,
            output_contract=TrimSilenceOutput,
            timeout_seconds=30.0,
            allow_shell=False,
            allow_arbitrary_fs=False,
            requires_tenant_scope=True,
        ),
        "extend_audio": MCPOperationDefinition(
            name="extend_audio",
            description="Extends audio to a target duration via looping or crossfade",
            category=MCPOperationCategory.AUDIO_PROCESSING,
            input_contract=ExtendAudioInput,
            output_contract=ExtendAudioOutput,
            timeout_seconds=45.0,
            allow_shell=False,
            allow_arbitrary_fs=False,
            requires_tenant_scope=True,
        ),
    }

    audio_server = MCPServerDefinition(
        server_id="audio-tools-mcp",
        display_name="Audio Tools MCP",
        path=".agents/plugins/super-video-maker-plugin/tools/mcp-servers/audio-tools-mcp",
        entrypoint="server.py",
        ownership_class=MCPOwnershipClass.RUNTIME_CONTROL,
        disposition=MCPDisposition.KEEP_AS_MCP,
        enabled=True,
        allowed_for_production=True,
        default_timeout_seconds=30.0,
        rationale="Retained for deterministic FFmpeg audio processing behind hardened adapter.",
        operations=audio_ops,
    )

    # 2. video-tools-mcp
    video_ops = {
        "trim_video": MCPOperationDefinition(
            name="trim_video",
            description="Trims a video file to target duration",
            category=MCPOperationCategory.VIDEO_PROCESSING,
            input_contract=TrimVideoInput,
            output_contract=TrimVideoOutput,
            timeout_seconds=45.0,
            allow_shell=False,
            allow_arbitrary_fs=False,
            requires_tenant_scope=True,
        ),
        "resize_video": MCPOperationDefinition(
            name="resize_video",
            description="Resizes video to specified dimensions with optional letterboxing",
            category=MCPOperationCategory.VIDEO_PROCESSING,
            input_contract=ResizeVideoInput,
            output_contract=ResizeVideoOutput,
            timeout_seconds=60.0,
            allow_shell=False,
            allow_arbitrary_fs=False,
            requires_tenant_scope=True,
        ),
        "extend_video": MCPOperationDefinition(
            name="extend_video",
            description="Extends video duration via loop or last frame freeze",
            category=MCPOperationCategory.VIDEO_PROCESSING,
            input_contract=ExtendVideoInput,
            output_contract=ExtendVideoOutput,
            timeout_seconds=60.0,
            allow_shell=False,
            allow_arbitrary_fs=False,
            requires_tenant_scope=True,
        ),
        "detect_and_trim_black_frames": MCPOperationDefinition(
            name="detect_and_trim_black_frames",
            description="Detects and trims pure black frames from video start/end",
            category=MCPOperationCategory.VIDEO_PROCESSING,
            input_contract=DetectBlackFramesInput,
            output_contract=DetectBlackFramesOutput,
            timeout_seconds=45.0,
            allow_shell=False,
            allow_arbitrary_fs=False,
            requires_tenant_scope=True,
        ),
    }

    video_server = MCPServerDefinition(
        server_id="video-tools-mcp",
        display_name="Video Tools MCP",
        path=".agents/plugins/super-video-maker-plugin/tools/mcp-servers/video-tools-mcp",
        entrypoint="server.py",
        ownership_class=MCPOwnershipClass.RUNTIME_CONTROL,
        disposition=MCPDisposition.KEEP_AS_MCP,
        enabled=True,
        allowed_for_production=True,
        default_timeout_seconds=60.0,
        rationale="Retained for deterministic FFmpeg video manipulation behind hardened adapter.",
        operations=video_ops,
    )

    # 3. image-tools-mcp
    image_ops = {
        "upscale_image": MCPOperationDefinition(
            name="upscale_image",
            description="Resizes or upscales an image using Lanczos filter",
            category=MCPOperationCategory.IMAGE_PROCESSING,
            input_contract=UpscaleImageInput,
            output_contract=UpscaleImageOutput,
            timeout_seconds=30.0,
            allow_shell=False,
            allow_arbitrary_fs=False,
            requires_tenant_scope=True,
        ),
        "crop_to_ratio": MCPOperationDefinition(
            name="crop_to_ratio",
            description="Crops an image to a specific aspect ratio",
            category=MCPOperationCategory.IMAGE_PROCESSING,
            input_contract=CropRatioInput,
            output_contract=CropRatioOutput,
            timeout_seconds=20.0,
            allow_shell=False,
            allow_arbitrary_fs=False,
            requires_tenant_scope=True,
        ),
        "auto_crop_content": MCPOperationDefinition(
            name="auto_crop_content",
            description="Automatically removes solid borders around image content",
            category=MCPOperationCategory.IMAGE_PROCESSING,
            input_contract=AutoCropInput,
            output_contract=AutoCropOutput,
            timeout_seconds=20.0,
            allow_shell=False,
            allow_arbitrary_fs=False,
            requires_tenant_scope=True,
        ),
    }

    image_server = MCPServerDefinition(
        server_id="image-tools-mcp",
        display_name="Image Tools MCP",
        path=".agents/plugins/super-video-maker-plugin/tools/mcp-servers/image-tools-mcp",
        entrypoint="server.py",
        ownership_class=MCPOwnershipClass.RUNTIME_CONTROL,
        disposition=MCPDisposition.KEEP_AS_MCP,
        enabled=True,
        allowed_for_production=True,
        default_timeout_seconds=30.0,
        rationale="Retained for deterministic Pillow image processing behind hardened adapter.",
        operations=image_ops,
    )

    # 4. media-sources-mcp
    media_sources_server = MCPServerDefinition(
        server_id="media-sources-mcp",
        display_name="Media Sources MCP",
        path=".agents/plugins/super-video-maker-plugin/tools/mcp-servers/media-sources-mcp",
        entrypoint="server.py",
        ownership_class=MCPOwnershipClass.DEV_ONLY,
        disposition=MCPDisposition.CONVERT_TO_DOMAIN_SERVICE,
        enabled=True,
        allowed_for_production=False,
        default_timeout_seconds=30.0,
        rationale="Lifecycle authority (change_asset_status) migrated to AssetService; provider search migrated to capability adapters; direct production invocation blocked.",
        operations={},
    )

    # 5. common-tools-mcp
    common_server = MCPServerDefinition(
        server_id="common-tools-mcp",
        display_name="Common Tools MCP",
        path=".agents/plugins/super-video-maker-plugin/tools/mcp-servers/common-tools-mcp",
        entrypoint="server.py",
        ownership_class=MCPOwnershipClass.DEV_ONLY,
        disposition=MCPDisposition.CONVERT_TO_DOMAIN_SERVICE,
        enabled=True,
        allowed_for_production=False,
        default_timeout_seconds=15.0,
        rationale="Asset caching (check_cache/save_to_cache) converted to AssetService domain authority; legacy files preserved for development boundary tests.",
        operations={},
    )

    # 6. ffmpeg-mcp-server
    ffmpeg_server = MCPServerDefinition(
        server_id="ffmpeg-mcp-server",
        display_name="FFmpeg MCP Server (Legacy Node)",
        path=".agents/plugins/super-video-maker-plugin/tools/mcp-servers/ffmpeg-mcp-server",
        entrypoint="server.js",
        ownership_class=MCPOwnershipClass.DEV_ONLY,
        disposition=MCPDisposition.DEPRECATE,
        enabled=False,
        allowed_for_production=False,
        default_timeout_seconds=30.0,
        rationale="Deprecated due to raw shell command concatenation (execAsync) and platform-locked PowerShell WMI queries; strictly quarantined from production.",
        operations={},
    )

    return {
        audio_server.server_id: audio_server,
        video_server.server_id: video_server,
        image_server.server_id: image_server,
        media_sources_server.server_id: media_sources_server,
        common_server.server_id: common_server,
        ffmpeg_server.server_id: ffmpeg_server,
    }


class MCPCatalog:
    """Authoritative registry and query boundary for MCP servers and tools."""
    def __init__(self, servers: Optional[Dict[str, MCPServerDefinition]] = None):
        self._servers = dict(servers) if servers is not None else _build_canonical_mcp_servers()
        self._lock = threading.Lock()

    def get_server(self, server_id: str) -> Optional[MCPServerDefinition]:
        """Looks up server definition by canonical ID."""
        with self._lock:
            return self._servers.get(server_id)

    def list_servers(
        self,
        include_disabled: bool = True,
        production_only: bool = False,
    ) -> List[MCPServerDefinition]:
        """Returns registered servers in stable, deterministic order."""
        with self._lock:
            servers = list(self._servers.values())

        if not include_disabled:
            servers = [s for s in servers if s.enabled]
        if production_only:
            servers = [s for s in servers if s.allowed_for_production]

        return sorted(servers, key=lambda s: s.server_id)

    def is_operation_allowed(
        self,
        server_id: str,
        operation_name: str,
        is_production: bool = True,
    ) -> bool:
        """Determines if a specific server operation is authorized for execution."""
        server = self.get_server(server_id)
        if not server or not server.enabled:
            return False
        if is_production and not server.allowed_for_production:
            return False
        return operation_name in server.operations

    def get_operation(
        self,
        server_id: str,
        operation_name: str,
    ) -> Optional[MCPOperationDefinition]:
        """Retrieves operation metadata if registered on server."""
        server = self.get_server(server_id)
        if not server:
            return None
        return server.operations.get(operation_name)


default_mcp_catalog = MCPCatalog()
