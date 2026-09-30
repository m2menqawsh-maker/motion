import sys
import subprocess
import json
import shutil
import pytest
import asyncio
from pathlib import Path
from api.services.pipeline_service import PipelineService
from api.core.errors import UnsupportedGateOperationError
from scripts.core.lifecycle_service import LifecyclePreconditionFailedError
from scripts.core.review_service import ReviewService, create_local_trusted_principal
from scripts.core.state_store import StateStore
from scripts.core.state_model import LifecycleState
from tests.factories.canonical_factory import create_canonical_e2e_project

"""
Classification: INTEGRATION_SUITE (LED-077 Resolved)
Verifies end-to-end gate execution and lifecycle transitions strictly through public/canonical
execution paths (PipelineService, Orchestrator, ReviewService).
State bypasses, internal state mutations, and unverified transitions are explicitly forbidden
and tested as rejected fail-closed.
"""

def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


@pytest.fixture(autouse=True)
def unmock_pipeline_service_project_dir(monkeypatch):
    """Ensure PipelineService uses the canonical workspace projects directory for real CLI integration."""
    from api.services.pipeline_service import PipelineService
    monkeypatch.setattr(PipelineService, "_get_project_dir", classmethod(lambda cls, pid: Path(f"projects/{pid}")))


@pytest.fixture(scope="module")
def project_setup():
    code, stdout, stderr = run([sys.executable, "scripts/scaffold_project.py", "--name", "IntegrationTest", "--language", "ar"])
    assert code == 0
    project_id = stdout.strip()
    project_dir = Path("projects") / project_id

    # Populate canonical structure via canonical factory
    create_canonical_e2e_project(
        project_dir=project_dir,
        project_id=project_id,
        template="animatedtext-element",
        aspect="16:9",
        fps=30,
        duration_frames=30,
        with_audio=False,
    )

    yield project_id, project_dir

    if project_dir.exists():
        shutil.rmtree(project_dir, ignore_errors=True)


def test_scaffold_creates_project(project_setup):
    project_id, project_dir = project_setup
    assert (project_dir / "project.json").exists()
    assert (project_dir / ".pipeline_state.json").exists()


def test_blueprint_passes_schema(project_setup):
    project_id, project_dir = project_setup
    code, _, _ = run([sys.executable, "scripts/validators/validate_schemas.py", str(project_dir)])
    assert code == 0


@pytest.mark.asyncio
async def test_canonical_pipeline_and_review_flow(project_setup):
    """
    LED-077 Happy Path:
    Executes through canonical Orchestrator and durable ReviewService.
    No direct state mutations, no test bypass helpers.
    """
    project_id, project_dir = project_setup

    # 1. Pass 1: Run orchestrator to execute real gates through probe_qc
    res1 = await PipelineService.run_pipeline(project_id)
    assert res1["status"] in ["success", "locked"], f"Pipeline failed: {res1.get('stderr')} {res1.get('stdout')}"

    # Verify project is at Studio Review (AWAITING_REVIEW / PROBE_PASSED)
    status1 = await PipelineService.get_status(project_id)
    assert status1["current_stage"] == "qc_gate"

    state1 = StateStore.load(project_dir)
    assert state1 is not None
    assert state1.lifecycle_state in [LifecycleState.PROBE_PASSED, LifecycleState.AWAITING_REVIEW]
    bundle = state1.get_active_review_bundle()
    assert bundle is not None, "Probe QC must have created an active ReviewBundle"

    # 2. Legitimate Durable Approval via ReviewService / PipelineService
    principal = create_local_trusted_principal(actor_id="integration_tester")
    approval_res = await PipelineService.approve_gate(project_id, "qc_gate", principal=principal)
    assert approval_res["decision"] == "APPROVED"

    # Verify locked / approved state
    status_after_approve = await PipelineService.get_status(project_id)
    assert status_after_approve["status"] == "locked"

    # 3. Pass 2: Execute rendering and strict Final QC through orchestrator
    res2 = await PipelineService.run_pipeline(project_id)
    assert res2["status"] == "success", f"Pass 2 failed. STDOUT:\n{res2.get('stdout')}\nSTDERR:\n{res2.get('stderr')}"
    assert res2["return_code"] == 0

    state2 = StateStore.load(project_dir)
    assert state2 is not None
    assert state2.lifecycle_state in [LifecycleState.FINAL_QC_PASSED, LifecycleState.COMPLETE]

    qc_report_path = project_dir / "final_qc_report.json"
    assert qc_report_path.exists()
    qc_data = json.loads(qc_report_path.read_text(encoding="utf-8"))
    assert qc_data.get("status") == "PASS"


