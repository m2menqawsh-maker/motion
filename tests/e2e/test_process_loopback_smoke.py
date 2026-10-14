"""
tests/e2e/test_process_loopback_smoke.py
========================================
Isolated process-level smoke test verifying MOTION as an independently deployed
backend product over a real loopback network connection.

Guarantees:
1. Spawns API server (Uvicorn) as an independent operating system process.
2. Exercises HTTP routing and media retrieval over real loopback TCP (http://127.0.0.1:<port>).
3. Uses an isolated disposable SQLite database.
4. Executes background worker in a separate operating system process.
5. Verifies safe worker process restart and lease recovery behavior.
6. Retrieves media artifact over HTTP 206 range streaming.
7. Validates MP4 bytes using ffprobe.
8. 100% deterministic and free of external AI provider calls.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import time
import wave
from pathlib import Path

import httpx
import pytest

from tests.factories.canonical_factory import create_canonical_blueprint


def get_free_loopback_port() -> int:
    """Binds to ephemeral port on loopback and releases it to get an available port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def test_isolated_process_loopback_smoke(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """
    Independent process-level verification:
    Real HTTP loopback -> Process API -> Disposable SQL DB -> Process Worker -> Render -> HTTP 206 MP4.
    """
    port = get_free_loopback_port()
    db_file = tmp_path / "smoke_runs.db"
    db_url = f"sqlite:///{db_file}"
    workspace_root = Path.cwd().resolve()

    # Configure environment for current process and child processes
    monkeypatch.setenv("MOTION_ENV", "test")
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("MOTION_DATABASE_URL", db_url)
    monkeypatch.setenv("RUNS_DB_PATH", str(db_file))
    monkeypatch.setenv("MOTION_RUNS_DB_PATH", str(db_file))
    monkeypatch.setenv("PYTHONPATH", str(workspace_root))
    monkeypatch.setenv("TESTING", "1")
    monkeypatch.setenv("AGY_IS_MANAGED", "1")

    env = os.environ.copy()

    # Pre-seed disposable database with authenticated tenant credentials
    from scripts.core.database import DatabaseEngine, TenantRepository, set_database_engine
    from scripts.core.security.principal import Principal, PrincipalType, Role
    from api.core.auth import create_signed_token

    db_engine = DatabaseEngine(db_url)
    set_database_engine(db_engine)
    tenant_repo = TenantRepository(db_engine)
    
    ws_smoke = "ws_smoke_corp"
    usr_smoke = "usr_smoke_admin"
    tenant_repo.create_user(usr_smoke, "smoke@example.com")
    tenant_repo.create_workspace(ws_smoke, "Smoke Corp Workspace", created_by=usr_smoke)
    tenant_repo.add_member(ws_smoke, usr_smoke, Role.ADMIN)

    principal = Principal(
        principal_id=usr_smoke,
        principal_type=PrincipalType.HUMAN,
        roles={Role.ADMIN},
        project_scopes={"*": {Role.ADMIN}},
        auth_method="SIGNED_BEARER_TOKEN",
    )
    token = create_signed_token(principal)
    auth_headers = {"Authorization": f"Bearer {token}", "X-Workspace-ID": ws_smoke}

    # 1. Start the API server in an independent OS subprocess
    api_cmd = [
        sys.executable,
        "-m",
        "uvicorn",
        "api.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
        "--log-level",
        "warning",
    ]
    api_proc = subprocess.Popen(api_cmd, env=env, cwd=str(workspace_root))

    proj_dir = None
    try:
        # Wait for API server to become responsive on /health/live
        base_url = f"http://127.0.0.1:{port}"
        started = False
        with httpx.Client(base_url=base_url, timeout=10.0, follow_redirects=True) as client:
            for _ in range(50):
                time.sleep(0.2)
                try:
                    resp = client.get("/health/live")
                    if resp.status_code == 200:
                        started = True
                        break
                except Exception:
                    pass

            assert started, f"API server failed to start on {base_url} within 10 seconds"

            # 2. Test authentic HTTP requests over real loopback connection
            # Create Project via HTTP POST /projects/
            proj_resp = client.post("/projects/", headers=auth_headers, json={"name": "Smoke Test Video"})
            assert proj_resp.status_code == 200, f"Project creation failed: {proj_resp.text}"
            project_id = proj_resp.json()["project_id"]

            proj_dir = workspace_root / "projects" / ws_smoke / project_id
            proj_dir.mkdir(parents=True, exist_ok=True)
            assets_dir = proj_dir / "assets"
            assets_dir.mkdir(parents=True, exist_ok=True)

            # Generate advisory AI creative proposal via HTTP POST /projects/{id}/creative/proposals
            proposal_req = {
                "prompt": "Create an independent smoke test video",
                "aspect_ratio": "16:9",
                "target_duration": 1.0,
            }
            proposal_resp = client.post(
                f"/projects/{project_id}/creative/proposals",
                headers=auth_headers,
                json=proposal_req,
            )
            assert proposal_resp.status_code == 200, f"Proposal failed: {proposal_resp.text}"
            proposal_data = proposal_resp.json()
            proposal_id = proposal_data["proposal_id"]

            # Apply proposal via HTTP POST /projects/{id}/creative/apply
            canonical_bp = create_canonical_blueprint(
                project_id=project_id,
                template="animatedtext-element",
                aspect="16:9",
                fps=30,
                duration_frames=30,
                assets=[],
                audio={"voiceover": None, "music": None, "global_sfx": []},
            )
            apply_payload = {
                "proposal_id": proposal_id,
                "blueprint": canonical_bp,
                "base_revision": 1,
                "operation_id": "op_smoke_proposal_apply",
            }
            apply_resp = client.post(
                f"/projects/{project_id}/creative/apply",
                headers={**auth_headers, "If-Match": '"1"', "Idempotency-Key": "op_smoke_proposal_apply"},
                json=apply_payload,
            )
            assert apply_resp.status_code == 200, f"Apply failed: {apply_resp.text}"

            # Write master plan and supporting metadata
            (proj_dir / "02_asset_manifest.json").write_text(json.dumps({"project_id": project_id, "assets": []}), encoding="utf-8")
            (proj_dir / "04_timings.json").write_text(json.dumps({"words": []}), encoding="utf-8")
            (proj_dir / "media_map.json").write_text(json.dumps({}), encoding="utf-8")
            brand_data = {
                "brandName": "Smoke Video",
                "logoSrc": None,
                "colors": {"primary": "#00F5FF", "accent": "#FFD700", "background": "#1a2238", "text": "#FFFFFF"},
                "fonts": {"display": "Cairo", "body": "Cairo"},
            }
            (proj_dir / "brand.json").write_text(json.dumps(brand_data), encoding="utf-8")
            (proj_dir / "master_plan.md").write_text("# Smoke Master Plan\n- Scene 1: 1.0s\n", encoding="utf-8")

            # Initialize state and execute Probe QC
            from scripts.core.state_store import StateStore, ValidationLevel, LifecycleState
            from scripts.core.lifecycle_service import LifecycleService
            from scripts.gates.probe_qc import run_probe_qc

            st = StateStore.load(proj_dir)
            st.workspace_id = ws_smoke
            st.lifecycle_state = LifecycleState.MATERIALIZED
            st.record_evidence(StateStore.create_artifact_record(proj_dir, "05_blueprint.json", ValidationLevel.SHA256))
            st.record_evidence(StateStore.create_artifact_record(proj_dir, "master_plan.md", ValidationLevel.SHA256))
            StateStore.save(proj_dir, st)

            qc_res = run_probe_qc(project_id, workspace_id=ws_smoke)
            assert qc_res.get("status") == "PASS", f"Probe QC failed: {qc_res}"

            LifecycleService.transition(proj_dir, LifecycleState.PROBE_PASSED, artifacts=[
                ("probe_qc_report.json", ValidationLevel.SHA256),
                ("contact_sheet.png", ValidationLevel.SHA256),
            ])
            LifecycleService.transition(proj_dir, LifecycleState.AWAITING_REVIEW)

            # Retrieve Review Bundle via HTTP GET /projects/{id}/review
            rev_resp = client.get(f"/projects/{project_id}/review", headers=auth_headers)
            assert rev_resp.status_code == 200
            active_bundle = rev_resp.json().get("active_bundle")
            assert active_bundle is not None
            bundle_id = active_bundle["review_bundle_id"]

            # Approve via HTTP POST /projects/{id}/review/approve
            app_resp = client.post(
                f"/projects/{project_id}/review/approve",
                headers=auth_headers,
                json={"bundle_id": bundle_id, "reason": "Smoke Process Approved"},
            )
            assert app_resp.status_code == 200

            # Enqueue Run via HTTP POST /projects/{id}/runs
            run_resp = client.post(
                f"/projects/{project_id}/runs",
                headers={**auth_headers, "Idempotency-Key": "smoke_run_idemp_01"},
                json={"approved_review_bundle_id": bundle_id, "idempotency_key": "smoke_run_idemp_01"},
            )
            assert run_resp.status_code == 202
            run_id = run_resp.json()["run_id"]

            # 3. Demonstrate genuine worker crash recovery and lease transfer
            # Step 3a: Worker 1 claims durable lease with short duration (1.0s) and starts processing
            w1_cmd = [
                sys.executable,
                "-c",
                f"import sys, time; sys.path.insert(0, '.'); from scripts.core.worker import PipelineWorker; "
                f"w = PipelineWorker(worker_id='w_crash_victim', db_path='{db_file}', lease_duration=1.0); "
                f"claimed = w.repo.claim_next_run(worker_id='w_crash_victim', lease_duration_seconds=1.0); "
                f"assert claimed is not None, 'Worker 1 failed to claim run'; "
                f"time.sleep(30)",  # Abruptly killed while holding active lease
            ]
            w1_proc = subprocess.Popen(w1_cmd, env=env, cwd=str(workspace_root))

            # Verify in DB that Worker 1 genuinely claimed and holds the active lease
            from scripts.core.run_repository import RunRepository
            smoke_repo = RunRepository(db_path=db_file)
            claimed_by_w1 = False
            for _ in range(40):
                time.sleep(0.1)
                r_check = smoke_repo.get_run(run_id)
                if r_check and r_check.worker_id == "w_crash_victim":
                    claimed_by_w1 = True
                    break
            assert claimed_by_w1, "Worker 1 failed to record durable lease claim in database"
            assert smoke_repo.is_lease_active(run_id, "w_crash_victim"), "Worker 1 lease was not active"

            # Step 3b: Worker 1 terminates abruptly (hard crash via kill / SIGKILL)
            w1_proc.kill()
            w1_proc.wait(timeout=5)

            # Step 3c: Wait for Worker 1's lease to expire (1.0s duration + margin)
            time.sleep(1.2)
            assert not smoke_repo.is_lease_active(run_id, "w_crash_victim"), "Worker 1 lease should be expired"

            # Step 3d: Spawn Worker 2 in a fresh OS process.
            # Worker 2 runs orphan recovery pass, fences/reclaims the expired run, and completes execution
            w2_cmd = [
                sys.executable,
                "-c",
                f"import sys; sys.path.insert(0, '.'); from scripts.core.worker import PipelineWorker; "
                f"w = PipelineWorker(worker_id='w_smoke_active', db_path='{db_file}'); "
                f"processed = w.process_one(); sys.exit(0 if processed else 1)",
            ]
            w2_res = subprocess.run(w2_cmd, env=env, cwd=str(workspace_root), capture_output=True, text=True, timeout=90)
            assert w2_res.returncode == 0, f"Worker process failed:\nSTDOUT: {w2_res.stdout}\nSTDERR: {w2_res.stderr}"

            # Verify that Worker 2 recovered the run and attempt counter was incremented
            recovered_run = smoke_repo.get_run(run_id)
            assert recovered_run is not None
            assert recovered_run.worker_id == "w_smoke_active", f"Expected w_smoke_active, got {recovered_run.worker_id}"
            assert recovered_run.attempt >= 2, f"Expected attempt >= 2 after crash recovery, got {recovered_run.attempt}"

            # 4. Verify run status via HTTP GET /projects/{id}/runs/{run_id}
            run_stat_resp = client.get(f"/projects/{project_id}/runs/{run_id}", headers=auth_headers)
            assert run_stat_resp.status_code == 200
            run_stat = run_stat_resp.json()
            assert run_stat["status"] == "SUCCEEDED", f"Run did not succeed: {run_stat}"

            # 5. Media retrieval over HTTP Range Streaming (HTTP 206)
            artifacts_resp = client.get(f"/projects/{project_id}/artifacts", headers=auth_headers)
            assert artifacts_resp.status_code == 200
            artifacts = artifacts_resp.json().get("artifacts", [])
            mp4_items = [a for a in artifacts if a.get("filename") == "out.mp4" or str(a.get("kind")) == "render_output"]
            assert len(mp4_items) > 0, f"No MP4 artifact found in inventory: {artifacts}"

            # Stream byte range over real TCP loopback
            range_resp = client.get(
                f"/projects/{project_id}/outputs/out.mp4",
                headers={**auth_headers, "Range": "bytes=0-1023"},
            )
            assert range_resp.status_code == 206, f"Expected 206 Partial Content, got {range_resp.status_code}"
            assert range_resp.headers.get("Content-Range", "").startswith("bytes 0-1023/")
            assert len(range_resp.content) == 1024

            # Full download over real TCP loopback
            full_resp = client.get(
                f"/projects/{project_id}/outputs/out.mp4",
                headers=auth_headers,
            )
            assert full_resp.status_code == 200
            assert full_resp.headers.get("Content-Type") == "video/mp4"
            assert len(full_resp.content) > 10000

            # 6. ffprobe verification of received media bytes
            saved_mp4 = tmp_path / "smoke_received.mp4"
            saved_mp4.write_bytes(full_resp.content)
            ff_res = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration,size", "-show_streams", "-print_format", "json", str(saved_mp4)],
                capture_output=True,
                text=True,
                check=True,
            )
            meta = json.loads(ff_res.stdout)
            video_streams = [s for s in meta.get("streams", []) if s.get("codec_type") == "video"]
            assert len(video_streams) > 0, "No video stream in retrieved media file"
            assert video_streams[0]["codec_name"] == "h264"
            assert video_streams[0]["width"] == 1920
            assert video_streams[0]["height"] == 1080

    finally:
        set_database_engine(None)
        # Graceful cleanup of background API server
        if api_proc.poll() is None:
            api_proc.terminate()
            try:
                api_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                api_proc.kill()
                api_proc.wait()
        # Clean up project directory from disk
        if proj_dir and proj_dir.exists():
            shutil.rmtree(proj_dir, ignore_errors=True)
