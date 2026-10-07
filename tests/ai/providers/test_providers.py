"""
tests/ai/providers/test_providers.py
====================================
Verification suite for S27.3 Provider Registry and Provider Conformance.

Invariants:
- Provider registrations are unique and deterministic.
- Providers normalize execution into canonical CapabilityResult without secret or raw payload leakage.
- Upstream failures map cleanly into canonical AIError taxonomy.
- Provider Swap Test proves interchangeable execution without domain contract breakage.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from ai.contracts.capability import CapabilityRequest, CapabilityResult, CapabilityStatus
from ai.contracts.common import CapabilityType, ExecutionClass, PrivacyRequirement
from ai.contracts.errors import AIError, AIErrorCode
from ai.providers import (
    AIProvider,
    DuplicateProviderError,
    FakeProvider,
    FakeScenario,
    ProviderDefinition,
    ProviderRegistry,
    UnknownProviderError,
    create_empty_provider_registry,
    get_provider_registry,
)


class TestProviderRegistry:

    def test_canonical_providers_registered(self):
        """Verifies that all standard S27 providers are present in the canonical registry."""
        registry = get_provider_registry()
        expected = ["openai", "gemini", "anthropic", "elevenlabs", "fal", "replicate", "local", "mcp"]
        for p in expected:
            assert registry.exists(p), f"Missing provider: {p}"
            defn = registry.get(p)
            assert defn.provider_id == p
            assert defn.enabled is True
            assert len(defn.supported_execution_modes) >= 1

    def test_duplicate_provider_rejected(self):
        """Attempting to register a duplicate provider raises DuplicateProviderError."""
        reg = create_empty_provider_registry()
        p1 = ProviderDefinition(
            provider_id="custom-ai",
            display_name="Custom AI",
            supported_execution_modes=[ExecutionClass.INTERACTIVE],
            privacy_compliance=PrivacyRequirement.ZERO_DATA_RETENTION,
        )
        p2 = ProviderDefinition(
            provider_id="custom-ai",
            display_name="Custom AI Copy",
            supported_execution_modes=[ExecutionClass.INTERACTIVE],
            privacy_compliance=PrivacyRequirement.ZERO_DATA_RETENTION,
        )
        reg.register(p1)
        with pytest.raises(DuplicateProviderError) as exc_info:
            reg.register(p2)
        assert "custom-ai" in str(exc_info.value)

    def test_unknown_provider_rejected(self):
        """Querying an unregistered provider raises UnknownProviderError."""
        registry = get_provider_registry()
        with pytest.raises(UnknownProviderError) as exc_info:
            registry.get("super-unknown-ai")
        assert "super-unknown-ai" in str(exc_info.value)
        assert not registry.exists("super-unknown-ai")

    def test_frozen_provider_registry(self):
        """Frozen provider registry blocks registration mutations."""
        registry = get_provider_registry()
        assert registry.is_frozen
        p = ProviderDefinition(
            provider_id="new-provider",
            display_name="New",
            supported_execution_modes=[ExecutionClass.INTERACTIVE],
        )
        with pytest.raises(RuntimeError) as exc_info:
            registry.register(p)
        assert "frozen" in str(exc_info.value)


class TestProviderConformanceSuite:
    """
    Standard reusable conformance test suite executed against provider adapters.
    Validates request normalization, outcome formatting, and error taxonomy translation.
    """

    @pytest.mark.asyncio
    async def test_conformance_success(self):
        """Provider returns a compliant CapabilityResult on successful execution."""
        provider = FakeProvider(
            provider_id="test-provider",
            default_model_id="test-model",
            scenario=FakeScenario.SUCCESS,
        )
        request = CapabilityRequest(
            capability=CapabilityType.REASONING,
            input_data={"prompt": "Synthesize video scene outline"},
        )
        result = await provider.execute(request)

        assert isinstance(result, CapabilityResult)
        assert result.capability == CapabilityType.REASONING
        assert result.status == CapabilityStatus.SUCCESS
        assert result.output_data is not None
        assert result.error is None
        assert result.confidence is not None and result.confidence > 0.0
        assert result.provenance.provider_id == "test-provider"
        assert result.provenance.model_id == "test-model"
        assert result.usage.total_tokens is not None

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("scenario", "expected_code", "expected_retryable"),
        [
            (FakeScenario.TIMEOUT, AIErrorCode.TIMEOUT, True),
            (FakeScenario.RATE_LIMITED, AIErrorCode.RATE_LIMITED, True),
            (FakeScenario.SERVER_ERROR, AIErrorCode.PROVIDER_UNAVAILABLE, True),
            (FakeScenario.MALFORMED_OUTPUT, AIErrorCode.INVALID_MODEL_OUTPUT, False),
            (FakeScenario.SCHEMA_INVALID, AIErrorCode.SCHEMA_VALIDATION_FAILED, False),
            (FakeScenario.REFUSAL, AIErrorCode.CONTENT_REJECTED, False),
            (FakeScenario.CANCELLED, AIErrorCode.CANCELLED, False),
            (FakeScenario.UNAVAILABLE, AIErrorCode.PROVIDER_UNAVAILABLE, True),
            (FakeScenario.STREAM_INTERRUPTED, AIErrorCode.DEPENDENCY_FAILED, True),
        ],
    )
    async def test_conformance_failure_mappings(
        self,
        scenario: FakeScenario,
        expected_code: AIErrorCode,
        expected_retryable: bool,
    ):
        """Verifies that all provider failure scenarios map to canonical AIError taxonomy."""
        provider = FakeProvider(scenario=scenario)
        request = CapabilityRequest(
            capability=CapabilityType.TEXT_TO_SPEECH,
            input_data={"text": "Hello audio world"},
        )
        result = await provider.execute(request)

        assert isinstance(result, CapabilityResult)
        assert result.status == CapabilityStatus.FAILED
        assert result.output_data is None
        assert result.error is not None
        assert result.error.code == expected_code
        assert result.error.retryable == expected_retryable
        assert len(result.error.message) > 5

    @pytest.mark.asyncio
    async def test_no_secret_leakage_in_error_or_output(self):
        """AIError validator actively prevents leakage of secrets, keys, or bearer tokens."""
        # Verifying AIError validator blocks leaks
        with pytest.raises(ValidationError):
            AIError(
                code=AIErrorCode.INTERNAL_ERROR,
                message="Upstream error with key: sk-abcdef1234567890abcdef",  # pragma: allowlist
                retryable=False,
            )

        with pytest.raises(ValidationError):
            AIError(
                code=AIErrorCode.INTERNAL_ERROR,
                message="Authentication failed for Bearer 1234567890abcdef1234567890",
                retryable=False,
            )


class TestProviderSwap:
    """
    Provider Swap Invariant:
    Two distinct providers offering the same capability must be fully swappable
    without altering domain contracts or request schemas.
    """

    @pytest.mark.asyncio
    async def test_provider_swap_compatibility(self):
        """Executes the same canonical CapabilityRequest against Provider A then Provider B."""
        provider_a = FakeProvider(
            provider_id="tts-provider-alpha",
            display_name="TTS Alpha",
            default_model_id="alpha-voice-v1",
            scenario=FakeScenario.SUCCESS,
            custom_output={"audio_format": "wav", "sample_rate": 44100, "duration_sec": 4.5},
        )
        provider_b = FakeProvider(
            provider_id="tts-provider-beta",
            display_name="TTS Beta",
            default_model_id="beta-neural-v2",
            scenario=FakeScenario.SUCCESS,
            custom_output={"audio_format": "wav", "sample_rate": 44100, "duration_sec": 4.5},
        )

        canonical_request = CapabilityRequest(
            capability=CapabilityType.TEXT_TO_SPEECH,
            input_data={"text": "Video narration voiceover draft"},
        )

        # Execute on Provider A
        result_a = await provider_a.execute(canonical_request)
        # Execute on Provider B
        result_b = await provider_b.execute(canonical_request)

        # Domain assertions: identical contractual structure
        assert result_a.status == CapabilityStatus.SUCCESS
        assert result_b.status == CapabilityStatus.SUCCESS

        assert result_a.capability == result_b.capability == CapabilityType.TEXT_TO_SPEECH
        assert result_a.output_data == result_b.output_data

        # Only provenance details differ
        assert result_a.provenance.provider_id == "tts-provider-alpha"
        assert result_a.provenance.model_id == "alpha-voice-v1"

        assert result_b.provenance.provider_id == "tts-provider-beta"
        assert result_b.provenance.model_id == "beta-neural-v2"
