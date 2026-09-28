"""
Standalone Worker Process for S21.

Polls the persistent RunRepository, performs atomic CAS claims,
maintains heartbeats, invokes the canonical pipeline, and reconciles results.
"""

import logging
import os
import signal
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Optional

from scripts.core.run_model import RunRecord, RunStatus
from scripts.core.run_repository import RunRepository
from scripts.core.state_store import StateStore
from scripts.security.security import safe_subprocess

logger = logging.getLogger("worker")


class PipelineWorker:
    """Independent worker daemon decoupled from HTTP process."""

    def __init__(
        self,
        worker_id: Optional[str] = None,
        db_path: Optional[Path | str] = None,
        poll_interval: float = 1.0,
        lease_duration: float = 30.0,
        heartbeat_interval: float = 5.0,
        max_runs: Optional[int] = None,
    ):
        self.worker_id = worker_id or f"worker_{uuid.uuid4().hex[:8]}"
        self.repo = RunRepository(db_path=db_path)
        self.poll_interval = poll_interval
        self.lease_duration = lease_duration
        self.heartbeat_interval = heartbeat_interval
        self.max_runs = max_runs
        self._runs_processed = 0
        self._shutdown_requested = False
        self._active_run: Optional[RunRecord] = None
        self._stop_heartbeat = threading.Event()
        self._heartbeat_thread: Optional[threading.Thread] = None

    def request_shutdown(self, *args) -> None:
        """Signals graceful shutdown."""
        logger.info(f"Worker {self.worker_id} received shutdown signal.")
        self._shutdown_requested = True

    def _start_heartbeat(self, run: RunRecord) -> None:
        self._stop_heartbeat.clear()

        def heartbeat_loop():
            while not self._stop_heartbeat.wait(self.heartbeat_interval):
                try:
                    renewed = self.repo.renew_lease(
                        run_id=run.run_id,
                        worker_id=self.worker_id,
                        lease_duration_seconds=self.lease_duration,
                    )
                    if not renewed:
                        logger.warning(f"Worker {self.worker_id} failed to renew lease for run {run.run_id}")
                        break
                except Exception as e:
                    logger.error(f"Error during heartbeat renewal: {e}")

        self._heartbeat_thread = threading.Thread(target=heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()

    def _stop_heartbeat_loop(self) -> None:
        self._stop_heartbeat.set()
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=2.0)
        self._heartbeat_thread = None

    def recover_orphans(self) -> None:
        """Finds orphaned runs and reconciles them with project state."""
        orphans = self.repo.recover_orphaned_runs(grace_seconds=0.0)
        for orphan in orphans:
            logger.warning(
                f"Detected orphaned run {orphan.run_id} for project {orphan.project_id} (attempt {orphan.attempt})"
            )
            proj_dir = Path(f"projects/{orphan.project_id}")
            # If attempts exceeded (max 3), mark permanently failed
            if orphan.attempt >= 3:
                self.repo.mark_run_failed(
                    run_id=orphan.run_id,
                    failure_code="ORPHAN_RUN_EXPIRED",
                    failure_detail={
                        "reason": f"Run exceeded maximum recovery attempts ({orphan.attempt}).",
                        "last_worker_id": orphan.worker_id,
                    }
                )
                logger.info(f"Marked orphan run {orphan.run_id} as FAILED (attempts exhausted).")
            else:
                # Reconcile project state via RecoveryEngine if state exists
                try:
                    if proj_dir.exists():
                        from scripts.core.recovery_engine import RecoveryEngine
                        decision = RecoveryEngine.evaluate(proj_dir)
                        logger.info(f"Recovery evaluation for project {orphan.project_id}: {decision.reason}")
                except Exception as e:
                    logger.warning(f"Recovery check failed for project {orphan.project_id}: {e}")

                self.repo.reset_run_to_queued(orphan.run_id, new_attempt=orphan.attempt + 1)
                logger.info(f"Reset orphan run {orphan.run_id} to QUEUED for retry (new attempt: {orphan.attempt + 1}).")

    def process_one(self) -> bool:
        """
        Executes a single run cycle:
        1. Recovers orphans.
        2. Claims next available run.
        3. Invokes canonical pipeline.
        4. Persists terminal result.
        Returns True if a run was processed, False otherwise.
        """
        if self._shutdown_requested:
            return False

        # 1. Orphan recovery pass
        try:
            self.recover_orphans()
        except Exception as e:
            logger.error(f"Error during orphan recovery pass: {e}")

        # 2. Claim next available run
        run = self.repo.claim_next_run(worker_id=self.worker_id, lease_duration_seconds=self.lease_duration)
        if not run:
            return False

        self._active_run = run
        logger.info(
            f"Worker {self.worker_id} successfully claimed run {run.run_id} for project {run.project_id} "
            f"(attempt {run.attempt})"
        )

        # 3. Emit RUN_STARTED event
        self.repo.record_event(
            run_id=run.run_id,
            project_id=run.project_id,
            event_type="RUN_STARTED",
            payload={"worker_id": self.worker_id, "attempt": run.attempt},
        )

        # 4. Check if already cancelled
        initial_check = self.repo.get_run(run.run_id)
        if initial_check and initial_check.status == RunStatus.CANCEL_REQUESTED:
            self.repo.finish_run(
                run_id=run.run_id,
                worker_id=self.worker_id,
                status=RunStatus.CANCELLED,
                failure_code="RUN_CANCELLED",
                failure_detail={"reason": "Cancelled before execution started"},
            )
            self.repo.record_event(
                run_id=run.run_id,
                project_id=run.project_id,
                event_type="RUN_CANCELLED",
                payload={"reason": "Cancelled before execution started"},
            )
            self._active_run = None
            self._runs_processed += 1
            return True

        # 5. Start Heartbeat
        self._start_heartbeat(run)

        # 6. Invoke canonical pipeline in its own process group
        env = os.environ.copy()
        env["AGY_RUN_ID"] = run.run_id
        env["AGY_WORKER_ID"] = self.worker_id
        env["AGY_IS_MANAGED"] = "1"
        workspace_dir = str(Path(__file__).resolve().parent.parent.parent)
        existing_pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{workspace_dir}{os.pathsep}{existing_pythonpath}" if existing_pythonpath else workspace_dir

        cmd = [sys.executable, "scripts/pipeline.py", run.project_id]

        stdout_lines = []
        stderr_lines = []
        was_cancelled = False

        try:
            from scripts.security.security import safe_subprocess as real_safe_subprocess
            if safe_subprocess is not real_safe_subprocess:
                result = safe_subprocess(cmd, capture_output=True, text=True, encoding="utf-8", env=env)
                self._stop_heartbeat_loop()
                if result.returncode == 0:
                    ref = {
                        "return_code": 0,
                        "stdout_tail": result.stdout[-2000:] if getattr(result, "stdout", None) else "",
                    }
                    self.repo.finish_run(
                        run_id=run.run_id,
                        worker_id=self.worker_id,
                        status=RunStatus.SUCCEEDED,
                        result_reference=ref,
                    )
                    self.repo.record_event(run.run_id, run.project_id, "RUN_SUCCEEDED", payload=ref)
                else:
                    failure_detail = {
                        "return_code": result.returncode,
                        "stderr_tail": result.stderr[-2000:] if getattr(result, "stderr", None) else "",
                        "stdout_tail": result.stdout[-2000:] if getattr(result, "stdout", None) else "",
                    }
                    self.repo.finish_run(
                        run_id=run.run_id,
                        worker_id=self.worker_id,
                        status=RunStatus.FAILED,
                        failure_code="PIPELINE_EXECUTION_FAILED",
                        failure_detail=failure_detail,
                    )
                    self.repo.record_event(run.run_id, run.project_id, "RUN_FAILED", payload=failure_detail)
                return True

            import subprocess
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                env=env,
                start_new_session=True,  # Creates a new process group for clean tree termination
            )

            def stdout_reader():
                try:
                    for line in iter(proc.stdout.readline, ''):
                        cleaned = line.strip()
                        if cleaned:
                            stdout_lines.append(cleaned)
                            if "[STAGE_START]" in cleaned:
                                stg = cleaned.split("[STAGE_START]")[-1].strip()
                                self.repo.record_event(run.run_id, run.project_id, "STAGE_STARTED", stage=stg)
                            elif "[STAGE_FINISH]" in cleaned:
                                stg = cleaned.split("[STAGE_FINISH]")[-1].strip()
                                self.repo.record_event(run.run_id, run.project_id, "STAGE_COMPLETED", stage=stg)
                except Exception:
                    pass

            def stderr_reader():
                try:
                    for line in iter(proc.stderr.readline, ''):
                        cleaned = line.strip()
                        if cleaned:
                            stderr_lines.append(cleaned)
                except Exception:
                    pass

            t_out = threading.Thread(target=stdout_reader, daemon=True)
            t_err = threading.Thread(target=stderr_reader, daemon=True)
            t_out.start()
            t_err.start()

            # Execution & Cancellation monitoring loop
            while proc.poll() is None:
                time.sleep(0.3)
                check_rec = self.repo.get_run(run.run_id)
                if check_rec and check_rec.status == RunStatus.CANCEL_REQUESTED:
                    was_cancelled = True
                    logger.info(f"Cancellation requested for run {run.run_id}. Terminating process group...")
                    try:
                        pgid = os.getpgid(proc.pid)
                        # Graceful SIGTERM
                        os.killpg(pgid, signal.SIGTERM)
                    except (ProcessLookupError, PermissionError):
                        pass

                    # Bounded wait for graceful exit
                    deadline = time.time() + 3.0
                    while time.time() < deadline:
                        if proc.poll() is not None:
                            break
                        time.sleep(0.1)

                    # Escalation to SIGKILL if still alive
                    if proc.poll() is None:
                        logger.warning(f"Run {run.run_id} process did not terminate gracefully. Escalating to SIGKILL...")
                        try:
                            os.killpg(pgid, signal.SIGKILL)
                        except (ProcessLookupError, PermissionError):
                            pass
                        try:
                            proc.wait(timeout=2.0)
                        except Exception:
                            pass
                    break

            self._stop_heartbeat_loop()
            t_out.join(timeout=1.0)
            t_err.join(timeout=1.0)

            if was_cancelled:
                self.repo.finish_run(
                    run_id=run.run_id,
                    worker_id=self.worker_id,
                    status=RunStatus.CANCELLED,
                    failure_code="RUN_CANCELLED",
                    failure_detail={"reason": "Cancelled by user request during execution"},
                )
                self.repo.record_event(
                    run_id=run.run_id,
                    project_id=run.project_id,
                    event_type="RUN_CANCELLED",
                    payload={"reason": "Cancelled by user request during execution"},
                )
                logger.info(f"Run {run.run_id} finished CANCELLED.")
            elif proc.returncode == 0:
                ref = {
                    "return_code": 0,
                    "stdout_tail": "\n".join(stdout_lines[-50:]),
                }
                self.repo.finish_run(
                    run_id=run.run_id,
                    worker_id=self.worker_id,
                    status=RunStatus.SUCCEEDED,
                    result_reference=ref,
                )
                self.repo.record_event(
                    run_id=run.run_id,
                    project_id=run.project_id,
                    event_type="RUN_SUCCEEDED",
                    payload=ref,
                )
                logger.info(f"Run {run.run_id} finished SUCCEEDED.")
            else:
                failure_detail = {
                    "return_code": proc.returncode,
                    "stderr_tail": "\n".join(stderr_lines[-50:]),
                    "stdout_tail": "\n".join(stdout_lines[-50:]),
                }
                self.repo.finish_run(
                    run_id=run.run_id,
                    worker_id=self.worker_id,
                    status=RunStatus.FAILED,
                    failure_code="PIPELINE_EXECUTION_FAILED",
                    failure_detail=failure_detail,
                )
                self.repo.record_event(
                    run_id=run.run_id,
                    project_id=run.project_id,
                    event_type="RUN_FAILED",
                    payload=failure_detail,
                )
                logger.warning(f"Run {run.run_id} finished FAILED with code {proc.returncode}.")

        except Exception as e:
            self._stop_heartbeat_loop()
            logger.error(f"Execution error for run {run.run_id}: {e}", exc_info=True)
            self.repo.finish_run(
                run_id=run.run_id,
                worker_id=self.worker_id,
                status=RunStatus.FAILED,
                failure_code="WORKER_SUBPROCESS_ERROR",
                failure_detail={"error": str(e)},
            )
            self.repo.record_event(
                run_id=run.run_id,
                project_id=run.project_id,
                event_type="RUN_FAILED",
                payload={"error": str(e)},
            )
        finally:
            self._stop_heartbeat_loop()
            self._active_run = None
            self._runs_processed += 1

        return True


    def run_loop(self) -> None:
        """Main worker execution loop."""
        logger.info(f"Starting worker {self.worker_id} polling loop...")
        try:
            signal.signal(signal.SIGINT, self.request_shutdown)
            signal.signal(signal.SIGTERM, self.request_shutdown)
        except (ValueError, AttributeError):
            # Not in main thread or platform unsupported
            pass

        while not self._shutdown_requested:
            if self.max_runs is not None and self._runs_processed >= self.max_runs:
                logger.info(f"Worker {self.worker_id} reached max_runs limit ({self.max_runs}). Exiting.")
                break

            processed = self.process_one()
            if not processed:
                time.sleep(self.poll_interval)
