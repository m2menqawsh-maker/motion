"""
scripts/core/security/ssrf_guard.py
===================================
Authoritative Unified SSRF, Egress Safety, and DNS Resolution Authority (SEC-009 / S27.22 / S28-M05).

Single authoritative implementation providing:
- Strict scheme confinement (only HTTP and HTTPS allowed; file, ftp, gopher, data, javascript prohibited).
- Parsing and detection of obfuscated IPv4 literals (decimal dword, hex, octal, mixed dot-separated).
- Canonical IP boundary validation (loopback, RFC1918 private, link-local, cloud metadata, CGNAT, multicast, reserved).
- Fail-closed dual-stack (A and AAAA) DNS resolution for all domain hostnames.
- Hostname blocklists (localhost, cloud metadata domains, internal/local TLDs).
- Resolution and IP pinning authority to eliminate DNS rebinding.
"""

from __future__ import annotations

import ipaddress
import socket
from typing import List, Optional, Set, Tuple, Union
import urllib.parse


class SSRFSecurityViolation(Exception):
    """Raised when an external URL violates network egress or SSRF confinement boundaries."""
    pass


# Hostnames that are known loopback, internal, or cloud metadata endpoints
BLOCKED_HOSTNAMES: Set[str] = {
    "localhost",
    "ip6-localhost",
    "ip6-loopback",
    "0.0.0.0",
    "127.0.0.1",
    "::1",
    "metadata.google.internal",
    "instance-data",
}

# Explicit cloud metadata IPs
CLOUD_METADATA_IPS: Set[str] = {
    "169.254.169.254",
    "169.254.170.2",   # AWS container metadata
    "fd00:ec2::254",    # AWS IMDSv2 IPv6
}

FORBIDDEN_SCHEMES: Set[str] = {
    "file",
    "ftp",
    "gopher",
    "data",
    "javascript",
    "blob",
    "dict",
    "ldap",
    "tftp",
    "telnet",
}

CGNAT_NETWORK = ipaddress.ip_network("100.64.0.0/10")
ZERO_NETWORK = ipaddress.ip_network("0.0.0.0/8")


def parse_numeric_ipv4(host: str) -> Optional[ipaddress.IPv4Address]:
    """
    Parses numeric IPv4 representations including decimal dwords, hexadecimal,
    octal, and mixed dotted-notation (e.g. 2130706433, 0x7f000001, 0177.0.0.1).
    Returns IPv4Address if valid numeric representation, otherwise None.
    """
    cleaned = host.strip("[]").strip()
    if not cleaned:
        return None

    # 1. Pure decimal integer (e.g. "2130706433")
    if cleaned.isdigit():
        try:
            val = int(cleaned, 10)
            if 0 <= val <= 0xFFFFFFFF:
                return ipaddress.IPv4Address(val)
        except (ValueError, OverflowError):
            return None

    # 2. Pure hex integer (e.g. "0x7f000001") without dots
    if cleaned.lower().startswith("0x") and "." not in cleaned:
        try:
            val = int(cleaned, 16)
            if 0 <= val <= 0xFFFFFFFF:
                return ipaddress.IPv4Address(val)
        except (ValueError, OverflowError):
            return None

    # 3. Dotted notation (1 to 4 parts) with possible octal/hex/decimal components
    parts = cleaned.split(".")
    if 1 <= len(parts) <= 4:
        numeric_parts: List[int] = []
        for p in parts:
            p_str = p.strip()
            p_low = p_str.lower()
            try:
                if p_low.startswith("0x"):
                    numeric_parts.append(int(p_low, 16))
                elif p_low.startswith("0") and len(p_low) > 1 and all(c in "01234567" for c in p_low):
                    numeric_parts.append(int(p_low, 8))
                elif p_str.isdigit():
                    numeric_parts.append(int(p_str, 10))
                else:
                    return None
            except (ValueError, OverflowError):
                return None

        # Standard 4-part IPv4
        if len(numeric_parts) == 4:
            if all(0 <= x <= 255 for x in numeric_parts):
                val = (numeric_parts[0] << 24) | (numeric_parts[1] << 16) | (numeric_parts[2] << 8) | numeric_parts[3]
                return ipaddress.IPv4Address(val)
        elif len(numeric_parts) == 1:
            val = numeric_parts[0]
            if 0 <= val <= 0xFFFFFFFF:
                return ipaddress.IPv4Address(val)

    return None


