"""
tests/ai/routing/test_constraints.py
====================================
Verification suite for Hard Constraints in Model Router (S27.4).

Invariants:
- Hard constraints are non-negotiable binary gates.
- Ineligible models can NEVER be selected as primary or fallback.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import pytest

from ai.contracts.common import CapabilityType, ExecutionClass, PrivacyRequirement, QualityTarget
from ai.contracts.model import ModelRequirement
from ai.contracts.usage import CostEstimate
from ai.capabilities.types import CapabilityPrivacyClass
from ai.providers import ProviderDefinition, ProviderRegistry, create_empty_provider_registry
from ai.models.types import CostTier, LatencyTier, ModelDefinition, ModelPricing
from ai.routing import evaluate_hard_constraints, WorkloadEstimate
from ai.routing.policy import STANDARD_POLICY


@pytest.fixture
def test_registries():
    provider_reg = create_empty_provider_registry()
    provider_reg.register(
        ProviderDefinition(
            provider_id="prov-public",
            display_name="Public Cloud Provider",
            supported_execution_modes=[ExecutionClass.INTERACTIVE],
            privacy_compliance=PrivacyRequirement.PUBLIC_ALLOWED,
            enabled=True,
        )
    )
    provider_reg.register(
        ProviderDefinition(
            provider_id="prov-zero-retention",
            display_name="Zero Retention Provider",
            supported_execution_modes=[ExecutionClass.INTERACTIVE],
            privacy_compliance=PrivacyRequirement.ZERO_DATA_RETENTION,
            enabled=True,
        )
    )
    provider_reg.register(
        ProviderDefinition(
            provider_id="prov-local",
            display_name="Local Compute",
            supported_execution_modes=[ExecutionClass.INTERACTIVE],
            privacy_compliance=PrivacyRequirement.INTERNAL_ONLY,
            enabled=True,
        )
    )
    provider_reg.register(
        ProviderDefinition(
            provider_id="prov-disabled",
            display_name="Disabled Provider",
            supported_execution_modes=[ExecutionClass.INTERACTIVE],
            privacy_compliance=PrivacyRequirement.PUBLIC_ALLOWED,
            enabled=False,
        )
    )
    return provider_reg


class TestHardConstraints:

    def test_disabled_model_rejected(self, test_registries):
        """A disabled model is immediately marked ineligible."""
        model = ModelDefinition(
            model_id="disabled-m1",
            provider_id="prov-public",
            display_name="Disabled Model",
            capabilities=[CapabilityType.REASONING],
            quality_profile=QualityTarget.HIGH,
            cost_profile=CostTier.LOW,
            latency_profile=LatencyTier.FAST,
            reliability=0.99,
            enabled=False,
        )
        req = ModelRequirement(capability=CapabilityType.REASONING)
        eligible, reasons, _ = evaluate_hard_constraints(model, req, test_registries)
        assert not eligible
        assert any("disabled in registry" in r for r in reasons)

    def test_disabled_provider_rejected(self, test_registries):
        """A model hosted by a disabled provider is marked ineligible."""
        model = ModelDefinition(
            model_id="orphan-m",
            provider_id="prov-disabled",
            display_name="Model with Disabled Provider",
            capabilities=[CapabilityType.REASONING],
            quality_profile=QualityTarget.HIGH,
            cost_profile=CostTier.LOW,
            latency_profile=LatencyTier.FAST,
            reliability=0.99,
            enabled=True,
        )
        req = ModelRequirement(capability=CapabilityType.REASONING)
        eligible, reasons, _ = evaluate_hard_constraints(model, req, test_registries)
        assert not eligible
        assert any("currently disabled" in r for r in reasons)

    def test_unsupported_capability_rejected(self, test_registries):
        """Model lacking requested capability is strictly ineligible."""
        model = ModelDefinition(
            model_id="vision-only-m",
            provider_id="prov-public",
            display_name="Vision Model",
            capabilities=[CapabilityType.VISION],
            quality_profile=QualityTarget.ULTRA,
            cost_profile=CostTier.FREE,
            latency_profile=LatencyTier.REALTIME,
            reliability=0.999,
            enabled=True,
        )
        req = ModelRequirement(capability=CapabilityType.SPEECH_TO_TEXT)
        eligible, reasons, _ = evaluate_hard_constraints(model, req, test_registries)
        assert not eligible
        assert any("does not support requested capability" in r for r in reasons)

    def test_privacy_internal_only_rejected_on_public_cloud(self, test_registries):
        """INTERNAL_ONLY requirement rejects public cloud models and non-local models."""
        public_model = ModelDefinition(
            model_id="cloud-llm",
            provider_id="prov-public",
            display_name="Cloud LLM",
            capabilities=[CapabilityType.TEXT_GENERATION],
            quality_profile=QualityTarget.ULTRA,
            cost_profile=CostTier.LOW,
            latency_profile=LatencyTier.FAST,
            reliability=0.999,
            privacy_class=CapabilityPrivacyClass.PUBLIC_SAFE,
            enabled=True,
        )
        req = ModelRequirement(
            capability=CapabilityType.TEXT_GENERATION,
            privacy_requirement=PrivacyRequirement.INTERNAL_ONLY,
        )
        eligible, reasons, _ = evaluate_hard_constraints(public_model, req, test_registries)
        assert not eligible
        assert any("INTERNAL_ONLY" in r for r in reasons)

    def test_privacy_zero_data_retention_filtering(self, test_registries):
        """ZERO_DATA_RETENTION requirement rejects providers that only offer standard public terms."""
        public_model = ModelDefinition(
            model_id="standard-cloud",
            provider_id="prov-public",
            display_name="Standard Cloud",
            capabilities=[CapabilityType.TEXT_GENERATION],
            quality_profile=QualityTarget.HIGH,
            cost_profile=CostTier.LOW,
            latency_profile=LatencyTier.FAST,
            reliability=0.99,
            enabled=True,
        )
        zdr_model = ModelDefinition(
            model_id="zdr-cloud",
            provider_id="prov-zero-retention",
            display_name="ZDR Cloud",
            capabilities=[CapabilityType.TEXT_GENERATION],
            quality_profile=QualityTarget.HIGH,
            cost_profile=CostTier.LOW,
            latency_profile=LatencyTier.FAST,
            reliability=0.99,
            enabled=True,
        )
        req = ModelRequirement(
            capability=CapabilityType.TEXT_GENERATION,
            privacy_requirement=PrivacyRequirement.ZERO_DATA_RETENTION,
        )
        pub_eligible, pub_reasons, _ = evaluate_hard_constraints(public_model, req, test_registries)
        zdr_eligible, zdr_reasons, _ = evaluate_hard_constraints(zdr_model, req, test_registries)

        assert not pub_eligible
        assert any("zero data retention" in r for r in pub_reasons)
        assert zdr_eligible
        assert len(zdr_reasons) == 0

    def test_language_hard_mismatch_rejected(self, test_registries):
        """Model supporting only English rejects Arabic language requirement."""
        en_model = ModelDefinition(
            model_id="en-stt",
            provider_id="prov-public",
            display_name="English STT",
            capabilities=[CapabilityType.SPEECH_TO_TEXT],
            quality_profile=QualityTarget.HIGH,
            cost_profile=CostTier.LOW,
            latency_profile=LatencyTier.FAST,
            reliability=0.99,
            languages=["en"],
            enabled=True,
        )
        ar_model = ModelDefinition(
            model_id="ar-stt",
            provider_id="prov-public",
            display_name="Multilingual STT",
            capabilities=[CapabilityType.SPEECH_TO_TEXT],
            quality_profile=QualityTarget.HIGH,
            cost_profile=CostTier.LOW,
            latency_profile=LatencyTier.FAST,
            reliability=0.99,
            languages=["ar", "en"],
            enabled=True,
        )
        req = ModelRequirement(
            capability=CapabilityType.SPEECH_TO_TEXT,
            language="ar",
        )
        en_eligible, en_reasons, _ = evaluate_hard_constraints(en_model, req, test_registries)
        ar_eligible, ar_reasons, _ = evaluate_hard_constraints(ar_model, req, test_registries)

        assert not en_eligible
        assert any("do not satisfy required language" in r for r in en_reasons)
        assert ar_eligible

    def test_required_feature_filtering(self, test_registries):
        """Model lacking required structured output or streaming is marked ineligible."""
        basic_model = ModelDefinition(
            model_id="basic-model",
            provider_id="prov-public",
            display_name="Basic Model",
            capabilities=[CapabilityType.TEXT_GENERATION],
            quality_profile=QualityTarget.STANDARD,
            cost_profile=CostTier.LOW,
            latency_profile=LatencyTier.FAST,
            reliability=0.99,
            supports_structured_output=False,
            supports_streaming=False,
            enabled=True,
        )
        req = ModelRequirement(
            capability=CapabilityType.TEXT_GENERATION,
            required_features=["structured_output", "streaming"],
        )
        eligible, reasons, _ = evaluate_hard_constraints(basic_model, req, test_registries)
        assert not eligible
        assert any("structured JSON" in r for r in reasons)
        assert any("streaming" in r for r in reasons)

    def test_budget_hard_ceiling_rejected(self, test_registries):
        """Model exceeding hard budget ceiling is marked ineligible."""
        now_tz = datetime.now(timezone.utc)
        expensive_model = ModelDefinition(
            model_id="expensive-model",
            provider_id="prov-public",
            display_name="Expensive Model",
            capabilities=[CapabilityType.TEXT_GENERATION],
            quality_profile=QualityTarget.ULTRA,
            cost_profile=CostTier.HIGH,
            latency_profile=LatencyTier.FAST,
            reliability=0.999,
            enabled=True,
            pricing=ModelPricing(
                pricing_version="v1",
                valid_from=now_tz,
                input_token_price=Decimal("0.001"),
                output_token_price=Decimal("0.002"),
            ),
        )
        # Workload: 1000 input, 1000 output -> cost = $1.0 + $2.0 = $3.0
        workload = WorkloadEstimate(input_tokens=1000, output_tokens=1000)
        req = ModelRequirement(
            capability=CapabilityType.TEXT_GENERATION,
            budget_constraint=CostEstimate(estimated_cost=Decimal("0.50")),
        )
        eligible, reasons, cost = evaluate_hard_constraints(
            expensive_model, req, test_registries, workload=workload, policy=STANDARD_POLICY
        )
        assert not eligible
        assert cost == Decimal("3.000000")
        assert any("exceeds hard budget ceiling" in r for r in reasons)
