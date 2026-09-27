"""
Reproduction and Regression Tests for S04: Legacy Gate Facade Remediation.

Findings Covered:
- Finding A: Unknown stage/gate returns success & mutates metadata.
- Finding B: Stringly-typed gate operations entering domain.
- Finding C: Fake rejection (reject_gate claiming success without durable Review Decision).

Invariants Enforced:
1. Invalid/unknown/unsupported gate operation -> explicit failure + zero side effects.
2. Legacy gate endpoint must not claim domain success for something that didn't happen.
3. Zero persistence side effects on rejected operations (state file bytes, revision, updated_at, approval_metadata).
"""

import pytest
import shutil
from pathlib import Path
from fastapi.testclient import TestClient

from api.main import app
from scripts.core.state_store import StateStore
from scripts.core.state_model import ProjectState, LifecycleState
from api.services.pipeline_service import PipelineService
from api.services.gate_service import reject_gate, approve_gate, start_stage, finish_stage
from api.core.errors import InvalidGateError, InvalidStageError, UnsupportedGateOperationError


@pytest.fixture
def test_project():
    pid = "test_s04_facade_repro"
    pdir = PipelineService._get_project_dir(pid)
    if pdir.exists():
        shutil.rmtree(pdir)
    pdir.mkdir(parents=True, exist_ok=True)
    
    state = ProjectState(project_id=pid, lifecycle_state=LifecycleState.DRAFT)
    StateStore.save(pdir, state)
    
    yield pid, pdir
    
    if pdir.exists():
        shutil.rmtree(pdir)


@pytest.fixture
def auth_client():
    return TestClient(
        app,
        headers={"X-Principal-ID": "test_admin", "X-Principal-Roles": "admin,reviewer,editor"}
    )


def take_state_snapshot(pdir: Path):
    state_file = pdir / ".pipeline_state.json"
    raw_bytes = state_file.read_bytes() if state_file.exists() else None
    state = StateStore.load(pdir)
    return {
        "bytes": raw_bytes,
        "revision": state.revision if state else None,
        "updated_at": state.updated_at if state else None,
        "lifecycle_state": state.lifecycle_state if state else None,
        "approval_metadata": dict(state.approval_metadata) if state else None,
    }


def assert_snapshot_unchanged(before, after):
    assert before["bytes"] == after["bytes"], "State file bytes changed on rejected operation!"
    assert before["revision"] == after["revision"], "State revision mutated on rejected operation!"
    assert before["updated_at"] == after["updated_at"], "State updated_at mutated on rejected operation!"
    assert before["lifecycle_state"] == after["lifecycle_state"], "Lifecycle state mutated on rejected operation!"
    assert before["approval_metadata"] == after["approval_metadata"], "Approval metadata mutated on rejected operation!"


class TestS04Reproductions:

    def test_red_1_unknown_stage_fails_with_zero_side_effects(self, test_project, auth_client):
        """
        RED 1: Unknown stage in start/finish must fail explicitly (HTTP 422)
        and produce ZERO persistence side effects.
        """
        pid, pdir = test_project
        snapshot_before = take_state_snapshot(pdir)

        # 1. API: start with unknown stage
        res = auth_client.post(f"/gates/{pid}/start/definitely-not-a-stage")
        assert res.status_code == 422, f"Expected 422 for unknown stage, got {res.status_code}: {res.text}"
        assert_snapshot_unchanged(snapshot_before, take_state_snapshot(pdir))

        # 2. API: finish with unknown stage
        res_finish = auth_client.post(f"/gates/{pid}/finish/definitely-not-a-stage")
        assert res_finish.status_code == 422, f"Expected 422 for unknown stage finish, got {res_finish.status_code}: {res_finish.text}"
        assert_snapshot_unchanged(snapshot_before, take_state_snapshot(pdir))

    @pytest.mark.asyncio
    async def test_red_1_service_unknown_stage_raises_without_mutation(self, test_project):
        """
        RED 1 (Service Level): Calling start_stage/finish_stage with unknown stage directly in Python
        must raise InvalidStageError before any mutation.
        """
        pid, pdir = test_project
        snapshot_before = take_state_snapshot(pdir)

        with pytest.raises((InvalidStageError, UnsupportedGateOperationError)):
            await PipelineService.start_stage(pid, "definitely-not-a-stage")
        assert_snapshot_unchanged(snapshot_before, take_state_snapshot(pdir))

        with pytest.raises((InvalidStageError, UnsupportedGateOperationError)):
            await PipelineService.finish_stage(pid, "definitely-not-a-stage")
        assert_snapshot_unchanged(snapshot_before, take_state_snapshot(pdir))

    def test_red_2_unknown_gate_approval_fails_with_zero_side_effects(self, test_project, auth_client):
        """
        RED 2: Unknown gate approval via API must fail (HTTP 422)
        and must NOT write approved_by or mutate metadata.
        """
        pid, pdir = test_project
        snapshot_before = take_state_snapshot(pdir)

        res = auth_client.post(f"/gates/{pid}/approve/unknown_gate")
        assert res.status_code == 422, f"Expected 422 for unknown gate approval, got {res.status_code}: {res.text}"
        
        snapshot_after = take_state_snapshot(pdir)
        assert_snapshot_unchanged(snapshot_before, snapshot_after)

    @pytest.mark.asyncio
    async def test_red_2_service_unknown_gate_approval_raises_without_mutation(self, test_project):
        """
        RED 2 (Service Level): PipelineService.approve_gate with unknown gate
        must raise InvalidGateError before any mutation or StateStore write.
        """
        pid, pdir = test_project
        snapshot_before = take_state_snapshot(pdir)

        with pytest.raises(InvalidGateError):
            await PipelineService.approve_gate(pid, "unknown_gate", approved_by="sneaky_user")

        assert_snapshot_unchanged(snapshot_before, take_state_snapshot(pdir))

    def test_red_3_fake_rejection_is_unsupported_and_fails_closed(self, test_project, auth_client):
        """
        RED 3: reject_gate must NOT return 200 claiming fake success.
        Until ReviewService (S09), it must fail closed with an explicit error (409 or 422)
        and produce ZERO state mutations.
        """
        pid, pdir = test_project
        snapshot_before = take_state_snapshot(pdir)

        res = auth_client.post(f"/gates/{pid}/reject/asset_gate?note=bad")
        assert res.status_code != 200, "Fake rejection returned 200 OK!"
        assert res.status_code in (409, 422), f"Expected 409/422 unsupported, got {res.status_code}: {res.text}"

        assert_snapshot_unchanged(snapshot_before, take_state_snapshot(pdir))

    @pytest.mark.asyncio
    async def test_red_3_service_reject_gate_fails_closed(self, test_project):
        """
        RED 3 (Service Level): reject_gate must raise UnsupportedGateOperationError
        and never silently delegate to start_stage.
        """
        pid, pdir = test_project
        snapshot_before = take_state_snapshot(pdir)

        with pytest.raises(UnsupportedGateOperationError):
            await reject_gate(pid, "asset_gate", by="reviewer", note="bad quality")

        assert_snapshot_unchanged(snapshot_before, take_state_snapshot(pdir))
