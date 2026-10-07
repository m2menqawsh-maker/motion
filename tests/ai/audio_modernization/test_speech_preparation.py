"""
tests/ai/audio_modernization/test_speech_preparation.py
=======================================================
Test suite for canonical SpeechPreparationService (S28-M07).
Validates deterministic segmentation, multilingual support, and edge cases.
"""

import pytest

from ai.speech.preparation import (
    SpeechPreparationService,
    get_punctuation_strength,
)


class TestSpeechPreparation:
    """Test suite for deterministic speech text and voiceover preparation."""

    def test_arabic_sentence_splitting(self):
        arabic_text = "مرحبا بكم في هذا الفيديو التعليمي! سنتحدث اليوم عن الذكاء الاصطناعي، وكيف يغير مستقبل التقنية."
        result = SpeechPreparationService.split_speech_text(
            text=arabic_text,
            language="ar",
            min_sentence_duration=1.0,
            max_sentence_duration=10.0,
        )
        assert result.total_segments >= 2
        assert result.language == "ar"
        assert result.total_words > 0
        assert all(seg.index >= 1 for seg in result.segments)
        assert all(len(seg.text) > 0 for seg in result.segments)

    def test_english_sentence_splitting(self):
        english_text = "Welcome to our channel. Today we explore deep learning architectures! Make sure to subscribe."
        result = SpeechPreparationService.split_speech_text(
            text=english_text,
            language="en",
            min_sentence_duration=1.0,
            max_sentence_duration=8.0,
        )
        assert result.total_segments == 3
        assert result.segments[0].text.startswith("Welcome")
        assert result.segments[1].text.startswith("Today")
        assert result.segments[2].text.startswith("Make sure")

    def test_mixed_arabic_english_splitting(self):
        mixed_text = "نظام Remotion يقدم إمكانيات مذهلة لصناعة الفيديو البرمجي. استخدم React لبناء المشاهد."
        result = SpeechPreparationService.split_speech_text(
            text=mixed_text,
            min_sentence_duration=1.0,
            max_sentence_duration=10.0,
        )
        assert result.total_segments >= 2
        assert any("Remotion" in s.text for s in result.segments)
        assert any("React" in s.text for s in result.segments)

    def test_timestamped_words_splitting(self):
        words = [
            {"word": "First", "start": 0.0, "end": 0.4},
            {"word": "sentence.", "start": 0.5, "end": 1.0},
            {"word": "Second", "start": 1.5, "end": 1.9},  # 0.5s silence gap
            {"word": "sentence.", "start": 2.0, "end": 2.6},
        ]
        segments = SpeechPreparationService.split_timestamped_words(
            words=words,
            min_sentence_duration=0.5,
            max_sentence_duration=5.0,
            silence_threshold=0.3,
        )
        assert len(segments) == 2
        assert segments[0]["text"] == "First sentence."
        assert segments[0]["start"] == 0.0
        assert segments[0]["end"] == 1.0
        assert segments[1]["text"] == "Second sentence."
        assert segments[1]["start"] == 1.5
        assert segments[1]["end"] == 2.6

    def test_duration_backtracking_and_forced_split(self):
        # Long sentence with no punctuation should be force-split near max_sentence_duration
        long_words = []
        for i in range(40):
            long_words.append({
                "word": f"word{i}",
                "start": float(i * 0.4),
                "end": float(i * 0.4 + 0.35),
            })
        segments = SpeechPreparationService.split_timestamped_words(
            words=long_words,
            min_sentence_duration=2.0,
            max_sentence_duration=5.0,
            silence_threshold=0.5,
        )
        assert len(segments) > 1
        for seg in segments:
            assert seg["duration"] <= 6.0  # Respects maximum duration constraints

    def test_empty_and_whitespace_edge_cases(self):
        res1 = SpeechPreparationService.split_speech_text(text="")
        assert res1.total_segments == 0
        assert res1.total_words == 0

        res2 = SpeechPreparationService.split_speech_text(text="   \n\t  ")
        assert res2.total_segments == 0

        res3 = SpeechPreparationService.split_speech_text(text="... !!! ؟؟؟")
        assert res3.total_segments == 0

    def test_prepare_vo_segments(self):
        text_segments = [
            "Introduction to clean architecture.",
            "Decomposing legacy tools into canonical services.",
            "Conclusion and verification.",
        ]
        out = SpeechPreparationService.prepare_vo_segments(
            project_id="prj_test",
            text_segments=text_segments,
            audio_mode="cinematic_intro",
            speaking_rate=1.1,
        )
        assert out.total_segments == 3
        assert out.audio_mode == "cinematic_intro"
        assert out.total_estimated_duration_seconds > 0.0
        assert len(out.segments) == 3
        assert out.segments[0].segment_id == "vo_seg_001"
        assert out.segments[0].index == 1

    def test_align_audio_metadata(self):
        words = [
            {"word": "Hello", "start": 0.2, "end": 0.6},
            {"word": "world", "start": 0.7, "end": 1.2},
        ]
        out = SpeechPreparationService.align_audio_metadata(
            project_id="prj_meta",
            audio_storage_key="storage/prj/audio.wav",
            transcript="Hello world",
            words=words,
            audio_duration_seconds=2.0,
        )
        assert out.project_id == "prj_meta"
        assert out.total_words == 2
        assert out.audio_duration_seconds == 2.0
        assert out.covered_duration_seconds > 0.0
        assert 0.0 < out.coverage_ratio <= 1.0
        assert out.is_valid is True
