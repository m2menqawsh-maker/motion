"""
scripts/core/blueprint_model.py — Canonical Blueprint V2 Pydantic Models (S12).
Authoritative Python representation of the Blueprint Contract.
Enforces Project Identity, Scene Timings, AssetKind alignment, and AudioPlan.
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator



class TransitionRef(BaseModel):
    """Structural envelope defining the transition out of a scene."""
    type: str = Field(default="fade", min_length=1, pattern=r"^[a-zA-Z0-9_\-]+$", description="Transition identifier")
    durationFrames: int = Field(default=15, ge=1, description="Duration of transition in frames")
    timing: Optional[str] = Field(default=None, pattern=r"^(linear|ease-in-out)$", description="Optional timing curve")


class EffectRef(BaseModel):
    """Effect envelope defining scene wrappers or overlays."""
    effect: str = Field(..., min_length=1, description="Registered effect identifier")
    apply: Optional[str] = Field(default="scene", description="'scene' (wrapper) or 'overlay'")
    params: Dict[str, Any] = Field(default_factory=dict, description="Parameters passed to the effect component")


class CaptionWord(BaseModel):
    """Individual word timing for dynamic captions."""
    word: str
    startMs: float = Field(ge=0)
    endMs: float = Field(ge=0)


# Type alias for canonical Asset Reference (string or tagged dict)
AssetRefType = Union[str, Dict[str, Any]]


class SceneContent(BaseModel):
    """Structured scene content envelope."""
    lines: Optional[List[str]] = None
    words: Optional[List[CaptionWord]] = None
    images: Optional[List[AssetRefType]] = None
    screen: Optional[AssetRefType] = None
    numbers: Optional[List[Union[int, float]]] = None
    range: Optional[Dict[str, Union[int, float]]] = None
    path: Optional[str] = None
    icons: Optional[List[AssetRefType]] = None
    audioRef: Optional[AssetRefType] = None
    spectrum: Optional[List[List[float]]] = None
    text: Optional[str] = None


class BlueprintSceneV2(BaseModel):
    """Canonical Blueprint Scene representation."""
    scene_id: str = Field(..., min_length=1, pattern=r"^[a-zA-Z0-9_\-]+$")
    template: str = Field(..., min_length=1)
    startFrame: int = Field(ge=0)
    durationFrames: int = Field(ge=1)
    content: Optional[SceneContent] = None
    template_props: Dict[str, Any] = Field(default_factory=dict)
    props: Optional[Dict[str, Any]] = None
    surface: Optional[Dict[str, Any]] = None
    layout: Optional[Dict[str, Any]] = None
    media_refs: List[AssetRefType] = Field(default_factory=list)
    sfx_ref: Optional[AssetRefType] = None
    captions_ref: Optional[AssetRefType] = None
    transition: Optional[TransitionRef] = None
    effects: List[EffectRef] = Field(default_factory=list)

    @property
    def endFrame(self) -> int:
        """Derived scene end frame."""
        return self.startFrame + self.durationFrames


class VoiceoverTrack(BaseModel):
    """Canonical Voiceover track configuration."""
    asset_ref: AssetRefType
    volume: float = Field(default=1.0, ge=0.0, le=1.0)
    startFrame: int = Field(default=0, ge=0)
    durationFrames: Optional[int] = Field(default=None, ge=1)
    mute: bool = False


class AudioDucking(BaseModel):
    """Music ducking parameters."""
    enabled: bool = True
    ducking_volume: float = Field(default=0.05, ge=0.0, le=1.0)
    duck_under: List[str] = Field(default_factory=lambda: ["voiceover"])


class MusicTrack(BaseModel):
    """Canonical Background Music track configuration."""
    asset_ref: AssetRefType
    volume: float = Field(default=0.15, ge=0.0, le=1.0)
    startFrame: int = Field(default=0, ge=0)
    durationFrames: Optional[int] = Field(default=None, ge=1)
    loop: bool = True
    mute: bool = False
    ducking: Optional[AudioDucking] = None


class GlobalSfxTrack(BaseModel):
    """Timeline-level SFX cue."""
    asset_ref: AssetRefType
    startFrame: int = Field(default=0, ge=0)
    durationFrames: Optional[int] = Field(default=None, ge=1)
    volume: float = Field(default=1.0, ge=0.0, le=1.0)


class AudioPlan(BaseModel):
    """Canonical AudioPlan uniting voiceover, music bed, and global SFX."""
    voiceover: Optional[VoiceoverTrack] = None
    music: Optional[MusicTrack] = None
    global_sfx: List[GlobalSfxTrack] = Field(default_factory=list)


class BlueprintV2(BaseModel):
    """
    Canonical Blueprint Version 2 Model.
    Single authoritative contract for Python and TypeScript video production.
    """
    blueprint_version: str = Field(default="2.0.0", pattern=r"^2\.(0|0\.0)$")
    project_id: str = Field(..., min_length=1, pattern=r"^[a-zA-Z0-9_\-]+$")
    fps: int = Field(..., ge=1, le=120)
    aspect_ratio: str = Field(..., pattern=r"^(9:16|16:9|1:1|4:5|21:9)$")
    scenes: List[BlueprintSceneV2] = Field(..., min_length=0)
    audio: Optional[AudioPlan] = None
    meta: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("fps")
    @classmethod
    def validate_fps(cls, v: int) -> int:
        if v not in (24, 25, 30, 50, 60, 120):
            # Allow custom fps if strictly between 1 and 120, but flag if 0
            if v < 1 or v > 120:
                raise ValueError(f"FPS {v} must be between 1 and 120")
        return v

    @property
    def total_duration_frames(self) -> int:
        """Project duration is strictly derived from the end of the last scene."""
        if not self.scenes:
            return 0
        return max(s.endFrame for s in self.scenes)

    @property
    def total_duration_seconds(self) -> float:
        """Derived project duration in seconds."""
        if self.fps <= 0 or not self.scenes:
            return 0.0
        return round(self.total_duration_frames / self.fps, 3)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize canonical Blueprint v2 to a pure dict."""
        return self.model_dump(mode="json", exclude_none=True)
