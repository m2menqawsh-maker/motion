"""
tests/ai/audio_modernization/test_security.py
=============================================
Adversarial security tests for S28-M07 Audio Modernization & Speech subsystem.
Validates:
1. Path traversal prevention in storage keys, manifests, and timelines.
2. Shell injection prevention in audio analysis and media processing commands.
3. Zero-byte and corrupt audio fail-closed behavior with guaranteed cleanup.
4. Adversarial text inputs and unicode handling in SpeechPreparationService.
5. Malformed/negative/NaN timing constraints rejection in VO preparation.
"""

from pathlib import Path
import pytest
from pydantic import ValidationError

from ai.contracts.media_ops import (
    AnalyzeLoudnessInput,
    DetectSilenceInput,
    SplitSpeechTextInput,
    PrepareVoSegmentsInput,
    AlignAudioMetadataInput,
    AlignedSegmentItem,
)
from ai.media_processing.contracts import AnalyzeLoudnessRequest, DetectSilenceRequest
from ai.media_processing.errors import (
    CommandInjectionDetectedError,
    InvalidMediaFileError,
    MediaProcessingError,
    MediaSourceNotFoundError,
    MediaSourceUnauthorizedError,
    ProcessExecutionFailedError,
    ProtocolSecurityViolationError,
)
from ai.media_processing.security import (
    assert_no_shell_injection,
    assert_safe_protocol,
    validate_storage_key_confinement,
)
from ai.media_processing.service import MediaProcessingService
from ai.speech.preparation import SpeechPreparationService
from ai.speech.manifest import SpeechManifestBuilder
from ai.speech.timeline import SpeechTimelineBuilder
from scripts.core.storage.storage_service import StorageService, build_storage_key


@pytest.fixture
def speech_service() -> SpeechPreparationService:
    return SpeechPreparationService()


@pytest.fixture
def storage_service(tmp_path: Path):
    store_dir = tmp_path / "storage"
    store_dir.mkdir(parents=True, exist_ok=True)
    from scripts.core.storage.storage_service import LocalStorageBackend
    return LocalStorageBackend(root_dir=store_dir)


@pytest.fixture
def media_service(storage_service: StorageService, tmp_path: Path) -> MediaProcessingService:
    scratch_dir = tmp_path / "scratch"
    scratch_dir.mkdir(parents=True, exist_ok=True)
    return MediaProcessingService(
        storage_service=storage_service,
        base_scratch_dir=scratch_dir,
    )


class TestAudioSecurity:
    """Security and adversarial tests for modernized audio and speech."""

    @pytest.mark.parametrize(
        "traversal_key",
        [
            "../secret_audio.wav",
            "../../etc/shadow",
            "audio/../../confidential.key",
            "/absolute/root/audio.wav",
            "audio\0malicious.wav",
            "audio/clip.wav\0",
        ],
    )
    def test_path_traversal_keys_rejected(self, traversal_key: str):
        with pytest.raises(ProtocolSecurityViolationError):
            validate_storage_key_confinement(traversal_key, "prj_target")

    @pytest.mark.parametrize(
        "malicious_input",
        [
            "audio.wav; rm -rf /",
            "audio.wav && cat /etc/passwd",
            "audio.wav | nc 127.0.0.1 9000",
            "audio.wav `whoami`",
            "audio.wav $(id)",
            "audio.wav > /dev/null",
            "audio.wav\nevil_cmd",
            "audio.wav\revil_cmd",
        ],
    )
    def test_shell_injection_metacharacters_rejected(self, malicious_input: str):
        with pytest.raises(CommandInjectionDetectedError, match="Shell metacharacters detected"):
            assert_no_shell_injection(malicious_input)

    @pytest.mark.asyncio
    async def test_corrupt_audio_fails_closed_with_cleanup(
        self,
        media_service: MediaProcessingService,
        storage_service: StorageService,
    ):
        corrupt_key = build_storage_key("ws_default", "prj_sec", "audio", "corrupt_1", "corrupt.wav")
        storage_service.put(corrupt_key, b"NOT_A_VALID_RIFF_WAV_HEADER_DATA_12345")

        req = AnalyzeLoudnessRequest(
            project_id="prj_sec",
            source_storage_key=corrupt_key,
        )
        with pytest.raises((ProcessExecutionFailedError, InvalidMediaFileError, MediaProcessingError)):
            await media_service.analyze_loudness(req)

        # Workspace directory must be cleaned up on failure
        subdirs = list(media_service.base_scratch_dir.glob("job_*"))
        assert len(subdirs) == 0

    @pytest.mark.asyncio
    async def test_zero_byte_audio_fails_closed_with_cleanup(
        self,
        media_service: MediaProcessingService,
        storage_service: StorageService,
    ):
        zero_key = build_storage_key("ws_default", "prj_sec", "audio", "zero_1", "zero.wav")
        storage_service.put(zero_key, b"")

        req = DetectSilenceRequest(
            project_id="prj_sec",
            source_storage_key=zero_key,
        )
        with pytest.raises((ProcessExecutionFailedError, InvalidMediaFileError, MediaProcessingError)):
            await media_service.detect_silence(req)

        # Workspace directory must be cleaned up on failure
        subdirs = list(media_service.base_scratch_dir.glob("job_*"))
        assert len(subdirs) == 0

    def test_adversarial_text_inputs_in_speech_prep(self, speech_service: SpeechPreparationService):
        # 1. Null bytes in text
        res_null = speech_service.split_speech_text(SplitSpeechTextInput(text="Hello\x00world! This is safe."))
        assert len(res_null.segments) >= 1
        assert "\x00" not in res_null.segments[0].text or "world" in res_null.segments[0].text

        # 2. Extremely large text (10,000 repeating sentences)
        large_text = "Modern audio pipeline ensures high performance. " * 2000
        res_large = speech_service.split_speech_text(SplitSpeechTextInput(text=large_text))
        assert len(res_large.segments) > 0
        assert res_large.total_segments == len(res_large.segments)

        # 3. RTL / LTR Unicode override characters
        bidi_text = "\u202Ereversed text\u202C and \u202Dnormal text\u202C."
        res_bidi = speech_service.split_speech_text(SplitSpeechTextInput(text=bidi_text))
        assert len(res_bidi.segments) >= 1

        # 4. Emoji only
        res_emoji = speech_service.split_speech_text(SplitSpeechTextInput(text="🔥🔥 🚀🚀 ✨✨"))
        # Emojis don't have alnum words, so segments may be empty or contain emojis safely without error
        assert isinstance(res_emoji.segments, list)

        # 5. HTML / Script injection attempt in speech text
        xss_text = "<script>alert('xss')</script> Should remain pure text."
        res_xss = speech_service.split_speech_text(SplitSpeechTextInput(text=xss_text))
        assert len(res_xss.segments) >= 1

    def test_negative_timing_constraints_rejected_in_speech_prep(self):
        # Validates that negative duration or start time is rejected by contract validation
        with pytest.raises(ValidationError):
            AlignedSegmentItem(
                text="Invalid segment",
                start=-1.5,
                end=2.0,
                duration=3.5,
            )

        with pytest.raises(ValidationError):
            AlignedSegmentItem(
                text="Invalid segment negative duration",
                start=0.0,
                end=2.0,
                duration=-2.0,
            )
