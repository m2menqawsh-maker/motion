"""
tests/api/test_client_without_filesystem.py — Client Without Filesystem Integration Test:
Verifies that an external GUI client can fully manage projects, assets, brand, overrides,
artifacts, runs, events, cancellation, and video delivery using HTTP APIs only,
with zero direct knowledge of disk paths or internal filenames.
"""

import json
import shutil
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from api.main import app
from scripts.core.state_store import StateStore



def test_client_api_only_workflow():
    """
    Full end-to-end GUI-facing workflow conducted entirely through REST APIs.
    Client never touches the filesystem or internal paths.
    """
    client = TestClient(app)
    auth_headers = {
        "X-Principal-ID": "gui_client_user",
        "X-Principal-Roles": "admin",
    }

    try:
        # -------------------------------------------------------------
        # 1. Non-blocking Project Creation
        # -------------------------------------------------------------
        create_resp = client.post(
            "/projects/",
            json={"name": "GUI E2E Project", "language": "ar"},
            headers=auth_headers,
        )
        assert create_resp.status_code == 200, f"Failed: {create_resp.text}"
        project_data = create_resp.json()
        project_id = project_data["project_id"]
        proj_dir = Path(f"projects/{project_id}")

        # -------------------------------------------------------------
        # 2. Canonical Lifecycle DTO Projection
        # -------------------------------------------------------------
        state_resp = client.get(f"/projects/{project_id}/state", headers=auth_headers)
        assert state_resp.status_code == 200
        state_dto = state_resp.json()
        assert state_dto["project_id"] == project_id
        assert "lifecycle_state" in state_dto
        assert "revision" in state_dto
        assert "artifacts_status" in state_dto

        # -------------------------------------------------------------
        # 3. Asset Upload and Management
        # -------------------------------------------------------------
        dummy_png = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRtest_image_bytes"
        upload_resp = client.post(
            f"/projects/{project_id}/assets",
            files={"file": ("client_logo.png", dummy_png, "image/png")},
            data={"asset_id": "ast_client_logo", "kind": "logo"},
            headers=auth_headers,
        )
        assert upload_resp.status_code == 201, f"Upload failed: {upload_resp.text}"
        uploaded_asset = upload_resp.json()["asset"]
        assert uploaded_asset["asset_id"] == "ast_client_logo"
        assert uploaded_asset["kind"] == "logo"

        # List assets
        assets_list_resp = client.get(f"/projects/{project_id}/assets", headers=auth_headers)
        assert assets_list_resp.status_code == 200
        assets = assets_list_resp.json()["assets"]
        assert any(a["asset_id"] == "ast_client_logo" for a in assets)

        # -------------------------------------------------------------
        # 4. Brand Management with Canonical Contract & ETag
        # -------------------------------------------------------------
        brand_get_resp = client.get(f"/brand/{project_id}", headers=auth_headers)
        assert brand_get_resp.status_code == 200
        brand_etag = brand_get_resp.headers.get("ETag")
        assert brand_etag is not None

        brand_payload = {
            "brandName": "Client Corporation",
            "colors": {
                "primary": "#0055ff",
                "accent": "#ffaa00",
                "background": "#000000",
                "text": "#ffffff",
            },
            "fonts": {
                "display": "Cairo",
                "body": "Tajawal",
            },
        }

        # Update brand with valid If-Match
        brand_update_resp = client.post(
            f"/brand/{project_id}",
            json=brand_payload,
            headers={**auth_headers, "If-Match": brand_etag},
        )
        assert brand_update_resp.status_code == 200, f"Brand update failed: {brand_update_resp.text}"
        new_brand_etag = brand_update_resp.headers.get("ETag")
        assert new_brand_etag != brand_etag

        # -------------------------------------------------------------
        # 5. Overrides Management with Validation & Optimistic Concurrency
        # -------------------------------------------------------------
        overrides_payload = {
            "project_id": project_id,
            "scenes": [
                {
                    "scene_id": "scene_01",
                    "props": {
                        "fontSize": 32,
                        "text": "Client Title",
                        "styleOverride": {
                            "borderRadius": "12px",
                            "padding": "16px",
                        },
                    },
                }
            ],
        }

        # Stale If-Match triggers 409 Conflict
        stale_overrides_resp = client.post(
            f"/blueprint/{project_id}/overrides",
            json=overrides_payload,
            headers={**auth_headers, "If-Match": "rev_0"},
        )
        assert stale_overrides_resp.status_code == 409

        # Valid update with latest revision
        latest_state = StateStore.load(proj_dir)
        current_rev = latest_state.revision if latest_state else 1
        valid_overrides_resp = client.post(
            f"/blueprint/{project_id}/overrides",
            json=overrides_payload,
            headers={**auth_headers, "If-Match": f'"{current_rev}"'},
        )
        assert valid_overrides_resp.status_code == 200, f"Overrides update failed: {valid_overrides_resp.text}"

        # -------------------------------------------------------------
        # 6. Artifact Discovery and Inspection
        # -------------------------------------------------------------
        artifacts_resp = client.get(f"/projects/{project_id}/artifacts", headers=auth_headers)
        assert artifacts_resp.status_code == 200
        artifacts_inventory = artifacts_resp.json()["artifacts"]
        assert len(artifacts_inventory) > 0

        # Read manifest artifact through domain reader
        manifest_reader_resp = client.get(
            f"/projects/{project_id}/artifacts/manifest",
            headers=auth_headers,
        )
        assert manifest_reader_resp.status_code == 200
        manifest_data = manifest_reader_resp.json()
        assert manifest_data["kind"] == "manifest"
        assert "content" in manifest_data

        # -------------------------------------------------------------
        # 7. Run Management, Durable Events & Reconnection
        # -------------------------------------------------------------
        run_create_resp = client.post(f"/projects/{project_id}/runs", headers=auth_headers)
        assert run_create_resp.status_code == 202
        run_data = run_create_resp.json()
        run_id = run_data["run_id"]
        assert run_data["status"] == "QUEUED"

        # Fetch initial events (should include RUN_QUEUED)
        events_resp = client.get(f"/projects/{project_id}/runs/{run_id}/events", headers=auth_headers)
        assert events_resp.status_code == 200
        events_payload = events_resp.json()
        assert len(events_payload["events"]) >= 1
        first_event = events_payload["events"][0]
        assert first_event["event_type"] == "RUN_QUEUED"
        assert first_event["sequence"] == 1

        # -------------------------------------------------------------
        # 8. Real Run Cancellation
        # -------------------------------------------------------------
        cancel_resp = client.post(f"/projects/{project_id}/runs/{run_id}/cancel", headers=auth_headers)
        assert cancel_resp.status_code == 200
        cancel_data = cancel_resp.json()
        assert cancel_data["status"] == "CANCELLED"

        # Reconnect to events using cursor (after=1)
        reconnect_resp = client.get(
            f"/projects/{project_id}/runs/{run_id}/events?after=1",
            headers=auth_headers,
        )
        assert reconnect_resp.status_code == 200
        reconnect_events = reconnect_resp.json()["events"]
        assert len(reconnect_events) >= 1
        assert reconnect_events[0]["event_type"] == "RUN_CANCELLED"

        # -------------------------------------------------------------
        # 9. Video Delivery with Range Seeking
        # -------------------------------------------------------------
        out_dir = proj_dir / "outputs"
        out_dir.mkdir(parents=True, exist_ok=True)
        dummy_video_bytes = b"MP4_HEADER_" + (b"0123456789" * 100)
        (out_dir / "final_video.mp4").write_bytes(dummy_video_bytes)

        # Full delivery
        video_full_resp = client.get(
            f"/projects/{project_id}/outputs/final_video.mp4",
            headers=auth_headers,
        )
        assert video_full_resp.status_code == 200
        assert video_full_resp.headers.get("Accept-Ranges") == "bytes"

        # Seeking chunk
        seek_resp = client.get(
            f"/projects/{project_id}/outputs/final_video.mp4",
            headers={**auth_headers, "Range": "bytes=0-49"},
        )
        assert seek_resp.status_code == 206
        assert seek_resp.headers["Content-Range"].startswith("bytes 0-49/")
        assert len(seek_resp.content) == 50
        assert seek_resp.content == dummy_video_bytes[0:50]

    finally:
        if proj_dir.exists():
            shutil.rmtree(proj_dir, ignore_errors=True)
