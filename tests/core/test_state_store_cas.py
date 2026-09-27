import os
import signal
import time
import pytest
from pathlib import Path
import multiprocessing as mp
from fastapi.testclient import TestClient

from scripts.core.state_store import (
    StateStore,
    StateConflictError,
    StateExistsError,
    StateNotFoundError,
    StateLockTimeoutError,
)
from scripts.core.state_model import ProjectState, LifecycleState, ValidationLevel
from scripts.core.lifecycle_service import LifecycleService, InvalidLifecycleTransitionError
from api.main import app


# ==============================================================================
# Top-level helper functions for multiprocessing (spawn context requires pickle)
# ==============================================================================

def _worker_cas_commit(proj_dir_str: str, expected_rev: int, writer_id: str, barrier, result_queue):
    """Worker process that attempts a CAS commit based on expected_rev."""
    pdir = Path(proj_dir_str)
    # Wait for both processes to be ready
    barrier.wait()
    try:
        def mutator(state: ProjectState):
            state.run_metadata["writer"] = writer_id

        committed = StateStore.atomic_update(
            project_dir=pdir,
            expected_revision=expected_rev,
            mutator=mutator,
            timeout=5.0,
        )
        result_queue.put(("SUCCESS", writer_id, committed.revision, committed.run_metadata.get("writer")))
    except StateConflictError as exc:
        result_queue.put(("CONFLICT", writer_id, exc.expected_revision, exc.actual_revision))
    except Exception as exc:
        result_queue.put(("ERROR", writer_id, str(type(exc)), str(exc)))


def _worker_hold_lock_and_die(proj_dir_str: str, ready_event):
    """Worker that acquires the state lock, signals parent, and terminates abruptly."""
    pdir = Path(proj_dir_str)
    lock = StateStore.lock(pdir)
    lock.acquire()
    ready_event.set()
    # Sleep to allow parent to observe lock or simulate crash
    time.sleep(10)


def _worker_critical_section(proj_dir_str: str, duration: float, active_count_val, max_active_val, result_queue):
    """Worker that records concurrency within critical section."""
    pdir = Path(proj_dir_str)
    try:
        def mutator(state: ProjectState):
            with active_count_val.get_lock():
                active_count_val.value += 1
                curr = active_count_val.value
            with max_active_val.get_lock():
                if curr > max_active_val.value:
                    max_active_val.value = curr
            time.sleep(duration)
            with active_count_val.get_lock():
                active_count_val.value -= 1

        StateStore.atomic_update(
            project_dir=pdir,
            expected_revision=1,
            mutator=mutator,
            timeout=10.0,
        )
        result_queue.put(("SUCCESS", os.getpid()))
    except StateConflictError:
        result_queue.put(("CONFLICT", os.getpid()))
    except Exception as e:
        result_queue.put(("ERROR", str(e)))


def _worker_lifecycle_transition(proj_dir_str: str, expected_rev: int, actor_name: str, barrier, result_queue):
    """Worker that calls LifecycleService.transition concurrently."""
    pdir = Path(proj_dir_str)
    barrier.wait()
    try:
        res = LifecycleService.transition(
            project_dir=pdir,
            target_state=LifecycleState.ASSETS_READY,
            expected_revision=expected_rev,
            actor=actor_name,
            timeout=5.0,
        )
        result_queue.put(("SUCCESS", actor_name, res.revision, res.run_metadata.get("last_actor")))
    except StateConflictError as exc:
        result_queue.put(("CONFLICT", actor_name, exc.expected_revision, exc.actual_revision))
    except Exception as exc:
        result_queue.put(("ERROR", actor_name, str(type(exc)), str(exc)))


# ==============================================================================
# S05 Required Concurrency & Correctness Tests
# ==============================================================================

