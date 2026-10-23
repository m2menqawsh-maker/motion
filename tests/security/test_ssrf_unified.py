"""
tests/security/test_ssrf_unified.py
===================================
Authoritative Unified SSRF Security Test Suite (SEC-009 / Part 2 Item 1).

Validates:
1. Strict fail-closed rejection of obfuscated IP literals:
   - Decimal dword (2130706433)
   - Hexadecimal (0x7f000001)
   - Octal (0177.0.0.1)
   - Mixed hex/decimal (0x7f.0.0.1)
2. Fail-closed dual-stack DNS resolution against rebinding / wildcard domains:
   - localtest.me -> 127.0.0.1 / ::1
   - 169.254.169.254.nip.io -> 169.254.169.254
   - metadata.google.internal -> NXDOMAIN / fail-closed
3. IPv6 loopback, link-local, and mapped addresses:
   - [::1], [fe80::1], [::ffff:127.0.0.1]
4. Private, reserved, CGNAT, multicast, and unspecified ranges:
   - 0.0.0.0, 10.0.0.1, 172.16.0.1, 192.168.1.1, 169.254.1.1, 100.64.0.1, 224.0.0.1
5. Userinfo evasion vectors:
   - http://evil@127.0.0.1/, http://127.0.0.1#@good.com
6. Forbidden non-HTTP schemes:
   - file:, gopher:, ftp:, data:
7. Single Authority Parity:
   - Verifies that url_policy.py, ai/security/ssrf.py, and safe_downloader.py all
     delegate directly to scripts.core.security.ssrf_guard.
"""

from unittest.mock import patch
import pytest

from scripts.core.security.ssrf_guard import (
    SSRFSecurityViolation,
    validate_url_security,
    validate_safe_url as ssrf_guard_validate_safe_url,
    is_ip_disallowed,
    parse_numeric_ipv4,
)
from scripts.core.security.url_policy import (
    validate_safe_url as url_policy_validate_safe_url,
    URLSecurityViolation,
)
from ai.security.ssrf import (
    SSRFProtection,
    SSRFValidationError,
)
from ai.acquisition.safe_downloader import (
    assert_safe_url,
    UnsafeDownloadSourceError,
)

# Canonical list of URLs that MUST be rejected by all filters
PROHIBITED_SSRF_URLS = [
    # 5 targets that previously slipped through
    "http://2130706433/",
    "http://0x7f000001/",
    "http://localtest.me/",
    "http://169.254.169.254.nip.io/",
    "http://metadata.google.internal/",
    # Octal & mixed representation
    "http://0177.0.0.1/",
    "http://0x7f.0.0.1/",
    # IPv6 loopback & mapped
    "http://[::1]/",
    "http://[::ffff:127.0.0.1]/",
    "http://::ffff:127.0.0.1/",
    # Unspecified & zero network
    "http://0.0.0.0/",
    # RFC 1918 private subnets
    "http://10.0.0.1/",
    "http://172.16.0.1/",
    "http://192.168.1.1/",
    # Link-local & cloud metadata
    "http://169.254.1.1/",
    "http://169.254.169.254/",
    "http://[fe80::1]/",
    # Carrier-grade NAT (100.64.0.0/10)
    "http://100.64.0.1/",
    # Multicast
    "http://224.0.0.1/",
    # Deceptive userinfo
    "http://evil@127.0.0.1/",
    "http://127.0.0.1#@good.com",
    # Prohibited schemes
    "file:///etc/passwd",
    "gopher://127.0.0.1/",
    "ftp://example.com/",
    "data:text/plain;base64,SGVsbG8=",
]


class TestUnifiedSSRFGuard:
    """Verifies that ssrf_guard.py rejects all malicious, internal, or evasive URLs."""

    @pytest.mark.parametrize("url", PROHIBITED_SSRF_URLS)
    def test_ssrf_guard_rejects_prohibited_urls(self, url: str):
        with pytest.raises(SSRFSecurityViolation):
            validate_url_security(url, require_dns_resolution=True)

    @pytest.mark.parametrize("url", PROHIBITED_SSRF_URLS)
    def test_url_policy_wrapper_rejects_prohibited_urls(self, url: str):
        with pytest.raises(URLSecurityViolation):
            url_policy_validate_safe_url(url)

    @pytest.mark.parametrize("url", PROHIBITED_SSRF_URLS)
    def test_ai_ssrf_wrapper_rejects_prohibited_urls(self, url: str):
        with pytest.raises(SSRFValidationError):
            SSRFProtection.validate_url(url)

    @pytest.mark.parametrize("url", PROHIBITED_SSRF_URLS)
    def test_safe_downloader_wrapper_rejects_prohibited_urls(self, url: str):
        with pytest.raises(UnsafeDownloadSourceError):
            assert_safe_url(url)


class TestUnifiedSSRFAllowedPublicURLs:
    """Verifies that legitimate public URLs resolve and pass validation."""

    def test_allowed_public_url_example_com(self):
        cleaned, resolved_ips = validate_url_security("https://example.com/asset.png")
        assert cleaned == "https://example.com/asset.png"
        assert len(resolved_ips) > 0
        for ip in resolved_ips:
            disallowed, _ = is_ip_disallowed(ip)
            assert not disallowed

    def test_allowed_public_ip_literal(self):
        cleaned, resolved_ips = validate_url_security("http://93.184.216.34/logo.jpg")
        assert cleaned == "http://93.184.216.34/logo.jpg"
        assert len(resolved_ips) == 1
        assert str(resolved_ips[0]) == "93.184.216.34"

    def test_nonexistent_subdomain_fails_closed_without_example_com_fallback(self):
        """
        Fix 4 Test:
        Verifies that querying a non-existent subdomain (*.example.com / *.example.org)
        fails closed with SSRFSecurityViolation and NEVER falls back to example.com.
        """
        with pytest.raises(SSRFSecurityViolation, match="DNS resolution failed"):
            validate_url_security("http://fake-nonexistent-subdomain.example.com/asset.mp4", require_dns_resolution=True)


class TestSSRFArchitectureSingleAuthority:
    """Verifies that all three wrapper entrypoints delegate to scripts.core.security.ssrf_guard."""

    def test_url_policy_delegates_to_ssrf_guard(self):
        with patch("scripts.core.security.ssrf_guard.validate_safe_url") as mock_guard:
            mock_guard.return_value = "https://example.com/"
            res = url_policy_validate_safe_url("https://example.com/")
            assert res == "https://example.com/"
            mock_guard.assert_called_once_with("https://example.com/", allow_private_networks=False)

    def test_ai_ssrf_delegates_to_ssrf_guard(self):
        with patch("scripts.core.security.ssrf_guard.validate_url_security") as mock_guard:
            mock_guard.return_value = ("https://example.com/", [])
            res = SSRFProtection.validate_url("https://example.com/")
            assert res == "https://example.com/"
            mock_guard.assert_called_once_with("https://example.com/", require_dns_resolution=True)

    def test_safe_downloader_delegates_to_ssrf_guard(self):
        with patch("scripts.core.security.ssrf_guard.validate_url_security") as mock_guard:
            mock_guard.return_value = ("https://example.com/", [])
            assert_safe_url("https://example.com/")
            mock_guard.assert_called_once_with("https://example.com/", require_dns_resolution=True)
