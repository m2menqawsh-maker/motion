"""
Security and SSRF Guard Tests for Safe Media Downloader (S28-M05).
"""

from unittest.mock import AsyncMock, patch
import pytest
import httpx

from ai.acquisition.contracts import StockMediaType
from ai.acquisition.errors import (
    AcquisitionAuthorizationError,
    DownloadFailedError,
    MediaValidationError,
    UnsafeDownloadSourceError,
)
from ai.acquisition.safe_downloader import (
    assert_safe_url,
    safe_download_media,
    verify_magic_bytes,
)
from ai.acquisition.service import AssetAcquisitionService
from ai.tools.types import TrustedToolExecutionContext


class TestSSRFGuards:
    """Verifies fail-closed SSRF protection for media downloads."""

    @pytest.mark.parametrize(
        "unsafe_url",
        [
            "http://127.0.0.1/video.mp4",
            "http://127.0.0.1:8080/image.jpg",
            "http://localhost/image.png",
            "http://localhost:3000/api",
            "http://10.0.0.1/private.mp4",
            "http://10.255.255.255/media.mp4",
            "http://192.168.1.1/router.png",
            "http://172.16.0.1/internal.mp3",
            "http://169.254.169.254/latest/meta-data/",
            "http://metadata.google.internal/computeMetadata/v1/",
            "file:///etc/passwd",
            "ftp://ftp.example.com/file.mp4",
            "data:text/html;base64,PHNjcmlwdD4=",
            "gopher://evil.com/1",
        ],
    )
    def test_assert_safe_url_blocks_unsafe_destinations(self, unsafe_url):
        with pytest.raises(UnsafeDownloadSourceError):
            assert_safe_url(unsafe_url)

    def test_assert_safe_url_allows_public_urls(self):
        assert_safe_url("https://images.pexels.com/photos/123/img.jpg")
        assert_safe_url("https://cdn.pixabay.com/video/123.mp4")
        assert_safe_url("https://api.iconify.design/mdi/home.svg")

    def test_dns_resolution_to_private_ip_is_blocked(self):
        """Domain names that resolve to RFC1918 / loopback IPs must be blocked by SSRF checks."""
        # Mock getaddrinfo returning loopback address for public-looking domain
        mock_addr = [(2, 1, 6, '', ('127.0.0.1', 80))]
        with patch("socket.getaddrinfo", return_value=mock_addr):
            with pytest.raises(UnsafeDownloadSourceError, match="SSRF blocked"):
                assert_safe_url("http://rebinding.attacker.com/payload.mp4")

    def test_dns_resolution_with_mixed_safe_and_unsafe_ips_fails_closed(self):
        """If a host resolves to both safe and unsafe IP records, it must fail closed."""
        mock_addr = [
            (2, 1, 6, '', ('93.184.215.14', 80)),
            (2, 1, 6, '', ('10.0.0.5', 80)),
        ]
        with patch("socket.getaddrinfo", return_value=mock_addr):
            with pytest.raises(UnsafeDownloadSourceError, match="SSRF blocked"):
                assert_safe_url("http://dual-homed.example.com/asset.mp4")


