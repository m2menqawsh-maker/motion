"""
tests/ai/speech/test_stt_provider_interface.py
==============================================
Tests for STTProvider abstraction, LocalSTTProvider implementation,
model lifecycle, model reuse, concurrency bounding, and device fallback (S28-M04).

Invariants verified:
- LocalSTTProvider strictly implements STTProvider ABC.
- Rejection of invalid provider types by ModelRouter.
- Model lazy loading: unloaded initially, loaded on first request.
- Model reuse: subsequent requests reuse loaded instance (load_count preserved).
- Concurrent initial load: two concurrent requests initialize model exactly once (no double-load).
- Bounded concurrency and queue backpressure: queue depth ceiling triggers ResourceExhaustedError.
- Deterministic device selection: real CPU execution, GPU fallback telemetry.
- Strict output validation: malformed output fails closed.
- Digital silence handling: produces clean empty transcript without error.
"""

import asyncio
from pathlib import Path
import pytest

from ai.contracts.common import CapabilityType, QualityTarget
from ai.contracts.errors import AIErrorCode
from ai.contracts.media import AnalysisProvenance, SpeechIntelligence
from ai.routing.router import ModelRouter
from ai.speech.lifecycle import WhisperLifecycleManager
from ai.speech.local_provider import LocalSTTProvider
from ai.speech.stt_provider import (
    DeviceUnavailableError,
    InvalidAudioError,
    OutputValidationError,
    ResourceExhaustedError,
    STTConfig,
    STTError,
    STTProvider,
    STTRequest,
)

AUDIO_FIXTURE_PATH = "assets/incoming/tests/human_vo_01.wav"


class DummyNonSTTProvider:
    """Class intentionally not inheriting from STTProvider."""
    pass


