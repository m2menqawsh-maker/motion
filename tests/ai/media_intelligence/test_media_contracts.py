"""
tests/ai/media_intelligence/test_media_contracts.py
===================================================
Tests for canonical Media Intelligence contracts (S27.13 / S27.14).
"""

from datetime import datetime, timezone
import pytest
from pydantic import ValidationError

from ai.contracts.media import (
    AnalysisProvenance,
    AudioIntelligenceFoundation,
    MediaIntelligence,
    MediaIntelligenceRef,
    MediaQualityIntelligence,
    SemanticIntelligenceFoundation,
    SpeechIntelligence,
    SpeechQuality,
    SpeechSegment,
    SpeechSpeaker,
    SpeechWord,
    TechnicalMetadata,
    VisualIntelligenceFoundation,
)


def make_valid_provenance(producer: str = "test_producer") -> AnalysisProvenance:
    return AnalysisProvenance(
        producer=producer,
        provider="local",
        model="whisper-large-v3",
        version="1.0.0",
        confidence=0.98,
        timestamp=datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc),
        analysis_version="1.0.0",
        contract_version="1.0.0",
    )


def test_media_intelligence_valid_round_trip():
    prov = make_valid_provenance()
    word = SpeechWord(text="مرحبا", start=0.0, end=0.8, speaker_id="SPEAKER_00", confidence=0.99)
    segment = SpeechSegment(
        id="seg_001",
        start=0.0,
        end=0.8,
        text="مرحبا",
        speaker_id="SPEAKER_00",
        confidence=0.99,
        words=[word],
    )
    speaker = SpeechSpeaker(speaker_id="SPEAKER_00", label="Host", confidence=0.99, total_speaking_time_seconds=0.8)
    speech = SpeechIntelligence(
        language="ar",
        language_confidence=0.99,
        transcript="مرحبا",
        segments=[segment],
        words=[word],
        speakers=[speaker],
        duration_seconds=0.8,
        overall_confidence=0.99,
        provenance=prov,
    )
    technical = TechnicalMetadata(
        format="wav",
        duration_seconds=0.8,
        has_audio=True,
        has_video=False,
        audio_channels=1,
        audio_sample_rate=44100,
        audio_codec="pcm_s16le",
    )

    report = MediaIntelligence(
        workspace_id="ws_test",
        asset_id="ast_test",
        content_hash="abcdef0123456789",
        analysis_version="1.0.0",
        contract_version="1.0.0",
        created_at=datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc),
        technical=technical,
        speech=speech,
        audio=AudioIntelligenceFoundation(),
        visual=VisualIntelligenceFoundation(),
        semantic=SemanticIntelligenceFoundation(),
        quality=MediaQualityIntelligence(overall_score=0.95),
        provenance=prov,
    )

    json_str = report.model_dump_json()
    loaded = MediaIntelligence.model_validate_json(json_str)

    assert loaded.workspace_id == "ws_test"
    assert loaded.speech is not None
    assert loaded.speech.transcript == "مرحبا"
    assert loaded.speech.words[0].text == "مرحبا"
    assert loaded.audio.status == "TYPED_FOUNDATION_AI13"
    assert loaded.visual.status == "TYPED_FOUNDATION_AI13"
    assert loaded.semantic.status == "TYPED_FOUNDATION_AI13"


def test_media_contracts_forbid_extra_fields():
    prov = make_valid_provenance()
    with pytest.raises(ValidationError):
        SpeechWord(text="test", start=0.0, end=1.0, extra_forbidden="illegal")

    with pytest.raises(ValidationError):
        SpeechIntelligence(
            transcript="test",
            provenance=prov,
            arbitrary_vendor_data={"hello": "world"},
        )


def test_speech_word_boundary_validation():
    # End before start must fail
    with pytest.raises(ValidationError):
        SpeechWord(text="test", start=2.0, end=1.0)


def test_speech_segment_boundary_validation():
    with pytest.raises(ValidationError):
        SpeechSegment(start=5.0, end=3.0, text="inverted segment")


def test_speech_intelligence_monotonicity_validation():
    prov = make_valid_provenance()
    w1 = SpeechWord(text="first", start=2.0, end=3.0)
    w2 = SpeechWord(text="second", start=1.0, end=2.0)  # Starts before w1

    with pytest.raises(ValidationError, match="Words must be chronologically ordered"):
        SpeechIntelligence(
            transcript="first second",
            words=[w1, w2],
            provenance=prov,
        )


def test_speech_intelligence_speaker_validation():
    prov = make_valid_provenance()
    spk = SpeechSpeaker(speaker_id="SPEAKER_00")
    w = SpeechWord(text="word", start=0.0, end=1.0, speaker_id="SPEAKER_99")  # Unregistered speaker

    with pytest.raises(ValidationError, match="references unknown speaker_id"):
        SpeechIntelligence(
            transcript="word",
            words=[w],
            speakers=[spk],
            provenance=prov,
        )


def test_media_intelligence_ref_storage_key_guard():
    # Path traversal rejected
    with pytest.raises(ValidationError, match="path traversal"):
        MediaIntelligenceRef(
            artifact_id="art_1",
            asset_id="ast_1",
            content_hash="12345678",
            storage_key="valid/../../secret.json",
            created_at=datetime.now(timezone.utc),
        )

    # Absolute path rejected
    with pytest.raises(ValidationError, match="host absolute path"):
        MediaIntelligenceRef(
            artifact_id="art_1",
            asset_id="ast_1",
            content_hash="12345678",
            storage_key="/var/data/report.json",
            created_at=datetime.now(timezone.utc),
        )

    # Raw projects directory rejected
    with pytest.raises(ValidationError, match="raw project workspace"):
        MediaIntelligenceRef(
            artifact_id="art_1",
            asset_id="ast_1",
            content_hash="12345678",
            storage_key="projects/prj_123/report.json",
            created_at=datetime.now(timezone.utc),
        )
