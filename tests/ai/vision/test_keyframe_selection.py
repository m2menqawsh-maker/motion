"""
tests/ai/vision/test_keyframe_selection.py
==========================================
Tests for deterministic keyframe selection and storage (S27.15 / AI-13 Rules 6, 30).
"""

import pytest
from ai.contracts.vision import VideoShot
from ai.vision.adaptive_resolution import ResolutionTier
from ai.vision.keyframe_extractor import KeyframeExtractionPolicy, KeyframeExtractor
from ai.vision.shot_detection import NativeShotDetector
from scripts.core.storage.storage_service import LocalStorageBackend


@pytest.fixture
def storage(tmp_path):
    return LocalStorageBackend(root_dir=tmp_path / "storage_root")


def test_keyframe_extraction_bounded_policy(storage):
    policy = KeyframeExtractionPolicy(
        max_keyframes_per_video=5,
        sub_sample_long_shots_sec=5.0,
        default_tier=ResolutionTier.MEDIUM,
    )
    extractor = KeyframeExtractor(storage_service=storage, policy=policy)
    detector = NativeShotDetector()

    # 4 short shots + 1 long shot (10s)
    shots = detector.detect_shots_from_timeline(
        duration_seconds=20.0,
        transition_points=[2.0, 4.0, 6.0, 8.0],
    )
    assert len(shots) == 5

    keyframes = extractor.extract_keyframes(
        workspace_id="ws_client_a",
        asset_id="ast_interview_01",
        shots=shots,
    )

    # Policy bounded extraction
    assert len(keyframes) <= policy.max_keyframes_per_video
    assert len(keyframes) >= 4

    # Verify storage keys and persistence in StorageService
    for kf in keyframes:
        assert kf.storage_key is not None
        assert kf.storage_key.startswith("workspaces/ws_client_a/assets/ast_interview_01/keyframes/")
        # Verify stored payload
        raw_data = storage.get(kf.storage_key)
        assert raw_data is not None
        assert len(raw_data) > 0
        assert kf.content_hash is not None
        assert kf.resolution_tier == "MEDIUM"


def test_keyframe_links_to_shot(storage):
    extractor = KeyframeExtractor(storage_service=storage)
    shot = VideoShot(
        shot_id="shot_alpha_001",
        start=0.0,
        end=4.0,
        duration=4.0,
    )

    keyframes = extractor.extract_keyframes(
        workspace_id="ws_client_a",
        asset_id="ast_clip_01",
        shots=[shot],
    )

    assert len(keyframes) == 1
    assert keyframes[0].shot_id == "shot_alpha_001"
    assert keyframes[0].timestamp == 2.0  # Midpoint of [0.0, 4.0]
    assert keyframes[0].is_representative is True
