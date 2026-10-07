"""
ai/contracts/vision.py
======================
Canonical typed contracts for Vision Intelligence & Video Understanding (S27.15 / AI-13).

Invariants:
- Absolute host filesystem paths are NEVER exposed (ADR-004 DEC-06.5).
- Storage artifacts referenced exclusively via abstract storage_key.
- Strict Pydantic models (no Dict[str, Any] at boundary contracts).
- Every analytical observation carries full provenance audit records.
- Shot boundaries validate: start >= 0, end >= start, chronological consistency.
- Native DSP/heuristic priority: costly multimodal model calls are avoided when local passes suffice.
"""

from __future__ import annotations

from typing import List, Optional
from pydantic import Field, model_validator
from typing_extensions import Self

from ai.contracts.base import AIContractModel
from ai.contracts.media import AnalysisProvenance


class BoundingBox(AIContractModel):
    """Normalized spatial 2D bounding box [0.0, 1.0]."""
    x: float = Field(ge=0.0, le=1.0, description="Normalized horizontal top-left origin")
    y: float = Field(ge=0.0, le=1.0, description="Normalized vertical top-left origin")
    width: float = Field(ge=0.0, le=1.0, description="Normalized box width")
    height: float = Field(ge=0.0, le=1.0, description="Normalized box height")


class VideoShot(AIContractModel):
    """
    Canonical video shot segment identified via deterministic/native detection or AI refinement.
    """
    shot_id: str = Field(min_length=1, description="Unique identifier for the shot")
    start: float = Field(ge=0.0, description="Shot start timestamp in seconds relative to video start")
    end: float = Field(ge=0.0, description="Shot end timestamp in seconds relative to video start")
    duration: float = Field(ge=0.0, description="Shot duration in seconds")
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Detection confidence")
    source: str = Field(default="native_algorithm", description="Algorithm or source (native_algorithm, ffmpeg, ai)")
    transition_type: Optional[str] = Field(default="hard_cut", description="Transition boundary type (hard_cut, dissolve, fade)")
    keyframe_indices: List[int] = Field(default_factory=list, description="Frame indices associated with this shot")
    provenance: Optional[AnalysisProvenance] = Field(default=None, description="Detailed provenance audit")

    @model_validator(mode="after")
    def validate_shot_boundaries(self) -> Self:
        if self.end < self.start:
            raise ValueError(f"Shot end timestamp ({self.end}) must be >= start timestamp ({self.start})")
        if abs(self.duration - (self.end - self.start)) > 0.05:
            raise ValueError(
                f"Shot duration ({self.duration}) must match end - start ({round(self.end - self.start, 3)})"
            )
        return self


class Keyframe(AIContractModel):
    """
    Representative extracted keyframe linked deterministically to a shot or time interval.
    """
    keyframe_id: str = Field(min_length=1, description="Unique keyframe record identifier")
    shot_id: Optional[str] = Field(default=None, description="Associated shot identifier")
    timestamp: float = Field(ge=0.0, description="Timestamp of keyframe within the video")
    frame_index: int = Field(ge=0, description="0-indexed absolute frame number")
    storage_key: Optional[str] = Field(default=None, description="Abstract StorageService key for keyframe image")
    width: Optional[int] = Field(default=None, ge=1, description="Pixel width of keyframe")
    height: Optional[int] = Field(default=None, ge=1, description="Pixel height of keyframe")
    is_representative: bool = Field(default=True, description="Whether this frame is primary representative for shot")
    resolution_tier: str = Field(default="MEDIUM", description="Extraction resolution tier (LOW, MEDIUM, HIGH)")
    content_hash: Optional[str] = Field(default=None, description="SHA-256 hash of keyframe image bytes")
    provenance: Optional[AnalysisProvenance] = Field(default=None, description="Provenance audit")


class VisualOCRObservation(AIContractModel):
    """
    Optical Character Recognition observation supporting Arabic, English, and UI/screen text.
    """
    text: str = Field(min_length=1, description="Detected verbatim text content")
    bounding_box: Optional[BoundingBox] = Field(default=None, description="Spatial bounding coordinates")
    timestamp: float = Field(ge=0.0, description="Timestamp in seconds where text appeared")
    frame_ref: Optional[str] = Field(default=None, description="Associated keyframe identifier or reference")
    confidence: float = Field(ge=0.0, le=1.0, description="OCR detection confidence score")
    language: Optional[str] = Field(default=None, description="Detected text language (e.g. 'ar', 'en')")
    is_ui_screen: bool = Field(default=False, description="Whether text was detected in UI / screen demo context")
    provenance: AnalysisProvenance = Field(description="Audit record tracking OCR engine source")


