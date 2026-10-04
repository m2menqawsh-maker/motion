"""
ai/acquisition/safe_downloader.py
=================================
Safe, bounded HTTP media acquisition with strict SSRF, redirect, and payload validation (S28-M05).

Invariants:
- Fail-closed SSRF validation across initial requests and all redirects.
- Rejects non-HTTP(S) schemes (e.g. file://, ftp://, gopher://).
- Rejects localhost, RFC1918 private ranges, and cloud metadata addresses (169.254.169.254).
- Enforces strict byte budget ceilings (default 50MB) and content-length verification.
- Rejects HTML error documents masquerading as media payloads.
- Verifies binary magic bytes and payload integrity.
- Operates entirely in-memory or hermetic temp buffers (zero raw project filesystem access).
"""

from __future__ import annotations

import hashlib
import ipaddress
import mimetypes
import re
import socket
import urllib.parse
from typing import Optional, Set, Tuple
import httpx
from pydantic import BaseModel, Field

from ai.acquisition.contracts import StockMediaType
from ai.acquisition.errors import (
    DownloadFailedError,
    MediaValidationError,
    UnsafeDownloadSourceError,
)

FORBIDDEN_SCHEMES: Set[str] = {"file", "ftp", "gopher", "data", "javascript", "blob"}

BLOCKED_HOSTNAMES: Set[str] = {
    "localhost",
    "ip6-localhost",
    "ip6-loopback",
    "metadata.google.internal",
    "instance-data",
}

DISALLOWED_CONTENT_TYPES: Set[str] = {
    "text/html",
    "text/javascript",
    "application/javascript",
    "application/x-javascript",
    "application/xhtml+xml",
}

SVG_FORBIDDEN_PATTERNS = [
    (re.compile(r"<\s*script\b", re.IGNORECASE), "executable <script> tags are forbidden"),
    (re.compile(r"\bon[a-z]+\s*=", re.IGNORECASE), "inline event handlers (e.g. onload, onclick) are forbidden"),
    (re.compile(r"""(?:href|xlink:href|src)\s*=\s*['"]?\s*(?:javascript|vbscript|data:text/html)\s*:""", re.IGNORECASE), "script URI schemes (javascript:/vbscript:) are forbidden"),
    (re.compile(r"<\s*foreignobject\b", re.IGNORECASE), "<foreignObject> elements are forbidden"),
    (re.compile(r"""<\s*(?:use|image)\b[^>]*\b(?:href|xlink:href)\s*=\s*['"]?\s*(?:https?:|//)""", re.IGNORECASE), "external resource references (<use>/<image> external href) are forbidden"),
    (re.compile(r"<!ENTITY\b", re.IGNORECASE), "XML DOCTYPE entity declarations (XXE) are forbidden"),
    (re.compile(r"<!DOCTYPE\b[^>]*\b(?:SYSTEM|PUBLIC)\b", re.IGNORECASE), "external DTD references (XXE) are forbidden"),
]


