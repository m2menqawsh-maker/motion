"""
tests/ai/vision/test_shot_detection.py
======================================
Tests for deterministic native shot detection (S27.15 / AI-13 Rules 5, 30).

Validations:
- No negative timestamps
- No end < start
- No impossible overlaps
- Within asset duration
- Shot duration arithmetic exact
- Deterministic frame hash transitions
"""

import pytest
from pydantic import ValidationError

from ai.contracts.vision import VideoShot
from ai.vision.shot_detection import NativeShotDetector


def test_shot_detection_boundary_invariants():
    detector = NativeShotDetector(min_shot_duration=0.5)

    # Video duration = 10.0s with cuts at 2.5s and 6.0s
    shots = detector.detect_shots_from_timeline(
        duration_seconds=10.0,
        transition_points=[2.5, 6.0],
    )

    assert len(shots) == 3

    # Invariant 1: Within duration
    assert shots[0].start == 0.0
    assert shots[0].end == 2.5
    assert shots[1].start == 2.5
    assert shots[1].end == 6.0
    assert shots[2].start == 6.0
    assert shots[2].end == 10.0

    for idx, s in enumerate(shots):
        # Invariant 2: No negative timestamps
        assert s.start >= 0.0
        assert s.end >= 0.0
        # Invariant 3: End >= Start
        assert s.end >= s.start
        # Invariant 4: Duration exact
        assert s.duration == round(s.end - s.start, 3)
        assert s.confidence is not None
        assert s.provenance is not None

    # Invariant 5: Chronological monotonicity
    for i in range(len(shots) - 1):
        assert shots[i + 1].start >= shots[i].start
        assert shots[i + 1].start == shots[i].end


def test_shot_detection_rejects_negative_duration():
    detector = NativeShotDetector()
    with pytest.raises(ValueError, match="cannot be negative"):
        detector.detect_shots_from_timeline(duration_seconds=-5.0)


def test_shot_contract_rejects_end_before_start():
    with pytest.raises(ValidationError):
        VideoShot(
            shot_id="shot_invalid",
            start=5.0,
            end=2.0,  # End < Start
            duration=-3.0,
        )


def test_shot_contract_rejects_mismatched_duration():
    with pytest.raises(ValidationError, match="duration"):
        VideoShot(
            shot_id="shot_invalid",
            start=1.0,
            end=4.0,
            duration=5.0,  # Mismatched duration (should be 3.0)
        )


def test_shot_detection_from_frame_hashes():
    detector = NativeShotDetector()

    # 4 frames spanning 3 seconds; cut occurs between frame 1 and 2
    hashes = [
        (0.0, "hash_scene_a"),
        (1.0, "hash_scene_a"),
        (2.0, "hash_scene_b"),
        (3.0, "hash_scene_b"),
    ]

    shots = detector.detect_shots_from_frame_hashes(hashes, duration_seconds=3.0)
    assert len(shots) == 2
    assert shots[0].start == 0.0
    assert shots[0].end == 1.5
    assert shots[1].start == 1.5
    assert shots[1].end == 3.0
