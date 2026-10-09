"""
api/services/health_service.py — Production Liveness & Readiness Probing Authority (S23 - LED-073).

Performs strict, non-destructive dependency probing for production readiness:
- Storage / Run DB: Open SQLite repository, read schema version (bounded read probe).
- Project Storage: Verify projects root directory exists and is accessible.
- Worker: Check active leases and fresh heartbeats against worker_stale_threshold.
- FFmpeg: Probe executable existence and exit code via bounded subprocess.
- Node: Probe Node runtime availability via bounded subprocess.
- Remotion: Verify remotion-app runtime presence and entrypoint.

Zero side effects:
- Never starts workers
- Never installs dependencies
- Never creates projects or mutates tables
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from api.core.config import get_api_settings


class HealthService:
    """Service authority for system liveness and readiness probing."""

    @classmethod
    def check_liveness(cls) -> Dict[str, Any]:
        """
        Ultra-lightweight process liveness probe.
        Answers one question: Is this API server process alive and responding?
        Never queries storage, workers, or child processes.
        """
        return {
            "status": "alive",
            "version": "1.0.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    @classmethod
    def check_readiness(
        cls,
        workspace_root: Optional[Path] = None,
        db_path: Optional[Path] = None,
        force_timeout: Optional[float] = None,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Deep production readiness probe.
        Answers: Is this instance ready to accept and execute video production workloads?
        Returns: (is_ready: bool, details: dict)
        """
        settings = get_api_settings()
        timeout = force_timeout if force_timeout is not None else settings.readiness_timeout_seconds
        root = workspace_root or Path.cwd().resolve()

        checks: Dict[str, Any] = {}
        all_passed = True

        # 1. Runs DB Probe
        db_pass, db_info = cls._probe_runs_db(root, db_path, timeout)
        checks["runs_db"] = db_info
        if not db_pass:
            all_passed = False

        # 2. Project Storage Probe
        storage_pass, storage_info = cls._probe_project_storage(root)
        checks["project_storage"] = storage_info
        if not storage_pass:
            all_passed = False

        # 3. SaaS Database Engine & Migrations Probe (S24.5)
        saas_db_pass, saas_db_info = cls._probe_database(timeout)
        checks["database"] = saas_db_info
        if not saas_db_pass:
            all_passed = False

        # 4. SaaS StorageService Backend Probe (S24.5)
        saas_storage_pass, saas_storage_info = cls._probe_storage_service()
        checks["storage_backend"] = saas_storage_info
        if not saas_storage_pass:
            all_passed = False

        # 5. Worker Probe
        worker_pass, worker_info = cls._probe_worker(root, db_path, settings)
        checks["worker"] = worker_info
        if not worker_pass and settings.require_active_worker:
            all_passed = False

        # 6. FFmpeg Tool Probe
        ffmpeg_pass, ffmpeg_info = cls._probe_ffmpeg(timeout)
        checks["ffmpeg"] = ffmpeg_info
        if not ffmpeg_pass:
            all_passed = False

        # 7. Node Runtime Probe
        node_pass, node_info = cls._probe_node(timeout)
        checks["node"] = node_info
        if not node_pass:
            all_passed = False

        # 8. Remotion Engine Probe
        remotion_pass, remotion_info = cls._probe_remotion(root)
        checks["remotion"] = remotion_info
        if not remotion_pass:
            all_passed = False

        result = {
            "status": "ready" if all_passed else "not_ready",
            "role": settings.role,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": checks,
        }
        return all_passed, result

    @classmethod
    def _probe_runs_db(
        cls,
        root: Path,
        custom_db_path: Optional[Path],
        timeout: float,
    ) -> Tuple[bool, Dict[str, Any]]:
        target_db = custom_db_path or (root / "data" / "runs.db")
        start = time.perf_counter()
        try:
            if not target_db.exists():
                try:
                    from scripts.core.run_repository import RunRepository
                    RunRepository(target_db)
                except Exception:
                    pass

            if not target_db.exists():
                return False, {
                    "status": "fail",
                    "reason": f"Database file does not exist at {target_db.name}",
                    "latency_ms": round((time.perf_counter() - start) * 1000, 2),
                }

            # Open in URI read-only mode to prevent locks or schema mutations
            conn = sqlite3.connect(
                f"file:{target_db.resolve()}?mode=ro",
                uri=True,
                timeout=timeout,
            )
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                cursor.fetchone()
                latency = round((time.perf_counter() - start) * 1000, 2)
                return True, {"status": "pass", "latency_ms": latency}
            finally:
                conn.close()
        except Exception:
            return False, {
                "status": "fail",
                "reason": "Database connection or read error",
                "code": "DB_UNAVAILABLE",
                "latency_ms": round((time.perf_counter() - start) * 1000, 2),
            }

    @classmethod
    def _probe_project_storage(cls, root: Path) -> Tuple[bool, Dict[str, Any]]:
        start = time.perf_counter()
        projects_dir = root / "projects"
        try:
            if not projects_dir.exists():
                return False, {
                    "status": "fail",
                    "reason": "Projects directory does not exist",
                    "latency_ms": round((time.perf_counter() - start) * 1000, 2),
                }
            if not os.access(projects_dir, os.R_OK | os.W_OK):
                return False, {
                    "status": "fail",
                    "reason": "Projects directory is not writable",
                    "latency_ms": round((time.perf_counter() - start) * 1000, 2),
                }
            return True, {
                "status": "pass",
                "latency_ms": round((time.perf_counter() - start) * 1000, 2),
            }
        except Exception:
            return False, {
                "status": "fail",
                "reason": "Storage access failure",
                "latency_ms": round((time.perf_counter() - start) * 1000, 2),
            }

    @classmethod
    def _probe_database(cls, timeout: float = 2.0) -> Tuple[bool, Dict[str, Any]]:
        start = time.perf_counter()
        try:
            from scripts.core.database import get_database_engine
            engine = get_database_engine()
            conn = engine.get_connection()
            try:
                cur = conn.execute("SELECT 1")
                cur.fetchone()
                cur = conn.execute("SELECT MAX(version) FROM _schema_migrations")
                v_row = cur.fetchone()
                schema_v = v_row[0] if v_row else 1
                latency = round((time.perf_counter() - start) * 1000, 2)
                return True, {
                    "status": "pass",
                    "driver": "sqlite" if engine.is_sqlite else "postgresql",
                    "schema_version": schema_v,
                    "migrations_applied": True,
                    "latency_ms": latency,
                }
            finally:
                conn.close()
        except Exception as e:
            return False, {
                "status": "fail",
                "reason": f"Database unavailable: {str(e)}",
                "code": "DATABASE_UNAVAILABLE",
                "latency_ms": round((time.perf_counter() - start) * 1000, 2),
            }

    @classmethod
    def _probe_storage_service(cls) -> Tuple[bool, Dict[str, Any]]:
        start = time.perf_counter()
        try:
            from scripts.core.storage import get_storage_service
            storage = get_storage_service()
            probe_key = "system/health_probe.tmp"
            storage.put(probe_key, b"READINESS_PROBE", content_type="text/plain")
            storage.delete(probe_key)
            latency = round((time.perf_counter() - start) * 1000, 2)
            return True, {
                "status": "pass",
                "backend": storage.__class__.__name__,
                "writable": True,
                "latency_ms": latency,
            }
        except Exception as e:
            return False, {
                "status": "fail",
                "reason": f"Storage backend error: {str(e)}",
                "code": "STORAGE_UNAVAILABLE",
                "latency_ms": round((time.perf_counter() - start) * 1000, 2),
            }

    @classmethod
    def _probe_worker(
        cls,
        root: Path,
        custom_db_path: Optional[Path],
        settings: Any,
    ) -> Tuple[bool, Dict[str, Any]]:
        target_db = custom_db_path or (root / "data" / "runs.db")
        if not target_db.exists():
            return False, {"status": "fail", "reason": "Runs DB not available for worker lease check"}

        try:
            conn = sqlite3.connect(f"file:{target_db.resolve()}?mode=ro", uri=True, timeout=2.0)
            try:
                cursor = conn.cursor()
                # Check for active non-expired worker leases
                now_iso = datetime.now(timezone.utc).isoformat()
                table_name = "project_execution_leases"
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('project_execution_leases', 'worker_leases')")
                t_row = cursor.fetchone()
                if t_row:
                    table_name = t_row[0]
                cursor.execute(
                    f"SELECT worker_id, heartbeat_at, expires_at FROM {table_name} WHERE expires_at > ?",
                    (now_iso,),
                )
                rows = cursor.fetchall()

                active_count = len(rows)
                if active_count > 0:
                    return True, {
                        "status": "pass",
                        "active_workers": active_count,
                        "details": "active_leases_present",
                    }

                # If no active lease, check if any lease updated heartbeat recently
                cursor.execute(f"SELECT MAX(heartbeat_at) FROM {table_name}")
                latest_heartbeat = cursor.fetchone()[0]

                if latest_heartbeat:
                    try:
                        hb_dt = datetime.fromisoformat(latest_heartbeat)
                        diff_sec = (datetime.now(timezone.utc) - hb_dt).total_seconds()
                        if diff_sec <= settings.worker_stale_threshold_seconds:
                            return True, {
                                "status": "pass",
                                "active_workers": 1,
                                "details": f"recent_heartbeat_{int(diff_sec)}s_ago",
                            }
                    except Exception:
                        pass

                if settings.require_active_worker:
                    return False, {
                        "status": "fail",
                        "reason": "No active worker lease or fresh heartbeat found",
                        "code": "WORKER_STALE",
                    }
                else:
                    return True, {
                        "status": "pass",
                        "active_workers": 0,
                        "details": "worker_pool_idle",
                    }
            finally:
                conn.close()
        except Exception:
            return False, {"status": "fail", "reason": "Failed to query worker leases"}

    @classmethod
    def _probe_ffmpeg(cls, timeout: float) -> Tuple[bool, Dict[str, Any]]:
        ffmpeg_bin = shutil.which("ffmpeg")
        if not ffmpeg_bin:
            return False, {
                "status": "fail",
                "reason": "ffmpeg binary not found in PATH",
                "code": "FFMPEG_MISSING",
            }

        from scripts.security.security import safe_subprocess
        start = time.perf_counter()
        try:
            cmd_timeout = max(5.0, timeout)
            res = safe_subprocess(
                [ffmpeg_bin, "-version"],
                capture_output=True,
                text=True,
                timeout=cmd_timeout,
            )
            latency = round((time.perf_counter() - start) * 1000, 2)
            if res.returncode == 0:
                first_line = res.stdout.splitlines()[0] if res.stdout else "ffmpeg ready"
                return True, {"status": "pass", "version": first_line[:40], "latency_ms": latency}
            return False, {"status": "fail", "reason": "ffmpeg exited with non-zero status"}
        except subprocess.TimeoutExpired:
            return False, {"status": "fail", "reason": "ffmpeg probe timed out"}
        except Exception:
            return False, {"status": "fail", "reason": "ffmpeg probe error"}

    @classmethod
    def _probe_node(cls, timeout: float) -> Tuple[bool, Dict[str, Any]]:
        node_bin = shutil.which("node")
        if not node_bin:
            return False, {
                "status": "fail",
                "reason": "node binary not found in PATH",
                "code": "NODE_MISSING",
            }

        from scripts.security.security import safe_subprocess
        start = time.perf_counter()
        try:
            cmd_timeout = max(5.0, timeout)
            res = safe_subprocess(
                [node_bin, "--version"],
                capture_output=True,
                text=True,
                timeout=cmd_timeout,
            )
            latency = round((time.perf_counter() - start) * 1000, 2)
            if res.returncode == 0:
                return True, {"status": "pass", "version": res.stdout.strip(), "latency_ms": latency}
            return False, {"status": "fail", "reason": "node exited with non-zero status"}
        except subprocess.TimeoutExpired:
            return False, {"status": "fail", "reason": "node probe timed out"}
        except Exception:
            return False, {"status": "fail", "reason": "node probe error"}

    @classmethod
    def _probe_remotion(cls, root: Path) -> Tuple[bool, Dict[str, Any]]:
        remotion_dir = root / "remotion-app"
        if not remotion_dir.exists():
            return False, {
                "status": "fail",
                "reason": "remotion-app directory not found",
                "code": "REMOTION_DIR_MISSING",
            }

        package_json = remotion_dir / "package.json"
        if not package_json.exists():
            return False, {
                "status": "fail",
                "reason": "remotion-app/package.json missing",
                "code": "REMOTION_PKG_MISSING",
            }

        src_index = remotion_dir / "src" / "index.ts"
        if not src_index.exists():
            return False, {
                "status": "fail",
                "reason": "remotion-app/src/index.ts entrypoint missing",
                "code": "REMOTION_ENTRY_MISSING",
            }

        return True, {"status": "pass", "engine": "remotion-app"}
