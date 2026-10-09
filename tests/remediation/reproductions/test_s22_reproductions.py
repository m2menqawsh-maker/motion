"""
tests/remediation/reproductions/test_s22_reproductions.py — S22 Red Reproductions Suite.

Proves the baseline failure (CONFIRMED_ON_MAIN) for all 12 S22 findings:
- LED-060: Events not live/durable (no run_events table, no event stream/reconnect)
- LED-062: Cancellation not real (no cancel endpoint, worker cannot cancel child process)
- LED-063: No Media Upload / Management API
- LED-064: No Artifact / Reports API (no domain inventory or canonical readers)
- LED-065: No Video Delivery API (no Range support or streaming output endpoint)
- LED-066: Brand API without contract (accepts invalid payload, no downstream invalidation)
- LED-067: Overrides API without schema (accepts invalid/dangerous properties)
- LED-068: Artifact writes not atomic/optimistic (no ETag / If-Match / 409 Conflict)
- LED-069: Router / Service / Repository mixing (direct file writes in routers)
- LED-070: Blocking project creation in async route (sync subprocess in async def)
- LED-071: Legacy lifecycle facade (no canonical Lifecycle DTO, qc_gate collapse)
- LED-072: Hardcoded CORS (allow_origins hardcoded to localhost:3000)
"""

import ast
import json
import os
import shutil
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from tests.conftest import make_test_auth_headers

ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.main import app
from scripts.core.run_repository import RunRepository


# =========================================================================
# LED-060: Events not Live / Durable
# =========================================================================
def test_reproduce_led_060_events_not_live_or_durable(tmp_path, monkeypatch):
    """
    Finding: LED-060 (P1)
    Status: CONFIRMED_ON_MAIN
    Red Evidence:
    1. GET /projects/{project_id}/runs/{run_id}/events returns 404 (endpoint does not exist).
    2. RunRepository has no run_events table.
    """
    db_file = tmp_path / "test_runs_060.db"
    monkeypatch.setenv("MOTION_RUNS_DB_PATH", str(db_file))

    project_id = "prj_repro_led060"
    proj_dir = Path(f"projects/{project_id}")
    proj_dir.mkdir(parents=True, exist_ok=True)

    try:
        repo = RunRepository(db_path=db_file)
        conn = repo._get_connection()
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='run_events'"
        )
        table_exists = cur.fetchone() is not None
        conn.close()

        # On main before S22, run_events table does NOT exist
        assert not table_exists, "run_events table already exists before S22 patch"

        client = TestClient(app)
        auth_headers = make_test_auth_headers(principal_id="usr_test_user", roles=["admin"], project_scopes={"*": ["admin"]})
        resp = client.get(f"/projects/{project_id}/runs/run_fake123/events", headers=auth_headers)
        # On main before S22, returns 404
        assert resp.status_code == 404
    finally:
        if proj_dir.exists():
            shutil.rmtree(proj_dir, ignore_errors=True)


# =========================================================================
# LED-062: Cancellation is not real
# =========================================================================
def test_reproduce_led_062_cancellation_endpoint_missing(tmp_path, monkeypatch):
    """
    Finding: LED-062 (P1)
    Status: CONFIRMED_ON_MAIN
    Red Evidence:
    POST /projects/{project_id}/runs/{run_id}/cancel returns 404/405.
    """
    db_file = tmp_path / "test_runs_062.db"
    monkeypatch.setenv("MOTION_RUNS_DB_PATH", str(db_file))

    project_id = "prj_repro_led062"
    proj_dir = Path(f"projects/{project_id}")
    proj_dir.mkdir(parents=True, exist_ok=True)

    try:
        client = TestClient(app)
        auth_headers = make_test_auth_headers(principal_id="usr_test_user", roles=["admin"], project_scopes={"*": ["admin"]})
        resp = client.post(f"/projects/{project_id}/runs/run_dummy/cancel", headers=auth_headers)
        assert resp.status_code == 404
    finally:
        if proj_dir.exists():
            shutil.rmtree(proj_dir, ignore_errors=True)


# =========================================================================
# LED-063: Media Upload / Management API Missing
# =========================================================================
def test_reproduce_led_063_media_upload_management_api_missing():
    """
    Finding: LED-063 (P1)
    Status: CONFIRMED_ON_MAIN
    Red Evidence:
    POST /projects/{project_id}/assets and GET /projects/{project_id}/assets return 404.
    """
    client = TestClient(app)
    auth_headers = make_test_auth_headers(principal_id="usr_test_user", roles=["admin"], project_scopes={"*": ["admin"]})
    resp_get = client.get("/projects/prj_dummy/assets", headers=auth_headers)
    assert resp_get.status_code == 404

    resp_post = client.post("/projects/prj_dummy/assets", headers=auth_headers)
    assert resp_post.status_code == 404


