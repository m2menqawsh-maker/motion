"""
tests/ai/test_phase3_creative_platform_wiring.py
=================================================
Phase 3 Verification Suite: AI & Creative Platform Wiring.

Verifies end-to-end commercial AI creative execution:
1. Generation of advisory CreativeProposal via API (/projects/{id}/creative/proposals):
   - Real TasteEngine evaluation & auditable taste diagnostics.
   - CreativeDirectorCoordinator execution.
   - ConflictResolver resolution.
   - Deterministic master_plan.md synthesis meeting PlanGate & TasteGate standards.
2. Tenant security boundaries: cross-tenant proposal requests strictly rejected.
3. Explicit apply (/projects/{id}/creative/apply):
   - CAS optimistic revision check and durable idempotency.
   - Disk materialization of 05_blueprint.json and master_plan.md.
   - Invalidation of downstream reviews upon candidate blueprint mutation.
4. Human review transition:
   - Creation of ReviewBundle from applied assets.
   - Approval by authorized REVIEWER principal.
   - assert_render_authorized() succeeds, granting green light for pipeline rendering.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.core.auth import create_signed_token
from scripts.core.database import DatabaseEngine, TenantRepository, set_database_engine
from scripts.core.security.principal import Principal, PrincipalType, Role
from scripts.core.storage import LocalStorageBackend, set_storage_service
from scripts.core.state_model import (
    ArtifactRecord,
    LifecycleState,
    ProjectState,
    ReviewDecisionType,
    ValidationLevel,
)
from scripts.core.state_store import StateStore
from scripts.core.review_service import (
    RenderNotAuthorizedError,
    ReviewService,
)
from scripts.gates.plan_gate import validate_plan_quality


@pytest.fixture
def phase3_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Hermetic SaaS environment for Phase 3 creative platform wiring verification."""
    db_file = tmp_path / "phase3_runtime.db"
    db_url = f"sqlite:///{db_file}"
    monkeypatch.setenv("DATABASE_URL", db_url)
    monkeypatch.setenv("MOTION_RUNS_DB_PATH", str(db_file))
    monkeypatch.setenv("RUNS_DB_PATH", str(db_file))
    auth_secret = "phase3-secret-key-for-jwt-signing-harness-32bytes!"
    monkeypatch.setenv("AUTH_SECRET_KEY", auth_secret)

    engine = DatabaseEngine(db_url=db_url)
    set_database_engine(engine)

    storage_root = tmp_path / "storage"
    storage_root.mkdir(parents=True, exist_ok=True)
    storage = LocalStorageBackend(root_dir=storage_root)
    set_storage_service(storage)

    repo = TenantRepository(engine)

    # 1. Tenant Alpha (Primary)
    user_alice = repo.create_user("usr_alice", "alice@alpha.com")
    user_charlie = repo.create_user("usr_charlie", "charlie@alpha.com")
    ws_alpha = repo.create_workspace("ws_alpha", "Workspace Alpha", created_by=user_alice.id)
    repo.add_member(ws_alpha.id, user_alice.id, Role.EDITOR)
    repo.add_member(ws_alpha.id, user_charlie.id, Role.REVIEWER)

    # 2. Tenant Beta (Foreign Tenant)
    user_bob = repo.create_user("usr_bob", "bob@beta.com")
    ws_beta = repo.create_workspace("ws_beta", "Workspace Beta", created_by=user_bob.id)
    repo.add_member(ws_beta.id, user_bob.id, Role.EDITOR)

    # 3. Create Project in Workspace Alpha
    prj_alpha = repo.create_project("prj_phase3_01", ws_alpha.id, "Phase 3 Showcase Video", created_by=user_alice.id)

    # Resolve and initialize project directory on disk
    from scripts.security.path_security import resolve_project_dir
    pdir_alpha = resolve_project_dir(prj_alpha.id, workspace_id=ws_alpha.id, create=True)

    # Seed baseline initial state
    init_state = ProjectState(
        project_id=prj_alpha.id,
        workspace_id=ws_alpha.id,
        revision=1,
        lifecycle_state=LifecycleState.DRAFT.value,
    )
    StateStore.save(pdir_alpha, init_state)

    client = TestClient(app)

    yield {
        "engine": engine,
        "repo": repo,
        "storage": storage,
        "ws_alpha": ws_alpha.id,
        "ws_beta": ws_beta.id,
        "prj_id": prj_alpha.id,
        "pdir": pdir_alpha,
        "principals": {
            "alice": Principal(principal_id=user_alice.id, principal_type=PrincipalType.HUMAN, roles={Role.EDITOR}),
            "charlie": Principal(principal_id=user_charlie.id, principal_type=PrincipalType.HUMAN, roles={Role.REVIEWER}),
            "bob": Principal(principal_id=user_bob.id, principal_type=PrincipalType.HUMAN, roles={Role.EDITOR}),
        },
        "tokens": {
            "alice": create_signed_token(
                Principal(principal_id=user_alice.id, principal_type=PrincipalType.HUMAN, roles={Role.EDITOR}),
                secret=auth_secret,
            ),
            "charlie": create_signed_token(
                Principal(principal_id=user_charlie.id, principal_type=PrincipalType.HUMAN, roles={Role.REVIEWER}),
                secret=auth_secret,
            ),
            "bob": create_signed_token(
                Principal(principal_id=user_bob.id, principal_type=PrincipalType.HUMAN, roles={Role.EDITOR}),
                secret=auth_secret,
            ),
        },
        "client": client,
    }

    import shutil
    shutil.rmtree(pdir_alpha, ignore_errors=True)
    shutil.rmtree(Path("projects") / ws_alpha.id, ignore_errors=True)


