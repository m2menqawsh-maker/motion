"""
tests/ai/providers/test_openrouter.py
======================================
Comprehensive verification suite for OpenRouter Development Provider (DEV-OPENROUTER).

Validates:
1. Provider Registry registration (development-only, enabled=True, production_default=False).
2. Model Registry registration (openrouter-dev-model for REASONING, PLANNING, VISION).
3. Model Router integration & production exclusion (hard constraint blocks OpenRouter in production).
4. Secret Loading: strictly from environment, no secret leakage in errors or traces.
5. Conformance: Failure mappings (Missing key, 401 invalid key, Timeout, 429 rate limit, 500 error, malformed output).
6. Budget safety: Pre-flight BUDGET_EXCEEDED enforcement before external dispatch.
7. Observability: Telemetry span creation, cost/usage tracking, and secret scan verification.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, Dict
import pytest
import httpx

from ai.contracts.capability import CapabilityRequest, CapabilityResult, CapabilityStatus
from ai.contracts.common import CapabilityType, ExecutionClass, QualityTarget
from ai.contracts.errors import AIError, AIErrorCode
from ai.contracts.model import ModelRequirement
from ai.contracts.observability import SpanType
from ai.contracts.usage import CostEstimate
from ai.models.registry import get_model_registry
from ai.observability.redaction import scan_trace_for_secrets
from ai.observability.tracer import AITracer
from ai.providers import get_provider_registry
from ai.providers.openrouter import (
    OpenRouterConfigurationError,
    OpenRouterProvider,
    get_openrouter_provider_definition,
)
from ai.routing.router import ModelRouter
from scripts.core.ai_trace_repository import SQLTraceRepository
from scripts.core.database import DatabaseEngine


# ============================================================================
# 1. Provider Registry & Metadata Tests
# ============================================================================

class TestOpenRouterProviderRegistry:
    def test_openrouter_registered_in_canonical_registry(self):
        """Verifies OpenRouter is registered in canonical ProviderRegistry with development status."""
        registry = get_provider_registry()
        assert registry.exists("openrouter")
        defn = registry.get("openrouter")
        assert defn.provider_id == "openrouter"
        assert defn.enabled is True
        assert defn.environment == "development"
        assert defn.production_default is False
        assert "Development gateway for S28" in (defn.description or "")

    def test_openrouter_definition_helper(self):
        """Verifies definition factory returns compliant development metadata."""
        defn = get_openrouter_provider_definition()
        assert defn.provider_id == "openrouter"
        assert defn.environment == "development"
        assert defn.production_default is False
        assert ExecutionClass.INTERACTIVE in defn.supported_execution_modes


# ============================================================================
# 2. Model Registry Tests
# ============================================================================

class TestOpenRouterModelRegistry:
    def test_openrouter_dev_model_registered(self):
        """Verifies openrouter-dev-model is registered with REASONING, PLANNING, and VISION capabilities."""
        model_reg = get_model_registry()
        assert model_reg.exists("openrouter-dev-model")
        m = model_reg.get("openrouter-dev-model")
        assert m.provider_id == "openrouter"
        assert CapabilityType.REASONING in m.capabilities
        assert CapabilityType.PLANNING in m.capabilities
        assert CapabilityType.VISION in m.capabilities
        assert m.supports_structured_output is True
        assert m.supports_tools is True
        assert m.pricing is not None
        assert isinstance(m.pricing.input_token_price, Decimal)
        assert isinstance(m.pricing.output_token_price, Decimal)


# ============================================================================
# 3. Model Router Integration & Production Hard Exclusion Tests
# ============================================================================

class TestOpenRouterRoutingAndProductionSafety:
    def test_router_selects_models_in_development(self, monkeypatch):
        """In development environment, router can resolve capabilities."""
        monkeypatch.setenv("MOTION_ENV", "development")
        router = ModelRouter()
        req = ModelRequirement(
            capability=CapabilityType.REASONING,
            quality_target=QualityTarget.STANDARD,
            execution_class=ExecutionClass.INTERACTIVE,
        )
        selection = router.route(req)
        assert selection.primary_model is not None

    def test_production_environment_strictly_excludes_openrouter(self, monkeypatch):
        """In production environment, ModelRouter hard constraints strictly reject OpenRouter."""
        monkeypatch.setenv("MOTION_ENV", "production")
        from ai.models.types import CostTier, LatencyTier, ModelDefinition
        from ai.providers import ProviderDefinition, create_empty_provider_registry
        from ai.routing.constraints import evaluate_hard_constraints

        provider_reg = create_empty_provider_registry()
        provider_reg.register(
            ProviderDefinition(
                provider_id="openrouter",
                display_name="OpenRouter Dev",
                supported_execution_modes=[ExecutionClass.INTERACTIVE],
                environment="development",
                production_default=False,
            )
        )

        model = ModelDefinition(
            model_id="openrouter-dev-model",
            provider_id="openrouter",
            display_name="OpenRouter Dev",
            capabilities=[CapabilityType.REASONING],
            quality_profile=QualityTarget.HIGH,
            cost_profile=CostTier.LOW,
            latency_profile=LatencyTier.FAST,
            reliability=0.99,
        )

        req = ModelRequirement(capability=CapabilityType.REASONING)
        is_eligible, reasons, _ = evaluate_hard_constraints(
            model=model,
            requirement=req,
            provider_registry=provider_reg,
        )
        assert not is_eligible
        assert any("restricted to development environment only" in r for r in reasons)


# ============================================================================
# 4. Secret Loading & Sanitization Tests
# ============================================================================

class TestOpenRouterSecretHandling:
    def test_missing_api_key_returns_clear_failure_without_crash(self, monkeypatch):
        """When OPENROUTER_API_KEY is unset, provider returns clear structured failure."""
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        provider = OpenRouterProvider()

        assert provider.api_key is None
        with pytest.raises(OpenRouterConfigurationError) as exc_info:
            provider.validate_credentials()
        assert "OPENROUTER_API_KEY is required to enable the OpenRouter development provider." in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_with_missing_key_returns_provider_unavailable(self, monkeypatch):
        """execute() with unset key returns structured AIError with exact message."""
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        provider = OpenRouterProvider()
        req = CapabilityRequest(
            capability=CapabilityType.REASONING,
            input_data={"prompt": "Confirm operational status"},
        )
        result = await provider.execute(req)

        assert result.status == CapabilityStatus.FAILED
        assert result.error is not None
        assert result.error.code == AIErrorCode.PROVIDER_UNAVAILABLE
        assert "OPENROUTER_API_KEY is required to enable the OpenRouter development provider." in result.error.message

    def test_api_key_loaded_from_env_without_leakage(self, monkeypatch):
        """API key is read from env only and never printed in string representations."""
        test_key = "sk-or-v1-testkey1234567890abcdef1234567890abcdef"
        monkeypatch.setenv("OPENROUTER_API_KEY", test_key)
        provider = OpenRouterProvider()

        assert provider.api_key == test_key
        # Ensure __repr__ or __str__ does not expose key
        assert test_key not in repr(provider)
        assert test_key not in str(provider)


# ============================================================================
# 5. Failure Tests (Mocked wire interactions)
# ============================================================================

class TestOpenRouterFailureScenarios:
    @pytest.mark.asyncio
    async def test_invalid_key_401_authentication_failure(self, monkeypatch):
        """HTTP 401 returns structured authentication error with zero secret leakage."""
        test_key = "sk-or-v1-invalidkey1234567890"
        monkeypatch.setenv("OPENROUTER_API_KEY", test_key)

        def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                401,
                json={"error": {"message": "Invalid API key", "code": 401}},
            )

        client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
        provider = OpenRouterProvider(http_client=client)

        req = CapabilityRequest(
            capability=CapabilityType.REASONING,
            input_data={"prompt": "Ping"},
        )
        result = await provider.execute(req)

        assert result.status == CapabilityStatus.FAILED
        assert result.error is not None
        assert result.error.code == AIErrorCode.PROVIDER_UNAVAILABLE
        assert "authentication failed" in result.error.message.lower()
        # Verify no secret leaked
        assert test_key not in result.error.message
        assert test_key not in str(result.error.details)

    @pytest.mark.asyncio
    async def test_provider_timeout_handling(self, monkeypatch):
        """Request timeout maps to canonical AIErrorCode.TIMEOUT with retryable=True."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-validfakekey1234567890")

        def mock_handler(request: httpx.Request):
            raise httpx.ReadTimeout("Connection timed out")

        client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
        provider = OpenRouterProvider(http_client=client, max_retries=1)

        req = CapabilityRequest(
            capability=CapabilityType.PLANNING,
            input_data={"prompt": "Plan scene 1"},
        )
        result = await provider.execute(req)

        assert result.status == CapabilityStatus.FAILED
        assert result.error is not None
        assert result.error.code == AIErrorCode.TIMEOUT
        assert result.error.retryable is True

    @pytest.mark.asyncio
    async def test_provider_rate_limited_429(self, monkeypatch):
        """HTTP 429 maps to AIErrorCode.RATE_LIMITED with retryable=True."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-validfakekey1234567890")

        def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                429,
                json={"error": {"message": "Rate limit exceeded", "code": 429}},
            )

        client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
        provider = OpenRouterProvider(http_client=client, max_retries=1)

        req = CapabilityRequest(
            capability=CapabilityType.REASONING,
            input_data={"prompt": "Test rate limit"},
        )
        result = await provider.execute(req)

        assert result.status == CapabilityStatus.FAILED
        assert result.error is not None
        assert result.error.code == AIErrorCode.RATE_LIMITED
        assert result.error.retryable is True

    @pytest.mark.asyncio
    async def test_provider_server_error_500(self, monkeypatch):
        """HTTP 500 maps to AIErrorCode.PROVIDER_UNAVAILABLE with retryable=True."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-validfakekey1234567890")

        def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="Internal Server Error")

        client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
        provider = OpenRouterProvider(http_client=client, max_retries=1)

        req = CapabilityRequest(
            capability=CapabilityType.REASONING,
            input_data={"prompt": "Test 500"},
        )
        result = await provider.execute(req)

        assert result.status == CapabilityStatus.FAILED
        assert result.error is not None
        assert result.error.code == AIErrorCode.PROVIDER_UNAVAILABLE
        assert result.error.retryable is True

    @pytest.mark.asyncio
    async def test_malformed_non_json_output(self, monkeypatch):
        """Non-JSON response maps to AIErrorCode.INVALID_MODEL_OUTPUT."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-validfakekey1234567890")

        def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, text="<HTML>Not JSON</HTML>")

        client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
        provider = OpenRouterProvider(http_client=client)

        req = CapabilityRequest(
            capability=CapabilityType.REASONING,
            input_data={"prompt": "Test non-json"},
        )
        result = await provider.execute(req)

        assert result.status == CapabilityStatus.FAILED
        assert result.error is not None
        assert result.error.code == AIErrorCode.INVALID_MODEL_OUTPUT

    @pytest.mark.asyncio
    async def test_structured_validation_failure(self, monkeypatch):
        """When structured output is requested but response is not JSON, maps to SCHEMA_VALIDATION_FAILED."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-validfakekey1234567890")

        def mock_handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "id": "gen-1",
                    "model": "google/gemini-2.0-flash-001",
                    "choices": [{"message": {"role": "assistant", "content": "I am not a JSON object"}}],
                },
            )

        client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
        provider = OpenRouterProvider(http_client=client)

        req = CapabilityRequest(
            capability=CapabilityType.PLANNING,
            input_data={"prompt": "Generate scene plan", "structured": True},
        )
        result = await provider.execute(req)

        assert result.status == CapabilityStatus.FAILED
        assert result.error is not None
        assert result.error.code == AIErrorCode.SCHEMA_VALIDATION_FAILED