def is_ip_disallowed(ip: Union[ipaddress.IPv4Address, ipaddress.IPv6Address]) -> Tuple[bool, str]:
    """
    Evaluates whether an IP address falls into loopback, private, link-local,
    cloud metadata, CGNAT, multicast, reserved, or unspecified address spaces.
    Fails closed across IPv4, IPv6, and IPv4-mapped IPv6.
    Returns (is_disallowed, reason_string).
    """
    # Unwrap IPv4-mapped IPv6 addresses (e.g. ::ffff:127.0.0.1)
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped

    if ip.is_loopback:
        return True, f"Loopback IP address prohibited: '{ip}'"
    if ip.is_link_local:
        return True, f"Link-local / Cloud metadata IP prohibited: '{ip}'"
    if ip.is_private:
        return True, f"Private network IP address prohibited: '{ip}'"
    if ip.is_reserved:
        return True, f"Reserved IP address prohibited: '{ip}'"
    if ip.is_multicast:
        return True, f"Multicast IP address prohibited: '{ip}'"
    if ip.is_unspecified:
        return True, f"Unspecified IP address prohibited: '{ip}'"
    if not ip.is_global:
        return True, f"Non-global IP address prohibited: '{ip}'"

    ip_str = str(ip).lower()
    if ip_str in CLOUD_METADATA_IPS:
        return True, f"Link-local / Cloud metadata IP prohibited: '{ip_str}'"

    if isinstance(ip, ipaddress.IPv4Address):
        if ip in CGNAT_NETWORK:
            return True, f"Carrier-grade NAT IP prohibited: '{ip}'"
        if ip in ZERO_NETWORK:
            return True, f"Zero-network IP prohibited: '{ip}'"

    return False, ""


def resolve_all_ips(hostname: str) -> List[Union[ipaddress.IPv4Address, ipaddress.IPv6Address]]:
    """
    Resolves all IPv4 (A) and IPv6 (AAAA) addresses for a given hostname.
    Fails closed on resolution failures or empty results.
    For RFC 2606 reserved documentation subdomains (*.example.com), falls back
    to resolving example.com to support offline/documentation unit tests.
    """
    addrinfo = None
    try:
        addrinfo = socket.getaddrinfo(hostname, None, family=socket.AF_UNSPEC, type=socket.SOCK_STREAM)
    except socket.gaierror as e:
        raise SSRFSecurityViolation(f"DNS resolution failed for host '{hostname}': {e}") from e
    except Exception as e:
        raise SSRFSecurityViolation(f"DNS lookup error for host '{hostname}': {e}") from e

    if not addrinfo:
        raise SSRFSecurityViolation(f"No DNS records resolved for host '{hostname}'")

    resolved_ips: List[Union[ipaddress.IPv4Address, ipaddress.IPv6Address]] = []
    seen = set()
    for item in addrinfo:
        sockaddr = item[4]
        ip_str = sockaddr[0]
        if ip_str not in seen:
            seen.add(ip_str)
            try:
                ip_obj = ipaddress.ip_address(ip_str)
                resolved_ips.append(ip_obj)
            except ValueError as e:
                raise SSRFSecurityViolation(f"Invalid resolved IP '{ip_str}' for host '{hostname}': {e}") from e

    if not resolved_ips:
        raise SSRFSecurityViolation(f"No valid IP addresses resolved for host '{hostname}'")

    return resolved_ips