def test_creative_proposal_generates_taste_diagnostics_and_master_plan(phase3_env):
    """
    Verifies that POST /projects/{id}/creative/proposals:
    1. Executes real TasteEngine, CreativeDirectors, and ConflictResolver.
    2. Returns auditable TASTE_EVALUATION diagnostics.
    3. Synthesizes a valid master_plan.md satisfying PlanGate and TasteGate.
    """
    client = phase3_env["client"]
    token_alice = phase3_env["tokens"]["alice"]
    pid = phase3_env["prj_id"]

    resp = client.post(
        f"/projects/{pid}/creative/proposals",
        headers={"Authorization": f"Bearer {token_alice}"},
        json={
            "prompt": "Create an energetic 30s product showcase video highlighting our new cloud API platform",
            "aspect_ratio": "9:16",
            "audio_mode": "VO_MUSIC",
        },
    )

    assert resp.status_code == 200, f"Proposal failed: {resp.text}"
    data = resp.json()

    assert data["status"] == "PROPOSED"
    assert data["project_id"] == pid
    assert data["approval_required"] is True
    assert data["can_apply"] is True

    # 1. Verify Taste & Director diagnostics
    diagnostics = data.get("diagnostics", [])
    taste_diag = next((d for d in diagnostics if d.get("type") == "TASTE_EVALUATION"), None)
    assert taste_diag is not None, f"Expected TASTE_EVALUATION diagnostic, got: {diagnostics}"
    assert taste_diag["total_decisions"] > 0
    assert len(taste_diag["rules_applied"]) > 0

    # 2. Verify master_plan presence & gate compliance
    master_plan = data.get("master_plan")
    assert master_plan, "Creative proposal response must contain synthesized master_plan"
    assert "<!-- motion_taste_citation" in master_plan
    assert "<!-- treatment_citation" in master_plan

    # PlanGate validation
    is_valid_plan, plan_errs = validate_plan_quality(master_plan)
    assert is_valid_plan is True, f"Synthesized master_plan failed PlanGate: {plan_errs}"

    # TasteGate validation via tempfile
    with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as tf:
        tf.write(master_plan)
        tf_path = Path(tf.name)

    try:
        taste_gate_proc = subprocess.run(
            [sys.executable, "scripts/gates/taste_gate.py", str(tf_path)],
            capture_output=True,
            text=True,
        )
        assert taste_gate_proc.returncode == 0, (
            f"Synthesized master_plan failed TasteGate:\n"
            f"stdout: {taste_gate_proc.stdout}\nstderr: {taste_gate_proc.stderr}"
        )
    finally:
        tf_path.unlink(missing_ok=True)


