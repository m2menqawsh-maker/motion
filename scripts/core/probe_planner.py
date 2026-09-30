"""
scripts/core/probe_planner.py — Canonical Probe Frame Derivation & Planning Authority (S18 - LED-047, LED-048).

Single authority for deriving deterministic representative probe frames from canonical Blueprint scenes:
- Scene Start, Middle, End
- Transition Boundaries (Pre, Exact, Post)
- Animation / Dynamic Caption Critical Frames
- Strict FPS Authority (No silent default, fail-closed on mismatch)
"""
from __future__ import annotations

import hashlib
import json
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, ConfigDict


class ProbeFrameReason(str, Enum):
    SCENE_START = "SCENE_START"
    SCENE_MIDDLE = "SCENE_MIDDLE"
    SCENE_END = "SCENE_END"
    TRANSITION_PRE = "TRANSITION_PRE"
    TRANSITION_BOUNDARY = "TRANSITION_BOUNDARY"
    TRANSITION_POST = "TRANSITION_POST"
    ANIMATION_CRITICAL = "ANIMATION_CRITICAL"


class ProbePlannerError(Exception):
    """Base error for probe planning domain."""
    pass


class ProbeInvalidBlueprintError(ProbePlannerError):
    """Raised when blueprint violates canonical structure required for probe sampling."""
    pass