class TestMagicByteValidation:
    """Verifies MIME-type and payload signature verification."""

    def test_valid_image_and_video_signatures(self):
        # JPEG
        assert verify_magic_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF", StockMediaType.IMAGE) == "image/jpeg"
        # PNG
        assert verify_magic_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR", StockMediaType.IMAGE) == "image/png"
        # MP4
        assert verify_magic_bytes(b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00", StockMediaType.VIDEO) == "video/mp4"
        # SVG
        assert verify_magic_bytes(b"<svg xmlns='http://www.w3.org/2000/svg'><path d='M0 0h24v24H0z'/></svg>", StockMediaType.ICON) == "image/svg+xml"
        # MP3
        assert verify_magic_bytes(b"ID3\x03\x00\x00\x00\x00\x00", StockMediaType.AUDIO) == "audio/mpeg"

    def test_html_masquerading_as_media_is_rejected(self):
        html_payload = b"<!DOCTYPE html><html><body>404 Not Found</body></html>"
        with pytest.raises(MediaValidationError, match="HTML error page"):
            verify_magic_bytes(html_payload, StockMediaType.VIDEO)

    def test_empty_payload_is_rejected(self):
        with pytest.raises(MediaValidationError, match="empty download"):
            verify_magic_bytes(b"", StockMediaType.IMAGE)

    def test_payload_too_small_is_rejected(self):
        with pytest.raises(MediaValidationError, match="too small"):
            verify_magic_bytes(b"abc", StockMediaType.IMAGE)


class TestSVGSecurity:
    """Verifies strict fail-closed screening of malicious SVG constructs."""

    def test_svg_with_script_tag_rejected(self):
        malicious = b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>"
        with pytest.raises(MediaValidationError, match="executable <script>"):
            verify_magic_bytes(malicious, StockMediaType.ICON)

    def test_svg_with_event_handler_rejected(self):
        malicious = b"<svg xmlns='http://www.w3.org/2000/svg' onload='alert(1)'><circle r='5'/></svg>"
        with pytest.raises(MediaValidationError, match="inline event handlers"):
            verify_magic_bytes(malicious, StockMediaType.ICON)

    def test_svg_with_javascript_uri_rejected(self):
        malicious = b"<svg xmlns='http://www.w3.org/2000/svg'><a href='javascript:alert(1)'><circle r='5'/></a></svg>"
        with pytest.raises(MediaValidationError, match="script URI schemes"):
            verify_magic_bytes(malicious, StockMediaType.ICON)

    def test_svg_with_foreign_object_rejected(self):
        malicious = b"<svg xmlns='http://www.w3.org/2000/svg'><foreignObject width='100' height='50'><body>evil</body></foreignObject></svg>"
        with pytest.raises(MediaValidationError, match="<foreignObject>"):
            verify_magic_bytes(malicious, StockMediaType.ICON)

    def test_svg_with_external_use_href_rejected(self):
        malicious = b"<svg xmlns='http://www.w3.org/2000/svg'><use href='http://evil.com/exploit.svg#id'/></svg>"
        with pytest.raises(MediaValidationError, match="external resource references"):
            verify_magic_bytes(malicious, StockMediaType.ICON)

    def test_svg_with_xxe_doctype_rejected(self):
        malicious = b"<?xml version='1.0'?><!DOCTYPE svg [<!ENTITY xxe SYSTEM 'file:///etc/passwd'>]><svg>&xxe;</svg>"
        with pytest.raises(MediaValidationError, match="XML DOCTYPE"):
            verify_magic_bytes(malicious, StockMediaType.ICON)

    def test_valid_iconify_svg_passes(self):
        valid = (
            b"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'>"
            b"<path fill='currentColor' d='M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z'/>"
            b"</svg>"
        )
        detected = verify_magic_bytes(valid, StockMediaType.ICON)
        assert detected == "image/svg+xml"


class TestRedirectAndCeilingSecurity:
    """Verifies that redirects to private IPs and size ceiling violations fail closed."""

    @pytest.mark.asyncio
    async def test_redirect_to_private_ip_is_blocked(self):
        """A public URL redirecting to 127.0.0.1 must be aborted before requesting the target."""
        initial_url = "https://example.com/redirect"
        evil_redirect = "http://127.0.0.1:8080/admin/dump"

        # Mock initial 302 response to evil location
        mock_response = AsyncMock()
        mock_response.status_code = 302
        mock_response.headers = {"Location": evil_redirect}

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            with pytest.raises(UnsafeDownloadSourceError, match="SSRF blocked"):
                await safe_download_media(initial_url, StockMediaType.VIDEO)

    @pytest.mark.asyncio
    async def test_exceeding_byte_ceiling_fails_closed(self):
        """Responses with content exceeding max_bytes must be rejected."""
        valid_url = "https://example.com/huge.mp4"
        # 10 bytes max
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Length": "1000"}
        mock_response.content = b"x" * 1000

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            with pytest.raises((DownloadFailedError, MediaValidationError)):
                await safe_download_media(valid_url, StockMediaType.VIDEO, max_bytes=50)

    @pytest.mark.asyncio
    async def test_declared_vs_detected_mime_mismatch_rejected(self):
        """A download declared as image/png that returns MP4 video bytes must be rejected."""
        valid_url = "https://example.com/mismatch.png"
        mp4_bytes = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00" + (b"\x00" * 50)

        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "image/png"}
        mock_response.content = mp4_bytes

        with patch("httpx.AsyncClient.get", return_value=mock_response):
            with pytest.raises(MediaValidationError, match="MIME type mismatch"):
                await safe_download_media(valid_url, StockMediaType.IMAGE)


class TestTenantConfinement:
    """Verifies multi-tenant isolation and workspace confinement in AssetAcquisitionService."""

    def test_mismatched_workspace_confinement_fails(self):
        service = AssetAcquisitionService()
        trusted_context = TrustedToolExecutionContext(
            workspace_id="ws_allowed",
            actor_id="user_123",
            accessible_projects=["proj_1"],
        )

        # Attempt to access project with different workspace
        with pytest.raises(AcquisitionAuthorizationError, match="Cross-tenant access violation"):
            service._validate_tenant_confinement(
                project_id="proj_1",
                workspace_id="ws_forbidden",
                context=trusted_context,
            )

        # Attempt to access non-accessible project
        with pytest.raises(AcquisitionAuthorizationError, match="Cross-project access violation"):
            service._validate_tenant_confinement(
                project_id="proj_other",
                workspace_id="ws_allowed",
                context=trusted_context,
            )

    def test_matching_workspace_confinement_passes(self):
        service = AssetAcquisitionService()
        trusted_context = TrustedToolExecutionContext(
            workspace_id="ws_allowed",
            actor_id="user_123",
            accessible_projects=["proj_1"],
        )

        # Matching workspace passes without exception (mocking DB if needed)
        with patch("scripts.core.database.get_database_engine", side_effect=Exception("DB skipped")):
            service._validate_tenant_confinement(
                project_id="proj_1",
                workspace_id="ws_allowed",
                context=trusted_context,
            )