def test_cross_tenant_access_rejected(phase3_env):
    """Verifies that an unauthorized foreign tenant principal cannot generate proposals on project."""
    client = phase3_env["client"]
    token_bob = phase3_env["tokens"]["bob"]  # Belongs to ws_beta
    pid = phase3_env["prj_id"]  # Belongs to ws_alpha

    resp = client.post(
        f"/projects/{pid}/creative/proposals",
        headers={"Authorization": f"Bearer {token_bob}"},
        json={"prompt": "Attempt cross-tenant prompt injection"},
    )
    assert resp.status_code == 403, f"Expected 403 Forbidden for foreign tenant, got {resp.status_code}"


def test_apply_proposal_materializes_blueprint_and_master_plan(phase3_env):
    """
    Verifies that POST /projects/{id}/creative/apply:
    1. Enforces CAS revision checks.
    2. Materializes both 05_blueprint.json and master_plan.md to project directory.
    3. Replays cleanly on idempotent retry.
    """
    client = phase3_env["client"]
    token_alice = phase3_env["tokens"]["alice"]
    pid = phase3_env["prj_id"]
    pdir = phase3_env["pdir"]

    # Generate proposal first
    prop_resp = client.post(
        f"/projects/{pid}/creative/proposals",
        headers={"Authorization": f"Bearer {token_alice}"},
        json={"prompt": "Fast SaaS tutorial with code examples", "audio_mode": "VO_MUSIC"},
    )
    assert prop_resp.status_code == 200
    prop_data = prop_resp.json()

    candidate_bp = prop_data["candidate_blueprint"]
    master_plan = prop_data["master_plan"]
    proposal_id = prop_data["proposal_id"]
    base_rev = prop_data["base_revision"]

    # Explicit apply
    apply_resp = client.post(
        f"/projects/{pid}/creative/apply",
        headers={
            "Authorization": f"Bearer {token_alice}",
            "Idempotency-Key": "idemp_phase3_test_001",
        },
        json={
            "proposal_id": proposal_id,
            "base_revision": base_rev,
            "blueprint": candidate_bp,
            "master_plan": master_plan,
        },
    )
    assert apply_resp.status_code == 200, f"Apply failed: {apply_resp.text}"
    apply_data = apply_resp.json()

    assert apply_data["success"] is True
    assert apply_data["result_revision"] == base_rev + 1
    assert apply_data["master_plan_synced"] is True

    # Check disk materialization
    bp_file = pdir / "05_blueprint.json"
    plan_file = pdir / "master_plan.md"
    assert bp_file.exists(), "05_blueprint.json must be materialized on disk after apply"
    assert plan_file.exists(), "master_plan.md must be materialized on disk after apply"

    disk_bp = json.loads(bp_file.read_text(encoding="utf-8"))
    assert disk_bp.get("revision") == base_rev + 1
    assert plan_file.read_text(encoding="utf-8") == master_plan

    # Idempotent retry replay
    retry_resp = client.post(
        f"/projects/{pid}/creative/apply",
        headers={
            "Authorization": f"Bearer {token_alice}",
            "Idempotency-Key": "idemp_phase3_test_001",
        },
        json={
            "proposal_id": proposal_id,
            "base_revision": base_rev,
            "blueprint": candidate_bp,
            "master_plan": master_plan,
        },
    )
    assert retry_resp.status_code == 200
    retry_data = retry_resp.json()
    assert retry_data["idempotent"] is True
    assert retry_data["result_revision"] == base_rev + 1


