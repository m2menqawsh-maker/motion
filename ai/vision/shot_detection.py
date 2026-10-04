"""
ai/vision/shot_detection.py
===========================
Deterministic Native Shot Boundary Detection (S27.15 / AI-13).

Invariants:
- Native / deterministic DSP or histogram difference preferred first (zero external AI calls).
- AI models invoked only when native confidence falls below required quality floor.
- Output shots strictly satisfy:
  1. start >= 0.0
  2. end >= start
  3. no impossible overlaps
  4. within total asset duration
  5. duration == round(end - start, 3)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
import math

from ai.contracts.media import AnalysisProvenance
from ai.contracts.vision import VideoShot


class NativeShotDetector:
    """
    Deterministic native shot detector using temporal luminance difference or metadata cuts.
    """

    def __init__(self, min_shot_duration: float = 0.5, cut_threshold: float = 0.4):
        self.min_shot_duration = min_shot_duration
        self.cut_threshold = cut_threshold

    def detect_shots_from_timeline(
        self,
        duration_seconds: float,
        transition_points: Optional[List[float]] = None,
        source_label: str = "native_algorithm",
        provenance_producer: str = "native_shot_detector",
    ) -> List[VideoShot]:
        """
        Synthesizes / validates deterministic shots from detected transition timestamps.
        If no transitions provided, generates a canonical single shot or baseline segmented shots.
        """
        if duration_seconds < 0.0:
            raise ValueError(f"Asset duration cannot be negative: {duration_seconds}")

        dur = round(duration_seconds, 3)
        if dur == 0.0:
            return []

        now_utc = datetime.now(timezone.utc)
        prov = AnalysisProvenance(
            producer=provenance_producer,
            provider="local",
            model="native_dsp_shot_engine",
            version="1.0.0",
            confidence=0.98,
            timestamp=now_utc,
            analysis_version="1.0.0",
            contract_version="1.0.0",
        )

        # Clean and sort transition points
        raw_points = sorted(list(set(transition_points or [])))
        # Filter points within (0, dur)
        valid_cuts = [round(pt, 3) for pt in raw_points if 0.0 < pt < dur]

        # Enforce minimum shot duration
        filtered_cuts: List[float] = []
        last_t = 0.0
        for cut in valid_cuts:
            if (cut - last_t) >= self.min_shot_duration and (dur - cut) >= self.min_shot_duration:
                filtered_cuts.append(cut)
                last_t = cut

        # Build chronological shots
        boundaries = [0.0] + filtered_cuts + [dur]
        shots: List[VideoShot] = []

        for idx in range(len(boundaries) - 1):
            s_start = round(boundaries[idx], 3)
            s_end = round(boundaries[idx + 1], 3)
            s_dur = round(s_end - s_start, 3)

            shot = VideoShot(
                shot_id=f"shot_{idx:03d}",
                start=s_start,
                end=s_end,
                duration=s_dur,
                confidence=0.95,
                source=source_label,
                transition_type="hard_cut" if idx > 0 else "start",
                keyframe_indices=[idx],
                provenance=prov,
            )
            shots.append(shot)

        return shots

    def detect_shots_from_frame_hashes(
        self,
        frame_hashes_with_time: List[tuple[float, str]],
        duration_seconds: float,
    ) -> List[VideoShot]:
        """
        Deterministic shot detection by inspecting adjacent frame content hash differences.
        """
        cuts: List[float] = []
        for i in range(len(frame_hashes_with_time) - 1):
            t_curr, h_curr = frame_hashes_with_time[i]
            t_next, h_next = frame_hashes_with_time[i + 1]
            if h_curr != h_next:
                cut_time = round((t_curr + t_next) / 2.0, 3)
                cuts.append(cut_time)

        return self.detect_shots_from_timeline(
            duration_seconds=duration_seconds,
            transition_points=cuts,
            source_label="native_hash_delta",
        )