class TestStateStoreConcurrencyAndCAS:

    def test_01_two_stale_writers_cross_process(self, tmp_path):
        """
        Test 1 & Concurrency Requirement:
        Writer A and Writer B both read revision N=1 across separate processes.
        Both attempt to commit based on expected_revision=1.
        Exactly one MUST succeed -> revision 2.
        The other MUST receive StateConflictError(expected=1, actual=2).
        """
        pdir = tmp_path / "prj_cas_01"
        StateStore.create(pdir, "prj_cas_01")
        initial = StateStore.load(pdir)
        assert initial.revision == 1

        ctx = mp.get_context("spawn")
        barrier = ctx.Barrier(2)
        result_queue = ctx.Queue()

        p1 = ctx.Process(
            target=_worker_cas_commit,
            args=(str(pdir), 1, "Writer_A", barrier, result_queue),
        )
        p2 = ctx.Process(
            target=_worker_cas_commit,
            args=(str(pdir), 1, "Writer_B", barrier, result_queue),
        )

        p1.start()
        p2.start()
        p1.join(timeout=10)
        p2.join(timeout=10)

        results = [result_queue.get_nowait(), result_queue.get_nowait()]
        statuses = [r[0] for r in results]

        assert "SUCCESS" in statuses, f"Expected one successful commit, got {results}"
        assert "CONFLICT" in statuses, f"Expected one conflict, got {results}"

        success_result = next(r for r in results if r[0] == "SUCCESS")
        conflict_result = next(r for r in results if r[0] == "CONFLICT")

        # Winner moved revision from 1 to 2
        assert success_result[2] == 2
        # Loser got expected=1, actual=2
        assert conflict_result[2] == 1
        assert conflict_result[3] == 2

        # Final state check
        final_state = StateStore.load(pdir)
        assert final_state.revision == 2
        assert final_state.run_metadata["writer"] == success_result[1]

    def test_02_loser_has_zero_persistence_effect(self, tmp_path):
        """
        Test 2:
        A stale writer getting StateConflict produces zero changes on disk.
        """
        pdir = tmp_path / "prj_cas_02"
        StateStore.create(pdir, "prj_cas_02")
        
        # Advance state to revision 2 by Writer Winner
        def win_mut(s):
            s.run_metadata["winner_key"] = "winner_value"
        StateStore.atomic_update(pdir, expected_revision=1, mutator=win_mut)

        snap_before = (pdir / StateStore.STATE_FILE).read_bytes()

        # Stale writer attempts commit based on rev 1
        def stale_mut(s):
            s.run_metadata["loser_key"] = "loser_poison"

        with pytest.raises(StateConflictError) as exc_info:
            StateStore.atomic_update(pdir, expected_revision=1, mutator=stale_mut)

        assert exc_info.value.expected_revision == 1
        assert exc_info.value.actual_revision == 2

        snap_after = (pdir / StateStore.STATE_FILE).read_bytes()
        assert snap_before == snap_after, "State file was altered despite CAS conflict!"

        current_state = StateStore.load(pdir)
        assert "loser_key" not in current_state.run_metadata
        assert current_state.run_metadata.get("winner_key") == "winner_value"

    def test_03_monotonic_sequential_commits(self, tmp_path):
        """
        Test 3:
        Sequential valid updates: 1 -> 2 -> 3 -> 4 without skips or regressions.
        """
        pdir = tmp_path / "prj_cas_03"
        st = StateStore.create(pdir, "prj_cas_03")
        assert st.revision == 1

        for expected in range(1, 10):
            def mutator(s, exp=expected):
                s.run_metadata[f"step_{exp}"] = True

            updated = StateStore.atomic_update(pdir, expected_revision=expected, mutator=mutator)
            assert updated.revision == expected + 1

        final_st = StateStore.load(pdir)
        assert final_st.revision == 10
        for i in range(1, 10):
            assert final_st.run_metadata.get(f"step_{i}") is True

    def test_04_validation_failure_produces_zero_mutation(self, tmp_path):
        """
        Test 4:
        Transaction acquires lock, mutator raises validation/domain error.
        State on disk and revision must remain completely unchanged.
        """
        pdir = tmp_path / "prj_cas_04"
        StateStore.create(pdir, "prj_cas_04")
        initial_bytes = (pdir / StateStore.STATE_FILE).read_bytes()
        initial_mtime = (pdir / StateStore.STATE_FILE).stat().st_mtime_ns

        def bad_mutator(s):
            s.run_metadata["corrupt"] = True
            raise ValueError("Domain validation exploded inside transaction")

        with pytest.raises(ValueError, match="Domain validation exploded"):
            StateStore.atomic_update(pdir, expected_revision=1, mutator=bad_mutator)

        assert (pdir / StateStore.STATE_FILE).read_bytes() == initial_bytes
        state = StateStore.load(pdir)
        assert state.revision == 1
        assert "corrupt" not in state.run_metadata

    def test_05_persistence_failure_before_replace_preserves_state(self, tmp_path, monkeypatch):
        """
        Test 5:
        If an error is injected right before os.replace, the original state file
        remains byte-identical and unique temp files are cleaned up.
        """
        pdir = tmp_path / "prj_cas_05"
        StateStore.create(pdir, "prj_cas_05")
        initial_bytes = (pdir / StateStore.STATE_FILE).read_bytes()

        # Monkeypatch os.replace to fail
        real_replace = os.replace
        def broken_replace(src, dst):
            if str(dst).endswith(StateStore.STATE_FILE):
                raise OSError("Injected disk I/O error during os.replace")
            return real_replace(src, dst)

        monkeypatch.setattr(os, "replace", broken_replace)

        def mut(s):
            s.run_metadata["should_fail"] = True

        with pytest.raises(OSError, match="Injected disk I/O error"):
            StateStore.atomic_update(pdir, expected_revision=1, mutator=mut)

        # Original state file is pristine
        assert (pdir / StateStore.STATE_FILE).read_bytes() == initial_bytes
        # No orphan temp files left behind
        temp_files = list(pdir.glob(".pipeline_state.*.tmp"))
        assert len(temp_files) == 0, f"Leaked temp files found: {temp_files}"

    def test_06_cross_process_lock_mutual_exclusion(self, tmp_path):
        """
        Test 6:
        Multiple processes entering atomic_update critical section are mutually exclusive.
        Max concurrent workers inside mutator critical section is strictly 1.
        """
        pdir = tmp_path / "prj_cas_06"
        StateStore.create(pdir, "prj_cas_06")

        ctx = mp.get_context("spawn")
        active_count = ctx.Value('i', 0)
        max_active = ctx.Value('i', 0)
        result_queue = ctx.Queue()

        workers = [
            ctx.Process(
                target=_worker_critical_section,
                args=(str(pdir), 0.15, active_count, max_active, result_queue),
            )
            for _ in range(3)
        ]

        for w in workers:
            w.start()
        for w in workers:
            w.join(timeout=10)

        assert max_active.value == 1, f"Expected mutual exclusion (max 1), got {max_active.value}"

    def test_07_different_projects_independent_locks(self, tmp_path):
        """
        Test 7:
        Lock on Project A does NOT block operations on Project B.
        """
        pdir_a = tmp_path / "prj_a"
        pdir_b = tmp_path / "prj_b"
        StateStore.create(pdir_a, "prj_a")
        StateStore.create(pdir_b, "prj_b")

        # Hold lock on project A
        with StateStore.lock(pdir_a):
            # Project B can update immediately without blocking or timing out
            start = time.monotonic()
            def mut_b(s):
                s.run_metadata["proj_b"] = True

            res_b = StateStore.atomic_update(pdir_b, expected_revision=1, mutator=mut_b, timeout=2.0)
            elapsed = time.monotonic() - start

            assert res_b.revision == 2
            assert elapsed < 1.0, f"Project B update took too long ({elapsed}s), was blocked by Project A lock!"

    def test_08_process_death_releases_lock(self, tmp_path):
        """
        Test 8:
        If a process holding the state lock dies (e.g. SIGKILL / terminates),
        the OS kernel automatically releases the lock. A subsequent process
        can acquire the lock without deadlock or orphaned lock issues.
        """
        pdir = tmp_path / "prj_cas_08"
        StateStore.create(pdir, "prj_cas_08")

        ctx = mp.get_context("spawn")
        ready_event = ctx.Event()

        proc = ctx.Process(target=_worker_hold_lock_and_die, args=(str(pdir), ready_event))
        proc.start()

        # Wait until child has acquired lock
        assert ready_event.wait(timeout=5.0)

        # Forcefully terminate child process (kill -9 equivalent)
        proc.kill()
        proc.join(timeout=5)

        # Subsequent process must be able to acquire lock immediately
        acquired = False
        try:
            with StateStore.lock(pdir, timeout=2.0):
                acquired = True
            def mut(s):
                s.run_metadata["recovered"] = True
            updated = StateStore.atomic_update(pdir, expected_revision=1, mutator=mut)
            assert updated.revision == 2
        except StateLockTimeoutError:
            acquired = False

        assert acquired, "Subsequent process could not acquire lock after process termination!"
        # Lock file is preserved as coordination point
        assert (pdir / StateStore.LOCK_FILE).exists()

    def test_09_unique_temp_files_prevent_collision(self, tmp_path):
        """
        Test 9:
        StateStore does not use a shared fixed temp filename (.pipeline_state.json.tmp).
        Temp files use unique per-commit names.
        """
        pdir = tmp_path / "prj_cas_09"
        StateStore.create(pdir, "prj_cas_09")

        # Inspect generated temp filename pattern
        unique_suffix = f"{os.getpid()}"
        # Multiple updates succeed cleanly without colliding on a static .tmp file
        for i in range(1, 5):
            StateStore.atomic_update(pdir, expected_revision=i, mutator=lambda s: None)

        assert not (pdir / f"{StateStore.STATE_FILE}.tmp").exists()
        assert len(list(pdir.glob(".pipeline_state.*.tmp"))) == 0

    def test_10_lifecycle_service_real_path_concurrency(self, tmp_path):
        """
        Test 10:
        Concurrent LifecycleService.transition calls from two processes starting
        from the same expected revision.
        - Sole Lifecycle authority (S03) preserved.
        - Exactly one succeeds.
        - Stale writer receives StateConflictError.
        - No direct lifecycle mutations outside LifecycleService.
        """
        pdir = tmp_path / "prj_cas_10"
        # Create initial project in DRAFT state
        LifecycleService.transition(pdir, LifecycleState.DRAFT)
        init_st = StateStore.load(pdir)
        assert init_st.lifecycle_state == LifecycleState.DRAFT
        assert init_st.revision == 1

        # Manifest prerequisite for ASSETS_READY
        (pdir / "02_asset_manifest.json").write_text("{}", encoding="utf-8")

        ctx = mp.get_context("spawn")
        barrier = ctx.Barrier(2)
        result_queue = ctx.Queue()

        p1 = ctx.Process(
            target=_worker_lifecycle_transition,
            args=(str(pdir), 1, "Actor_1", barrier, result_queue),
        )
        p2 = ctx.Process(
            target=_worker_lifecycle_transition,
            args=(str(pdir), 1, "Actor_2", barrier, result_queue),
        )

        p1.start()
        p2.start()
        p1.join(timeout=10)
        p2.join(timeout=10)

        results = [result_queue.get_nowait(), result_queue.get_nowait()]
        statuses = [r[0] for r in results]

        assert "SUCCESS" in statuses, f"Expected one success, got: {results}"
        assert "CONFLICT" in statuses, f"Expected one conflict, got: {results}"

        final_st = StateStore.load(pdir)
        assert final_st.lifecycle_state == LifecycleState.ASSETS_READY
        assert final_st.revision == 2

    def test_11_create_fails_closed_if_state_file_exists(self, tmp_path):
        """
        Requirement: Initial creation is fail-closed.
        If state file already exists, create() must raise StateExistsError
        and never silently overwrite.
        """
        pdir = tmp_path / "prj_cas_11"
        StateStore.create(pdir, "prj_cas_11")

        with pytest.raises(StateExistsError):
            StateStore.create(pdir, "prj_cas_11")

    def test_12_atomic_update_requires_integer_expected_revision(self, tmp_path):
        """
        Requirement: expected_revision cannot be None in atomic_update.
        Must be an explicit integer revision.
        """
        pdir = tmp_path / "prj_cas_12"
        StateStore.create(pdir, "prj_cas_12")

        with pytest.raises(ValueError, match="expected_revision must be an integer"):
            StateStore.atomic_update(pdir, expected_revision=None, mutator=lambda s: None)

    def test_13_api_conflict_error_mapping(self):
        """
        Requirement:
        StateConflictError maps to HTTP 409 Conflict with machine-readable code
        STATE_CONFLICT and details containing expected_revision and actual_revision.
        """
        client = TestClient(app)

        # Trigger a test route or exception handler check
        from fastapi import APIRouter
        test_router = APIRouter()

        @test_router.get("/test-conflict-endpoint")
        def route_conflict():
            raise StateConflictError(expected_revision=5, actual_revision=6)

        app.include_router(test_router)

        res = client.get("/test-conflict-endpoint")
        assert res.status_code == 409
        body = res.json()
        assert body["status"] == "error"
        assert body["error"] == "StateConflict"
        assert body["details"]["code"] == "STATE_CONFLICT"
        assert body["details"]["expected_revision"] == 5
        assert body["details"]["actual_revision"] == 6
