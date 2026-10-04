"""
ai/providers/fake.py
====================
Deterministic, offline Fake Provider infrastructure for tests and conformance (S27.3).

Supports configurable simulation scenarios:
- SUCCESS
- TIMEOUT
- RATE_LIMITED (429)
- SERVER_ERROR (500)
- MALFORMED_OUTPUT
- SCHEMA_INVALID
- REFUSAL (Content policy / moderation rejection)
- CANCELLED
- UNAVAILABLE
- STREAM_INTERRUPTED
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Optional
from pydantic import JsonValue

from ai.contracts.capability import CapabilityRequest, CapabilityResult, CapabilityStatus
from ai.contracts.common import CapabilityType, ExecutionClass, PrivacyRequirement, ProvenanceRecord
from ai.contracts.errors import AIError, AIErrorCode
from ai.contracts.usage import UsageRecord
from ai.providers.base import AIProvider, ProviderDefinition


class FakeScenario(str, Enum):
    """Simulated execution outcome scenarios."""
    SUCCESS = "SUCCESS"
    TIMEOUT = "TIMEOUT"
    RATE_LIMITED = "RATE_LIMITED"
    SERVER_ERROR = "SERVER_ERROR"
    MALFORMED_OUTPUT = "MALFORMED_OUTPUT"
    SCHEMA_INVALID = "SCHEMA_INVALID"
    REFUSAL = "REFUSAL"
    CANCELLED = "CANCELLED"
    UNAVAILABLE = "UNAVAILABLE"
    STREAM_INTERRUPTED = "STREAM_INTERRUPTED"


class FakeProvider(AIProvider):
    """
    Offline, deterministic provider adapter simulating wire interactions.
    Guarantees strict zero-secret leakage and normalized canonical contracts.
    """

    def __init__(
        self,
        provider_id: str = "fake-provider",
        display_name: str = "Fake Test Provider",
        default_model_id: str = "fake-model-v1",
        scenario: FakeScenario = FakeScenario.SUCCESS,
        custom_output: Optional[Dict[str, JsonValue]] = None,
    ):
        definition = ProviderDefinition(
            provider_id=provider_id,
            display_name=display_name,
            supported_execution_modes=[ExecutionClass.INTERACTIVE, ExecutionClass.BATCH],
            privacy_compliance=PrivacyRequirement.ZERO_DATA_RETENTION,
            enabled=True,
            description="Offline mock provider for deterministic testing",
        )
        super().__init__(definition)
        self.default_model_id = default_model_id
        self.scenario = scenario
        self.custom_output = custom_output
        self.invocation_count = 0
        self.last_request: Optional[CapabilityRequest] = None

    def set_scenario(self, scenario: FakeScenario) -> None:
        self.scenario = scenario

    async def execute(self, request: CapabilityRequest) -> CapabilityResult:
        self.invocation_count += 1
        self.last_request = request

        now = datetime.now(timezone.utc)
        provenance = ProvenanceRecord(
            source="fake_provider_adapter",
            model_id=self.default_model_id,
            provider_id=self.provider_id,
            timestamp=now,
            latency_ms=15,
        )

        # 1. Success scenario
        if self.scenario == FakeScenario.SUCCESS:
            default_data: Dict[str, JsonValue] = {
                "result": f"Simulated output for capability {request.capability.value}",
                "audio_format": "wav",
                "text_content": "Deterministic synthetic text",
                "processed": True,
            }
            output_payload = self.custom_output if self.custom_output is not None else default_data

            return CapabilityResult(
                capability=request.capability,
                status=CapabilityStatus.SUCCESS,
                output_data=output_payload,
                confidence=0.98,
                provenance=provenance,
                usage=UsageRecord(input_tokens=10, output_tokens=25, total_tokens=35),
                error=None,
            )

        # 2. Timeout
        if self.scenario == FakeScenario.TIMEOUT:
            err = AIError(
                code=AIErrorCode.TIMEOUT,
                message=f"Request to provider '{self.provider_id}' timed out after 15000ms",
                retryable=True,
                dependency_reference=self.provider_id,
            )
            return CapabilityResult(
                capability=request.capability,
                status=CapabilityStatus.FAILED,
                output_data=None,
                provenance=provenance,
                error=err,
            )

        # 3. Rate Limited (429)
        if self.scenario == FakeScenario.RATE_LIMITED:
            err = AIError(
                code=AIErrorCode.RATE_LIMITED,
                message=f"Rate limit exceeded on provider '{self.provider_id}'",
                retryable=True,
                details={"retry_after_seconds": 30, "tier": "free"},
                dependency_reference=self.provider_id,
            )
            return CapabilityResult(
                capability=request.capability,
                status=CapabilityStatus.FAILED,
                output_data=None,
                provenance=provenance,
                error=err,
            )

        # 4. Server Error (500)
        if self.scenario == FakeScenario.SERVER_ERROR:
            err = AIError(
                code=AIErrorCode.PROVIDER_UNAVAILABLE,
                message=f"Upstream provider '{self.provider_id}' encountered internal server error (HTTP 500)",
                retryable=True,
                dependency_reference=self.provider_id,
            )
            return CapabilityResult(
                capability=request.capability,
                status=CapabilityStatus.FAILED,
                output_data=None,
                provenance=provenance,
                error=err,
            )

        # 5. Malformed Output
        if self.scenario == FakeScenario.MALFORMED_OUTPUT:
            err = AIError(
                code=AIErrorCode.INVALID_MODEL_OUTPUT,
                message=f"Provider '{self.provider_id}' returned unparseable or corrupted payload",
                retryable=False,
                details={"raw_excerpt": "ERR_NON_JSON_STREAM_TRUNCATED"},
            )
            return CapabilityResult(
                capability=request.capability,
                status=CapabilityStatus.FAILED,
                output_data=None,
                provenance=provenance,
                error=err,
            )

        # 6. Schema Invalid
        if self.scenario == FakeScenario.SCHEMA_INVALID:
            err = AIError(
                code=AIErrorCode.SCHEMA_VALIDATION_FAILED,
                message=f"Provider output failed schema compliance for capability {request.capability.value}",
                retryable=False,
                details={"missing_field": "required_payload_root"},
            )
            return CapabilityResult(
                capability=request.capability,
                status=CapabilityStatus.FAILED,
                output_data=None,
                provenance=provenance,
                error=err,
            )

        # 7. Refusal / Content policy
        if self.scenario == FakeScenario.REFUSAL:
            err = AIError(
                code=AIErrorCode.CONTENT_REJECTED,
                message="Upstream provider refused prompt under safety policy",
                retryable=False,
                details={"policy_category": "safety_filter"},
            )
            return CapabilityResult(
                capability=request.capability,
                status=CapabilityStatus.FAILED,
                output_data=None,
                provenance=provenance,
                error=err,
            )

        # 8. Cancelled
        if self.scenario == FakeScenario.CANCELLED:
            err = AIError(
                code=AIErrorCode.CANCELLED,
                message="Operation cancelled by caller before provider completion",
                retryable=False,
            )
            return CapabilityResult(
                capability=request.capability,
                status=CapabilityStatus.FAILED,
                output_data=None,
                provenance=provenance,
                error=err,
            )

        # 9. Provider Unavailable
        if self.scenario == FakeScenario.UNAVAILABLE:
            err = AIError(
                code=AIErrorCode.PROVIDER_UNAVAILABLE,
                message=f"Provider gateway for '{self.provider_id}' is unreachable (DNS/TCP failure)",
                retryable=True,
                dependency_reference=self.provider_id,
            )
            return CapabilityResult(
                capability=request.capability,
                status=CapabilityStatus.FAILED,
                output_data=None,
                provenance=provenance,
                error=err,
            )

        # 10. Stream Interrupted
        if self.scenario == FakeScenario.STREAM_INTERRUPTED:
            err = AIError(
                code=AIErrorCode.DEPENDENCY_FAILED,
                message="SSE/HTTP stream disconnected prematurely",
                retryable=True,
            )
            return CapabilityResult(
                capability=request.capability,
                status=CapabilityStatus.FAILED,
                output_data=None,
                provenance=provenance,
                error=err,
            )

        raise RuntimeError(f"Unhandled scenario: {self.scenario}")