# ============================================================================
# 6. Budget Safety & Pre-Flight Check Tests
# ============================================================================

class TestOpenRouterBudgetSafety:
    @pytest.mark.asyncio
    async def test_preflight_budget_exceeded_rejects_before_network(self, monkeypatch):
        """If request budget constraint is exceeded by estimated cost, pre-flight aborts with BUDGET_EXCEEDED."""
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-validfakekey1234567890")

        call_occurred = False

        def mock_handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_occurred
            call_occurred = True
            return httpx.Response(200, json={})

        client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
        provider = OpenRouterProvider(http_client=client)

        # Impossibly low budget constraint (e.g. $0.0000000001)
        req = CapabilityRequest(
            capability=CapabilityType.REASONING,
            input_data={"prompt": "Evaluate budget check"},
            requirements=ModelRequirement(
                capability=CapabilityType.REASONING,
                budget_constraint=CostEstimate(estimated_cost="0.0000000001"),
            ),
        )
        result = await provider.execute(req)

        assert result.status == CapabilityStatus.FAILED
        assert result.error is not None
        assert result.error.code == AIErrorCode.BUDGET_EXCEEDED
        assert not call_occurred, "Network call should not have occurred when pre-flight budget is exceeded"


# ============================================================================
# 7. Successful Wire Execution & Observability Integration Tests
# ============================================================================