class VisualObjectObservation(AIContractModel):
    """
    Spatial object detection observation with bounded confidence and coordinates.
    """
    label: str = Field(min_length=1, description="Identified object class label")
    bounding_box: Optional[BoundingBox] = Field(default=None, description="Spatial bounding box")
    timestamp: float = Field(ge=0.0, description="Timestamp in seconds")
    frame_ref: Optional[str] = Field(default=None, description="Keyframe identifier")
    confidence: float = Field(ge=0.0, le=1.0, description="Detection confidence score")
    provenance: AnalysisProvenance = Field(description="Audit record tracking detection model source")


class VisualPersonObservation(AIContractModel):
    """
    Human subject detection and tracking observation. Uses neutral person identifiers.
    """
    person_id: str = Field(min_length=1, description="Neutral identifier (e.g. 'PERSON_00')")
    bounding_box: Optional[BoundingBox] = Field(default=None, description="Spatial bounding coordinates")
    timestamp: float = Field(ge=0.0, description="Timestamp in seconds")
    frame_ref: Optional[str] = Field(default=None, description="Keyframe identifier")
    confidence: float = Field(ge=0.0, le=1.0, description="Detection confidence score")
    provenance: AnalysisProvenance = Field(description="Audit record tracking person detector source")


class VisualSceneClassification(AIContractModel):
    """
    Semantic scene classification (e.g. studio, b-roll, screen-recording, urban, indoor).
    """
    label: str = Field(min_length=1, description="Scene category label")
    start: float = Field(ge=0.0, description="Start timestamp of classified scene")
    end: float = Field(ge=0.0, description="End timestamp of classified scene")
    confidence: float = Field(ge=0.0, le=1.0, description="Classification confidence")
    resolution_tier: str = Field(default="LOW", description="Analysis resolution tier utilized")
    provenance: AnalysisProvenance = Field(description="Audit record tracking classification source")

    @model_validator(mode="after")
    def validate_scene_boundaries(self) -> Self:
        if self.end < self.start:
            raise ValueError(f"Scene end timestamp ({self.end}) must be >= start timestamp ({self.start})")
        return self


class VisualObservation(AIContractModel):
    """
    Important visual event or narrative observation extracted from video stream.
    """
    summary: str = Field(min_length=1, description="Concise textual summary of visual observation")
    start: float = Field(ge=0.0, description="Start timestamp")
    end: float = Field(ge=0.0, description="End timestamp")
    importance_score: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Salience/importance score")
    category: Optional[str] = Field(default=None, description="Semantic category (e.g. 'talking_head', 'screen_demo')")
    provenance: AnalysisProvenance = Field(description="Audit record tracking observation source")

    @model_validator(mode="after")
    def validate_observation_boundaries(self) -> Self:
        if self.end < self.start:
            raise ValueError(f"Observation end timestamp ({self.end}) must be >= start timestamp ({self.start})")
        return self


class VisualIntelligence(AIContractModel):
    """
    Canonical Visual Intelligence & Video Understanding contract.
    Unifies shots, keyframes, OCR, objects, people, and scene classifications.
    """
    status: str = Field(default="TYPED_FOUNDATION_AI13", description="Subsystem readiness state")
    has_visual_analysis: bool = Field(default=False, description="Whether visual analysis has been executed")
    shots: List[VideoShot] = Field(default_factory=list, description="Chronological detected video shots")
    keyframes: List[Keyframe] = Field(default_factory=list, description="Extracted representative keyframes")
    ocr: List[VisualOCRObservation] = Field(default_factory=list, description="Extracted OCR text observations")
    objects: List[VisualObjectObservation] = Field(default_factory=list, description="Detected visual objects")
    people: List[VisualPersonObservation] = Field(default_factory=list, description="Detected human subjects")
    scene_classifications: List[VisualSceneClassification] = Field(default_factory=list, description="Scene categories")
    observations: List[VisualObservation] = Field(default_factory=list, description="Important visual observations")
    provenance: Optional[AnalysisProvenance] = Field(default=None, description="Overall visual analysis provenance")

    @model_validator(mode="after")
    def validate_visual_coherence(self) -> Self:
        for i in range(len(self.shots) - 1):
            if self.shots[i + 1].start < self.shots[i].start:
                raise ValueError(
                    f"Shots must be chronologically ordered. Shot {i} starts at {self.shots[i].start}, "
                    f"shot {i+1} starts at {self.shots[i+1].start}"
                )
            # Check impossible overlaps (next shot start should not be strictly less than previous start)
            if self.shots[i + 1].start < self.shots[i].end - 0.05:
                raise ValueError(
                    f"Impossible shot overlap detected: Shot {i} ends at {self.shots[i].end}, "
                    f"but Shot {i+1} starts at {self.shots[i+1].start}"
                )
        return self
