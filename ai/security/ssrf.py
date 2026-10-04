"""
ai/security/ssrf.py
===================
Server-Side Request Forgery (SSRF) and URL Egress Filter (S27.22 / AI-15).

Invariants:
- AI components never execute unmediated outbound network requests.
- All media/asset imports must be routed through the dedicated Media Import Service.
- Prohibits loopback (127.0.0.1, localhost, ::1).
- Prohibits cloud metadata addresses (169.254.169.254).
- Prohibits RFC 1918 private subnets (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16).
- Prohibits non-HTTP/HTTPS schemes (e.g. file://, gopher://, dict://, ftp://).
- Fails closed on malformed URLs or DNS resolution pointing to private IPs.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse
from typing import Optional, Set


class SSRFValidationError(Exception):
    """Raised when an egress URL fails SSRF protection rules."""
    pass


class SSRFProtection:
    """
    Evaluates outbound URLs against SSRF policies.
    """

    ALLOWED_SCHEMES: Set[str] = {"http", "https"}
    BLOCKED_HOSTNAMES: Set[str] = {
        "localhost",
        "127.0.0.1",
        "::1",
        "0.0.0.0",
        "metadata.google.internal",
        "169.254.169.254",
    }

    @classmethod
    def validate_url(cls, url: str, resolve_dns: bool = False) -> str:
        """
        Validates URL for SSRF vulnerabilities.
        Returns canonical clean URL or raises SSRFValidationError.
        """
        if not url or not isinstance(url, str):
            raise SSRFValidationError("URL cannot be empty.")

        url_clean = url.strip()
        try:
            parsed = urlparse(url_clean)
        except Exception as e:
            raise SSRFValidationError(f"Malformed URL: {e}")

        # 1. Scheme check
        if not parsed.scheme or parsed.scheme.lower() not in cls.ALLOWED_SCHEMES:
            raise SSRFValidationError(
                f"Prohibited URL scheme '{parsed.scheme}'. Only HTTP and HTTPS are permitted."
            )

        hostname = (parsed.hostname or "").lower()
        if not hostname:
            raise SSRFValidationError("URL missing hostname.")

        # 2. Blocked hostnames check
        if hostname in cls.BLOCKED_HOSTNAMES:
            raise SSRFValidationError(f"Target host '{hostname}' is blocked (loopback/cloud metadata).")

        # 3. IP address evaluation (direct IP literals)
        try:
            ip_obj = ipaddress.ip_address(hostname)
            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_reserved:
                raise SSRFValidationError(
                    f"Direct access to private/reserved IP address '{ip_obj}' is strictly prohibited."
                )
        except ValueError:
            # Not an IP literal, standard domain name
            pass

        # 4. Optional DNS resolution check (prevent DNS rebinding to private IPs)
        if resolve_dns:
            try:
                resolved_ips = socket.gethostbyname_ex(hostname)[2]
                for rip in resolved_ips:
                    ip_obj = ipaddress.ip_address(rip)
                    if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_link_local or ip_obj.is_reserved:
                        raise SSRFValidationError(
                            f"Host '{hostname}' resolves to private IP '{rip}', which is prohibited."
                        )
            except socket.gaierror as e:
                raise SSRFValidationError(f"DNS resolution failure for host '{hostname}': {e}")

        return url_clean