# =========================================================================
# LED-064: Artifact / Reports API Missing
# =========================================================================
def test_reproduce_led_064_artifact_reports_api_missing():
    """
    Finding: LED-064 (P1)
    Status: CONFIRMED_ON_MAIN
    Red Evidence:
    GET /projects/{project_id}/artifacts returns 404.
    """
    client = TestClient(app)
    auth_headers = make_test_auth_headers(principal_id="usr_test_user", roles=["admin"], project_scopes={"*": ["admin"]})
    resp = client.get("/projects/prj_dummy/artifacts", headers=auth_headers)
    assert resp.status_code == 404


# =========================================================================
# LED-065: Video Delivery API Missing
# =========================================================================
def test_reproduce_led_065_video_delivery_api_missing():
    """
    Finding: LED-065 (P1)
    Status: CONFIRMED_ON_MAIN
    Red Evidence:
    GET /projects/{project_id}/outputs/out.mp4 returns 404.
    """
    client = TestClient(app)
    auth_headers = make_test_auth_headers(principal_id="usr_test_user", roles=["admin"], project_scopes={"*": ["admin"]})
    resp = client.get("/projects/prj_dummy/outputs/out.mp4", headers=auth_headers)
    assert resp.status_code == 404


# =========================================================================
# LED-066: Brand API without Contract
# =========================================================================
def test_reproduce_led_066_brand_api_without_contract():
    """
    Finding: LED-066 (P1)
    Status: CONFIRMED_ON_MAIN
    Red Evidence:
    POST /brand/{project_id} accepts arbitrary dict without schema validation
    and writes it directly to disk.
    """
    project_id = "prj_repro_led066"
    proj_dir = Path(f"projects/{project_id}")
    proj_dir.mkdir(parents=True, exist_ok=True)
    brand_file = proj_dir / "brand.json"

    try:
        client = TestClient(app)
        auth_headers = make_test_auth_headers(principal_id="usr_test_user", roles=["admin"], project_scopes={"*": ["admin"]})
        # Ensure brand.json exists initially
        brand_file.write_text("{}", encoding="utf-8")
        # Invalid payload according to brand.schema.json (missing brandName, colors, fonts)
        invalid_payload = {"arbitrary_field": "unvalidated_value"}

        resp = client.post(f"/brand/{project_id}", json=invalid_payload, headers=auth_headers)
        # On main before S22: accepted with 200 and written directly!
        assert resp.status_code == 200
        assert brand_file.exists()
        saved = json.loads(brand_file.read_text(encoding="utf-8"))
        assert saved == invalid_payload
    finally:
        if proj_dir.exists():
            shutil.rmtree(proj_dir, ignore_errors=True)


# =========================================================================
# LED-067: Overrides API without Schema
# =========================================================================
def test_reproduce_led_067_overrides_api_without_schema():
    """
    Finding: LED-067 (P1)
    Status: CONFIRMED_ON_MAIN
    Red Evidence:
    POST /blueprint/{project_id}/overrides accepts dangerous payload without validation.
    """
    project_id = "prj_repro_led067"
    proj_dir = Path(f"projects/{project_id}")
    proj_dir.mkdir(parents=True, exist_ok=True)
    overrides_file = proj_dir / "overrides.json"

    try:
        client = TestClient(app)
        auth_headers = make_test_auth_headers(principal_id="usr_test_user", roles=["admin"], project_scopes={"*": ["admin"]})
        # Dangerous payload containing script injection and invalid structure
        dangerous_payload = {"malicious_key": "javascript:alert('xss')"}

        resp = client.post(f"/blueprint/{project_id}/overrides", json=dangerous_payload, headers=auth_headers)
        # On main before S22: accepted with 200 and written directly!
        assert resp.status_code == 200
        assert overrides_file.exists()
        saved = json.loads(overrides_file.read_text(encoding="utf-8"))
        assert saved == dangerous_payload
    finally:
        if proj_dir.exists():
            shutil.rmtree(proj_dir, ignore_errors=True)


