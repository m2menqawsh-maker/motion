"""
tests/security/test_url_security.py — URL and Network Safety Tests (SEC-009).

Validates:
- Prohibited schemes: file://, ftp://, javascript:, gopher:, data:
- Blocked loopback destinations: localhost, 127.0.0.1, ::1, 0.0.0.0
- Blocked cloud metadata service: 169.254.169.254
- Blocked private RFC 1918 subnets: 10.0.0.1, 192.168.1.1, 172.16.0.1
- Allowed safe public URLs: https://images.unsplash.com/photo-123, http://example.com/asset.png
- Integration with parse_asset_ref in scripts/core/asset_resolution.py
"""
import pytest
from scripts.core.security.url_policy import validate_safe_url, URLSecurityViolation
from scripts.core.asset_resolution import parse_asset_ref, MalformedAssetRefError


class TestURLSecurityPolicy:
    def test_prohibited_file_scheme(self):
        with pytest.raises(URLSecurityViolation, match="Prohibited URL scheme 'file'"):
            validate_safe_url("file:///etc/passwd")

    def test_prohibited_ftp_scheme(self):
        with pytest.raises(URLSecurityViolation, match="Prohibited URL scheme 'ftp'"):
            validate_safe_url("ftp://internal.vault/secret.key")

    def test_prohibited_javascript_scheme(self):
        with pytest.raises(URLSecurityViolation, match="Prohibited URL scheme 'javascript'"):
            validate_safe_url("javascript:alert(1)")

    def test_blocked_localhost(self):
        with pytest.raises(URLSecurityViolation, match="Loopback access prohibited"):
            validate_safe_url("http://localhost:8080/admin")

    def test_blocked_loopback_ipv4(self):
        with pytest.raises(URLSecurityViolation, match="Loopback"):
            validate_safe_url("http://127.0.0.1:8000/metrics")

    def test_blocked_loopback_ipv6(self):
        with pytest.raises(URLSecurityViolation, match="Loopback"):
            validate_safe_url("http://[::1]:8080/")

    def test_blocked_cloud_metadata(self):
        with pytest.raises(URLSecurityViolation, match="Link-local / Cloud metadata IP prohibited"):
            validate_safe_url("http://169.254.169.254/latest/meta-data/")

    def test_blocked_private_subnets(self):
        with pytest.raises(URLSecurityViolation, match="Private network IP address prohibited"):
            validate_safe_url("http://192.168.1.100/video.mp4")

        with pytest.raises(URLSecurityViolation, match="Private network IP address prohibited"):
            validate_safe_url("http://10.0.0.5:9000/asset.jpg")

        with pytest.raises(URLSecurityViolation, match="Private network IP address prohibited"):
            validate_safe_url("http://172.16.1.1/internal.png")

    def test_allowed_public_urls(self):
        url1 = "https://images.unsplash.com/photo-1579783900882-c0d3dad7b119"
        assert validate_safe_url(url1) == url1

        url2 = "http://example.com/assets/sample.mp4"
        assert validate_safe_url(url2) == url2

    def test_asset_resolution_integration_blocks_ssrf(self):
        # file:// scheme rejected
        with pytest.raises(MalformedAssetRefError, match="URL security violation"):
            parse_asset_ref({"kind": "url", "url": "file:///etc/shadow"})

        # Cloud metadata rejected
        with pytest.raises(MalformedAssetRefError, match="URL security violation"):
            parse_asset_ref({"kind": "url", "url": "http://169.254.169.254/secret"})

        # Localhost rejected
        with pytest.raises(MalformedAssetRefError, match="URL security violation"):
            parse_asset_ref({"kind": "url", "url": "http://localhost:3000/internal"})

        # Valid public URL accepted
        valid_ref = parse_asset_ref({"kind": "url", "url": "https://cdn.example.com/logo.png"})
        assert valid_ref.is_url
        assert valid_ref.url == "https://cdn.example.com/logo.png"
