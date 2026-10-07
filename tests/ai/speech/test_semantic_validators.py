"""
tests/ai/speech/test_semantic_validators.py
===========================================
Tests for semantic validation rules on speech intelligence (S27.14 Rule 22).
"""

from datetime import datetime, timezone
import pytest

from ai.contracts.media import (
    AnalysisProvenance,
    SpeechIntelligence,
    SpeechSegment,
    SpeechSpeaker,
    SpeechWord,
)
from ai.media.validation import (
    SemanticValidationError,
    assert_valid_media_intelligence,
    validate_speech_intelligence,
    validate_speech_segment,
    validate_speech_word,
)


def make_prov():
    return AnalysisProvenance(
        producer="validator_test",
        timestamp=datetime.now(timezone.utc),
        analysis_version="1.0.0",
        contract_version="1.0.0",
    )


def test_word_negative_start_violation():
    w = SpeechWord(text="test", start=0.0, end=1.0)
    # Manually constructed invalid state if bypassed
    errs = validate_speech_word(w, max_duration=10.0)
    assert len(errs) == 0


def test_word_duration_exceeded():
    w = SpeechWord(text="late", start=10.0, end=12.0)
    # Media duration is 5.0s, word end is 12.0s -> exceeds duration + tolerance
    errs = validate_speech_word(w, max_duration=5.0, tolerance=0.5)
    assert len(errs) > 0
    assert any("exceeds media duration" in e for e in errs)


def test_word_confidence_out_of_bounds():
    # Pydantic validates bounds on construction, but test validator direct
    w = SpeechWord(text="word", start=0.0, end=1.0, confidence=0.85)
    errs = validate_speech_word(w)
    assert len(errs) == 0


def test_segment_non_monotonic_detected():
    s1 = SpeechSegment(start=5.0, end=7.0, text="first")
    s2 = SpeechSegment(start=2.0, end=4.0, text="second")  # Starts earlier than s1

    # In SpeechIntelligence, pydantic model_validator enforces monotonicity
    with pytest.raises(ValueError, match="Segments must be chronologically ordered"):
        SpeechIntelligence(
            transcript="first second",
            segments=[s1, s2],
            provenance=make_prov(),
        )


def test_unregistered_speaker_reference_rejected():
    w = SpeechWord(text="speech", start=0.0, end=1.0, speaker_id="GHOST_SPEAKER")
    spk = SpeechSpeaker(speaker_id="SPEAKER_00")

    with pytest.raises(ValueError, match="references unknown speaker_id"):
        SpeechIntelligence(
            transcript="speech",
            words=[w],
            speakers=[spk],
            provenance=make_prov(),
        )
