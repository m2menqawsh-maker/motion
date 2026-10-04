"""
ai/cost/__init__.py
===================
Canonical Cost Observability, Attribution, and Efficiency Hardening package (S28-08C).
"""

from __future__ import annotations

from ai.cost.accounting import (
    CreativeCostEstimator,
    TokenAccounting,
)
from ai.cost.analyzer import (
    CreativeEfficiencyAnalyzer,
)
from ai.cost.baseline import (
    CANONICAL_EFFICIENCY_BASELINES,
    FormatBaseline,
    get_efficiency_baseline,
)
from ai.cost.collector import (
    CreativeUsageCollector,
)
from ai.cost.errors import (
    CostObservabilityError,
    PricingNotFoundError,
    TenantAuthorizationError,
)

__all__ = [
    "CANONICAL_EFFICIENCY_BASELINES",
    "CostObservabilityError",
    "CreativeCostEstimator",
    "CreativeEfficiencyAnalyzer",
    "CreativeUsageCollector",
    "FormatBaseline",
    "PricingNotFoundError",
    "TenantAuthorizationError",
    "TokenAccounting",
    "get_efficiency_baseline",
]
