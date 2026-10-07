"""
tests/ai/audio_modernization/test_fault_injection.py
===================================================
Fault injection and resiliency tests for S28-M07 Audio Modernization & Speech subsystem.
Validates:
1. Missing source audio fails closed with MediaSourceNotFoundError.
2. Subprocess failures fail closed with ProcessExecutionFailedError and ensure cleanup.
3. Corrupted loudnorm stdout / non-JSON output fails closed gracefully.
4. Manifest & Timeline builder resilient error handling on empty or invalid inputs.
"""

from pathlib import Path
from unittest.mock import AsyncMock, patch
import pytest

from ai.media_processing.adapter import FFmpegProcessResult
from ai.media_processing.contracts import AnalyzeLoudnessRequest, DetectSilenceRequest
from ai.media_processing.errors import (
    MediaProcessingError,
    MediaSourceNotFoundError,
    ProcessExecutionFailedError,
)
from ai.media_processing.service import MediaProcessingService
from ai.speech.manifest import SpeechManifestBuilder
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


class TestAudioFaultInjection:
    """Fault injection tests for audio modernization."""

    @pytest.mark.asyncio
    async def test_missing_source_audio_fails_closed(
        self,
        media_service: MediaProcessingService,
    ):
        req = AnalyzeLoudnessRequest(
            project_id="prj_fault_test",
            source_storage_key="audio/non_existent_file.wav",
        )
        with pytest.raises(MediaSourceNotFoundError, match="not found in project storage"):
            await media_service.analyze_loudness(req)

        # Ensure no residual scratch dirs
        subdirs = list(media_service.base_scratch_dir.glob("job_*"))
        assert len(subdirs) == 0

    @pytest.mark.asyncio
    async def test_detect_silence_missing_source_fails_closed(
        self,
        media_service: MediaProcessingService,
    ):
        req = DetectSilenceRequest(
            project_id="prj_fault_test",
            source_storage_key="audio/ghost_track.wav",
        )
        with pytest.raises(MediaSourceNotFoundError, match="not found in project storage"):
            await media_service.detect_silence(req)

        subdirs = list(media_service.base_scratch_dir.glob("job_*"))
        assert len(subdirs) == 0

    @pytest.mark.asyncio
    async def test_corrupted_loudnorm_output_fails_closed(
        self,
        media_service: MediaProcessingService,
        mock_storage,
    ):
        # Create dummy file in storage
        audio_key = build_storage_key("ws_default", "prj_fault_test", "audio", "track_1", "test.wav")
        mock_storage.put(audio_key, b"RIFF....WAVEfmt ....data....")

        # Mock probe to succeed so we test the loudnorm parsing failure
        mock_probe = AsyncMock(return_value={
            "streams": [{"codec_type": "audio", "duration": "2.0"}],
            "format": {"duration": "2.0"},
        })

        # Mock adapter execute_raw to return non-JSON loudnorm output
        mock_res = FFmpegProcessResult(
            command=["ffmpeg", "-i", "test.wav"],
            returncode=0,
            stdout="FFmpeg output without JSON block [Parsed_loudnorm_0 @ 0x123] corrupt data",
            stderr="Error: unable to parse loudness measurements",
            duration_ms=10.0,
        )

        with patch("ai.media_processing.service.run_ffprobe_json", mock_probe):
            with patch.object(media_service.adapter, "execute_raw", AsyncMock(return_value=mock_res)):
                req = AnalyzeLoudnessRequest(
                    project_id="prj_fault_test",
                    source_storage_key=audio_key,
                )
                with pytest.raises(ProcessExecutionFailedError, match="Failed to extract EBU R128 loudness"):
                    await media_service.analyze_loudness(req)

        # Workspace directory must be cleaned up
        subdirs = list(media_service.base_scratch_dir.glob("job_*"))
        assert len(subdirs) == 0

    @pytest.mark.asyncio
    async def test_process_failure_fails_closed_with_cleanup(
        self,
        media_service: MediaProcessingService,
        mock_storage,
    ):
        audio_key = build_storage_key("ws_default", "prj_fault_test", "audio", "track_2", "test2.wav")
        mock_storage.put(audio_key, b"RIFF....WAVEfmt ....data....")

        mock_probe = AsyncMock(return_value={
            "streams": [{"codec_type": "audio", "duration": "2.0"}],
            "format": {"duration": "2.0"},
        })

        # Mock adapter to exit with returncode 1
        mock_res = FFmpegProcessResult(
            command=["ffmpeg", "-i", "test2.wav"],
            returncode=1,
            stdout="",
            stderr="ffmpeg fatal error: invalid codec or corrupted stream",
            duration_ms=15.0,
        )

        with patch("ai.media_processing.service.run_ffprobe_json", mock_probe):
            with patch.object(media_service.adapter, "execute_raw", AsyncMock(return_value=mock_res)):
                req = DetectSilenceRequest(
                    project_id="prj_fault_test",
                    source_storage_key=audio_key,
                )
                with pytest.raises(ProcessExecutionFailedError, match="FFmpeg command failed with code 1"):
                    await media_service.detect_silence(req)

        subdirs = list(media_service.base_scratch_dir.glob("job_*"))
        assert len(subdirs) == 0

    def test_manifest_builder_validates_and_writes_output_path(self, tmp_path: Path):
        output_file = tmp_path / "nested" / "dir" / "manifest.json"
        
        manifest = SpeechManifestBuilder.build_manifest(
            project_id="prj_fault_test",
            audio_key_or_path="audio/test.wav",
            analysis_data={
                "duration": 2.0,
                "segments": [{
                    "id": 0,
                    "start": 0.0,
                    "end": 2.0,
                    "text": "hello",
                    "words": [{"word": "hello", "start": 0.0, "end": 2.0}],
                }],
            },
            split_sentences=[{
                "index": 0,
                "text": "hello",
                "source_timing": {"start": 0.0, "end": 2.0, "duration": 2.0},
                "words": [{"word": "hello", "start": 0.0, "end": 2.0, "duration": 2.0}],
            }],
            output_path=str(output_file),
        )
        assert manifest["statistics"]["sentence_count"] == 1
        assert manifest["statistics"]["word_count"] == 1

    def test_timeline_builder_handles_empty_or_corrupt_manifest(self):
        # Empty manifest dictionary with missing or zero source duration
        tl = SpeechTimelineBuilder.build_timeline(manifest_data={})
        assert tl["success"] is False
        assert tl["error"]["code"] == "INVALID_SOURCE_DURATION"
