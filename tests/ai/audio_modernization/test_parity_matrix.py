"""
tests/ai/audio_modernization/test_parity_matrix.py
==================================================
Parity verification tests comparing legacy audio-tools-mcp behaviors
with modernized canonical S28-M07 audio and speech subsystems.

Proves:
1. Sentence splitting parity (sentence_splitter.py vs SpeechPreparationService).
2. Manifest building parity (manifest_builder.py vs SpeechManifestBuilder).
3. Timeline generation parity (timeline_builder.py vs SpeechTimelineBuilder).
4. Audio loudness normalization parity (MediaProcessingService / NORMALIZE_AUDIO).
5. Silence detection parity (MediaProcessingService / DETECT_SILENCE).
6. Audio trimming parity (MediaProcessingService / TRIM_AUDIO).
7. Audio extension parity (MediaProcessingService / EXTEND_AUDIO).
8. Voiceover segment preparation & metadata alignment parity.
"""

from pathlib import Path
import subprocess
import pytest

from ai.contracts.media_ops import (
    AlignAudioMetadataInput,
    AlignedWordItem,
    PrepareVoSegmentsInput,
)
from ai.media_processing.contracts import (
    DetectSilenceRequest,
    ExtendAudioRequest,
    NormalizeMediaRequest,
    TrimAudioRequest,
)
from ai.media_processing.service import MediaProcessingService
from ai.speech.manifest import SpeechManifestBuilder
from ai.speech.preparation import SpeechPreparationService
from ai.speech.timeline import SpeechTimelineBuilder
from scripts.core.storage.storage_service import LocalStorageBackend, build_storage_key


@pytest.fixture
def mock_storage(tmp_path: Path):
    store_dir = tmp_path / "storage"
    store_dir.mkdir(parents=True, exist_ok=True)
    return LocalStorageBackend(root_dir=store_dir)


@pytest.fixture
def media_service(mock_storage, tmp_path: Path) -> MediaProcessingService:
    scratch_dir = tmp_path / "scratch"
    scratch_dir.mkdir(parents=True, exist_ok=True)
    return MediaProcessingService(
        storage_service=mock_storage,
        base_scratch_dir=scratch_dir,
    )


@pytest.fixture
def speech_service() -> SpeechPreparationService:
    return SpeechPreparationService()


@pytest.fixture
def sample_speech_words():
    return [
        {"word": "Welcome", "start": 0.0, "end": 0.5, "probability": 0.99},
        {"word": "to", "start": 0.55, "end": 0.75, "probability": 0.98},
        {"word": "the", "start": 0.8, "end": 0.95, "probability": 0.99},
        {"word": "modernized", "start": 1.0, "end": 1.6, "probability": 0.95},
        {"word": "audio", "start": 1.65, "end": 2.0, "probability": 0.97},
        {"word": "pipeline.", "start": 2.05, "end": 2.6, "probability": 0.96},
        {"word": "Everything", "start": 3.2, "end": 3.8, "probability": 0.99},
        {"word": "is", "start": 3.85, "end": 4.0, "probability": 0.99},
        {"word": "deterministic.", "start": 4.05, "end": 4.9, "probability": 0.98},
    ]


@pytest.fixture
def sample_analysis_dict(sample_speech_words):
    return {
        "text": "Welcome to the modernized audio pipeline. Everything is deterministic.",
        "duration": 5.0,
        "language": "en",
        "segments": [
            {
                "id": 0,
                "start": 0.0,
                "end": 2.6,
                "text": "Welcome to the modernized audio pipeline.",
                "words": sample_speech_words[:6],
            },
            {
                "id": 1,
                "start": 3.2,
                "end": 4.9,
                "text": "Everything is deterministic.",
                "words": sample_speech_words[6:],
            },
        ],
        "silence_periods": [
            {"start": 2.6, "end": 3.2, "duration": 0.6},
        ],
    }


