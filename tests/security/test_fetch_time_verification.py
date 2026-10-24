"""
tests/security/test_fetch_time_verification.py
==============================================
Tests for Fetch-Time Verification & DNS Rebinding Prevention (SEC-009 / Part 2 Item 2).

Validates:
1. DNS Rebinding Mitigation:
   A fake resolver returns a public IP on resolution 1 and a private/loopback IP on resolution 2.
   With IP pinning in PinnedNetworkBackend, safe_download_media strictly connects to the
   first (validated public) IP, ignoring the poisoned second resolution.
2. Render Path External URL Guard:
   Any blueprint containing a raw/unmaterialized external URL (e.g. {"kind": "url", "url": "..."})
   reaching build_render_input is strictly rejected with RenderInputValidationError.
   Remotion receives local materialized assets only.
"""

import json
import http.server
import json
from pathlib import Path
import pytest
import socket
import socketserver
import threading

from ai.acquisition.safe_downloader import (
    safe_download_media,
    PinnedNetworkBackend,
    PinnedAsyncHTTPTransport,
)
from ai.acquisition.errors import UnsafeDownloadSourceError
import scripts.core.security.ssrf_guard as ssrf_guard
from scripts.core.render_input import (
    build_render_input,
    RenderInputValidationError,
)


class TestDNSRebindingPrevention:
    """Verifies that safe_download_media pins to the first validated IP and closes rebinding attacks."""

    @pytest.mark.asyncio
    async def test_dns_rebinding_pins_to_first_ip_only(self, monkeypatch: pytest.MonkeyPatch):
        """
        Real two-server DNS rebinding verification:
        - Server A (127.0.0.1) serves 'GOOD' JPEG binary content.
        - Server B (127.0.0.2) serves 'EVIL' JPEG binary content on the same port.
        - Mock resolver returns 127.0.0.1 on resolution 1, and 127.0.0.2 on subsequent resolutions.
        - Policy is monkeypatched inside this test only to permit loopback evaluation.
        - Proves that PinnedAsyncHTTPTransport connects strictly to Server A (127.0.0.1),
          receiving 'GOOD', and only 1 DNS resolution occurs during the entire request.
        """
        good_content = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00GOOD_PAYLOAD" + b"\x00" * 80
        evil_content = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00EVIL_PAYLOAD" + b"\x00" * 80

        class ServerAHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", str(len(good_content)))
                self.end_headers()
                self.wfile.write(good_content)
            def log_message(self, *args): pass

        class ServerBHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "image/jpeg")
                self.send_header("Content-Length", str(len(evil_content)))
                self.end_headers()
                self.wfile.write(evil_content)
            def log_message(self, *args): pass

        # Allocate ephemeral port available on both 127.0.0.1 and 127.0.0.2
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
        probe.close()

        srv_a = socketserver.TCPServer(("127.0.0.1", port), ServerAHandler)
        srv_b = socketserver.TCPServer(("127.0.0.2", port), ServerBHandler)
        th_a = threading.Thread(target=srv_a.serve_forever, daemon=True)
        th_b = threading.Thread(target=srv_b.serve_forever, daemon=True)
        th_a.start()
        th_b.start()

        orig_gai = socket.getaddrinfo
        resolutions = []

        def mock_gai(host, p, *args, **kwargs):
            host_str = host.decode() if isinstance(host, (bytes, bytearray)) else str(host)
            if host_str == "rebinding.test":
                resolutions.append(len(resolutions) + 1)
                port_num = int(p) if p else port
                if len(resolutions) == 1:
                    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port_num))]
                else:
                    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.2", port_num))]
            return orig_gai(host, p, *args, **kwargs)

        monkeypatch.setattr(socket, "getaddrinfo", mock_gai)
        monkeypatch.setattr(ssrf_guard, "is_ip_disallowed", lambda ip: (False, ""))

        try:
            payload = await safe_download_media(f"http://rebinding.test:{port}/photo.jpg")

            # 1. Must receive GOOD content from 127.0.0.1
            assert b"GOOD_PAYLOAD" in payload.content_bytes
            assert b"EVIL_PAYLOAD" not in payload.content_bytes

            # 2. Must only perform exactly 1 DNS resolution (during validation)
            assert len(resolutions) == 1
        finally:
            srv_a.shutdown()
            srv_b.shutdown()
            srv_a.server_close()
            srv_b.server_close()

    @pytest.mark.asyncio
    async def test_redirect_hop_to_internal_ip_is_rejected(self, monkeypatch: pytest.MonkeyPatch):
        """
        Verifies that redirect hops are strictly re-evaluated against SSRF policy:
        Hop 1 is permitted by policy, but redirects to an internal/forbidden IP on Hop 2.
        Must fail closed with UnsafeDownloadSourceError.
        """
        class RedirectHandler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(302)
                self.send_header("Location", "http://10.0.0.1/secret_exfil.jpg")
                self.end_headers()
            def log_message(self, *args): pass

        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
        probe.close()

        srv = socketserver.TCPServer(("127.0.0.1", port), RedirectHandler)
        th = threading.Thread(target=srv.serve_forever, daemon=True)
        th.start()

        orig_disallowed = ssrf_guard.is_ip_disallowed

        def allow_only_first_server(ip):
            if str(ip) == "127.0.0.1":
                return False, ""
            return orig_disallowed(ip)

        monkeypatch.setattr(ssrf_guard, "is_ip_disallowed", allow_only_first_server)

        try:
            with pytest.raises(UnsafeDownloadSourceError) as exc_info:
                await safe_download_media(f"http://127.0.0.1:{port}/image.jpg")
            assert "SSRF blocked" in str(exc_info.value)
        finally:
            srv.shutdown()
            srv.server_close()


