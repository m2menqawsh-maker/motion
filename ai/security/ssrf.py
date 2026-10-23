"""
ai/security/ssrf.py
===================
Server-Side Request Forgery (SSRF) and URL Egress Filter (S27.22 / AI-15).

Thin wrapper delegating to canonical SSRF authority in scripts.core.security.ssrf_guard.
"""

from __future__ import annotations

from typing import Set
from scripts.core.security import ssrf_guard
from scripts.core.security.ssrf_guard import (
    SSRFSecurityViolation,
    BLOCKED_HOSTNAMES as _BLOCKED_HOSTNAMES,
)

# Maintain backward compatibility for callers and exception handlers
SSRFValidationError = SSRFSecurityViolation


class SSRFProtection:
    """
    Evaluates outbound URLs against SSRF policies.
    Delegates to canonical ssrf_guard authority.
    """

    ALLOWED_SCHEMES: Set[str] = {"http", "https"}
    BLOCKED_HOSTNAMES: Set[str] = _BLOCKED_HOSTNAMES

    @classmethod
    def validate_url(cls, url: str, resolve_dns: bool = True) -> str:
        """
        Validates URL for SSRF vulnerabilities.
        Always resolves DNS (fail-closed) to eliminate bypasses and rebinding risks.
        Returns canonical clean URL or raises SSRFValidationError.
        """
        try:
            cleaned, _ = ssrf_guard.validate_url_security(url, require_dns_resolution=True)
            return cleaned
        except SSRFSecurityViolation as e:
            raise SSRFValidationError(str(e)) from e
