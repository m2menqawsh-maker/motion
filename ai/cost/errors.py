"""
ai/cost/errors.py
=================
Exceptions for Creative Cost Observability and Efficiency Hardening (S28-08C).
"""

from __future__ import annotations


class CostObservabilityError(Exception):
    """Base exception for all cost observability errors."""
    pass


class TenantAuthorizationError(CostObservabilityError):
    """Raised when an actor attempts to access or aggregate cross-tenant cost/usage data."""
    pass


class PricingNotFoundError(CostObservabilityError):
    """Raised when cost estimation is requested for an unregistered model or missing rate card."""
    pass