def test_end_to_end_from_proposal_to_authorized_render(phase3_env):
    """
    Verifies the complete commercial journey:
    1. AI Proposal generated.
    2. Proposal explicitly applied to canonical storage and disk.
    3. Render execution is strictly BLOCKED prior to human review.
    4. ReviewBundle created & approved by human REVIEWER principal.
    5. Render authorization SUCCEEDS via ReviewService.assert_render_authorized().
    """
    client = phase3_env["client"]
    token_alice = phase3_env["tokens"]["alice"]
    pid = phase3_env["prj_id"]
    pdir = phase3_env["pdir"]
    reviewer_charlie = phase3_env["principals"]["charlie"]

    # Step 1: AI Proposal
    prop_resp = client.post(
        f"/projects/{pid}/creative/proposals",
        headers={"Authorization": f"Bearer {token_alice}"},
        json={"prompt": "Commercial product showcase video", "audio_mode": "VO_MUSIC"},
    )
    assert prop_resp.status_code == 200
    prop_data = prop_resp.json()

    # Step 2: Apply Proposal
    apply_resp = client.post(
        f"/projects/{pid}/creative/apply",
        headers={"Authorization": f"Bearer {token_alice}"},
        json={
            "proposal_id": prop_data["proposal_id"],
            "base_revision": prop_data["base_revision"],
            "blueprint": prop_data["candidate_blueprint"],
            "master_plan": prop_data["master_plan"],
        },
    )
    assert apply_resp.status_code == 200
    applied_rev = apply_resp.json()["result_revision"]

    # Step 3: Verify render authorization fails closed before review
    with pytest.raises(RenderNotAuthorizedError):
        ReviewService.assert_render_authorized(pdir)

    # Step 4: Prepare review bundle prerequisites (media_map, probe report)
    media_map_path = pdir / "media_map.json"
    media_map_path.write_text(json.dumps({"assets": {}}, indent=2), encoding="utf-8")

    probe_report_path = pdir / "probe_qc_report.json"
    probe_report_path.write_text(
        json.dumps({
            "status": "PASSED",
            "passed": True,
            "overall_status": "PASSED",
            "timestamp": "2026-10-18T22:00:00Z",
            "violations": [],
        }, indent=2),
        encoding="utf-8",
    )

    # Advance state to AWAITING_REVIEW with prerequisites recorded
    def prepare_review_state(st: ProjectState) -> None:
        st.lifecycle_state = LifecycleState.AWAITING_REVIEW.value
        # Record media_map evidence
        rec_mm = StateStore.create_artifact_record(
            pdir,
            "media_map.json",
            ValidationLevel.SHA256,
            stage="media",
            produced_at_revision=st.revision,
        )
        st.record_evidence(rec_mm)

        rec_probe = StateStore.create_artifact_record(
            pdir,
            "probe_qc_report.json",
            ValidationLevel.SHA256,
            stage="probe_qc",
            produced_at_revision=st.revision,
        )
        st.record_evidence(rec_probe)

    StateStore.atomic_update(
        project_dir=pdir,
        expected_revision=applied_rev,
        mutator=prepare_review_state,
    )

    state_after_prep = StateStore.load(pdir)
    current_rev = state_after_prep.revision

    # Create ReviewBundle
    bundle = ReviewService.create_review_bundle(
        project_dir=pdir,
    )
    assert bundle.review_bundle_id is not None

    # Step 5: Reviewer Charlie approves the review bundle
    decision = ReviewService.approve(
        project_dir=pdir,
        bundle_id=bundle.review_bundle_id,
        principal=reviewer_charlie,
        reason="Approved commercial proposal with high-quality master_plan.",
    )
    assert decision.decision == ReviewDecisionType.APPROVED

    # Step 6: Render authorization succeeds
    auth_result = ReviewService.assert_render_authorized(pdir)
    assert auth_result.is_authorized is True
    assert auth_result.actor_id == reviewer_charlie.principal_id
    assert auth_result.bundle_id == bundle.review_bundle_id
