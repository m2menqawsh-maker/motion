"""
ai/vision/keyframe_extractor.py
===============================
Deterministic Keyframe Extraction Policy Engine (S27.15 / AI-13).

Invariants:
- Keyframes are strictly linked to detected shots.
- Frame extraction policy is deterministic, bounded, and configurable.
- Does NOT dump thousands of redundant frames (token/bandwidth conservation).
- Persists extracted frames to StorageService under abstract storage keys.
- Never writes directly to arbitrary project filesystem paths.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import List, Optional

from ai.contracts.media import AnalysisProvenance
from ai.contracts.vision import Keyframe, VideoShot
from ai.vision.adaptive_resolution import AdaptiveResolutionPolicy, ResolutionTier
from scripts.core.storage.storage_service import StorageService


class KeyframeExtractionPolicy:
    """Configuration defining keyframe extraction rules per shot."""
    def __init__(
        self,
        max_keyframes_per_video: int = 60,
        sub_sample_long_shots_sec: float = 8.0,
        default_tier: ResolutionTier = ResolutionTier.MEDIUM,
    ):
        self.max_keyframes_per_video = max_keyframes_per_video
        self.sub_sample_long_shots_sec = sub_sample_long_shots_sec
        self.default_tier = default_tier


class KeyframeExtractor:
    """
    Deterministic keyframe selector and storage coordinator.
    """

    def __init__(
        self,
        storage_service: StorageService,
        policy: Optional[KeyframeExtractionPolicy] = None,
    ):
        self.storage_service = storage_service
        self.policy = policy or KeyframeExtractionPolicy()

    def _build_storage_key(self, workspace_id: str, asset_id: str, keyframe_id: str) -> str:
        return f"workspaces/{workspace_id}/assets/{asset_id}/keyframes/{keyframe_id}.jpg"

    def extract_keyframes(
        self,
        workspace_id: str,
        asset_id: str,
        shots: List[VideoShot],
        resolution_tier: Optional[ResolutionTier] = None,
        frame_bytes_supplier: Optional[callable] = None,
    ) -> List[Keyframe]:
        """
        Extracts representative keyframes from shots according to deterministic policy.
        """
        tier = resolution_tier or self.policy.default_tier
        width, height = AdaptiveResolutionPolicy.get_dimensions(tier)
        now_utc = datetime.now(timezone.utc)

        prov = AnalysisProvenance(
            producer="keyframe_extractor",
            provider="local",
            model="deterministic_policy_extractor",
            version="1.0.0",
            confidence=0.99,
            timestamp=now_utc,
            analysis_version="1.0.0",
            contract_version="1.0.0",
        )

        keyframes: List[Keyframe] = []
        frame_counter = 0

        for shot in shots:
            if len(keyframes) >= self.policy.max_keyframes_per_video:
                break

            # 1. Primary representative keyframe at shot midpoint
            mid_t = round(shot.start + (shot.duration / 2.0), 3)
            kf_id = f"kf_{shot.shot_id}_mid"
            storage_key = self._build_storage_key(workspace_id, asset_id, kf_id)

            # Generate or obtain frame bytes
            if frame_bytes_supplier:
                f_bytes = frame_bytes_supplier(mid_t, tier)
            else:
                # Deterministic synthetic JPEG representation
                header = f"KEYFRAME:{asset_id}:{shot.shot_id}:{mid_t}:{tier.value}".encode("utf-8")
                f_bytes = b"\xFF\xD8\xFF\xE0" + header + b"\xFF\xD9"

            content_hash = hashlib.sha256(f_bytes).hexdigest()

            # Save to StorageService
            self.storage_service.put(
                key=storage_key,
                data=f_bytes,
                content_type="image/jpeg",
            )

            primary_kf = Keyframe(
                keyframe_id=kf_id,
                shot_id=shot.shot_id,
                timestamp=mid_t,
                frame_index=frame_counter,
                storage_key=storage_key,
                width=width,
                height=height,
                is_representative=True,
                resolution_tier=tier.value,
                content_hash=content_hash,
                provenance=prov,
            )
            keyframes.append(primary_kf)
            frame_counter += 1

            # 2. Secondary keyframe if shot is sufficiently long
            if shot.duration >= self.policy.sub_sample_long_shots_sec and len(keyframes) < self.policy.max_keyframes_per_video:
                late_t = round(shot.start + (shot.duration * 0.8), 3)
                kf_late_id = f"kf_{shot.shot_id}_late"
                late_storage_key = self._build_storage_key(workspace_id, asset_id, kf_late_id)

                if frame_bytes_supplier:
                    f_late_bytes = frame_bytes_supplier(late_t, tier)
                else:
                    late_header = f"KEYFRAME:{asset_id}:{shot.shot_id}:{late_t}:{tier.value}".encode("utf-8")
                    f_late_bytes = b"\xFF\xD8\xFF\xE0" + late_header + b"\xFF\xD9"

                late_hash = hashlib.sha256(f_late_bytes).hexdigest()
                self.storage_service.put(
                    key=late_storage_key,
                    data=f_late_bytes,
                    content_type="image/jpeg",
                )

                sec_kf = Keyframe(
                    keyframe_id=kf_late_id,
                    shot_id=shot.shot_id,
                    timestamp=late_t,
                    frame_index=frame_counter,
                    storage_key=late_storage_key,
                    width=width,
                    height=height,
                    is_representative=False,
                    resolution_tier=tier.value,
                    content_hash=late_hash,
                    provenance=prov,
                )
                keyframes.append(sec_kf)
                frame_counter += 1

        return keyframes
