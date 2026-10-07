"""
tests/ai/speech/test_language_and_code_switching.py
===================================================
Tests for multilingual transcripts and code-switching robustness (S27.14 Rules 15, 16).

Covers:
- Arabic Modern Standard (MSA)
- Palestinian Arabic Dialect
- English
- Arabic-English Code-Switching within the same utterance/segment
"""

from datetime import datetime, timezone
import pytest

from ai.contracts.media import AnalysisProvenance, SpeechIntelligence, SpeechSegment, SpeechWord
from ai.media.validation import assert_valid_media_intelligence, validate_speech_intelligence


def make_prov():
    return AnalysisProvenance(
        producer="test_multilingual",
        provider="local",
        model="whisper-large-v3",
        timestamp=datetime.now(timezone.utc),
        analysis_version="1.0.0",
        contract_version="1.0.0",
    )


def test_arabic_msa_speech_contract():
    msa_text = "الموبايل الذي تحمله في يدك أقوى من حواسيب ناسا القديمة"
    speech = SpeechIntelligence(
        language="ar",
        language_confidence=0.99,
        transcript=msa_text,
        segments=[SpeechSegment(start=0.0, end=4.5, text=msa_text, language="ar")],
        duration_seconds=4.5,
        overall_confidence=0.98,
        provenance=make_prov(),
    )

    errs = validate_speech_intelligence(speech)
    assert len(errs) == 0
    assert speech.language == "ar"


def test_palestinian_arabic_dialect_contract():
    pal_text = "الموبايل الي بايدك هادا فيه شغلات ما بتخطر على بالك"
    speech = SpeechIntelligence(
        language="ar",
        language_confidence=0.95,
        transcript=pal_text,
        segments=[SpeechSegment(start=0.0, end=4.0, text=pal_text, language="ar")],
        duration_seconds=4.0,
        overall_confidence=0.96,
        provenance=make_prov(),
    )

    errs = validate_speech_intelligence(speech)
    assert len(errs) == 0


def test_arabic_english_code_switching_within_same_segment():
    """
    Mandatory Test (Rule 16):
    Contract must NOT break or crash if transcript contains Arabic + English
    in the same segment or file.
    """
    code_switch_text = "عملنا render للفيديو الجديد على Remotion وطلعت الـ performance ممتازة"

    words = [
        SpeechWord(text="عملنا", start=0.0, end=0.5, language="ar"),
        SpeechWord(text="render", start=0.6, end=1.0, language="en"),
        SpeechWord(text="للفيديو", start=1.1, end=1.6, language="ar"),
        SpeechWord(text="الجديد", start=1.7, end=2.2, language="ar"),
        SpeechWord(text="على", start=2.3, end=2.6, language="ar"),
        SpeechWord(text="Remotion", start=2.7, end=3.3, language="en"),
        SpeechWord(text="وطلعت", start=3.4, end=3.8, language="ar"),
        SpeechWord(text="الـ", start=3.9, end=4.1, language="ar"),
        SpeechWord(text="performance", start=4.2, end=5.0, language="en"),
        SpeechWord(text="ممتازة", start=5.1, end=5.8, language="ar"),
    ]

    segment = SpeechSegment(
        start=0.0,
        end=5.8,
        text=code_switch_text,
        language="ar",
        words=words,
    )

    speech = SpeechIntelligence(
        language="ar",
        language_confidence=0.94,
        transcript=code_switch_text,
        segments=[segment],
        words=words,
        duration_seconds=5.8,
        overall_confidence=0.95,
        provenance=make_prov(),
    )

    errs = validate_speech_intelligence(speech)
    assert len(errs) == 0
    assert "render" in speech.transcript
    assert "Remotion" in speech.transcript
    assert "performance" in speech.transcript
