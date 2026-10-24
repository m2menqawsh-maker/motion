"""URL and Network Request Safety Policy (SEC-009).

Thin wrapper delegating to canonical SSRF authority in scripts.core.security.ssrf_guard.
"""
from __future__ import annotations

from scripts.core.security import ssrf_guard
from scripts.core.security.ssrf_guard import SSRFSecurityViolation

# Maintain backward compatibility for existing callers and exception handlers
URLSecurityViolation = SSRFSecurityViolation


def validate_safe_url(url: str, allow_private_networks: bool = False) -> str:
    """
    Validates that a URL is safe for external resource fetching and free of SSRF risks.
    Delegates to authoritative ssrf_guard implementation.
    """
    return ssrf_guard.validate_safe_url(url, allow_private_networks=allow_private_networks)