class TestAudioParityMatrix:
    """Parity verification for all 8 legacy audio capabilities."""

    def test_01_sentence_splitter_parity(self, speech_service: SpeechPreparationService, sample_speech_words):
        """Parity check for sentence splitting and word grouping."""
        split_result = speech_service.split_timestamped_words(
            words=sample_speech_words,
            min_sentence_duration=1.0,
            max_sentence_duration=7.0,
            silence_threshold=0.3,
        )

        assert len(split_result) == 2
        # Sentence 1
        assert split_result[0]["text"] == "Welcome to the modernized audio pipeline."
        assert split_result[0]["source_timing"]["start"] == 0.0
        assert split_result[0]["source_timing"]["end"] == 2.6
        assert len(split_result[0]["words"]) == 6

        # Sentence 2
        assert split_result[1]["text"] == "Everything is deterministic."
        assert split_result[1]["source_timing"]["start"] == 3.2
        assert split_result[1]["source_timing"]["end"] == 4.9
        assert len(split_result[1]["words"]) == 3

    def test_02_manifest_builder_parity(self, sample_analysis_dict, sample_speech_words, speech_service):
        """Parity check for manifest construction."""
        split_sentences = speech_service.split_timestamped_words(
            words=sample_speech_words,
            min_sentence_duration=1.0,
            max_sentence_duration=7.0,
            silence_threshold=0.3,
        )

        manifest = SpeechManifestBuilder.build_manifest(
            project_id="prj_parity",
            audio_key_or_path="audio/narration.wav",
            analysis_data=sample_analysis_dict,
            split_sentences=split_sentences,
        )

        assert manifest["success"] is True
        assert manifest["statistics"]["sentence_count"] == 2
        assert manifest["statistics"]["word_count"] == 9
        assert manifest["source"]["duration"] == 5.0
        assert len(manifest["unmapped_intervals"]) >= 1
        silence_gap = manifest["unmapped_intervals"][0]
        assert silence_gap["start"] >= 2.6
        assert silence_gap["end"] <= 3.2
        assert silence_gap["type"] == "silence"

    def test_03_timeline_builder_parity(self, sample_analysis_dict, sample_speech_words, speech_service):
        """Parity check for timeline construction."""
        split_sentences = speech_service.split_timestamped_words(
            words=sample_speech_words,
            min_sentence_duration=1.0,
            max_sentence_duration=7.0,
            silence_threshold=0.3,
        )
        manifest = SpeechManifestBuilder.build_manifest(
            project_id="prj_parity",
            audio_key_or_path="audio/narration.wav",
            analysis_data=sample_analysis_dict,
            split_sentences=split_sentences,
        )

        timeline = SpeechTimelineBuilder.build_timeline(
            manifest_data=manifest,
            fps=30.0,
        )

        assert timeline["success"] is True
        assert timeline["validation"]["valid"] is True
        assert timeline["source"]["fps"] == 30.0
        assert timeline["source"]["total_frames"] == int(5.0 * 30.0)
        assert len(timeline["words"]) == 9
        assert len(timeline["sentences"]) == 2

    def test_04_voiceover_preparation_and_alignment_parity(self, speech_service: SpeechPreparationService):
        """Parity check for voiceover preparation and metadata alignment."""
        prep_out = speech_service.prepare_vo_segments(
            project_id="prj_parity",
            text_segments=["Step one.", "Step two.", "Step three."],
            audio_mode="cinematic_intro",
            speaking_rate=1.1,
        )

        assert prep_out.total_segments == 3
        assert [s.text for s in prep_out.segments] == ["Step one.", "Step two.", "Step three."]
        assert prep_out.audio_mode == "cinematic_intro"

        words = [
            {"word": "Step", "start": 0.0, "end": 0.4},
            {"word": "one.", "start": 0.45, "end": 0.9},
            {"word": "Step", "start": 1.5, "end": 1.9},
            {"word": "two.", "start": 1.95, "end": 2.4},
        ]
        align_out = speech_service.align_audio_metadata(
            project_id="prj_parity",
            audio_storage_key="audio/steps.wav",
            transcript="Step one. Step two.",
            words=words,
            audio_duration_seconds=3.0,
        )
        assert align_out.total_words == 4
        assert align_out.coverage_ratio > 0.0
        assert align_out.is_valid is True

    @pytest.mark.asyncio
    async def test_05_normalize_audio_loudness_parity(
        self,
        media_service: MediaProcessingService,
        mock_storage,
    ):
        """Parity check for loudness normalization via canonical MediaProcessingService."""
        job_dir = Path(media_service.base_scratch_dir) / "parity_norm_setup"
        job_dir.mkdir(parents=True, exist_ok=True)
        test_wav = job_dir / "test_tone.wav"
        
        cmd = [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=1.0",
            "-c:a", "pcm_s16le", str(test_wav)
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert proc.returncode == 0

        audio_key = build_storage_key("ws_default", "prj_parity", "audio", "sine_1", "sine.wav")
        mock_storage.put(audio_key, test_wav.read_bytes())

        req = NormalizeMediaRequest(
            project_id="prj_parity",
            source_storage_key=audio_key,
            target_lufs=-16.0,
            true_peak_db=-1.5,
        )
        res = await media_service.normalize_media(req)

        assert res.output_storage_key is not None
        assert res.measured_lufs is not None
        assert abs(res.target_lufs - (-16.0)) < 0.1
        assert res.file_size_bytes > 0

    @pytest.mark.asyncio
    async def test_06_detect_silence_parity(
        self,
        media_service: MediaProcessingService,
        mock_storage,
    ):
        """Parity check for silence detection via canonical MediaProcessingService."""
        job_dir = Path(media_service.base_scratch_dir) / "parity_silence_setup"
        job_dir.mkdir(parents=True, exist_ok=True)
        silence_wav = job_dir / "tone_with_silence.wav"

        # 0.5s tone, 1.0s silence, 0.5s tone
        cmd = [
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "sine=frequency=440:duration=0.5",
            "-f", "lavfi",
            "-i", "anullsrc=r=44100:cl=mono:d=1.0",
            "-f", "lavfi",
            "-i", "sine=frequency=440:duration=0.5",
            "-filter_complex", "[0:a][1:a][2:a]concat=n=3:v=0:a=1[out]",
            "-map", "[out]", "-c:a", "pcm_s16le", str(silence_wav)
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert proc.returncode == 0

        audio_key = build_storage_key("ws_default", "prj_parity", "audio", "silence_test", "silence.wav")
        mock_storage.put(audio_key, silence_wav.read_bytes())

        req = DetectSilenceRequest(
            project_id="prj_parity",
            source_storage_key=audio_key,
            threshold_db=-30.0,
            min_silence_duration=0.5,
        )
        res = await media_service.detect_silence(req)

        assert len(res.silence_intervals) >= 1
        intv = res.silence_intervals[0]
        assert 0.4 <= intv.start_seconds <= 0.6
        assert 1.4 <= intv.end_seconds <= 1.6
        assert res.total_silence_duration_seconds > 0.0

    @pytest.mark.asyncio
    async def test_07_trim_audio_parity(
        self,
        media_service: MediaProcessingService,
        mock_storage,
    ):
        """Parity check for audio trimming via canonical MediaProcessingService."""
        job_dir = Path(media_service.base_scratch_dir) / "parity_trim_setup"
        job_dir.mkdir(parents=True, exist_ok=True)
        long_wav = job_dir / "long_tone.wav"

        cmd = [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=3.0",
            "-c:a", "pcm_s16le", str(long_wav)
        ]
        subprocess.run(cmd, check=True)

        audio_key = build_storage_key("ws_default", "prj_parity", "audio", "long_1", "long.wav")
        mock_storage.put(audio_key, long_wav.read_bytes())

        req = TrimAudioRequest(
            project_id="prj_parity",
            source_storage_key=audio_key,
            target_duration_seconds=1.5,
        )
        res = await media_service.trim_audio(req)

        assert res.output_storage_key is not None
        assert abs(res.duration_seconds - 1.5) < 0.1

    @pytest.mark.asyncio
    async def test_08_extend_audio_parity(
        self,
        media_service: MediaProcessingService,
        mock_storage,
    ):
        """Parity check for audio extension via canonical MediaProcessingService."""
        job_dir = Path(media_service.base_scratch_dir) / "parity_extend_setup"
        job_dir.mkdir(parents=True, exist_ok=True)
        short_wav = job_dir / "short_tone.wav"

        cmd = [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=1.0",
            "-c:a", "pcm_s16le", str(short_wav)
        ]
        subprocess.run(cmd, check=True)

        audio_key = build_storage_key("ws_default", "prj_parity", "audio", "short_1", "short.wav")
        mock_storage.put(audio_key, short_wav.read_bytes())

        req = ExtendAudioRequest(
            project_id="prj_parity",
            source_storage_key=audio_key,
            target_duration_seconds=2.5,
            method="loop",
            short_duration_threshold=0.5,
        )
        res = await media_service.extend_audio(req)

        assert res.output_storage_key is not None
        assert abs(res.duration_seconds - 2.5) < 0.2