@pytest.mark.asyncio
async def test_negative_direct_finish_stage_forbidden(project_setup):
    """LED-077: Direct unverified stage advancement via finish_stage must fail closed."""
    project_id, _ = project_setup
    with pytest.raises(LifecyclePreconditionFailedError):
        await PipelineService.finish_stage(project_id, "asset_gate")


@pytest.mark.asyncio
async def test_negative_legacy_gate_approval_forbidden(project_setup):
    """LED-077: Legacy approval for non-qc gates must be rejected fail-closed."""
    project_id, _ = project_setup
    with pytest.raises(UnsupportedGateOperationError):
        await PipelineService.approve_gate(project_id, "asset_gate")


@pytest.mark.asyncio
async def test_negative_render_without_approval_rejected():
    """LED-077: Attempting to render directly before review approval must fail closed."""
    import uuid
    unapproved_id = f"prj_{uuid.uuid4().hex[:8]}"
    unapproved_dir = Path("projects") / unapproved_id
    if unapproved_dir.exists():
        shutil.rmtree(unapproved_dir)

    try:
        create_canonical_e2e_project(
            project_dir=unapproved_dir,
            project_id=unapproved_id,
            template="animatedtext-element",
            aspect="16:9",
            fps=30,
            duration_frames=30,
            with_audio=False,
        )

        # Directly attempt rendering before probe QC or approval
        res = subprocess.run(
            [sys.executable, "scripts/render_project.py", unapproved_id],
            capture_output=True,
            text=True,
        )
        assert res.returncode != 0, "Direct render must fail when project has not been approved"
    finally:
        if unapproved_dir.exists():
            shutil.rmtree(unapproved_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_negative_tamper_after_approval_rejected():
    """LED-077: Tampering with blueprint after approval must invalidate gate and reject render."""
    import uuid
    tamper_id = f"prj_{uuid.uuid4().hex[:8]}"
    tamper_dir = Path("projects") / tamper_id
    if tamper_dir.exists():
        shutil.rmtree(tamper_dir)

    try:
        create_canonical_e2e_project(
            project_dir=tamper_dir,
            project_id=tamper_id,
            template="animatedtext-element",
            aspect="16:9",
            fps=30,
            duration_frames=30,
            with_audio=False,
        )

        # Pass 1: Run to probe_qc / awaiting review
        res1 = await PipelineService.run_pipeline(tamper_id)
        assert res1["return_code"] == 0

        # Approve
        principal = create_local_trusted_principal(actor_id="tamper_tester")
        await PipelineService.approve_gate(tamper_id, "qc_gate", principal=principal)

        # Deliberately tamper with 05_blueprint.json after approval
        bp_path = tamper_dir / "05_blueprint.json"
        bp_data = json.loads(bp_path.read_text(encoding="utf-8"))
        bp_data["meta"]["tampered"] = True
        bp_data["fps"] = 24  # Tamper with canonical fps
        bp_path.write_text(json.dumps(bp_data, indent=2), encoding="utf-8")

        # Pass 2 must detect the tamper / hash mismatch and refuse to complete render
        res2 = await PipelineService.run_pipeline(tamper_id)
        state_after = StateStore.load(tamper_dir)
        assert state_after.lifecycle_state != LifecycleState.COMPLETE
        assert not (tamper_dir / "out.mp4").exists()
    finally:
        if tamper_dir.exists():
            shutil.rmtree(tamper_dir, ignore_errors=True)
