"""
tests/ai/budget/test_estimator.py
=================================
Unit tests for deterministic and conservative cost estimation (S27.5).
"""

from datetime import datetime, timezone
from decimal import Decimal
import pytest

from ai.models.types import ModelPricing
from ai.routing.types import WorkloadEstimate
from ai.budget.estimator import BudgetEstimator
from ai.budget.types import CostProfile


@pytest.fixture
def sample_pricing() -> ModelPricing:
    return ModelPricing(
        pricing_version="pricing-v1.0.0",
        valid_from=datetime(2025, 1, 1, tzinfo=timezone.utc),
        currency="USD",
        input_token_price=Decimal("0.000002"),   # $2 per 1M input tokens
        output_token_price=Decimal("0.000010"),  # $10 per 1M output tokens
        audio_minute_price=Decimal("0.05"),
        request_price=Decimal("0.001"),
    )


class TestBudgetEstimator:

    def test_deterministic_cost_estimation_standard(self, sample_pricing):
        workload = WorkloadEstimate(
            input_tokens=1000,
            output_tokens=500,
            request_count=1,
        )
        # Expected:
        # Request: 0.001
        # Input: 1000 * 0.000002 = 0.002
        # Output: 500 * 0.000010 = 0.005
        # Total = 0.008
        cost = BudgetEstimator.estimate_cost(pricing=sample_pricing, workload=workload)
        assert cost == Decimal("0.008000")

    def test_conservative_estimation_with_missing_output_tokens(self, sample_pricing):
        # Workload specifies only input tokens; output is unconstrained
        workload = WorkloadEstimate(
            input_tokens=1000,
            request_count=1,
        )
        # Default bound = 4096 tokens
        # Base cost: 0.001 (req) + 0.002 (in) + 4096 * 0.000010 (out = 0.04096) = 0.043960
        # STANDARD profile headroom = 1.05 -> 0.043960 * 1.05 = 0.046158
        estimate = BudgetEstimator.estimate_conservative_cost(
            pricing=sample_pricing,
            workload=workload,
            cost_profile=CostProfile.STANDARD,
            default_output_tokens=4096,
        )
        assert estimate.estimated_cost == Decimal("0.043960")
        assert estimate.reserved_cost == Decimal("0.046158")
        assert estimate.currency == "USD"
        assert estimate.pricing_version == "pricing-v1.0.0"

    def test_cost_profile_multipliers(self, sample_pricing):
        workload = WorkloadEstimate(input_tokens=1000, output_tokens=1000, request_count=1)
        # Base cost = 0.001 + 0.002 + 0.010 = 0.013000

        est_econ = BudgetEstimator.estimate_conservative_cost(
            pricing=sample_pricing, workload=workload, cost_profile=CostProfile.ECONOMY
        )
        assert est_econ.reserved_cost == Decimal("0.013000")  # 1.0x

        est_prem = BudgetEstimator.estimate_conservative_cost(
            pricing=sample_pricing, workload=workload, cost_profile=CostProfile.PREMIUM
        )
        assert est_prem.reserved_cost == Decimal("0.014300")  # 1.10x

        est_max = BudgetEstimator.estimate_conservative_cost(
            pricing=sample_pricing, workload=workload, cost_profile=CostProfile.MAXIMUM
        )
        assert est_max.reserved_cost == Decimal("0.015600")  # 1.20x

    def test_missing_pricing_raises_error(self):
        with pytest.raises(ValueError, match="ModelPricing schedule is missing"):
            BudgetEstimator.estimate_conservative_cost(pricing=None)

    def test_safe_minimum_ceiling_for_billable_model(self):
        pricing = ModelPricing(
            pricing_version="flat-v1",
            valid_from=datetime(2025, 1, 1, tzinfo=timezone.utc),
            currency="USD",
            output_token_price=Decimal("0.000010"),
        )
        workload = WorkloadEstimate(input_tokens=0, output_tokens=0, request_count=1)
        est = BudgetEstimator.estimate_conservative_cost(
            pricing=pricing,
            workload=workload,
            default_output_tokens=0,
        )
        # Never $0 for a billable model
        assert est.reserved_cost > Decimal("0")