# =========================================================================
# LED-068: Artifact writes not Atomic / Optimistic (Lost Update)
# =========================================================================
def test_reproduce_led_068_lost_update_no_optimistic_concurrency():
    """
    Finding: LED-068 (P0/P1)
    Status: CONFIRMED_ON_MAIN
    Red Evidence:
    POST /brand/{project_id} allows silent overwriting with no ETag or If-Match checking.
    """
    project_id = "prj_repro_led068"
    proj_dir = Path(f"projects/{project_id}")
    proj_dir.mkdir(parents=True, exist_ok=True)

    try:
        (proj_dir / "brand.json").write_text("{}", encoding="utf-8")
        client = TestClient(app)
        auth_headers = make_test_auth_headers(principal_id="usr_test_user", roles=["admin"], project_scopes={"*": ["admin"]})

        # Write A
        client.post(f"/brand/{project_id}", json={"brandName": "BrandA"}, headers=auth_headers)
        # Write B with stale knowledge - on main it overwrites with 200 and no 409 Conflict
        resp = client.post(f"/brand/{project_id}", json={"brandName": "BrandB"}, headers=auth_headers)
        assert resp.status_code == 200  # Should have been 409 Conflict on optimistic concurrency
    finally:
        if proj_dir.exists():
            shutil.rmtree(proj_dir, ignore_errors=True)


# =========================================================================
# LED-069: Router / Service / Repository Mixing
# =========================================================================
def test_reproduce_led_069_router_filesystem_mixing():
    """
    Finding: LED-069 (P2)
    Status: CONFIRMED_ON_MAIN
    Red Evidence:
    api/routers/brand.py and api/routers/blueprint.py call write_text directly.
    """
    brand_router_path = ROOT / "api/routers/brand.py"
    tree = ast.parse(brand_router_path.read_text(encoding="utf-8"))

    has_direct_write = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in ("write_text", "write_bytes"):
            has_direct_write = True
            break

    # On main before S22: True (routers write directly to disk)
    assert has_direct_write, "api/routers/brand.py should have direct write_text before S22 patch"


# =========================================================================
# LED-070: Blocking Project Creation in Async Route
# =========================================================================
def test_reproduce_led_070_blocking_project_creation_in_async_route():
    """
    Finding: LED-070 (P1)
    Status: CONFIRMED_ON_MAIN
    Red Evidence:
    api/routers/projects.py defines an async def create() that calls create_project() synchronously.
    """
    projects_router_path = ROOT / "api/routers/projects.py"
    tree = ast.parse(projects_router_path.read_text(encoding="utf-8"))

    found_sync_call_in_async = False
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "create":
            for subnode in ast.walk(node):
                if isinstance(subnode, ast.Call):
                    func_name = getattr(subnode.func, "id", getattr(subnode.func, "attr", None))
                    if func_name == "create_project":
                        # Check if wrapped in asyncio.to_thread or run_in_executor
                        found_sync_call_in_async = True
                        break

    assert found_sync_call_in_async, "projects.py should have direct sync create_project in async def create"


# =========================================================================
# LED-071: Legacy Lifecycle Facade
# =========================================================================
def test_reproduce_led_071_legacy_lifecycle_facade_and_missing_state_dto():
    """
    Finding: LED-071 (P1)
    Status: CONFIRMED_ON_MAIN
    Red Evidence:
    GET /projects/{project_id}/state does not exist (404),
    and existing get_status formats state into legacy gate names.
    """
    client = TestClient(app)
    auth_headers = make_test_auth_headers(principal_id="usr_test_user", roles=["admin"], project_scopes={"*": ["admin"]})
    resp = client.get("/projects/prj_dummy/state", headers=auth_headers)
    assert resp.status_code == 404


# =========================================================================
# LED-072: Hardcoded CORS
# =========================================================================
def test_reproduce_led_072_hardcoded_cors_origin(monkeypatch):
    """
    Finding: LED-072 (P2)
    Status: CONFIRMED_ON_MAIN
    Red Evidence:
    CORS middleware on main only allows http://localhost:3000.
    Setting MOTION_CORS_ALLOWED_ORIGINS environment variable has no effect.
    """
    monkeypatch.setenv("MOTION_CORS_ALLOWED_ORIGINS", "https://app.custom-domain.com")
    client = TestClient(app)
    headers = {"Origin": "https://app.custom-domain.com"}
    resp = client.get("/health", headers=headers)
    # On main before S22: Access-Control-Allow-Origin header is NOT https://app.custom-domain.com
    assert resp.headers.get("access-control-allow-origin") != "https://app.custom-domain.com"