class TestRenderPathRejectsExternalURLs:
    """Verifies that raw external URLs cannot reach the render pipeline."""

    def test_build_render_input_rejects_external_url_in_blueprint(self, tmp_path: Path):
        project_dir = tmp_path / "prj_render_test"
        project_dir.mkdir(parents=True)

        (project_dir / "project.json").write_text('{"project_id": "prj_render_test", "title": "Test"}', encoding="utf-8")
        (project_dir / "media_map.json").write_text('{"ast_bg": "projects/prj_render_test/bg.jpg"}', encoding="utf-8")

        # Create blueprint containing a raw tagged external URL
        blueprint_dict = {
            "blueprint_version": "2.0.0",
            "project_id": "prj_render_test",
            "fps": 30,
            "aspect_ratio": "16:9",
            "scenes": [
                {
                    "scene_id": "scene_01",
                    "template": "HeroDeviceAssembleWrapper",
                    "startFrame": 0,
                    "durationFrames": 60,
                    "media_refs": [
                        {"kind": "url", "url": "https://example.com/unmaterialized_asset.png"}
                    ],
                    "content": {},
                }
            ],
        }
        (project_dir / "05_blueprint.json").write_text(json.dumps(blueprint_dict), encoding="utf-8")

        # Attempting to assemble render input must fail-closed
        with pytest.raises(RenderInputValidationError) as exc_info:
            build_render_input(
                project_dir_or_id=project_dir,
                verify_files_on_disk=False,
                write_to_disk=False,
            )

        err_msg = str(exc_info.value)
        assert "External URL" in err_msg
        assert "reached render path without local acquisition" in err_msg
        assert "Remotion requires local materialized assets only" in err_msg

    def test_build_render_input_accepts_pure_local_references(self, tmp_path: Path):
        project_dir = tmp_path / "prj_local_test"
        project_dir.mkdir(parents=True)

        (project_dir / "project.json").write_text('{"project_id": "prj_local_test", "title": "Test"}', encoding="utf-8")
        (project_dir / "media_map.json").write_text('{"ast_logo": "projects/prj_local_test/logo.png"}', encoding="utf-8")

        blueprint_dict = {
            "blueprint_version": "2.0.0",
            "project_id": "prj_local_test",
            "fps": 30,
            "aspect_ratio": "16:9",
            "scenes": [
                {
                    "scene_id": "scene_01",
                    "template": "HeroDeviceAssembleWrapper",
                    "startFrame": 0,
                    "durationFrames": 60,
                    "media_refs": ["ast_logo"],
                    "content": {},
                }
            ],
        }
        (project_dir / "05_blueprint.json").write_text(json.dumps(blueprint_dict), encoding="utf-8")

        envelope = build_render_input(
            project_dir_or_id=project_dir,
            verify_files_on_disk=False,
            write_to_disk=False,
        )
        assert envelope is not None
        assert "projectData" in envelope
        assert envelope["projectData"]["media_map"]["ast_logo"] == "projects/prj_local_test/logo.png"

    def test_build_render_input_rejects_external_url_in_brand_json(self, tmp_path: Path):
        """
        Fix 5 Test:
        Verifies that brand.json containing an external URL in logoSrc or fonts is strictly rejected.
        Remotion render envelope must receive local materialized assets only.
        """
        project_dir = tmp_path / "prj_brand_url_test"
        project_dir.mkdir(parents=True)

        (project_dir / "project.json").write_text('{"project_id": "prj_brand_url_test", "title": "Test"}', encoding="utf-8")
        (project_dir / "media_map.json").write_text('{}', encoding="utf-8")

        blueprint_dict = {
            "blueprint_version": "2.0.0",
            "project_id": "prj_brand_url_test",
            "fps": 30,
            "aspect_ratio": "16:9",
            "scenes": [],
        }
        (project_dir / "05_blueprint.json").write_text(json.dumps(blueprint_dict), encoding="utf-8")

        # 1. brand.json with external URL in logoSrc (e.g. metadata exfiltration target)
        brand_dict = {
            "brandName": "TestBrand",
            "logoSrc": "http://169.254.169.254/latest/meta-data/iam/",
        }
        (project_dir / "brand.json").write_text(json.dumps(brand_dict), encoding="utf-8")

        with pytest.raises(RenderInputValidationError) as exc_info:
            build_render_input(
                project_dir_or_id=project_dir,
                verify_files_on_disk=False,
                write_to_disk=False,
            )
        assert "External URL" in str(exc_info.value)
        assert "brand logoSrc" in str(exc_info.value)

        # 2. brand.json with external URL in fonts
        brand_dict_fonts = {
            "brandName": "TestBrand",
            "logoSrc": None,
            "fonts": {"primary": "http://evil.com/font.ttf"},
        }
        (project_dir / "brand.json").write_text(json.dumps(brand_dict_fonts), encoding="utf-8")

        with pytest.raises(RenderInputValidationError) as exc_info2:
            build_render_input(
                project_dir_or_id=project_dir,
                verify_files_on_disk=False,
                write_to_disk=False,
            )
        assert "External URL" in str(exc_info2.value) or "Non-local asset path" in str(exc_info2.value)
        assert "brand fonts" in str(exc_info2.value)

    @pytest.mark.parametrize("invalid_path", [
        "http:/169.254.169.254/",
        r"\\169.254.169.254\x",
        "file:///etc/passwd",
        "data:image/svg+xml;base64,PHN2Zz48L3N2Zz4=",
        "blob:http://evil/x",
        "HTTP://evil.com/asset.png",
        "   http://evil.com/asset.png",
        "javascript:alert(1)",
    ])
    def test_brand_json_rejects_non_local_path_schemes_and_unc(self, tmp_path: Path, invalid_path: str):
        """
        Blocker 2 Test:
        Verifies that brand.json rejects all non-local relative path schemes, UNC paths, and WHATWG bypasses
        for both logoSrc and fonts.
        """
        project_dir = tmp_path / "prj_brand_whitelist_test"
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "project.json").write_text('{"project_id": "prj_brand_whitelist_test", "title": "Test"}', encoding="utf-8")
        (project_dir / "media_map.json").write_text('{}', encoding="utf-8")
        (project_dir / "05_blueprint.json").write_text(json.dumps({
            "blueprint_version": "2.0.0",
            "project_id": "prj_brand_whitelist_test",
            "fps": 30,
            "aspect_ratio": "16:9",
            "scenes": [],
        }), encoding="utf-8")

        # Test logoSrc rejection
        (project_dir / "brand.json").write_text(json.dumps({
            "brandName": "TestBrand",
            "logoSrc": invalid_path,
        }), encoding="utf-8")
        with pytest.raises(RenderInputValidationError) as exc:
            build_render_input(project_dir_or_id=project_dir, verify_files_on_disk=False, write_to_disk=False)
        assert "Non-local asset path" in str(exc.value) or "External URL" in str(exc.value)

        # Test fonts rejection
        (project_dir / "brand.json").write_text(json.dumps({
            "brandName": "TestBrand",
            "logoSrc": None,
            "fonts": {"primary": invalid_path},
        }), encoding="utf-8")
        with pytest.raises(RenderInputValidationError) as exc:
            build_render_input(project_dir_or_id=project_dir, verify_files_on_disk=False, write_to_disk=False)
        assert "Non-local asset path" in str(exc.value) or "External URL" in str(exc.value)

    def test_brand_json_accepts_valid_local_relative_path(self, tmp_path: Path):
        """Verifies that valid local relative path in brand.json is accepted."""
        project_dir = tmp_path / "prj_brand_valid_test"
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "project.json").write_text('{"project_id": "prj_brand_valid_test", "title": "Test"}', encoding="utf-8")
        (project_dir / "media_map.json").write_text('{}', encoding="utf-8")
        (project_dir / "05_blueprint.json").write_text(json.dumps({
            "blueprint_version": "2.0.0",
            "project_id": "prj_brand_valid_test",
            "fps": 30,
            "aspect_ratio": "16:9",
            "scenes": [],
        }), encoding="utf-8")
        (project_dir / "brand.json").write_text(json.dumps({
            "brandName": "TestBrand",
            "logoSrc": "assets/logo.png",
            "fonts": {"primary": "fonts/custom.woff2"},
        }), encoding="utf-8")

        envelope = build_render_input(project_dir_or_id=project_dir, verify_files_on_disk=False, write_to_disk=False)
        assert envelope["projectData"]["brand"]["logoSrc"] == "assets/logo.png"
        assert envelope["projectData"]["brand"]["fonts"]["primary"] == "fonts/custom.woff2"

    @pytest.mark.parametrize("evasion_path", [
        "\x01//169.254.169.254/x",
        "\x7f//evil.com/x",
        "ht\ttp://evil.com",
        "assets/lo\ngo.png",
        "//evil.com/x",
        "assets/%2e%2e/%2e%2e/x",
        "assets/%2fetc/passwd",
        "assets/%5cetc",
        "\u200b//169.254.169.254/x",
        "\u00a0//169.254.169.254/x",
    ])
    def test_brand_json_rejects_control_chars_and_percent_encoding_evasion(self, tmp_path: Path, evasion_path: str):
        """
        Round 3 Final Hardening:
        Verifies that brand.json rejects C0 control characters (<0x20, 0x7f),
        non-ASCII spaces/formatting (Cc, Cf, Zs), and percent-encoded directory traversals (%2e, %2f, %5c).
        """
        project_dir = tmp_path / "prj_brand_control_char_test"
        project_dir.mkdir(parents=True, exist_ok=True)
        (project_dir / "project.json").write_text('{"project_id": "prj_brand_control_char_test", "title": "Test"}', encoding="utf-8")
        (project_dir / "media_map.json").write_text('{}', encoding="utf-8")
        (project_dir / "05_blueprint.json").write_text(json.dumps({
            "blueprint_version": "2.0.0",
            "project_id": "prj_brand_control_char_test",
            "fps": 30,
            "aspect_ratio": "16:9",
            "scenes": [],
        }), encoding="utf-8")

        # Test logoSrc rejection
        (project_dir / "brand.json").write_text(json.dumps({
            "brandName": "TestBrand",
            "logoSrc": evasion_path,
        }), encoding="utf-8")
        with pytest.raises(RenderInputValidationError) as exc:
            build_render_input(project_dir_or_id=project_dir, verify_files_on_disk=False, write_to_disk=False)
        assert "brand logoSrc" in str(exc.value)

        # Test fonts rejection
        (project_dir / "brand.json").write_text(json.dumps({
            "brandName": "TestBrand",
            "logoSrc": None,
            "fonts": {"primary": evasion_path},
        }), encoding="utf-8")
        with pytest.raises(RenderInputValidationError) as exc:
            build_render_input(project_dir_or_id=project_dir, verify_files_on_disk=False, write_to_disk=False)
        assert "brand fonts" in str(exc.value)