class ProbeFrameSample(BaseModel):
    """Explicit auditable record of an individual probe sample."""
    model_config = ConfigDict(extra='ignore', use_enum_values=True)

    frame: int = Field(ge=0, description="0-indexed absolute frame number in composition")
    reason: str = Field(description="Deterministic reason this frame was sampled")
    scene_id: Optional[str] = None
    scene_index: Optional[int] = None
    boundary_type: Optional[str] = None
    template_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class ProbeFramePlan(BaseModel):
    """Canonical representation of the complete probe frame plan for a project."""
    model_config = ConfigDict(extra='ignore', use_enum_values=True)

    project_id: str
    fps: int = Field(ge=1, le=120)
    total_duration_frames: int = Field(ge=0)
    samples: List[ProbeFrameSample] = Field(default_factory=list)
    frames: List[int] = Field(default_factory=list, description="Sorted deduplicated unique frame indices")
    plan_digest: str = Field(default="", description="Deterministic SHA256 of the plan")

    @classmethod
    def compute_plan_digest(cls, project_id: str, fps: int, total_duration_frames: int, frames: List[int], samples: List[Dict[str, Any]]) -> str:
        canonical_dict = {
            "project_id": project_id,
            "fps": fps,
            "total_duration_frames": total_duration_frames,
            "frames": sorted(list(set(frames))),
            "samples": [
                {
                    "frame": s["frame"] if isinstance(s, dict) else s.frame,
                    "reason": s["reason"] if isinstance(s, dict) else s.reason,
                    "scene_id": s.get("scene_id") if isinstance(s, dict) else s.scene_id,
                }
                for s in samples
            ]
        }
        canonical_json = json.dumps(canonical_dict, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(mode="json")


def derive_probe_frame_plan(
    blueprint: Union[Dict[str, Any], Any],
    project_id: Optional[str] = None,
    canonical_fps: Optional[int] = None,
) -> ProbeFramePlan:
    """
    Derives deterministic, representative probe frames strictly from canonical blueprint scenes.

    Invariants:
    1. Timing authority: strictly derived from blueprint.scenes[startFrame, durationFrames].
       bp['timeline'] is strictly forbidden.
    2. FPS authority: strictly derived from canonical blueprint.fps (or validated against canonical_fps).
       Silent default (e.g. 30) is strictly forbidden.
    3. Every scene is sampled at start, middle (if duration >= 3), and end.
    4. Supported active transitions generate boundary samples (pre, boundary, post).
    5. Animation/caption critical moments are sampled when canonical timing metadata exists.
    6. Output frames are sorted, deduplicated, and strictly clamped to [0, total_duration_frames - 1].
    """
    if isinstance(blueprint, dict):
        bp_dict = blueprint
    elif hasattr(blueprint, "to_dict"):
        bp_dict = blueprint.to_dict()
    elif hasattr(blueprint, "model_dump"):
        bp_dict = blueprint.model_dump(mode="json")
    else:
        raise ProbeInvalidBlueprintError(f"Unsupported blueprint type: {type(blueprint)}")

    # 1. FPS Authority Validation (LED-048)
    if "fps" not in bp_dict or bp_dict["fps"] is None:
        raise ProbeInvalidBlueprintError("Canonical blueprint is missing mandatory 'fps' field. Silent default forbidden.")

    fps_val = bp_dict["fps"]
    if not isinstance(fps_val, (int, float)) or int(fps_val) < 1 or int(fps_val) > 120:
        raise ProbeInvalidBlueprintError(f"Invalid canonical FPS {fps_val}: must be an integer between 1 and 120.")
    fps = int(fps_val)

    if canonical_fps is not None:
        if int(canonical_fps) != fps:
            raise ProbeInvalidBlueprintError(
                f"Canonical FPS mismatch: render input has {canonical_fps}, blueprint has {fps}."
            )

    # 2. Project ID derivation
    proj_id = project_id or bp_dict.get("project_id") or "unspecified_project"

    # 3. Scenes Authority Validation (LED-047)
    if "scenes" not in bp_dict or not isinstance(bp_dict["scenes"], list):
        raise ProbeInvalidBlueprintError("Canonical blueprint is missing mandatory 'scenes' list.")

    scenes = bp_dict["scenes"]
    if not scenes:
        plan = ProbeFramePlan(
            project_id=proj_id,
            fps=fps,
            total_duration_frames=0,
            samples=[],
            frames=[],
            plan_digest="",
        )
        plan.plan_digest = ProbeFramePlan.compute_plan_digest(proj_id, fps, 0, [], [])
        return plan

    # 4. Total Duration Calculation
    total_duration_frames = max((s.get("startFrame", 0) + s.get("durationFrames", 0) for s in scenes), default=0)
    max_allowed_frame = max(0, total_duration_frames - 1)

    samples: List[ProbeFrameSample] = []

    # 5. Per-Scene Sampling
    for idx, s in enumerate(scenes):
        scene_id = s.get("scene_id") or s.get("id") or f"scene_{idx}"
        template_id = s.get("template") or s.get("template_id")
        start = s.get("startFrame")
        duration = s.get("durationFrames")

        if start is None or duration is None:
            raise ProbeInvalidBlueprintError(
                f"Scene '{scene_id}' (index {idx}) missing startFrame or durationFrames."
            )

        if start < 0 or duration < 1:
            raise ProbeInvalidBlueprintError(
                f"Scene '{scene_id}' has invalid timing: startFrame={start}, durationFrames={duration}."
            )

        scene_start = min(max_allowed_frame, max(0, start))
        scene_end = min(max_allowed_frame, max(0, start + duration - 1))

        if duration == 1:
            # Single-frame scene: sample exactly this frame
            samples.append(ProbeFrameSample(
                frame=scene_start,
                reason=ProbeFrameReason.SCENE_START.value,
                scene_id=scene_id,
                scene_index=idx,
                template_id=template_id,
            ))
        elif duration == 2:
            # 2-frame scene: sample frame 0 and frame 1
            samples.append(ProbeFrameSample(
                frame=scene_start,
                reason=ProbeFrameReason.SCENE_START.value,
                scene_id=scene_id,
                scene_index=idx,
                template_id=template_id,
            ))
            samples.append(ProbeFrameSample(
                frame=scene_end,
                reason=ProbeFrameReason.SCENE_END.value,
                scene_id=scene_id,
                scene_index=idx,
                template_id=template_id,
            ))
        else:
            # duration >= 3: start, middle, end
            scene_middle = min(max_allowed_frame, max(0, start + (duration // 2)))

            samples.append(ProbeFrameSample(
                frame=scene_start,
                reason=ProbeFrameReason.SCENE_START.value,
                scene_id=scene_id,
                scene_index=idx,
                template_id=template_id,
            ))
            samples.append(ProbeFrameSample(
                frame=scene_middle,
                reason=ProbeFrameReason.SCENE_MIDDLE.value,
                scene_id=scene_id,
                scene_index=idx,
                template_id=template_id,
            ))
            samples.append(ProbeFrameSample(
                frame=scene_end,
                reason=ProbeFrameReason.SCENE_END.value,
                scene_id=scene_id,
                scene_index=idx,
                template_id=template_id,
            ))

        # 6. Transition Boundaries (Section 3)
        transition = s.get("transition")
        if transition and isinstance(transition, dict) and transition.get("type"):
            trans_type = transition.get("type")
            # In Remotion TransitionSeries, transition connects this scene to the next
            if idx < len(scenes) - 1:
                boundary = start + duration
                pre_f = max(0, boundary - 1)
                exact_f = min(max_allowed_frame, boundary)
                post_f = min(max_allowed_frame, boundary + 1)

                samples.append(ProbeFrameSample(
                    frame=pre_f,
                    reason=ProbeFrameReason.TRANSITION_PRE.value,
                    scene_id=scene_id,
                    scene_index=idx,
                    boundary_type=trans_type,
                    template_id=template_id,
                ))
                samples.append(ProbeFrameSample(
                    frame=exact_f,
                    reason=ProbeFrameReason.TRANSITION_BOUNDARY.value,
                    scene_id=scene_id,
                    scene_index=idx,
                    boundary_type=trans_type,
                    template_id=template_id,
                ))
                samples.append(ProbeFrameSample(
                    frame=post_f,
                    reason=ProbeFrameReason.TRANSITION_POST.value,
                    scene_id=scene_id,
                    scene_index=idx,
                    boundary_type=trans_type,
                    template_id=template_id,
                ))

        # 7. Animation / Caption Critical Frames (Section 4)
        content = s.get("content")
        if isinstance(content, dict):
            words = content.get("words")
            if isinstance(words, list):
                for w in words:
                    if isinstance(w, dict) and "startMs" in w:
                        word_frame = min(max_allowed_frame, max(0, int(round((float(w["startMs"]) / 1000.0) * fps))))
                        if scene_start <= word_frame <= scene_end:
                            samples.append(ProbeFrameSample(
                                frame=word_frame,
                                reason=ProbeFrameReason.ANIMATION_CRITICAL.value,
                                scene_id=scene_id,
                                scene_index=idx,
                                template_id=template_id,
                                details={"word": w.get("word"), "startMs": w.get("startMs")},
                            ))

    # 8. Deterministic Deduplication & Frame Extraction
    unique_frames = sorted(list({s.frame for s in samples}))

    plan_digest = ProbeFramePlan.compute_plan_digest(
        project_id=proj_id,
        fps=fps,
        total_duration_frames=total_duration_frames,
        frames=unique_frames,
        samples=[s.model_dump() for s in samples],
    )

    return ProbeFramePlan(
        project_id=proj_id,
        fps=fps,
        total_duration_frames=total_duration_frames,
        samples=samples,
        frames=unique_frames,
        plan_digest=plan_digest,
    )
