"""
tests/core/test_suite_hermetic_dns.py
=====================================
Regression test for Blocker 1:
Ensures suite-wide hermetic mock DNS resolution covers *.example.com and *.example.org
outside tests/security without network dependencies, while nonexistent subdomains fail closed.
"""

import socket
import pytest
from scripts.core.security.url_policy import validate_safe_url, URLSecurityViolation


def test_hermetic_dns_resolution_for_example_domains_outside_security_dir():
    """Verify *.example.com and *.example.org resolve hermetically outside tests/security/."""
    ips = socket.getaddrinfo("assets.example.com", 80)
    assert any(ip[4][0] == "93.184.216.34" for ip in ips)

    ips_org = socket.getaddrinfo("test.example.org", 443)
    assert any(ip[4][0] == "93.184.216.34" for ip in ips_org)

    # validate_safe_url should pass without network access
    assert validate_safe_url("https://assets.example.com/logo.png") == "https://assets.example.com/logo.png"


def test_nonexistent_subdomain_still_fails_closed_outside_security_dir():
    """Verify subdomains designated as nonexistent fail closed (do not resolve)."""
    with pytest.raises(URLSecurityViolation, match="DNS resolution failed"):
        validate_safe_url("http://fake-nonexistent-subdomain.example.com/asset.mp4")
