"""
tests/ai/audio_modernization/test_audio_contracts.py
====================================================
Contract validation suite for S28-M07 Audio Modernization.
Tests strict constraint enforcement, default values, and extra="forbid" behavior.
"""

import pytest
from pydantic import ValidationError

from ai.contracts.media_ops import (
    AlignAudioMetadataInput,
    AlignAudioMetadataOutput,
    AlignedSegmentItem,
    AlignedWordItem,
    AnalyzeLoudnessInput,
    AnalyzeLoudnessOutput,
    DetectSilenceInput,
    DetectSilenceOutput,
    NormalizeAudioInput,
    NormalizeAudioOutput,
    PrepareVoSegmentsInput,
    PrepareVoSegmentsOutput,
    PreparedVoSegmentItem,
    SilenceIntervalItem,
    SpeechTextSegmentItem,
    SplitSpeechTextInput,
    SplitSpeechTextOutput,
)


class TestAudioContracts:
    """Test suite for S28-M07 contracts."""

    def test_split_speech_text_contracts(self):
        # Valid input
        valid_input = SplitSpeechTextInput(
            text="Hello world! This is a test sentence.",
            language="en",
            min_sentence_duration=1.5,
            max_sentence_duration=8.0,
            silence_threshold=0.25,
        )
        assert valid_input.text.startswith("Hello")
        assert valid_input.language == "en"

        # Extra forbidden field
        with pytest.raises(ValidationError):
            SplitSpeechTextInput(
                text="Test",
                forbidden_extra="bad",
            )

        # Valid segment and output
        seg = SpeechTextSegmentItem(
            index=1,
            text="Hello world!",
            start_seconds=0.0,
            end_seconds=1.2,
            duration_seconds=1.2,
            split_reason="punctuation",
            word_count=2,
        )
        out = SplitSpeechTextOutput(
            segments=[seg],
            total_segments=1,
            total_words=2,
            language="en",
        )
        assert out.total_segments == 1
        assert out.segments[0].duration_seconds == 1.2

    def test_prepare_vo_segments_contracts(self):
        valid_input = PrepareVoSegmentsInput(
            project_id="prj_vo",
            text_segments=["Intro segment text.", "Next segment text."],
            audio_mode="cinematic",
            speaking_rate=1.2,
        )
        assert valid_input.audio_mode == "cinematic"
        assert valid_input.speaking_rate == 1.2

        # Extra fields forbidden
        with pytest.raises(ValidationError):
            PrepareVoSegmentsInput(
                project_id="prj_vo",
                text_segments=["Text"],
                unmodeled_field=123,
            )

        # Empty text_segments list forbidden (min_length=1)
        with pytest.raises(ValidationError):
            PrepareVoSegmentsInput(
                project_id="prj_vo",
                text_segments=[],
            )

        item = PreparedVoSegmentItem(
            segment_id="vo_001",
            index=1,
            text="Intro segment text.",
            estimated_duration_seconds=2.5,
            audio_mode="cinematic",
        )
        out = PrepareVoSegmentsOutput(
            project_id="prj_vo",
            segments=[item],
            total_segments=1,
            total_estimated_duration_seconds=2.5,
            audio_mode="cinematic",
        )
        assert out.audio_mode == "cinematic"

    def test_align_audio_metadata_contracts(self):
        word = AlignedWordItem(
            word="hello",
            start_seconds=0.1,
            end_seconds=0.4,
            duration_seconds=0.3,
            confidence=0.98,
        )
        assert word.confidence == 0.98

        inp = AlignAudioMetadataInput(
            project_id="prj_align",
            audio_storage_key="audio/track.wav",
            transcript="hello",
            words=[word],
            audio_duration_seconds=1.0,
        )
        assert inp.audio_duration_seconds == 1.0

        seg = AlignedSegmentItem(
            segment_id="seg_1",
            index=1,
            text="hello",
            start_seconds=0.1,
            end_seconds=0.4,
            duration_seconds=0.3,
            words=[word],
        )
        out = AlignAudioMetadataOutput(
            project_id="prj_align",
            segments=[seg],
            total_words=1,
            covered_duration_seconds=0.3,
            audio_duration_seconds=1.0,
            coverage_ratio=0.3,
        )
        assert out.total_words == 1
        assert out.coverage_ratio == 0.3
        assert out.is_valid is True

        # Extra fields forbidden
        with pytest.raises(ValidationError):
            AlignAudioMetadataInput(
                project_id="prj_align",
                audio_storage_key="audio/track.wav",
                transcript="hello",
                words=[word],
                audio_duration_seconds=1.0,
                extra_leak="forbidden",
            )

    def test_detect_silence_contracts(self):
        inp = DetectSilenceInput(
            project_id="prj_sil",
            audio_storage_key="storage/prj/audio.wav",
            threshold_db=-35.0,
            min_silence_duration_seconds=0.2,
        )
        assert inp.threshold_db == -35.0

        # Positive threshold rejected (le=0.0)
        with pytest.raises(ValidationError):
            DetectSilenceInput(
                project_id="prj_sil",
                audio_storage_key="storage/prj/audio.wav",
                threshold_db=5.0,
            )

        interval = SilenceIntervalItem(start_seconds=0.0, end_seconds=0.5, duration_seconds=0.5)
        out = DetectSilenceOutput(
            project_id="prj_sil",
            audio_storage_key="storage/prj/audio.wav",
            silence_intervals=[interval],
            total_silence_duration_seconds=0.5,
            audio_duration_seconds=10.0,
            silence_ratio=0.05,
            threshold_used_db=-35.0,
        )
        assert out.silence_ratio == 0.05

    def test_analyze_loudness_contracts(self):
        inp = AnalyzeLoudnessInput(
            project_id="prj_loud",
            audio_storage_key="storage/prj/vo.wav",
        )
        assert inp.project_id == "prj_loud"

        out = AnalyzeLoudnessOutput(
            project_id="prj_loud",
            audio_storage_key="storage/prj/vo.wav",
            integrated_lufs=-16.2,
            loudness_range=7.5,
            true_peak_db=-1.2,
            threshold_db=-26.4,
            measurement_standard="EBU R128",
            duration_seconds=12.4,
        )
        assert out.integrated_lufs == -16.2
        assert out.measurement_standard == "EBU R128"

        with pytest.raises(ValidationError):
            AnalyzeLoudnessInput(
                project_id="prj_loud",
                audio_storage_key="storage/prj/vo.wav",
                forbidden="field",
            )

    def test_normalize_audio_contracts(self):
        inp = NormalizeAudioInput(
            project_id="prj_norm",
            audio_storage_key="audio/raw.wav",
            target_lufs=-16.0,
            true_peak_db=-1.5,
            loudness_range=11.0,
            sample_rate=48000,
        )
        assert inp.sample_rate == 48000

        # Target LUFS too loud or too quiet
        with pytest.raises(ValidationError):
            NormalizeAudioInput(
                project_id="prj_norm",
                audio_storage_key="audio/raw.wav",
                target_lufs=5.0,  # Must be le=0.0
            )

        out = NormalizeAudioOutput(
            project_id="prj_norm",
            output_storage_key="audio/norm.wav",
            target_lufs=-16.0,
            measured_lufs=-16.05,
            duration_seconds=10.5,
            file_size_bytes=102400,
        )
        assert out.file_size_bytes == 102400
