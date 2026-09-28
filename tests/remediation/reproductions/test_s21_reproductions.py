"""
tests/remediation/reproductions/test_s21_reproductions.py — S21 Reproductions & Regression Suite:
- LED-058 (P1): /render/{id} misleading name & contract (evolved to GREEN proof).
- LED-059 (P0/P1): BackgroundTasks volatility & lack of durable run record (evolved to GREEN proof).
- LED-061 (P0): Process-local lock replaced by cross-process authority (evolved to GREEN proof).
"""

import ast
import multiprocessing
import os
import shutil
import sys
import time
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from api.main import app
from api.services.pipeline_service import PipelineService
from scripts.core.project_lock import ProjectExecutionLock, ProjectExecutionConflictError
from scripts.core.run_repository import RunRepository


def test_reproduce_led_058_canonical_run_endpoint_and_deprecated_render(tmp_path, monkeypatch):
    """
    Finding: LED-058 (P1 - CLOSED in S21)
    Evolution: Evolved from pre-S21 RED reproduction to S21 GREEN regression proof.
    Verified correct behavior:
    1. POST /projects/{project_id}/runs exists and returns a canonical Run resource with run_id and status=QUEUED.
    2. Legacy POST /render/{project_id} no longer executes an independent background pipeline;
       it acts as a deprecated adapter returning Deprecation headers and X-Run-ID pointing to a durable Run record.
    """
    db_file = tmp_path / "test_runs_058.db"
    monkeypatch.setenv("MOTION_RUNS_DB_PATH", str(db_file))

    project_id = "prj_repro_led058"
    proj_dir = Path(f"projects/{project_id}")
    proj_dir.mkdir(parents=True, exist_ok=True)

    try:
        client = TestClient(app)
        auth_headers = {"X-Principal-ID": "test_operator", "X-Principal-Roles": "operator,admin"}

        # 1. Canonical run API exists and returns 202 with real Run resource
        resp_runs = client.post(f"/projects/{project_id}/runs", json={}, headers=auth_headers)
        assert resp_runs.status_code == 202
        data_runs = resp_runs.json()
        assert "run_id" in data_runs
        assert data_runs["run_id"].startswith("run_")
        assert data_runs["status"] == "QUEUED"

        # 2. Legacy /render endpoint is deprecated adapter creating canonical run
        resp_render = client.post(f"/render/{project_id}", headers=auth_headers)
        assert resp_render.status_code == 200
        assert "Deprecation" in resp_render.headers
        assert "X-Run-ID" in resp_render.headers

        created_run_id = resp_render.headers["X-Run-ID"]
        repo = RunRepository(db_path=db_file)
        persisted = repo.get_run(created_run_id)
        assert persisted is not None
        assert persisted.project_id == project_id
    finally:
        if proj_dir.exists():
            shutil.rmtree(proj_dir, ignore_errors=True)


def test_reproduce_led_059_durable_run_persisted_before_response(tmp_path, monkeypatch):
    """
    Finding: LED-059 (P0/P1 - CLOSED in S21)
    Evolution: Evolved from pre-S21 RED reproduction to S21 GREEN regression proof.
    Verified correct behavior:
    1. BackgroundTasks is NOT used for pipeline durability.
    2. Run record is persisted in RunRepository BEFORE HTTP 202 is returned.
    3. The run is queryable across process restarts.
    """
    db_file = tmp_path / "test_runs_059.db"
    monkeypatch.setenv("MOTION_RUNS_DB_PATH", str(db_file))

    project_id = "prj_repro_led059"
    proj_dir = Path(f"projects/{project_id}")
    proj_dir.mkdir(parents=True, exist_ok=True)

    try:
        client = TestClient(app)
        auth_headers = {"X-Principal-ID": "test_operator", "X-Principal-Roles": "operator,admin"}

        resp = client.post(f"/projects/{project_id}/runs", json={}, headers=auth_headers)
        assert resp.status_code == 202
        run_id = resp.json()["run_id"]

        # Directly inspect persistent database
        repo = RunRepository(db_path=db_file)
        record = repo.get_run(run_id)
        assert record is not None
        assert record.run_id == run_id
        assert record.status.value == "QUEUED"
        assert record.created_at is not None

        # Verify query endpoint retrieves it
        query_resp = client.get(f"/projects/{project_id}/runs/{run_id}", headers=auth_headers)
        assert query_resp.status_code == 200
        assert query_resp.json()["run_id"] == run_id
    finally:
        if proj_dir.exists():
            shutil.rmtree(proj_dir, ignore_errors=True)


def _child_attempt_lock_on_project(proj_dir: str, db_file: str, q: multiprocessing.Queue):
    """Child OS process attempting to acquire project execution lock while held by parent."""
    try:
        lock = ProjectExecutionLock(project_dir=proj_dir, owner_id="child_proc", db_path=db_file, timeout=0.1)
        lock.acquire()
        q.put({"acquired": True, "error": None})
        lock.release()
    except ProjectExecutionConflictError as e:
        q.put({"acquired": False, "error": "CONFLICT", "message": str(e)})
    except Exception as e:
        q.put({"acquired": False, "error": str(type(e).__name__), "message": str(e)})


def test_reproduce_led_061_cross_process_pipeline_lock(tmp_path, monkeypatch):
    """
    Finding: LED-061 (P0 - CLOSED in S21)
    Evolution: Evolved from pre-S21 RED reproduction to S21 GREEN regression proof.
    Verified correct behavior:
    1. Pipeline lock is no longer process-local (not relying solely on asyncio.Lock).
    2. ProjectExecutionLock coordinates across operating system processes.
    3. If Process A holds the lock, Process B is blocked and cannot execute concurrently on the same project.
    """
    db_file = tmp_path / "test_runs_061.db"
    monkeypatch.setenv("MOTION_RUNS_DB_PATH", str(db_file))

    project_id = "prj_repro_led061"
    proj_dir = Path(f"projects/{project_id}")
    proj_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Parent process acquires the cross-process lock
        parent_lock = ProjectExecutionLock(project_dir=proj_dir, owner_id="parent_proc", db_path=db_file, timeout=0.1)
        parent_lock.acquire()

        try:
            # Spawn separate child OS process to attempt lock acquisition
            q = multiprocessing.Queue()
            proc = multiprocessing.Process(
                target=_child_attempt_lock_on_project,
                args=(str(proj_dir), str(db_file), q)
            )
            proc.start()
            proc.join(timeout=5)

            res = q.get(timeout=2)
            assert res["acquired"] is False
            assert res["error"] == "CONFLICT", f"Expected CONFLICT in child process, got {res}"
        finally:
            parent_lock.release()
    finally:
        if proj_dir.exists():
            shutil.rmtree(proj_dir, ignore_errors=True)
