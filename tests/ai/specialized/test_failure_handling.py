"""
tests/ai/specialized/test_failure_handling.py
=============================================
Failure handling and resiliency tests for Specialized Media AI (S27.17 / AI-13 Rule 24).

Invariants verified:
- Provider timeout -> raises SpecializedMediaError with code TIMEOUT.
- 429 Rate limited -> raises SpecializedMediaError with code RATE_LIMITED.
- 500 Server error -> raises SpecializedMediaError with code PROVIDER_UNAVAILABLE or INTERNAL_ERROR.
- Unsupported capability -> raises SpecializedMediaError with code UNSUPPORTED_CAPABILITY.
"""

import pytest

from ai.contracts.errors import AIErrorCode
from ai.contracts.specialized import ImageGenerationRequest, TTSRequest
from ai.specialized.adapters import FakeSpecializedMediaAdapterA, SpecializedFailureScenario
from ai.specialized.errors import SpecializedMediaError
from ai.specialized.service import SpecializedMediaService
from scripts.core.storage.storage_service import LocalStorageBackend


@pytest.fixture
def storage(tmp_path):
    return LocalStorageBackend(root_dir=tmp_path / "fail_storage")


@pytest.fixture
def service(storage):
    adapter = FakeSpecializedMediaAdapterA(storage_service=storage)
    svc = SpecializedMediaService(storage_service=storage)
    svc.register_provider_adapter("fake-specialized-a", adapter)
    return svc


@pytest.mark.asyncio
async def test_provider_timeout_handling(service):
    """Verifies that an upstream timeout translates to a structured TIMEOUT error."""
    adapter = service.get_provider_adapter("fake-specialized-a")
    adapter.set_scenario(SpecializedFailureScenario.TIMEOUT)

    req = TTSRequest(text="This should time out", voice_id="v1")
    with pytest.raises(SpecializedMediaError) as exc_info:
        await service.synthesize_speech("ws_fail", req, provider_id_override="fake-specialized-a")

    assert exc_info.value.code == AIErrorCode.TIMEOUT
    assert exc_info.value.retryable is True


@pytest.mark.asyncio
async def test_provider_rate_limit_429_handling(service):
    """Verifies that upstream 429 translates to a structured RATE_LIMITED error."""
    adapter = service.get_provider_adapter("fake-specialized-a")
    adapter.set_scenario(SpecializedFailureScenario.RATE_LIMITED)

    req = ImageGenerationRequest(prompt="Rate limit test", width=512, height=512)
    with pytest.raises(SpecializedMediaError) as exc_info:
        await service.generate_image("ws_fail", req, provider_id_override="fake-specialized-a")

    assert exc_info.value.code == AIErrorCode.RATE_LIMITED
    assert exc_info.value.retryable is True


@pytest.mark.asyncio
async def test_provider_server_error_500_handling(service):
    """Verifies that upstream 500 translates to a structured error."""
    adapter = service.get_provider_adapter("fake-specialized-a")
    adapter.set_scenario(SpecializedFailureScenario.SERVER_ERROR)

    req = TTSRequest(text="Internal server error test", voice_id="v1")
    with pytest.raises(SpecializedMediaError) as exc_info:
        await service.synthesize_speech("ws_fail", req, provider_id_override="fake-specialized-a")

    assert exc_info.value.code in [AIErrorCode.PROVIDER_UNAVAILABLE, AIErrorCode.INTERNAL_ERROR]


@pytest.mark.asyncio
async def test_unsupported_capability_rejection(service):
    """Verifies that attempting an unregistered provider raises UNSUPPORTED_CAPABILITY."""
    req = TTSRequest(text="Unregistered provider call", voice_id="v1")
    with pytest.raises(SpecializedMediaError) as exc_info:
        await service.synthesize_speech("ws_fail", req, provider_id_override="non-existent-provider-999")

    assert exc_info.value.code == AIErrorCode.CAPABILITY_UNAVAILABLE