class TestSTTProviderInterfaceAndLifecycle:

    def setup_method(self):
        """Reset singleton lifecycle manager for hermetic test isolation."""
        WhisperLifecycleManager.reset_instance()

    def teardown_method(self):
        WhisperLifecycleManager.reset_instance()

    def test_local_provider_implements_interface(self):
        """Section 69: LocalSTTProvider implements STTProvider."""
        provider = LocalSTTProvider()
        assert isinstance(provider, STTProvider)
        assert provider.provider_id == "local"

        caps = provider.get_capabilities()
        assert caps.model_family == "whisper"
        assert "base" in caps.supported_model_sizes
        assert "cpu" in caps.supported_devices
        assert caps.word_timestamps_supported is True
        assert caps.vad_supported is True

        health = provider.get_health()
        assert health.provider_id == "local"
        assert health.registered is True
        assert health.ready is True
        assert health.loaded is False  # Lazy loaded: false initially

    def test_router_rejects_invalid_provider_type(self):
        """Section 69: ModelRouter strictly rejects providers not implementing STTProvider."""
        router = ModelRouter()
        with pytest.raises(TypeError, match="Provider must implement STTProvider interface"):
            router.register_stt_provider("invalid", DummyNonSTTProvider())  # type: ignore

    @pytest.mark.asyncio
    async def test_model_lazy_load_and_reuse(self):
        """
        Sections 71: Model lifecycle lazy load + reuse.
        Request 1: loads model (load_count = 1).
        Request 2: reuses loaded instance (load_count still = 1).
        """
        manager = WhisperLifecycleManager.get_instance(default_model_size="tiny")
        provider = LocalSTTProvider(default_model_size="tiny", lifecycle_manager=manager)

        assert manager.load_count == 0
        assert manager.is_loaded is False

        req1 = STTRequest(
            request_id="req_reuse_1",
            audio_path=AUDIO_FIXTURE_PATH,
            audio_content_hash="hash_human_vo_01",
            config=STTConfig(model_size="tiny", language="ar"),
        )
        res1 = await provider.transcribe(req1)

        assert manager.load_count == 1
        assert manager.is_loaded is True
        assert res1.transcript != ""
        assert res1.model_load_ms > 0.0

        # Second request reuses warm model
        req2 = STTRequest(
            request_id="req_reuse_2",
            audio_path=AUDIO_FIXTURE_PATH,
            audio_content_hash="hash_human_vo_01",
            config=STTConfig(model_size="tiny", language="ar"),
        )
        res2 = await provider.transcribe(req2)

        # Invariant: model was NOT reloaded
        assert manager.load_count == 1
        assert res2.transcript == res1.transcript
        assert res2.model_load_ms == 0.0  # Warm reuse

    @pytest.mark.asyncio
    async def test_concurrent_load_initializes_once(self):
        """
        Section 72: Two requests arrive while unloaded; model must initialize exactly ONCE.
        """
        manager = WhisperLifecycleManager.get_instance(default_model_size="tiny")
        provider = LocalSTTProvider(default_model_size="tiny", lifecycle_manager=manager)

        assert manager.load_count == 0

        req_a = STTRequest(
            request_id="req_concurrent_a",
            audio_path=AUDIO_FIXTURE_PATH,
            audio_content_hash="hash_human_vo_01",
            config=STTConfig(model_size="tiny", language="ar"),
        )
        req_b = STTRequest(
            request_id="req_concurrent_b",
            audio_path=AUDIO_FIXTURE_PATH,
            audio_content_hash="hash_human_vo_01",
            config=STTConfig(model_size="tiny", language="ar"),
        )

        # Fire simultaneously
        res_a, res_b = await asyncio.gather(
            provider.transcribe(req_a),
            provider.transcribe(req_b),
        )

        assert res_a.transcript != ""
        assert res_b.transcript != ""
        # Invariant: exactly one initialization occurred
        assert manager.load_count == 1

    @pytest.mark.asyncio
    async def test_bounded_concurrency_and_backpressure(self):
        """
        Sections 15-16: Bounded concurrency queue and backpressure.
        When max_queue_depth is exceeded, raises ResourceExhaustedError.
        """
        # Create manager with max_concurrency=1 and max_queue_depth=1
        manager = WhisperLifecycleManager(
            default_model_size="tiny",
            max_concurrency=1,
            max_queue_depth=1,
        )

        # Acquire execution slot and fill queue
        await manager.acquire_execution_slot()
        manager._queue_depth = 1  # Queue is now at capacity

        # Next acquisition attempt must fail with ResourceExhaustedError
        with pytest.raises(ResourceExhaustedError, match="Backpressure limit reached") as exc_info:
            await manager.acquire_execution_slot()

        ai_err = exc_info.value.to_ai_error()
        assert ai_err.code == AIErrorCode.RATE_LIMITED
        assert ai_err.details.get("stt_error_category") == "RESOURCE_EXHAUSTED"

        # Cleanup
        manager._queue_depth = 0
        manager.release_execution_slot()

    def test_device_selection_and_fallback_telemetry(self):
        """
        Section 17-18 & 74: Device selection and fallback.
        Verifies CPU detection and explicit telemetry for requested vs selected devices.
        """
        manager = WhisperLifecycleManager(default_model_size="tiny")

        # Explicit CPU request
        dev, comp, fb_occ, fb_reason = manager.detect_device(requested_device="cpu")
        assert dev == "cpu"
        assert comp == "int8"
        assert fb_occ is False
        assert fb_reason is None

        # Auto detection on current machine:
        # Machine has CUDA count 1 but missing libcublas.so.12
        dev_auto, comp_auto, fb_occ_auto, fb_reason_auto = manager.detect_device(requested_device="auto")
        assert dev_auto == "cpu"
        assert comp_auto == "int8"
        # Since auto was requested, fallback to CPU is standard graceful fallback
        assert fb_reason_auto is not None
        assert "libcublas.so.12" in fb_reason_auto or "CUDA" in fb_reason_auto

    @pytest.mark.asyncio
    async def test_digital_silence_produces_clean_transcript(self, tmp_path):
        """
        Section 34: Valid silence file returns SUCCESS with empty transcript,
        segments=[], words=[], and not a crash or hallucination.
        """
        import soundfile as sf
        import numpy as np

        silence_file = tmp_path / "pure_silence.wav"
        sr = 16000
        samples = np.zeros(sr * 2, dtype=np.float32)  # 2 seconds of pure zero
        sf.write(str(silence_file), samples, sr)

        provider = LocalSTTProvider(default_model_size="tiny")
        req = STTRequest(
            request_id="req_silence",
            audio_path=str(silence_file),
            audio_content_hash="hash_silence",
            config=STTConfig(model_size="tiny"),
        )
        res = await provider.transcribe(req)

        assert res.transcript == ""
        assert len(res.segments) == 0
        assert len(res.words) == 0
        assert res.duration_seconds >= 1.9

    @pytest.mark.asyncio
    async def test_corrupt_audio_fails_closed(self, tmp_path):
        """
        Section 33: Corrupt or non-audio file fails closed with AudioDecodeError or InvalidAudioError,
        never fabricating success.
        """
        corrupt_file = tmp_path / "corrupt.wav"
        corrupt_file.write_bytes(b"NOT_A_VALID_WAV_HEADER_RANDOM_GARBAGE_12345")

        provider = LocalSTTProvider(default_model_size="tiny")
        req = STTRequest(
            request_id="req_corrupt",
            audio_path=str(corrupt_file),
            audio_content_hash="hash_corrupt",
            config=STTConfig(model_size="tiny"),
        )

        with pytest.raises(STTError) as exc_info:
            await provider.transcribe(req)

        ai_err = exc_info.value.to_ai_error()
        assert ai_err.code in (AIErrorCode.CONTENT_REJECTED, AIErrorCode.SCHEMA_VALIDATION_FAILED)
