"""
tests/ai/models/test_models.py
==============================
Verification suite for S27.3 Model Registry and Pricing Structures.

Invariants:
- All models reference valid registered providers and capabilities.
- Pricing strictly rejects floating point numbers in favor of Decimal.
- Pricing timestamps are timezone-aware.
- Unknown provider or capability references fail registration immediately.
- Duplicate models trigger DuplicateModelError.
- Registry is deterministic and frozen.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import pytest
from pydantic import ValidationError

from ai.contracts.common import CapabilityType, QualityTarget
from ai.capabilities.types import CapabilityPrivacyClass
from ai.capabilities import UnknownCapabilityError
from ai.providers import UnknownProviderError
from ai.models import (
    CANONICAL_MODELS_LIST,
    CostTier,
    DuplicateModelError,
    LatencyTier,
    ModelDefinition,
    ModelPricing,
    ModelRegistry,
    UnknownModelError,
    create_empty_model_registry,
    get_model_registry,
)


class TestModelRegistry:

    def test_canonical_models_registered(self):
        """Verifies that all canonical reference models are registered."""
        registry = get_model_registry()
        assert len(registry) >= 9
        for m in CANONICAL_MODELS_LIST:
            assert registry.exists(m.model_id)
            model_defn = registry.get(m.model_id)
            assert model_defn.provider_id == m.provider_id
            assert len(model_defn.capabilities) >= 1

    def test_duplicate_model_rejected(self):
        """Attempting to register a model with an existing ID raises DuplicateModelError."""
        reg = create_empty_model_registry()
        m1 = ModelDefinition(
            model_id="dup-model",
            provider_id="openai",
            display_name="Duplicate Model",
            capabilities=[CapabilityType.TEXT_GENERATION],
            quality_profile=QualityTarget.STANDARD,
            cost_profile=CostTier.LOW,
            latency_profile=LatencyTier.FAST,
            reliability=0.99,
        )
        m2 = ModelDefinition(
            model_id="dup-model",
            provider_id="openai",
            display_name="Duplicate Model Copy",
            capabilities=[CapabilityType.TEXT_GENERATION],
            quality_profile=QualityTarget.STANDARD,
            cost_profile=CostTier.LOW,
            latency_profile=LatencyTier.FAST,
            reliability=0.99,
        )
        reg.register(m1)
        with pytest.raises(DuplicateModelError) as exc_info:
            reg.register(m2)
        assert "dup-model" in str(exc_info.value)

    def test_unknown_model_rejected(self):
        """Querying an unregistered model raises UnknownModelError."""
        registry = get_model_registry()
        with pytest.raises(UnknownModelError) as exc_info:
            registry.get("non-existent-model-xyz")
        assert "non-existent-model-xyz" in str(exc_info.value)
        assert not registry.exists("non-existent-model-xyz")

    def test_unknown_provider_reference_rejected(self):
        """Registering a model referencing an unregistered provider raises UnknownProviderError."""
        reg = create_empty_model_registry()
        m = ModelDefinition(
            model_id="orphan-model",
            provider_id="phantom-provider",
            display_name="Orphan Model",
            capabilities=[CapabilityType.REASONING],
            quality_profile=QualityTarget.HIGH,
            cost_profile=CostTier.MEDIUM,
            latency_profile=LatencyTier.FAST,
            reliability=0.99,
        )
        with pytest.raises(UnknownProviderError) as exc_info:
            reg.register(m)
        assert "phantom-provider" in str(exc_info.value)

    def test_unknown_capability_reference_rejected(self):
        """Registering a model declaring an invalid capability raises validation error."""
        # Pydantic validates enum members for capabilities
        with pytest.raises(ValidationError):
            ModelDefinition(
                model_id="invalid-cap-model",
                provider_id="openai",
                display_name="Invalid Cap Model",
                capabilities=["UNREGISTERED_SUPER_POWER"],  # type: ignore
                quality_profile=QualityTarget.HIGH,
                cost_profile=CostTier.LOW,
                latency_profile=LatencyTier.FAST,
                reliability=0.99,
            )

    def test_enabled_disabled_filtering(self):
        """Disabled models are tracked properly and filterable."""
        reg = create_empty_model_registry()
        m_enabled = ModelDefinition(
            model_id="active-model",
            provider_id="openai",
            display_name="Active",
            capabilities=[CapabilityType.TEXT_GENERATION],
            quality_profile=QualityTarget.STANDARD,
            cost_profile=CostTier.LOW,
            latency_profile=LatencyTier.FAST,
            reliability=0.99,
            enabled=True,
        )
        m_disabled = ModelDefinition(
            model_id="inactive-model",
            provider_id="openai",
            display_name="Inactive",
            capabilities=[CapabilityType.TEXT_GENERATION],
            quality_profile=QualityTarget.STANDARD,
            cost_profile=CostTier.LOW,
            latency_profile=LatencyTier.FAST,
            reliability=0.99,
            enabled=False,
        )
        reg.register(m_enabled)
        reg.register(m_disabled)

        all_models = reg.list()
        assert len(all_models) == 2

        enabled_only = reg.list(enabled_only=True)
        assert len(enabled_only) == 1
        assert enabled_only[0].model_id == "active-model"

    def test_frozen_model_registry(self):
        """Frozen model registry blocks mutation."""
        registry = get_model_registry()
        assert registry.is_frozen
        m = ModelDefinition(
            model_id="new-model",
            provider_id="openai",
            display_name="New",
            capabilities=[CapabilityType.REASONING],
            quality_profile=QualityTarget.HIGH,
            cost_profile=CostTier.LOW,
            latency_profile=LatencyTier.FAST,
            reliability=0.99,
        )
        with pytest.raises(RuntimeError) as exc_info:
            registry.register(m)
        assert "frozen" in str(exc_info.value)


class TestModelPricing:

    def test_pricing_decimal_safety(self):
        """Pricing requires Decimal and actively rejects float inputs."""
        tz_now = datetime.now(timezone.utc)
        
        # Valid Decimal pricing
        pricing = ModelPricing(
            pricing_version="v1",
            valid_from=tz_now,
            input_token_price=Decimal("0.000005"),
            output_token_price=Decimal("0.000015"),
        )
        assert pricing.input_token_price == Decimal("0.000005")

        # Float pricing must be strictly rejected
        with pytest.raises(ValidationError) as exc_info:
            ModelPricing(
                pricing_version="v1",
                valid_from=tz_now,
                input_token_price=0.000005,  # float!
            )
        assert "Float values are strictly forbidden" in str(exc_info.value)

    def test_pricing_requires_timezone_aware_datetime(self):
        """Pricing valid_from datetime must be timezone-aware."""
        naive_dt = datetime(2026, 9, 30, 12, 0, 0)  # no tzinfo!
        with pytest.raises(ValidationError) as exc_info:
            ModelPricing(
                pricing_version="v1",
                valid_from=naive_dt,
                input_token_price=Decimal("0.01"),
            )
        assert "timezone-aware" in str(exc_info.value)

    def test_model_vs_deployment_support(self):
        """ModelDefinition allows explicit deployment_id and region without architectural restriction."""
        tz_now = datetime.now(timezone.utc)
        model = ModelDefinition(
            model_id="llama-3-local-us",
            provider_id="local",
            display_name="Llama 3 Local US Cluster",
            capabilities=[CapabilityType.TEXT_GENERATION],
            quality_profile=QualityTarget.HIGH,
            cost_profile=CostTier.FREE,
            latency_profile=LatencyTier.FAST,
            reliability=0.999,
            region="us-east-1",
            deployment_id="cluster-node-04",
        )
        assert model.region == "us-east-1"
        assert model.deployment_id == "cluster-node-04"