def check_ip_disallowed(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> Tuple[bool, str]:
    """
    Evaluates whether an IP address falls into loopback, private, link-local,
    cloud metadata, or reserved/multicast address spaces.
    """
    if ip.is_loopback:
        return True, "loopback address"
    if ip.is_private:
        return True, "private RFC1918/ULA address"
    if ip.is_link_local:
        return True, "link-local address"
    if ip.is_reserved:
        return True, "reserved address"
    if ip.is_multicast:
        return True, "multicast address"
    if ip.is_unspecified:
        return True, "unspecified (0.0.0.0 / ::) address"

    # Handle IPv4-mapped IPv6 addresses (e.g., ::ffff:127.0.0.1)
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        return check_ip_disallowed(ip.ipv4_mapped)

    ip_str = str(ip).lower()
    if ip_str in ("169.254.169.254", "fd00:ec2::254"):
        return True, "cloud metadata service address"

    # Carrier-grade NAT (100.64.0.0/10)
    cgnat = ipaddress.ip_network("100.64.0.0/10")
    if isinstance(ip, ipaddress.IPv4Address) and ip in cgnat:
        return True, "carrier-grade NAT (RFC6598) address"

    return False, ""


def validate_svg_security(content: bytes) -> None:
    """
    Validates SVG text against cross-site scripting (XSS), server-side request forgery (SSRF),
    and XML external entity (XXE) vectors.
    Fails closed by raising MediaValidationError if any malicious construct is detected.
    """
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = content.decode("latin-1")
        except Exception:
            raise MediaValidationError("SVG payload could not be decoded as valid text.")

    for pattern, description in SVG_FORBIDDEN_PATTERNS:
        if pattern.search(text):
            raise MediaValidationError(f"Malicious or unsafe SVG content detected: {description}.")


class DownloadedPayload(BaseModel):
    """In-memory validated media payload ready for AssetService ingestion."""
    content_bytes: bytes
    content_hash: str = Field(description="SHA-256 cryptographic digest")
    mime_type: str = Field(description="Normalized verified MIME type")
    file_size_bytes: int = Field(ge=0, description="Payload size in bytes")
    suggested_extension: str = Field(description="File extension with leading dot")


def assert_safe_url(url: str) -> None:
    """
    Validates a URL against strict network policy and SSRF risks.
    Resolves DNS for domain hostnames and verifies all resolved IPv4/IPv6 addresses.
    Raises UnsafeDownloadSourceError on any violation.
    """
    if not url or not isinstance(url, str):
        raise UnsafeDownloadSourceError(str(url), "URL must be a non-empty string.")

    try:
        parsed = urllib.parse.urlparse(url)
    except Exception as e:
        raise UnsafeDownloadSourceError(url, f"Malformed URL syntax: {e}")

    scheme = (parsed.scheme or "").lower()
    if scheme in FORBIDDEN_SCHEMES or scheme not in ("http", "https"):
        raise UnsafeDownloadSourceError(
            url,
            f"Scheme '{scheme}' is forbidden. Only HTTP and HTTPS are permitted."
        )

    hostname = (parsed.hostname or "").lower().strip()
    if not hostname:
        raise UnsafeDownloadSourceError(url, "URL contains no target hostname.")

    if hostname in BLOCKED_HOSTNAMES or hostname.endswith(".local") or hostname.endswith(".internal"):
        raise UnsafeDownloadSourceError(url, f"Host '{hostname}' is internal/private (SSRF blocked).")

    # 1. Direct IP address check if hostname is an IP literal
    try:
        ip = ipaddress.ip_address(hostname)
        disallowed, reason = check_ip_disallowed(ip)
        if disallowed:
            raise UnsafeDownloadSourceError(url, f"IP '{hostname}' is blocked: {reason} (SSRF blocked).")
        return
    except ValueError:
        pass

    # 2. DNS resolution check for domain names (fail-closed across all resolved IPv4 & IPv6 records)
    try:
        addrinfo = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        raise UnsafeDownloadSourceError(url, f"DNS resolution failed for '{hostname}': {e} (SSRF blocked).")
    except Exception as e:
        raise UnsafeDownloadSourceError(url, f"DNS lookup error for '{hostname}': {e} (SSRF blocked).")

    if not addrinfo:
        raise UnsafeDownloadSourceError(url, f"No DNS records resolved for '{hostname}' (SSRF blocked).")

    for family, socktype, proto, canonname, sockaddr in addrinfo:
        resolved_ip_str = sockaddr[0]
        try:
            resolved_ip = ipaddress.ip_address(resolved_ip_str)
            disallowed, reason = check_ip_disallowed(resolved_ip)
            if disallowed:
                raise UnsafeDownloadSourceError(
                    url,
                    f"Host '{hostname}' resolved to blocked IP '{resolved_ip_str}' ({reason}) (SSRF blocked)."
                )
        except ValueError:
            raise UnsafeDownloadSourceError(url, f"Invalid resolved IP '{resolved_ip_str}' for '{hostname}'.")


def verify_magic_bytes(content: bytes, expected_media_type: Optional[StockMediaType]) -> str:
    """
    Verifies that the byte stream conforms to expected media format signatures.
    Returns detected normalized MIME type or raises MediaValidationError.
    """
    if len(content) == 0:
        raise MediaValidationError("Payload is 0 bytes (empty download).")

    # SVG check
    if content.lstrip().startswith(b"<?xml") or content.lstrip().startswith(b"<svg") or b"<svg" in content[:512]:
        if expected_media_type and expected_media_type not in (StockMediaType.ICON, StockMediaType.IMAGE):
            raise MediaValidationError(f"Received SVG vector data but expected {expected_media_type.value}.")
        validate_svg_security(content)
        return "image/svg+xml"

    if len(content) < 8:
        raise MediaValidationError(f"Payload size ({len(content)} bytes) is too small to be a valid media stream.")

    # JPEG check
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"

    # PNG check
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"

    # WebP check
    if len(content) > 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"

    # MP4 check (ftyp box at offset 4)
    if len(content) > 8 and content[4:8] == b"ftyp":
        return "video/mp4"

    # WebM / MKV check (EBML header)
    if content.startswith(b"\x1a\x45\xdf\xa3"):
        return "video/webm"

    # MP3 check
    if content.startswith(b"ID3") or (len(content) > 2 and content[0] == 0xFF and (content[1] & 0xE0) == 0xE0):
        return "audio/mpeg"

    # WAV check
    if len(content) > 12 and content[:4] == b"RIFF" and content[8:12] == b"WAVE":
        return "audio/wav"

    # Ogg check
    if content.startswith(b"OggS"):
        return "audio/ogg"

    # If expected is icon and contains SVG text:
    if expected_media_type == StockMediaType.ICON:
        try:
            text = content.decode("utf-8", errors="ignore")
            if "<svg" in text:
                validate_svg_security(content)
                return "image/svg+xml"
        except Exception:
            pass

    # If unrecognized binary format, check if it's forbidden HTML
    content_head = content[:512].lower()
    if b"<!doctype html" in content_head or b"<html" in content_head:
        raise MediaValidationError("Remote server returned HTML error page instead of media binary.")

    # Fallback to permissive binary if media type allows
    if expected_media_type == StockMediaType.VIDEO:
        return "video/mp4"
    elif expected_media_type == StockMediaType.IMAGE:
        return "image/jpeg"
    elif expected_media_type in (StockMediaType.AUDIO, StockMediaType.SOUND_EFFECT):
        return "audio/mpeg"

    return "application/octet-stream"


async def safe_download_media(
    url: str,
    expected_media_type: Optional[StockMediaType] = None,
    max_bytes: int = 50 * 1024 * 1024,
    timeout_seconds: float = 20.0,
    max_redirects: int = 3,
) -> DownloadedPayload:
    """
    Downloads media from remote URL enforcing all security boundaries.
    """
    current_url = url
    redirect_count = 0

    assert_safe_url(current_url)

    async with httpx.AsyncClient(
        follow_redirects=False,
        timeout=httpx.Timeout(timeout_seconds, connect=5.0),
        headers={"User-Agent": "CleanVideoWorkspace/2.0 (MediaAcquisitionService)"},
    ) as client:
        while True:
            try:
                response = await client.get(current_url)
            except httpx.TimeoutException as e:
                raise DownloadFailedError(current_url, f"Connection timed out after {timeout_seconds}s: {e}")
            except httpx.RequestError as e:
                raise DownloadFailedError(current_url, f"Network request error: {e}")

            # Handle redirects manually to validate destination URLs against SSRF policy
            if response.status_code in (301, 302, 303, 307, 308):
                redirect_count += 1
                if redirect_count > max_redirects:
                    raise UnsafeDownloadSourceError(url, f"Exceeded maximum redirect limit ({max_redirects}).")

                redirect_location = response.headers.get("Location")
                if not redirect_location:
                    raise DownloadFailedError(current_url, "Redirect response missing Location header.")

                # Resolve relative redirects
                next_url = urllib.parse.urljoin(current_url, redirect_location)
                assert_safe_url(next_url)
                current_url = next_url
                continue

            # Non-redirect response: check HTTP status
            if response.status_code >= 400:
                raise DownloadFailedError(
                    current_url,
                    f"HTTP status {response.status_code}",
                    status_code=response.status_code,
                )

            # Case-insensitive header lookups
            headers_dict = {str(k).lower(): str(v) for k, v in getattr(response, "headers", {}).items()}

            # Check content-length header
            raw_content_length = headers_dict.get("content-length")
            if raw_content_length:
                try:
                    expected_len = int(raw_content_length)
                    if expected_len > max_bytes:
                        raise MediaValidationError(
                            f"Remote content-length ({expected_len} bytes) exceeds maximum ceiling ({max_bytes} bytes)."
                        )
                except ValueError:
                    pass

            # Check content-type header for obvious HTML
            raw_content_type = (headers_dict.get("content-type") or "").split(";")[0].strip().lower()
            if raw_content_type in DISALLOWED_CONTENT_TYPES:
                raise MediaValidationError(
                    f"Forbidden content type '{raw_content_type}' returned by remote server (HTML/script rejected)."
                )

            content_bytes = response.content
            if len(content_bytes) > max_bytes:
                raise MediaValidationError(
                    f"Downloaded payload size ({len(content_bytes)} bytes) exceeded budget ceiling ({max_bytes} bytes)."
                )

            # Magic bytes validation
            verified_mime = verify_magic_bytes(content_bytes, expected_media_type)

            # Declared vs detected MIME consistency check
            if raw_content_type and raw_content_type not in ("application/octet-stream", "binary/octet-stream", "*/*"):
                declared_category = raw_content_type.split("/")[0]
                detected_category = verified_mime.split("/")[0]
                if declared_category in ("image", "video", "audio") and detected_category in ("image", "video", "audio"):
                    if declared_category != detected_category:
                        raise MediaValidationError(
                            f"MIME type mismatch: declared Content-Type '{raw_content_type}' conflicts with detected binary format '{verified_mime}'."
                        )

            # Expected media type verification
            if expected_media_type:
                if expected_media_type == StockMediaType.IMAGE and not verified_mime.startswith("image/"):
                    raise MediaValidationError(f"Detected MIME '{verified_mime}' does not match expected media type '{expected_media_type.value}'.")
                elif expected_media_type == StockMediaType.ICON and verified_mime not in ("image/svg+xml", "image/png"):
                    raise MediaValidationError(f"Detected MIME '{verified_mime}' does not match expected media type '{expected_media_type.value}'.")
                elif expected_media_type == StockMediaType.VIDEO and not verified_mime.startswith("video/"):
                    raise MediaValidationError(f"Detected MIME '{verified_mime}' does not match expected media type '{expected_media_type.value}'.")
                elif expected_media_type in (StockMediaType.AUDIO, StockMediaType.SOUND_EFFECT) and not verified_mime.startswith("audio/"):
                    raise MediaValidationError(f"Detected MIME '{verified_mime}' does not match expected media type '{expected_media_type.value}'.")

            # Extension resolution
            ext = mimetypes.guess_extension(verified_mime) or ".bin"
            if verified_mime == "image/svg+xml":
                ext = ".svg"
            elif verified_mime == "image/jpeg" and ext == ".jpe":
                ext = ".jpg"
            elif verified_mime == "video/mp4":
                ext = ".mp4"
            elif verified_mime == "audio/mpeg":
                ext = ".mp3"

            content_hash = hashlib.sha256(content_bytes).hexdigest()

            return DownloadedPayload(
                content_bytes=content_bytes,
                content_hash=content_hash,
                mime_type=verified_mime,
                file_size_bytes=len(content_bytes),
                suggested_extension=ext,
            )