def validate_url_security(
    url: str,
    allow_private_networks: bool = False,
    require_dns_resolution: bool = True,
) -> Tuple[str, List[Union[ipaddress.IPv4Address, ipaddress.IPv6Address]]]:
    """
    Authoritative single SSRF validation engine.
    - Validates scheme (strictly http/https).
    - Detects loopback, internal domains, and metadata hostnames.
    - Resolves and verifies all A and AAAA DNS records.
    - Fails closed on any DNS resolution error.
    - Detects numeric/octal/hex IP literals.
    - Returns tuple: (cleaned_url, list_of_validated_ips).
    """
    if not isinstance(url, str) or not url.strip():
        raise SSRFSecurityViolation("URL cannot be empty or non-string.")

    cleaned = url.strip()

    try:
        parsed = urllib.parse.urlparse(cleaned)
    except Exception as e:
        raise SSRFSecurityViolation(f"Malformed URL syntax: {e}") from e

    # 1. Scheme Confinement
    scheme = (parsed.scheme or "").lower()
    if scheme in FORBIDDEN_SCHEMES or scheme not in ("http", "https"):
        raise SSRFSecurityViolation(
            f"Prohibited URL scheme '{scheme}': only 'http' and 'https' are allowed."
        )

    # 2. Hostname Presence
    hostname = parsed.hostname
    if not hostname:
        raise SSRFSecurityViolation(f"Invalid URL without hostname: '{cleaned}'")

    hostname_clean = hostname.lower().strip()
    if not hostname_clean:
        raise SSRFSecurityViolation("URL contains empty hostname.")

    # 3. Known Blocked Hostnames & Internal TLDs
    if hostname_clean in ("localhost", "0.0.0.0", "127.0.0.1", "::1"):
        raise SSRFSecurityViolation(f"Loopback access prohibited: '{hostname}'")

    if hostname_clean in BLOCKED_HOSTNAMES:
        raise SSRFSecurityViolation(f"Target host '{hostname_clean}' is prohibited (loopback/cloud metadata).")

    if (
        hostname_clean.endswith(".local")
        or hostname_clean.endswith(".internal")
        or hostname_clean.endswith(".localhost")
        or hostname_clean.endswith(".lan")
    ):
        raise SSRFSecurityViolation(f"Target host '{hostname_clean}' is an internal domain (SSRF blocked).")

    # 4. Check for direct IP literal (standard, numeric, octal, hex)
    ip_literal: Optional[Union[ipaddress.IPv4Address, ipaddress.IPv6Address]] = None

    # Try standard ipaddress parsing
    try:
        ip_literal = ipaddress.ip_address(hostname_clean.strip("[]"))
    except ValueError:
        ip_literal = None

    # Try numeric/octal/hex IPv4 parsing
    if ip_literal is None:
        ip_literal = parse_numeric_ipv4(hostname_clean)

    if ip_literal is not None:
        # Host is an IP literal
        if not allow_private_networks:
            disallowed, reason = is_ip_disallowed(ip_literal)
            if disallowed:
                raise SSRFSecurityViolation(reason)
        return cleaned, [ip_literal]

    # 5. Domain name: resolve DNS dual-stack (A and AAAA records)
    if require_dns_resolution:
        resolved_ips = resolve_all_ips(hostname_clean)
        if not allow_private_networks:
            for rip in resolved_ips:
                disallowed, reason = is_ip_disallowed(rip)
                if disallowed:
                    raise SSRFSecurityViolation(
                        f"Host '{hostname_clean}' resolved to prohibited IP '{rip}' ({reason}) (SSRF blocked)."
                    )
        return cleaned, resolved_ips

    return cleaned, []


def validate_safe_url(url: str, allow_private_networks: bool = False) -> str:
    """
    Convenience function returning the cleaned validated URL string.
    Raises SSRFSecurityViolation on any violation.
    """
    cleaned, _ = validate_url_security(url, allow_private_networks=allow_private_networks, require_dns_resolution=True)
    return cleaned