class TestOpenRouterSuccessfulExecutionAndObservability:
    @pytest.mark.asyncio
    async def test_successful_mocked_execution_with_telemetry_trace(self, monkeypatch, tmp_path):
        """
        Executes end-to-end through contracts, verifies structured response,
        records telemetry trace, and verifies zero secret leakage via scan_trace_for_secrets.
        """
        test_key = "sk-or-v1-validfakekey1234567890abcdef1234567890"
        monkeypatch.setenv("OPENROUTER_API_KEY", test_key)

        expected_response = {
            "status": "operational",
            "provider": "openrouter",
            "message": "Development AI provider confirmed operational.",
        }

        def mock_handler(request: httpx.Request) -> httpx.Response:
            auth_header = request.headers.get("Authorization", "")
            assert test_key in auth_header
            return httpx.Response(
                200,
                json={
                    "id": "gen-dev-12345",
                    "model": "google/gemini-2.0-flash-001",
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": json.dumps(expected_response),
                            },
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 15,
                        "completion_tokens": 25,
                        "total_tokens": 40,
                    },
                },
            )

        client = httpx.AsyncClient(transport=httpx.MockTransport(mock_handler))
        provider = OpenRouterProvider(http_client=client)

        db_file = tmp_path / "openrouter_trace.db"
        engine = DatabaseEngine(f"sqlite:///{db_file}")
        trace_repo = SQLTraceRepository(engine=engine)

        tracer = AITracer(
            run_id="run_openrouter_dev_01",
            workspace_id="ws_dev",
            trace_id="trc_openrouter_001",
            repository=trace_repo,
        )

        req = CapabilityRequest(
            capability=CapabilityType.REASONING,
            input_data={
                "prompt": "Return a short structured confirmation that the development AI provider is operational.",
                "structured": True,
            },
        )

        with tracer.start_span("openrouter_smoke_call", SpanType.PROVIDER_CALL) as span:
            span.set_capability("REASONING")
            span.set_model("openrouter", "google/gemini-2.0-flash-001")

            result = await provider.execute(req)

            assert result.status == CapabilityStatus.SUCCESS
            assert result.output_data is not None
            assert result.output_data["structured"] == expected_response
            assert result.usage.total_tokens == 40
            assert result.provenance.provider_id == "openrouter"

            # Record telemetry in span
            span.set_tokens(result.usage.input_tokens, result.usage.output_tokens)
            span.set_cost(Decimal("0.000015"), Decimal("0.000015"))
            span.set_attribute("provider_status", "operational")

        # Reload persisted trace and verify telemetry and secret cleanliness
        reloaded_trace = trace_repo.get_trace("trc_openrouter_001")
        assert reloaded_trace is not None
        assert len(reloaded_trace.spans) == 1
        span_rec = reloaded_trace.spans[0]

        assert span_rec.provider == "openrouter"
        assert span_rec.model == "google/gemini-2.0-flash-001"
        assert span_rec.capability == "REASONING"
        assert span_rec.input_tokens == 15
        assert span_rec.output_tokens == 25
        assert span_rec.status == "SUCCESS"

        # Secret scan verification: MUST BE CLEAN
        secret_violations = scan_trace_for_secrets(span_rec)
        assert secret_violations == [], f"Secret leakage in telemetry span: {secret_violations}"
        assert test_key not in str(span_rec.model_dump())
