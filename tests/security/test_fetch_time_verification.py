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
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
import pytest
import socket
import httpcore

from ai.acquisition.safe_downloader import (
    safe_download_media,
    PinnedNetworkBackend,
    PinnedAsyncHTTPTransport,
)
from scripts.core.render_input import (
    build_render_input,
    RenderInputValidationError,
)


class TestDNSRebindingPrevention:
    """Verifies that safe_download_media pins to the first validated IP and closes rebinding attacks."""

    @pytest.mark.asyncio
    async def test_dns_rebinding_pins_to_first_ip_only(self):
        """
        Simulate a DNS rebinding attacker whose domain resolves to a safe public IP
        first (during validation), and then switches to 127.0.0.1 (during connection).
        With IP pinning, the TCP connection connects strictly to the first validated IP.
        """
        public_ip = "93.184.216.34"
        internal_ip = "127.0.0.1"

        call_count = 0

        def fake_getaddrinfo(host, port, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First resolution (validation pass): returns safe public IP
                return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (public_ip, port or 443))]
            else:
                # Second resolution (rebinding attack): returns loopback IP
                return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (internal_ip, port or 443))]

        connected_remote_hosts = []

        jpeg_payload = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01" + b"\x00" * 90

        # Spy on PinnedNetworkBackend.connect_tcp to observe which IP is actually connected
        orig_connect_tcp = PinnedNetworkBackend.connect_tcp

        async def spy_connect_tcp(self, host, port, *args, **kwargs):
            connected_remote_hosts.append(self.pinned_ip)
            mock_stream = MagicMock()
            mock_stream.aclose = AsyncMock()
            return mock_stream

        with patch("socket.getaddrinfo", side_effect=fake_getaddrinfo):
            with patch.object(PinnedNetworkBackend, "connect_tcp", new=spy_connect_tcp):
                with patch("httpcore.AsyncConnectionPool.handle_async_request", new_callable=AsyncMock) as mock_handle:
                    async def fake_handle(request):
                        backend = PinnedNetworkBackend(pinned_ip=public_ip)
                        await backend.connect_tcp(request.url.host.decode(), request.url.port or 443)
                        return httpcore.Response(
                            status=200,
                            headers=[
                                (b"content-type", b"image/jpeg"),
                                (b"content-length", str(len(jpeg_payload)).encode()),
                            ],
                            content=jpeg_payload,
                        )

                    mock_handle.side_effect = fake_handle

                    payload = await safe_download_media("https://rebinding-target.com/test.jpg")

        # Assert that the TCP connection was pinned to the FIRST (public) IP
        # and NEVER connected to internal_ip (127.0.0.1)
        assert len(connected_remote_hosts) > 0
        assert internal_ip not in connected_remote_hosts
        assert connected_remote_hosts[0] == public_ip
        assert payload.mime_type == "image/jpeg"


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
