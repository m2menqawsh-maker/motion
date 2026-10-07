"""
tests/ai/audio_modernization/test_audio_analysis.py
===================================================
Test suite for audio analysis capabilities (ANALYZE_LOUDNESS, DETECT_SILENCE).
Validates EBU R128 loudness metrics and silencedetect parsing via MediaProcessingService.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch
import pytest

from ai.contracts import CapabilityRequest, CapabilityType
from ai.contracts.errors import AIErrorCode
from ai.contracts.media_ops import (
    AnalyzeLoudnessInput,
    AnalyzeLoudnessOutput,
    DetectSilenceInput,
    DetectSilenceOutput,
)
from ai.media_processing.contracts import (
    AnalyzeLoudnessRequest,
    DetectSilenceRequest,
)
from ai.media_processing.errors import (
    MediaProcessingError,
    MediaSourceNotFoundError,
)
from ai.media_processing.service import MediaProcessingService
from ai.tools.adapters.media_processing import MediaProcessingAdapter
from ai.tools.gateway import ToolGateway
from ai.tools.types import TrustedToolExecutionContext


@pytest.fixture
def mock_storage(tmp_path):
    storage_root = tmp_path / "storage"
    storage_root.mkdir(parents=True, exist_ok=True)
    from scripts.core.storage.storage_service import LocalStorageBackend
    return LocalStorageBackend(root_dir=storage_root)


@pytest.fixture
def media_service(mock_storage):
    return MediaProcessingService(storage_service=mock_storage)


@pytest.fixture
def media_adapter(media_service):
    return MediaProcessingAdapter(service=media_service)


@pytest.fixture
def trusted_context():
    return TrustedToolExecutionContext(
        workspace_id="ws_audio_qc",
        actor_id="usr_audio_qc",
        roles=["editor"],
        permissions=["editor", "viewer"],
    )


class TestAudioAnalysis:
    """Test suite for S28-M07 audio analysis services and adapter execution."""

    @pytest.mark.asyncio
    async def test_analyze_loudness_success(self, media_service, mock_storage, tmp_path):
        # Create a dummy audio file in storage
        audio_key = "audio/voiceover.wav"
        file_path = mock_storage.root_dir / audio_key
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(b"RIFF....WAVEfmt ....data....")

        # Mock probe_media duration and ffmpeg stderr
        fake_loudnorm_json = (
            "Parsed_loudnorm_0\n"
            "{\n"
            '  "input_i": "-16.50",\n'
            '  "input_tp": "-1.20",\n'
            '  "input_lra": "7.80",\n'
            '  "input_thresh": "-26.70"\n'
            "}\n"
        )

        with patch("ai.media_processing.service.run_ffprobe_json", new_callable=AsyncMock) as mock_probe, \
             patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_probe.return_value = {"format": {"duration": "15.0"}}

            mock_proc = AsyncMock()
            mock_proc.communicate.return_value = (b"", fake_loudnorm_json.encode("utf-8"))
            mock_proc.returncode = 0
            mock_exec.return_value = mock_proc

            req = AnalyzeLoudnessRequest(
                project_id="prj_audio_qc",
                source_storage_key=audio_key,
            )
            result = await media_service.analyze_loudness(req)

            assert result.integrated_lufs == -16.5
            assert result.true_peak_db == -1.2
            assert result.loudness_range == 7.8
            assert result.threshold_db == -26.7
            assert result.duration_seconds == 15.0
            assert result.measurement_standard == "EBU R128"

    @pytest.mark.asyncio
    async def test_analyze_loudness_invalid_audio_fails_closed(self, media_service, mock_storage):
        # Non-existent key
        req = AnalyzeLoudnessRequest(
            project_id="prj_audio_qc",
            source_storage_key="audio/non_existent.wav",
        )
        with pytest.raises(MediaProcessingError) as exc_info:
            await media_service.analyze_loudness(req)
        assert exc_info.value.code == "SOURCE_NOT_FOUND"

    @pytest.mark.asyncio
    async def test_detect_silence_success(self, media_service, mock_storage):
        audio_key = "audio/interview.wav"
        file_path = mock_storage.root_dir / audio_key
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(b"RIFF....WAVEfmt ....data....")

        fake_silence_stderr = (
            "[silencedetect @ 0x123] silence_start: 1.0\n"
            "[silencedetect @ 0x123] silence_end: 2.5 | silence_duration: 1.5\n"
            "[silencedetect @ 0x123] silence_start: 5.0\n"
            "[silencedetect @ 0x123] silence_end: 6.0 | silence_duration: 1.0\n"
        )

        with patch("ai.media_processing.service.run_ffprobe_json", new_callable=AsyncMock) as mock_probe, \
             patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_probe.return_value = {"format": {"duration": "10.0"}}

            mock_proc = AsyncMock()
            mock_proc.communicate.return_value = (b"", fake_silence_stderr.encode("utf-8"))
            mock_proc.returncode = 0
            mock_exec.return_value = mock_proc

            req = DetectSilenceRequest(
                project_id="prj_audio_qc",
                source_storage_key=audio_key,
                threshold_db=-35.0,
                min_silence_duration=0.2,
            )
            result = await media_service.detect_silence(req)

            assert len(result.silence_intervals) == 2
            assert result.silence_intervals[0].start_seconds == 1.0
            assert result.silence_intervals[0].end_seconds == 2.5
            assert result.silence_intervals[0].duration_seconds == 1.5
            assert result.silence_intervals[1].start_seconds == 5.0
            assert result.silence_intervals[1].end_seconds == 6.0
            assert result.silence_intervals[1].duration_seconds == 1.0

            assert result.total_silence_duration_seconds == 2.5
            assert result.audio_duration_seconds == 10.0
            assert result.silence_ratio == 0.25
            assert result.threshold_used_db == -35.0

    @pytest.mark.asyncio
    async def test_media_processing_adapter_analysis_dispatch(
        self,
        media_adapter,
        mock_storage,
        trusted_context,
    ):
        audio_key = "audio/sample.wav"
        file_path = mock_storage.root_dir / audio_key
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(b"RIFF....WAVEfmt ....data....")

        # Test ANALYZE_LOUDNESS dispatch
        with patch.object(media_adapter.service, "analyze_loudness", new_callable=AsyncMock) as mock_analyze:
            from ai.media_processing.contracts import AnalyzeLoudnessResult
            mock_analyze.return_value = AnalyzeLoudnessResult(
                project_id="prj_audio_qc",
                source_storage_key=audio_key,
                integrated_lufs=-16.0,
                loudness_range=6.0,
                true_peak_db=-1.5,
                threshold_db=-26.0,
                measurement_standard="EBU R128",
                duration_seconds=8.0,
            )

            req = CapabilityRequest(
                capability_id=CapabilityType.ANALYZE_LOUDNESS,
                workspace_id="ws_audio_qc",
                project_id="prj_audio_qc",
                input={
                    "project_id": "prj_audio_qc",
                    "audio_storage_key": audio_key,
                },
            )
            val_input = AnalyzeLoudnessInput(
                project_id="prj_audio_qc",
                audio_storage_key=audio_key,
            )
            out = await media_adapter.execute(req, val_input, trusted_context)
            assert out["integrated_lufs"] == -16.0
            assert out["true_peak_db"] == -1.5

        # Test DETECT_SILENCE dispatch
        with patch.object(media_adapter.service, "detect_silence", new_callable=AsyncMock) as mock_silence:
            from ai.media_processing.contracts import DetectSilenceResult, SilenceIntervalInfo
            mock_silence.return_value = DetectSilenceResult(
                project_id="prj_audio_qc",
                source_storage_key=audio_key,
                silence_intervals=[SilenceIntervalInfo(start_seconds=0.0, end_seconds=0.5, duration_seconds=0.5)],
                total_silence_duration_seconds=0.5,
                audio_duration_seconds=5.0,
                silence_ratio=0.1,
                threshold_used_db=-40.0,
            )

            req_sil = CapabilityRequest(
                capability_id=CapabilityType.DETECT_SILENCE,
                workspace_id="ws_audio_qc",
                project_id="prj_audio_qc",
                input={
                    "project_id": "prj_audio_qc",
                    "audio_storage_key": audio_key,
                    "threshold_db": -40.0,
                    "min_silence_duration_seconds": 0.1,
                },
            )
            val_sil_input = DetectSilenceInput(
                project_id="prj_audio_qc",
                audio_storage_key=audio_key,
                threshold_db=-40.0,
                min_silence_duration_seconds=0.1,
            )
            out_sil = await media_adapter.execute(req_sil, val_sil_input, trusted_context)
            assert out_sil["silence_ratio"] == 0.1
            assert len(out_sil["silence_intervals"]) == 1
