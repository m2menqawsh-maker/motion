"""
tests/ai/vision/test_object_person.py
=====================================
Tests for Object Detection, Person Tracking, and Scene Classification (S27.15 / AI-13 Rules 3, 30).
"""

import pytest
from ai.contracts.vision import Keyframe, VisualObjectObservation, VisualPersonObservation, VisualSceneClassification
from ai.vision.object_person import VisualClassificationEngine


@pytest.fixture
def keyframe():
    return Keyframe(
        keyframe_id="kf_test_002",
        shot_id="shot_002",
        timestamp=4.0,
        frame_index=120,
    )


def test_object_detection_canonicalization(keyframe):
    engine = VisualClassificationEngine()
    simulated_objs = [
        {"label": "microphone", "box": {"x": 0.4, "y": 0.6, "width": 0.2, "height": 0.3}, "confidence": 0.94},
        {"label": "laptop", "box": {"x": 0.2, "y": 0.7, "width": 0.4, "height": 0.25}, "confidence": 0.96},
    ]

    objects = engine.detect_objects(keyframe, simulated_objects=simulated_objs)
    assert len(objects) == 2
    assert isinstance(objects[0], VisualObjectObservation)
    assert objects[0].label == "microphone"
    assert objects[0].bounding_box.y == 0.6
    assert objects[1].label == "laptop"
    assert objects[1].confidence == 0.96


def test_person_detection_neutral_identifiers(keyframe):
    engine = VisualClassificationEngine()
    simulated_people = [
        {"person_id": "PERSON_00", "box": {"x": 0.3, "y": 0.1, "width": 0.4, "height": 0.8}, "confidence": 0.98},
        {"person_id": "PERSON_01", "box": {"x": 0.7, "y": 0.2, "width": 0.25, "height": 0.7}, "confidence": 0.95},
    ]

    people = engine.detect_people(keyframe, simulated_people=simulated_people)
    assert len(people) == 2
    assert isinstance(people[0], VisualPersonObservation)
    assert people[0].person_id == "PERSON_00"
    assert people[1].person_id == "PERSON_01"


def test_scene_classification():
    engine = VisualClassificationEngine()
    scene = engine.classify_scene(start=0.0, end=5.0, label="studio", confidence=0.97, resolution_tier="LOW")
    assert isinstance(scene, VisualSceneClassification)
    assert scene.label == "studio"
    assert scene.resolution_tier == "LOW"
    assert scene.start == 0.0
    assert scene.end == 5.0
