"""
tests/ai/speech/test_speech_canonicalization.py
===============================================
Tests for provider wire response canonicalization into SpeechIntelligence (S27.14).
"""

from datetime import datetime, timezone
import pytest

from ai.contracts.media import AnalysisProvenance, SpeechIntelligence
from ai.speech.adapter import GoogleStyleAdapter, WhisperStyleAdapter


@pytest.fixture
def provenance():
    return AnalysisProvenance(
        producer="test_adapter",
        provider="test_provider",
        model="test_model",
        timestamp=datetime.now(timezone.utc),
        analysis_version="1.0.0",
        contract_version="1.0.0",
    )


def test_whisper_style_canonicalization(provenance):
    adapter = WhisperStyleAdapter()
    raw_payload = {
        "text": "الموبايل الي بايدك",
        "language": "ar",
        "language_probability": 0.99,
        "duration": 2.0,
        "segments": [
            {
                "start": 0.0,
                "end": 2.0,
                "text": "الموبايل الي بايدك",
                "speaker": "SPEAKER_00",
                "confidence": 0.98,
                "words": [
                    {"word": "الموبايل", "start": 0.0, "end": 0.7, "speaker": "SPEAKER_00", "confidence": 0.99},
                    {"word": "الي", "start": 0.75, "end": 1.1, "speaker": "SPEAKER_00", "confidence": 0.97},
                    {"word": "بايدك", "start": 1.15, "end": 2.0, "speaker": "SPEAKER_00", "confidence": 0.98},
                ],
            }
        ],
    }

    speech = adapter.canonicalize_speech_output(raw_payload, provenance)

    assert isinstance(speech, SpeechIntelligence)
    assert speech.transcript == "الموبايل الي بايدك"
    assert speech.language == "ar"
    assert speech.language_confidence == 0.99
    assert len(speech.segments) == 1
    assert len(speech.words) == 3
    assert speech.words[0].text == "الموبايل"
    assert speech.words[0].start == 0.0
    assert speech.words[0].end == 0.7
    assert speech.words[2].text == "بايدك"
    assert len(speech.speakers) == 1
    assert speech.speakers[0].speaker_id == "SPEAKER_00"


def test_google_style_canonicalization(provenance):
    adapter = GoogleStyleAdapter()
    raw_payload = {
        "results": [
            {
                "languageCode": "ar-XA",
                "alternatives": [
                    {
                        "transcript": "أقوى من ناسا",
                        "confidence": 0.97,
                        "words": [
                            {"word": "أقوى", "startTime": "0.0s", "endTime": "0.6s", "speakerTag": 0},
                            {"word": "من", "startTime": "0.65s", "endTime": "0.9s", "speakerTag": 0},
                            {"word": "ناسا", "startTime": "0.95s", "endTime": "1.5s", "speakerTag": 0},
                        ],
                    }
                ],
            }
        ]
    }

    speech = adapter.canonicalize_speech_output(raw_payload, provenance)

    assert isinstance(speech, SpeechIntelligence)
    assert speech.transcript == "أقوى من ناسا"
    assert speech.language == "ar"
    assert len(speech.segments) == 1
    assert len(speech.words) == 3
    assert speech.words[0].text == "أقوى"
    assert speech.words[2].end == 1.5
    assert len(speech.speakers) == 1
    assert speech.speakers[0].speaker_id == "SPEAKER_00"
