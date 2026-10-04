"""
ai/mcp/contracts.py
===================
Authoritative strongly-typed contracts, classifications, and definitions
for Model Context Protocol (MCP) servers and tools (S27.10).

Invariants:
- Strict validation policy: unexpected fields forbidden (extra="forbid").
- Strict type checking: coercion of mismatched primitives disabled (strict=True).
- Immutability: models are frozen value objects (frozen=True).
- No dict[str, Any] at operational boundaries; typed via concrete models.
- Model neutrality: vendor names forbidden in canonical identifiers.
- Production AI boundary: caller identity originates strictly server-side.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional, Type
from pydantic import Field

from ai.contracts.base import AIContractModel, strict_enum


class MCPDisposition(str, Enum):
    """Authoritative disposition decision for an existing/legacy MCP integration."""
    KEEP_AS_MCP = "KEEP_AS_MCP"
    CONVERT_TO_DOMAIN_SERVICE = "CONVERT_TO_DOMAIN_SERVICE"
    CONVERT_TO_CAPABILITY_ADAPTER = "CONVERT_TO_CAPABILITY_ADAPTER"
    DEPRECATE = "DEPRECATE"
    DELETE = "DELETE"


class MCPOwnershipClass(str, Enum):
    """Environment and caller ownership classification."""
    DEV_ONLY = "DEV_ONLY"
    RUNTIME_CONTROL = "RUNTIME_CONTROL"
    SHARED_INVARIANT = "SHARED_INVARIANT"
    OBSOLETE = "OBSOLETE"


class MCPOperationCategory(str, Enum):
    """Functional taxonomy of MCP operations."""
    AUDIO_PROCESSING = "AUDIO_PROCESSING"
    VIDEO_PROCESSING = "VIDEO_PROCESSING"
    IMAGE_PROCESSING = "IMAGE_PROCESSING"
    DOMAIN_LIFECYCLE = "DOMAIN_LIFECYCLE"
    PROVIDER_SEARCH = "PROVIDER_SEARCH"
    CACHE_MANAGEMENT = "CACHE_MANAGEMENT"
    SYSTEM_COMMAND = "SYSTEM_COMMAND"


# ==============================================================================
# Retained Audio Operations (audio-tools-mcp)
# ==============================================================================

class TrimAudioInput(AIContractModel):
    """Input payload to trim an audio file."""
    file_path: str = Field(min_length=1, description="Source audio path")
    target_duration: float = Field(gt=0.0, description="Target duration in seconds")
    output_path: Optional[str] = Field(default=None, description="Optional target output path")


class TrimAudioOutput(AIContractModel):
    """Result of audio trim operation."""
    output_path: str = Field(description="Resolved path of trimmed audio")
    target_duration: float = Field(gt=0.0, description="Target duration in seconds")


class NormalizeLoudnessInput(AIContractModel):
    """Input payload to normalize audio loudness."""
    file_path: str = Field(min_length=1, description="Source audio path")
    target_lufs: float = Field(default=-16.0, le=0.0, ge=-70.0, description="Target integrated loudness in LUFS")
    output_path: Optional[str] = Field(default=None, description="Optional target output path")


class NormalizeLoudnessOutput(AIContractModel):
    """Result of audio loudness normalization."""
    output_path: str = Field(description="Resolved path of normalized audio")
    target_lufs: float = Field(description="Target LUFS applied")


class TrimSilenceInput(AIContractModel):
    """Input payload to detect and trim silence from audio."""
    file_path: str = Field(min_length=1, description="Source audio path")
    threshold_db: float = Field(default=-40.0, le=0.0, ge=-100.0, description="Silence threshold in dB")
    min_silence_duration: float = Field(default=0.1, gt=0.0, description="Minimum silence duration in seconds")
    trim_start: bool = Field(default=True, description="Trim leading silence")
    trim_end: bool = Field(default=True, description="Trim trailing silence")
    output_path: Optional[str] = Field(default=None, description="Optional target output path")


class TrimSilenceOutput(AIContractModel):
    """Result of silence trimming."""
    output_path: str = Field(description="Resolved path of trimmed audio")
    trimmed_start_seconds: float = Field(ge=0.0, description="Duration trimmed from start")
    trimmed_end_seconds: float = Field(ge=0.0, description="Duration trimmed from end")


class ExtendAudioInput(AIContractModel):
    """Input payload to extend audio duration."""
    file_path: str = Field(min_length=1, description="Source audio path")
    target_duration: float = Field(gt=0.0, description="Target extended duration in seconds")
    method: str = Field(default="loop", description="Extension method (loop or fade_extend)")
    auto_trim_silence_before_loop: bool = Field(default=True, description="Trim silence before looping")
    short_duration_threshold: float = Field(default=2.0, ge=0.0, description="Short duration threshold")
    output_path: Optional[str] = Field(default=None, description="Optional target output path")


class ExtendAudioOutput(AIContractModel):
    """Result of audio extension."""
    output_path: str = Field(description="Resolved path of extended audio")
    final_duration: float = Field(gt=0.0, description="Final duration")
    method: str = Field(description="Extension method used")


# ==============================================================================
# Retained Video Operations (video-tools-mcp)
# ==============================================================================

class TrimVideoInput(AIContractModel):
    """Input payload to trim a video file."""
    file_path: str = Field(min_length=1, description="Source video path")
    target_duration: float = Field(gt=0.0, description="Target duration in seconds")
    output_path: Optional[str] = Field(default=None, description="Optional target output path")


class TrimVideoOutput(AIContractModel):
    """Result of video trim operation."""
    output_path: str = Field(description="Resolved path of trimmed video")
    target_duration: float = Field(gt=0.0, description="Target duration in seconds")


class ResizeVideoInput(AIContractModel):
    """Input payload to resize video dimensions."""
    file_path: str = Field(min_length=1, description="Source video path")
    target_width: int = Field(gt=0, le=7680, description="Target width in pixels")
    target_height: int = Field(gt=0, le=4320, description="Target height in pixels")
    maintain_aspect_ratio: bool = Field(default=True, description="Add padding letterboxing if aspect differs")
    output_path: Optional[str] = Field(default=None, description="Optional target output path")


class ResizeVideoOutput(AIContractModel):
    """Result of video resize operation."""
    output_path: str = Field(description="Resolved path of resized video")
    width: int = Field(gt=0, description="Result width")
    height: int = Field(gt=0, description="Result height")


class ExtendVideoInput(AIContractModel):
    """Input payload to extend video duration."""
    file_path: str = Field(min_length=1, description="Source video path")
    target_duration: float = Field(gt=0.0, description="Target duration in seconds")
    method: str = Field(default="loop", description="Extension method (loop or freeze_last_frame)")
    short_duration_threshold: float = Field(default=2.0, ge=0.0, description="Short duration threshold")
    output_path: Optional[str] = Field(default=None, description="Optional target output path")


class ExtendVideoOutput(AIContractModel):
    """Result of video extension."""
    output_path: str = Field(description="Resolved path of extended video")
    target_duration: float = Field(gt=0.0, description="Target duration in seconds")
    warning: Optional[str] = Field(default=None, description="Optional processing warning")


class DetectBlackFramesInput(AIContractModel):
    """Input payload to detect and trim black frames."""
    file_path: str = Field(min_length=1, description="Source video path")
    threshold: float = Field(default=0.1, ge=0.0, le=1.0, description="Luminance threshold")
    min_duration: float = Field(default=0.1, gt=0.0, description="Minimum black duration in seconds")
    trim_start: bool = Field(default=True, description="Trim leading black frames")
    trim_end: bool = Field(default=True, description="Trim trailing black frames")
    output_path: Optional[str] = Field(default=None, description="Optional target output path")


class DetectBlackFramesOutput(AIContractModel):
    """Result of black frame detection and trimming."""
    output_path: str = Field(description="Resolved path of processed video")
    black_frames_detected: bool = Field(description="Whether black frames were trimmed")
    trimmed_start: float = Field(ge=0.0, description="Duration trimmed from start")
    trimmed_end: float = Field(ge=0.0, description="Duration trimmed from end")


# ==============================================================================
# Retained Image Operations (image-tools-mcp)
# ==============================================================================

class UpscaleImageInput(AIContractModel):
    """Input payload to resize/upscale an image."""
    file_path: str = Field(min_length=1, description="Source image path")
    target_width: int = Field(default=0, ge=0, le=16384, description="Target width (0 = auto)")
    target_height: int = Field(default=0, ge=0, le=16384, description="Target height (0 = auto)")
    output_path: Optional[str] = Field(default=None, description="Optional target output path")


class UpscaleImageOutput(AIContractModel):
    """Result of image resize/upscale."""
    output_path: str = Field(description="Resolved path of processed image")
    width: int = Field(gt=0, description="Output width")
    height: int = Field(gt=0, description="Output height")


class CropRatioInput(AIContractModel):
    """Input payload to crop an image to target aspect ratio."""
    file_path: str = Field(min_length=1, description="Source image path")
    target_ratio: str = Field(pattern=r"^[0-9]+:[0-9]+$", description="Target aspect ratio (e.g. 9:16, 16:9, 1:1)")
    output_path: Optional[str] = Field(default=None, description="Optional target output path")


class CropRatioOutput(AIContractModel):
    """Result of aspect ratio crop."""
    output_path: str = Field(description="Resolved path of cropped image")
    ratio: str = Field(description="Aspect ratio applied")


class AutoCropInput(AIContractModel):
    """Input payload to auto-crop border content."""
    file_path: str = Field(min_length=1, description="Source image path")
    background_color: str = Field(default="auto", description="Background color detection mode")
    background_threshold: int = Field(default=10, ge=0, le=255, description="Tolerance for border detection")
    output_path: Optional[str] = Field(default=None, description="Optional target output path")


class AutoCropOutput(AIContractModel):
    """Result of auto border crop."""
    output_path: str = Field(description="Resolved path of cropped image")
    original_size: List[int] = Field(description="Original [width, height]")
    cropped_size: List[int] = Field(description="Cropped [width, height]")


# ==============================================================================
# MCP Definitions
# ==============================================================================

class MCPOperationDefinition(AIContractModel):
    """Contract metadata for an individual operation within an MCP server."""
    name: str = Field(pattern=r"^[a-zA-Z0-9_\-]+$", description="Operation identifier")
    description: str = Field(min_length=1, description="Concise description")
    category: MCPOperationCategory = Field(description="Functional category")
    input_contract: Type[AIContractModel] = Field(description="Input model contract class")
    output_contract: Type[AIContractModel] = Field(description="Output model contract class")
    timeout_seconds: float = Field(default=30.0, gt=0.0, le=300.0, description="Bounded execution timeout")
    allow_shell: bool = Field(default=False, description="Strictly False: shell execution forbidden")
    allow_arbitrary_fs: bool = Field(default=False, description="Strictly False: unconfined fs forbidden")
    requires_tenant_scope: bool = Field(default=True, description="Requires trusted workspace context")


class MCPServerDefinition(AIContractModel):
    """Authoritative metadata and governance policy for an MCP server."""
    server_id: str = Field(pattern=r"^[a-zA-Z0-9_\-]+$", description="Canonical server ID")
    display_name: str = Field(min_length=1, description="Human-readable server name")
    path: str = Field(description="Repository path to the MCP server implementation")
    entrypoint: str = Field(description="Entrypoint filename (e.g. server.py, server.js)")
    ownership_class: MCPOwnershipClass = Field(description="Ownership environment classification")
    disposition: MCPDisposition = Field(description="Executive disposition decision")
    enabled: bool = Field(default=True, description="Whether server is active in configuration")
    allowed_for_production: bool = Field(default=False, description="Whether production AI can invoke this server")
    default_timeout_seconds: float = Field(default=30.0, gt=0.0, le=300.0, description="Default bounded timeout")
    rationale: str = Field(min_length=1, description="Architecture rationale for disposition")
    operations: Dict[str, MCPOperationDefinition] = Field(default_factory=dict, description="Exposed typed operations")
