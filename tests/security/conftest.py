"""
tests/security/conftest.py
==========================
Hermetic test fixtures for offline security testing.
Provides mock DNS resolution for standard RFC 2606 documentation domains
(example.com, cdn.example.com, images.unsplash.com) so the test suite can run
completely offline without internet DNS dependencies.
"""

import socket
import pytest

ORIG_GETADDRINFO = socket.getaddrinfo

# Safe, public IPs for hermetic test domains
HERMETIC_PUBLIC_DNS = {
    "example.com": "93.184.216.34",
    "cdn.example.com": "93.184.216.34",
    "sub.example.com": "93.184.216.34",
    "images.unsplash.com": "151.101.65.181",
}


@pytest.fixture(autouse=True)
def hermetic_security_test_dns(monkeypatch: pytest.MonkeyPatch):
    """
    Autouse fixture ensuring that standard test domains resolve offline to safe public IPs.
    Non-existent subdomains (e.g. fake-nonexistent-subdomain.example.com) will not be in
    HERMETIC_PUBLIC_DNS and thus fail closed.
    """
    def hermetic_getaddrinfo(host, port, *args, **kwargs):
        host_str = host.decode() if isinstance(host, (bytes, bytearray)) else str(host)
        if host_str in HERMETIC_PUBLIC_DNS:
            p = int(port) if port else 0
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (HERMETIC_PUBLIC_DNS[host_str], p))]
        return ORIG_GETADDRINFO(host, port, *args, **kwargs)

    monkeypatch.setattr(socket, "getaddrinfo", hermetic_getaddrinfo)
