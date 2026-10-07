"""
tests/ai/speech/test_stt_tenant_and_security.py
===============================================
Comprehensive security, tenant boundary, scratch isolation, and structured error
translation test suite for Speech-to-Text (S28-M04 PART 1).
"""

from __future__ import annotations

import asyncio
from pathlib import Path
import pytest

from ai.contracts import (
    AIErrorCode,
    CapabilityRequest,
    CapabilityResult,
    CapabilityStatus,
    CapabilityType,
)
from ai.contracts.errors import AIError
from ai.routing.router import ModelRouter
from ai.speech.local_provider import LocalSTTProvider
from ai.speech.storage_resolver import resolve_and_materialize_audio
from ai.speech.stt_provider import (
    AudioDecodeError,
    DeviceUnavailableError,
    InvalidAudioError,
    ModelInferenceError,
    ModelLoadError,
    ModelNotAvailableError,
    OutputValidationError,
    ResourceExhaustedError,
    STTCancelledError,
    STTTimeoutError,
    StorageReadError,
    TenantAccessDeniedError,
)
from ai.tools.types import TrustedToolExecutionContext


class TestSTTTenantAndSecurity:
    """Verifies strict adherence to tenant isolation, storage sandboxing, and safe error translation."""

    @pytest.mark.asyncio
    async def test_tenant_boundary_denied_for_unauthorized_project(self):
        """Verifies that an execution context without access to the project is rejected."""
        router = ModelRouter()
        local_stt = LocalSTTProvider()
        router.register_stt_provider("faster-whisper", local_stt)

        # Context only authorized for prj_other_99
        ctx = TrustedToolExecutionContext(
            workspace_id="ws_test",
            actor_id="user_restricted",
            roles=["editor"],
            permissions=["viewer", "editor"],
            is_admin=False,
            accessible_projects=["prj_other_99"],
        )

        req = CapabilityRequest(
            capability_id=CapabilityType.SPEECH_TO_TEXT,
            project_id="prj_alpha_1",
            input={
                "project_id": "prj_alpha_1",
                "audio_storage_key": "audio/voiceover.wav",
                "language": "ar",
            },
        )

        res = await router.execute_stt(req, ctx)
        assert res.status == CapabilityStatus.FAILED
        assert res.error is not None
        assert res.error.code == AIErrorCode.TENANT_ACCESS_DENIED
        assert "access denied" in res.error.message.lower() or "cannot access" in res.error.message.lower()

    @pytest.mark.asyncio
    async def test_path_traversal_storage_key_rejected(self):
        """Verifies that directory traversal tokens (../..) in storage keys fail immediately."""
        router = ModelRouter()
        local_stt = LocalSTTProvider()
        router.register_stt_provider("faster-whisper", local_stt)

        ctx = TrustedToolExecutionContext(
            workspace_id="ws_test",
            actor_id="user_admin",
            roles=["editor"],
            permissions=["viewer", "editor"],
            is_admin=False,
            accessible_projects=["prj_alpha_1"],
        )

        req = CapabilityRequest(
            capability_id=CapabilityType.SPEECH_TO_TEXT,
            project_id="prj_alpha_1",
            input={
                "project_id": "prj_alpha_1",
                "audio_storage_key": "../../etc/shadow",
                "language": "ar",
            },
        )

        res = await router.execute_stt(req, ctx)
        assert res.status == CapabilityStatus.FAILED
        assert res.error is not None
        assert res.error.code == AIErrorCode.TENANT_ACCESS_DENIED
        assert "traversal" in res.error.message.lower() or "denied" in res.error.message.lower()

    @pytest.mark.asyncio
    async def test_absolute_host_path_storage_key_rejected(self):
        """Verifies that raw absolute filesystem paths are rejected as storage keys."""
        router = ModelRouter()
        local_stt = LocalSTTProvider()
        router.register_stt_provider("faster-whisper", local_stt)

        ctx = TrustedToolExecutionContext(
            workspace_id="ws_test",
            actor_id="user_admin",
            roles=["editor"],
            permissions=["viewer", "editor"],
            is_admin=False,
            accessible_projects=["prj_alpha_1"],
        )

        req = CapabilityRequest(
            capability_id=CapabilityType.SPEECH_TO_TEXT,
            project_id="prj_alpha_1",
            input={
                "project_id": "prj_alpha_1",
                "audio_storage_key": "/etc/passwd",
                "language": "ar",
            },
        )

        res = await router.execute_stt(req, ctx)
        assert res.status == CapabilityStatus.FAILED
        assert res.error is not None
        assert res.error.code == AIErrorCode.TENANT_ACCESS_DENIED

    @pytest.mark.asyncio
    async def test_nonexistent_audio_asset_fails_closed(self):
        """Verifies that non-existent storage key fails with DEPENDENCY_FAILED (storage error)."""
        router = ModelRouter()
        local_stt = LocalSTTProvider()
        router.register_stt_provider("faster-whisper", local_stt)

        ctx = TrustedToolExecutionContext(
            workspace_id="ws_test",
            actor_id="user_admin",
            roles=["editor"],
            permissions=["viewer", "editor"],
            is_admin=False,
            accessible_projects=["prj_alpha_1"],
        )

        req = CapabilityRequest(
            capability_id=CapabilityType.SPEECH_TO_TEXT,
            project_id="prj_alpha_1",
            input={
                "project_id": "prj_alpha_1",
                "audio_storage_key": "audio/does_not_exist_file.wav",
                "language": "ar",
            },
        )

        res = await router.execute_stt(req, ctx)
        assert res.status == CapabilityStatus.FAILED
        assert res.error is not None
        assert res.error.code == AIErrorCode.DEPENDENCY_FAILED
        assert res.error.details.get("stt_error_category") == "STORAGE_READ_FAILED"

    @pytest.mark.asyncio
    async def test_scratch_workspace_guaranteed_cleanup_on_success(self):
        """Verifies that scratch files and directories are wiped clean after successful execution."""
        ctx = TrustedToolExecutionContext(
            workspace_id="ws_test",
            actor_id="user_admin",
            roles=["editor"],
            permissions=["viewer", "editor"],
            is_admin=False,
            accessible_projects=["prj_alpha_1"],
        )

        temp_audio_path: Path
        async with resolve_and_materialize_audio(
            project_id="prj_alpha_1",
            audio_storage_key="audio/voiceover.wav",
            context=ctx,
            request_id="req_cleanup_success_test",
        ) as (temp_path, content_hash, source_asset_id):
            temp_audio_path = temp_path
            assert temp_audio_path.exists()
            assert temp_audio_path.parent.name.startswith("req_cleanup_success_test")

        # After context exit, the directory and file MUST no longer exist
        assert not temp_audio_path.exists()
        assert not temp_audio_path.parent.exists()

    @pytest.mark.asyncio
    async def test_scratch_workspace_guaranteed_cleanup_on_exception(self):
        """Verifies that scratch files and directories are wiped clean even when processing crashes."""
        ctx = TrustedToolExecutionContext(
            workspace_id="ws_test",
            actor_id="user_admin",
            roles=["editor"],
            permissions=["viewer", "editor"],
            is_admin=False,
            accessible_projects=["prj_alpha_1"],
        )

        temp_audio_path: Path
        try:
            async with resolve_and_materialize_audio(
                project_id="prj_alpha_1",
                audio_storage_key="audio/voiceover.wav",
                context=ctx,
                request_id="req_cleanup_err_test",
            ) as (temp_path, content_hash, source_asset_id):
                temp_audio_path = temp_path
                assert temp_audio_path.exists()
                raise RuntimeError("Simulated crash during inference")
        except RuntimeError:
            pass

        # After exception exit, the directory and file MUST no longer exist
        assert not temp_audio_path.exists()
        assert not temp_audio_path.parent.exists()

    def test_stt_structured_error_taxonomy_mapping(self):
        """Verifies deterministic mapping of all 12 custom STT errors to canonical AIError codes."""
        errors_and_expected_codes = [
            (InvalidAudioError("Invalid audio format"), AIErrorCode.SCHEMA_VALIDATION_FAILED, "INVALID_AUDIO"),
            (AudioDecodeError("Failed to decode stream"), AIErrorCode.CONTENT_REJECTED, "AUDIO_DECODE_FAILED"),
            (ModelNotAvailableError("Model not found"), AIErrorCode.CAPABILITY_UNAVAILABLE, "MODEL_NOT_AVAILABLE"),
            (ModelLoadError("Failed to load weights"), AIErrorCode.PROVIDER_UNAVAILABLE, "MODEL_LOAD_FAILED"),
            (ModelInferenceError("CTranslate2 kernel crash"), AIErrorCode.DEPENDENCY_FAILED, "MODEL_INFERENCE_FAILED"),
            (DeviceUnavailableError("CUDA device not found"), AIErrorCode.PROVIDER_UNAVAILABLE, "DEVICE_UNAVAILABLE"),
            (ResourceExhaustedError("Queue limit exceeded"), AIErrorCode.RATE_LIMITED, "RESOURCE_EXHAUSTED"),
            (STTTimeoutError("Transcription timed out"), AIErrorCode.TIMEOUT, "TIMEOUT"),
            (STTCancelledError("Caller cancelled operation"), AIErrorCode.CANCELLED, "CANCELLED"),
            (OutputValidationError("Non-chronological segments"), AIErrorCode.INVALID_MODEL_OUTPUT, "OUTPUT_VALIDATION_FAILED"),
            (StorageReadError("Failed to read audio asset"), AIErrorCode.DEPENDENCY_FAILED, "STORAGE_READ_FAILED"),
            (TenantAccessDeniedError("Access to project denied"), AIErrorCode.TENANT_ACCESS_DENIED, "TENANT_ACCESS_DENIED"),
        ]

        for stt_err, expected_code, expected_cat in errors_and_expected_codes:
            ai_err = stt_err.to_ai_error()
            assert isinstance(ai_err, AIError)
            assert ai_err.code == expected_code
            assert ai_err.details is not None
            assert ai_err.details.get("stt_error_category") == expected_cat
