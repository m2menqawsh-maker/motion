"""URL and Network Request Safety Policy (SEC-009).

Guarantees SSRF protection and strict resource URI validation:
- Only HTTP and HTTPS schemes are permitted for external asset references.
- file://, ftp://, gopher://, javascript:, data: schemes are strictly prohibited.
- Loopback addresses (localhost, 127.0.0.1, ::1, 0.0.0.0) are blocked.
- Link-local / Cloud metadata service IPs (169.254.169.254) are blocked.
- RFC 1918 Private IPv4 and RFC 4193 Unique Local IPv6 ranges are blocked.
"""
from __future__ import annotations

import ipaddress
from urllib.parse import urlparse


class URLSecurityViolation(Exception):
    """Raised when an external URL violates security confinement boundaries."""
    pass


def validate_safe_url(url: str, allow_private_networks: bool = False) -> str:
    """
    Validates that a URL is safe for external resource fetching and free of SSRF risks.
    
    Returns the cleaned, validated URL string or raises URLSecurityViolation.
    """
    if not isinstance(url, str) or not url.strip():
        raise URLSecurityViolation("URL cannot be empty or non-string.")

    cleaned = url.strip()
    parsed = urlparse(cleaned)

    # 1. Scheme Confinement
    if parsed.scheme.lower() not in ("http", "https"):
        raise URLSecurityViolation(
            f"Prohibited URL scheme '{parsed.scheme}': only 'http' and 'https' are allowed."
        )

    # 2. Hostname Presence
    hostname = parsed.hostname
    if not hostname:
        raise URLSecurityViolation(f"Invalid URL without hostname: '{cleaned}'")

    hostname_lower = hostname.lower().strip("[]")

    # 3. Known Loopback and Internal Aliases
    if hostname_lower in ("localhost", "0.0.0.0", "127.0.0.1", "::1"):
        raise URLSecurityViolation(f"Loopback access prohibited: '{hostname}'")

    # 4. IP-Based Confinement (IPv4 & IPv6)
    try:
        ip = ipaddress.ip_address(hostname_lower)
    except ValueError:
        ip = None

    if ip is not None and not allow_private_networks:
        if ip.is_loopback:
            raise URLSecurityViolation(f"Loopback IP address prohibited: '{ip}'")
        if ip.is_link_local:
            raise URLSecurityViolation(f"Link-local / Cloud metadata IP prohibited: '{ip}'")
        if ip.is_private:
            raise URLSecurityViolation(f"Private network IP address prohibited: '{ip}'")
        if ip.is_reserved:
            raise URLSecurityViolation(f"Reserved IP address prohibited: '{ip}'")
        if ip.is_multicast:
            raise URLSecurityViolation(f"Multicast IP address prohibited: '{ip}'")
        if ip.is_unspecified:
            raise URLSecurityViolation(f"Unspecified IP address prohibited: '{ip}'")

    return cleaned
