"""
tests/ai/vision/test_ocr.py
===========================
Tests for OCR extraction, normalization, and multilingual support (S27.15 / AI-13 Rules 7, 30).

Validations:
- Arabic text extraction
- English text extraction
- UI / screen text detection
- Bounding box canonicalization
- Zero vendor-specific schema leakage
"""

import pytest
from ai.contracts.vision import Keyframe, VisualOCRObservation
from ai.vision.ocr import OCREngine


@pytest.fixture
def keyframe():
    return Keyframe(
        keyframe_id="kf_test_001",
        shot_id="shot_001",
        timestamp=2.5,
        frame_index=75,
        storage_key="workspaces/ws_01/assets/ast_01/keyframes/kf_test_001.jpg",
        width=1920,
        height=1080,
    )


def test_ocr_arabic_text_extraction(keyframe):
    engine = OCREngine()
    simulated_blocks = [
        {
            "text": "مرحباً بكم في منصة تحرير الفيديو",
            "box": {"x": 0.1, "y": 0.2, "width": 0.8, "height": 0.1},
            "confidence": 0.98,
        }
    ]

    results = engine.extract_text_from_keyframe(keyframe, simulated_text_blocks=simulated_blocks)

    assert len(results) == 1
    obs = results[0]
    assert isinstance(obs, VisualOCRObservation)
    assert obs.text == "مرحباً بكم في منصة تحرير الفيديو"
    assert obs.language == "ar"
    assert obs.timestamp == 2.5
    assert obs.frame_ref == "kf_test_001"
    assert obs.confidence == 0.98
    assert obs.bounding_box is not None
    assert obs.bounding_box.x == 0.1
    assert obs.bounding_box.width == 0.8
    assert obs.provenance.producer == "ocr_engine"


def test_ocr_english_and_ui_screen_detection(keyframe):
    engine = OCREngine()
    simulated_blocks = [
        {
            "text": "Export Video Project 1080p",
            "box": {"x": 0.7, "y": 0.05, "width": 0.25, "height": 0.05},
            "confidence": 0.96,
            "is_ui_screen": True,
            "language": "en",
        }
    ]

    results = engine.extract_text_from_keyframe(keyframe, simulated_text_blocks=simulated_blocks)

    assert len(results) == 1
    obs = results[0]
    assert obs.text == "Export Video Project 1080p"
    assert obs.language == "en"
    assert obs.is_ui_screen is True
    assert obs.bounding_box.x == 0.7


def test_ocr_schema_forbids_vendor_fields(keyframe):
    """Proves vendor-specific fields (e.g. google_bounding_poly, aws_polygon) cannot leak into domain contract."""
    with pytest.raises(Exception):
        VisualOCRObservation(
            text="Test Text",
            timestamp=1.0,
            confidence=0.9,
            provenance={
                "producer": "test",
                "timestamp": "2026-10-01T12:00:00Z",
            },
            google_bounding_poly={"vertices": [{"x": 10, "y": 20}]},  # Vendor field forbidden
        )
