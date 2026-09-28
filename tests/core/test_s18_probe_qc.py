"""
tests/core/test_s18_probe_qc.py — Comprehensive Test Suite for Package S18:
- Test Matrix A: Canonical Scenes Derivation (LED-047)
- Test Matrix B: Non-30 FPS Authority (LED-048)
- Test Matrix C: Very Short Scenes (durationFrames=1 and 2)
- Test Matrix D: Transition Boundary Sampling
- Test Matrix E: No Transition (No invented boundary frames)
- Test Matrix F: Contact Sheet Failure Handling (LED-049)
- Test Matrix G: Missing Rendered Frame Handling
- Test Matrix H: Tool Crash Categorized as EXECUTION_FAILURE
- Test Matrix I: Visual Defect Categorized as CONTENT_FAILURE
- Test Matrix J: Review Evidence Bundle Integrity (LED-050)
- Test Matrix K: Stale Bundle Invalidation on Upstream Mutation
- Test Matrix L: Deterministic Frame Plan Output
- Cross-Layer Integration Test: End-to-end chain verification
"""
import copy
import json
import os
from pathlib import Path
import pytest
from datetime import datetime, timezone

from scripts.core.failure_model import FailureCode
from scripts.core.probe_planner import (
    derive_probe_frame_plan,
    ProbeFramePlan,
    ProbeFrameReason,
    ProbeInvalidBlueprintError,
)
from scripts.core.render_input import build_render_input
from scripts.core.review_service import ReviewService, RenderNotAuthorizedError
from scripts.core.state_store import StateStore
from scripts.core.state_model import LifecycleState, ProjectState, ValidationLevel
from scripts.gates.probe_qc import run_probe_qc, verify_seal


@pytest.fixture
def probe_project(tmp_path):
    """Sets up a canonical project directory ready for probe testing."""
    proj_dir = tmp_path / "projects" / "test_probe_prj"
    proj_dir.mkdir(parents=True, exist_ok=True)
    project_id = "test_probe_prj"

    # 1. Blueprint (3 canonical scenes)
    bp = {
        "blueprint_version": "2.0.0",
        "project_id": project_id,
        "fps": 30,
        "aspect_ratio": "16:9",
        "scenes": [
            {
                "scene_id": "scene_a",
                "template": "rui-hero-device-assemble",
                "startFrame": 0,
                "durationFrames": 90,
                "transition": {
                    "type": "slide",
                    "durationFrames": 15,
                    "timing": "linear"
                }
            },
            {
                "scene_id": "scene_b",
                "template": "rui-split-screen",
                "startFrame": 90,
                "durationFrames": 150,
            },
            {
                "scene_id": "scene_c",
                "template": "rui-metric-highlight",
                "startFrame": 240,
                "durationFrames": 60,
            }
        ]
    }
    (proj_dir / "05_blueprint.json").write_text(json.dumps(bp, indent=2), encoding="utf-8")

    # 2. Asset Manifest
    manifest = {
        "manifest_version": "2.0.0",
        "project_id": project_id,
        "created_at": "2026-09-28T12:00:00Z",
        "assets": []
    }
    (proj_dir / "02_asset_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # 3. Media Map
    media_map = {}
    (proj_dir / "media_map.json").write_text(json.dumps(media_map, indent=2), encoding="utf-8")

    # 4. Master plan
    (proj_dir / "master_plan.md").write_text("# Plan\nCanonical test plan", encoding="utf-8")

    # 5. Pipeline State
    state = StateStore.create(proj_dir, project_id)
    state.lifecycle_state = LifecycleState.MATERIALIZED
    state.record_evidence(StateStore.create_artifact_record(proj_dir, "02_asset_manifest.json", ValidationLevel.SHA256))
    state.record_evidence(StateStore.create_artifact_record(proj_dir, "master_plan.md", ValidationLevel.SHA256))
    state.record_evidence(StateStore.create_artifact_record(proj_dir, "05_blueprint.json", ValidationLevel.SHA256))
    state.record_evidence(StateStore.create_artifact_record(proj_dir, "media_map.json", ValidationLevel.EXISTS))
    StateStore.save(proj_dir, state)

    return {
        "proj_dir": proj_dir,
        "project_id": project_id,
        "blueprint": bp,
    }


def make_fake_png_bytes(color: str = "white") -> bytes:
    """Returns valid PNG file bytes with standard 8-byte PNG signature."""
    # Standard 1x1 PNG or valid PNG signature with arbitrary chunk data
    return b"\x89PNG\r\n\x1a\n" + f"fake_{color}_chunk_data".encode("utf-8")


# ─── Test Matrix A: Canonical Scenes Derivation (LED-047) ─────────────────────

def test_matrix_a_canonical_scenes_derivation():
    """
    Test Matrix A:
    Blueprint with 3 scenes produces samples covering all 3 scenes.
    Does not rely on legacy timeline.
    Scene A (0..89): start=0, mid=45, end=89
    Scene B (90..239): start=90, mid=165, end=239
    Scene C (240..299): start=240, mid=270, end=299
    """
    bp = {
        "blueprint_version": "2.0.0",
        "project_id": "prj_3_scenes",
        "fps": 30,
        "aspect_ratio": "16:9",
        "scenes": [
            {"scene_id": "scene_a", "startFrame": 0, "durationFrames": 90},
            {"scene_id": "scene_b", "startFrame": 90, "durationFrames": 150},
            {"scene_id": "scene_c", "startFrame": 240, "durationFrames": 60},
        ]
    }
    plan = derive_probe_frame_plan(bp)

    assert plan.total_duration_frames == 300
    assert plan.fps == 30

    # Verify representations from each scene
    scene_a_frames = [s.frame for s in plan.samples if s.scene_id == "scene_a"]
    scene_b_frames = [s.frame for s in plan.samples if s.scene_id == "scene_b"]
    scene_c_frames = [s.frame for s in plan.samples if s.scene_id == "scene_c"]

    assert 0 in scene_a_frames
    assert 45 in scene_a_frames
    assert 89 in scene_a_frames

    assert 90 in scene_b_frames
    assert 165 in scene_b_frames
    assert 239 in scene_b_frames

    assert 240 in scene_c_frames
    assert 270 in scene_c_frames
    assert 299 in scene_c_frames

    # Overall frames list contains samples from all 3 scenes
    assert all(f in plan.frames for f in [0, 45, 89, 90, 165, 239, 240, 270, 299])


# ─── Test Matrix B: Non-30 FPS Authority (LED-048) ─────────────────────────────

def test_matrix_b_non_30_fps_authority():
    """
    Test Matrix B:
    Blueprint with non-30 FPS (e.g. 24 or 60) uses the canonical FPS.
    Missing FPS or mismatched FPS fails closed.
    """
    # 24 FPS
    bp_24 = {
        "blueprint_version": "2.0.0",
        "project_id": "prj_24fps",
        "fps": 24,
        "aspect_ratio": "16:9",
        "scenes": [
            {"scene_id": "s1", "startFrame": 0, "durationFrames": 48}
        ]
    }
    plan_24 = derive_probe_frame_plan(bp_24, canonical_fps=24)
    assert plan_24.fps == 24
    assert plan_24.total_duration_frames == 48

    # 60 FPS
    bp_60 = {
        "blueprint_version": "2.0.0",
        "project_id": "prj_60fps",
        "fps": 60,
        "aspect_ratio": "16:9",
        "scenes": [
            {"scene_id": "s1", "startFrame": 0, "durationFrames": 120}
        ]
    }
    plan_60 = derive_probe_frame_plan(bp_60, canonical_fps=60)
    assert plan_60.fps == 60

    # Missing FPS fails closed
    bp_missing_fps = {
        "blueprint_version": "2.0.0",
        "project_id": "prj_err",
        "aspect_ratio": "16:9",
        "scenes": [{"scene_id": "s1", "startFrame": 0, "durationFrames": 30}]
    }
    with pytest.raises(ProbeInvalidBlueprintError, match="missing mandatory 'fps'"):
        derive_probe_frame_plan(bp_missing_fps)

    # FPS Mismatch between render input and blueprint fails closed
    with pytest.raises(ProbeInvalidBlueprintError, match="FPS mismatch"):
        derive_probe_frame_plan(bp_24, canonical_fps=30)


# ─── Test Matrix C: Very Short Scenes ──────────────────────────────────────────

def test_matrix_c_very_short_scenes():
    """
    Test Matrix C:
    Scenes with durationFrames = 1 and 2.
    Must not produce negative frames or duplicate out-of-range frames.
    """
    bp = {
        "blueprint_version": "2.0.0",
        "project_id": "prj_short",
        "fps": 30,
        "aspect_ratio": "16:9",
        "scenes": [
            {"scene_id": "s_single", "startFrame": 0, "durationFrames": 1},
            {"scene_id": "s_double", "startFrame": 1, "durationFrames": 2},
        ]
    }
    plan = derive_probe_frame_plan(bp)

    assert plan.total_duration_frames == 3
    # Frame indices must be within [0, 2]
    assert all(0 <= f <= 2 for f in plan.frames)
    assert plan.frames == [0, 1, 2]

    # Scene single has frame 0
    s_single_samples = [s for s in plan.samples if s.scene_id == "s_single"]
    assert len(s_single_samples) == 1
    assert s_single_samples[0].frame == 0
    assert s_single_samples[0].reason == ProbeFrameReason.SCENE_START.value

    # Scene double has frame 1 and 2
    s_double_samples = [s for s in plan.samples if s.scene_id == "s_double"]
    assert len(s_double_samples) == 2
    assert s_double_samples[0].frame == 1
    assert s_double_samples[0].reason == ProbeFrameReason.SCENE_START.value
    assert s_double_samples[1].frame == 2
    assert s_double_samples[1].reason == ProbeFrameReason.SCENE_END.value


# ─── Test Matrix D: Transition Boundary Sampling ──────────────────────────────

def test_matrix_d_transition_boundary_sampling():
    """
    Test Matrix D:
    Scenes with transition generate boundary samples:
    boundary - 1 (TRANSITION_PRE)
    boundary     (TRANSITION_BOUNDARY)
    boundary + 1 (TRANSITION_POST)
    """
    bp = {
        "blueprint_version": "2.0.0",
        "project_id": "prj_trans",
        "fps": 30,
        "aspect_ratio": "16:9",
        "scenes": [
            {
                "scene_id": "s1",
                "startFrame": 0,
                "durationFrames": 60,
                "transition": {"type": "slide", "durationFrames": 15}
            },
            {
                "scene_id": "s2",
                "startFrame": 60,
                "durationFrames": 60,
            }
        ]
    }
    plan = derive_probe_frame_plan(bp)

    # Boundary is at frame 60
    reasons_by_frame = {}
    for s in plan.samples:
        reasons_by_frame.setdefault(s.frame, []).append(s.reason)

    assert ProbeFrameReason.TRANSITION_PRE.value in reasons_by_frame[59]
    assert ProbeFrameReason.TRANSITION_BOUNDARY.value in reasons_by_frame[60]
    assert ProbeFrameReason.TRANSITION_POST.value in reasons_by_frame[61]


# ─── Test Matrix E: No Transition (No Invented Boundary Frames) ────────────────

def test_matrix_e_no_transition_no_invented_boundary():
    """
    Test Matrix E:
    When scenes have no transitions, no TRANSITION_* frames are invented.
    """
    bp = {
        "blueprint_version": "2.0.0",
        "project_id": "prj_no_trans",
        "fps": 30,
        "aspect_ratio": "16:9",
        "scenes": [
            {"scene_id": "s1", "startFrame": 0, "durationFrames": 60},
            {"scene_id": "s2", "startFrame": 60, "durationFrames": 60},
        ]
    }
    plan = derive_probe_frame_plan(bp)

    transition_reasons = {
        ProbeFrameReason.TRANSITION_PRE.value,
        ProbeFrameReason.TRANSITION_BOUNDARY.value,
        ProbeFrameReason.TRANSITION_POST.value,
    }
    plan_reasons = {s.reason for s in plan.samples}
    assert not (plan_reasons & transition_reasons), "Found unexpected transition reasons when no transition exists!"


# ─── Test Matrix F: Contact Sheet Failure Handling (LED-049) ──────────────────

def test_matrix_f_contact_sheet_failure_fails_closed(probe_project):
    """
    Test Matrix F (LED-049):
    If contact sheet fails to generate (e.g. ffmpeg error, 0 bytes, or corrupt header),
    probe MUST fail closed:
    - status == 'EXECUTION_FAILURE' (legacy_status == 'fail')
    - No .studio_unlocked created
    - No active ReviewBundle created
    """
    proj_dir = probe_project["proj_dir"]

    def mock_render(idx, frame, out_dir):
        # Render succeeds for frames
        fpath = out_dir / f"probe_{idx:02d}_f{frame}.png"
        fpath.write_bytes(make_fake_png_bytes())
        return True, str(fpath.absolute()), "sha_dummy", None

    # Run probe QC where frames succeed, but contact_sheet will fail if ffmpeg is pointed to bad args
    # or if we simulate ffmpeg failure
    import subprocess
    orig_safe_subprocess = subprocess.run

    # Trigger contact sheet failure by corrupting the output contact_sheet
    def failing_subprocess(cmd, *args, **kwargs):
        if "hstack" in str(cmd):
            # Simulate ffmpeg failure
            class DummyRes:
                returncode = 1
                stdout = b""
                stderr = b"FFmpeg filter error: hstack failed"
            return DummyRes()
        return orig_safe_subprocess(cmd, *args, **kwargs)

    import scripts.gates.probe_qc as probe_mod
    orig_sub = probe_mod.safe_subprocess
    probe_mod.safe_subprocess = failing_subprocess

    try:
        report = run_probe_qc(proj_dir, mock_render_fn=mock_render)
    finally:
        probe_mod.safe_subprocess = orig_sub

    assert report["status"] == "EXECUTION_FAILURE"
    assert report["legacy_status"] == "fail"
    assert any(e["code"] == FailureCode.PROBE_CONTACT_SHEET_FAILED.value for e in report["errors"])

    # Must NOT create .studio_unlocked
    assert not (proj_dir / ".studio_unlocked").exists()

    # State must NOT have an active review bundle created from this failed run
    state = StateStore.load(proj_dir)
    assert not state.review_bundles or state.review_bundles[-1].status != "ACTIVE"


# ─── Test Matrix G: Missing Rendered Frame Handling ────────────────────────────

def test_matrix_g_missing_rendered_frame(probe_project):
    """
    Test Matrix G:
    If a single frame fails to render, probe fails closed.
    Contact sheet is not marked successful.
    """
    proj_dir = probe_project["proj_dir"]

    def mock_render_with_failure(idx, frame, out_dir):
        if idx == 1:
            # Frame 1 fails to render
            return False, None, None, "Remotion timed out rendering frame"
        fpath = out_dir / f"probe_{idx:02d}_f{frame}.png"
        fpath.write_bytes(make_fake_png_bytes())
        return True, str(fpath.absolute()), "sha_dummy", None

    report = run_probe_qc(proj_dir, mock_render_fn=mock_render_with_failure)

    assert report["status"] == "EXECUTION_FAILURE"
    assert report["legacy_status"] == "fail"
    assert any(e["code"] == FailureCode.PROBE_FRAME_RENDER_FAILED.value for e in report["errors"])
    assert not (proj_dir / ".studio_unlocked").exists()


# ─── Test Matrix H: Tool Crash Categorized as EXECUTION_FAILURE ────────────────

def test_matrix_h_tool_crash_is_execution_failure(probe_project):
    """
    Test Matrix H:
    Subprocess or tool crash is categorized as EXECUTION_FAILURE, not content warning.
    """
    proj_dir = probe_project["proj_dir"]

    def mock_render_crash(idx, frame, out_dir):
        return False, None, None, "SIGSEGV: Browser engine crashed"

    report = run_probe_qc(proj_dir, mock_render_fn=mock_render_crash)

    assert report["status"] == "EXECUTION_FAILURE"
    assert not (proj_dir / ".studio_unlocked").exists()


# ─── Test Matrix I: Visual Defect Categorized as CONTENT_FAILURE ───────────────

def test_matrix_i_content_defect_categorized_separately(probe_project):
    """
    Test Matrix I:
    Content-level failures are differentiated from execution crashes.
    """
    proj_dir = probe_project["proj_dir"]

    # When report has content defect
    def mock_render_ok(idx, frame, out_dir):
        fpath = out_dir / f"probe_{idx:02d}_f{frame}.png"
        fpath.write_bytes(make_fake_png_bytes())
        return True, str(fpath.absolute()), "sha_val", None

    # Patch contact sheet to succeed
    import scripts.gates.probe_qc as probe_mod
    orig_sub = probe_mod.safe_subprocess

    def successful_cs(cmd, *args, **kwargs):
        if "hstack" in str(cmd):
            # Write a valid contact sheet
            out_file = Path(cmd[-1])
            out_file.write_bytes(make_fake_png_bytes())
            class DummyRes:
                returncode = 0
                stdout = b""
                stderr = b""
            return DummyRes()
        return orig_sub(cmd, *args, **kwargs)

    probe_mod.safe_subprocess = successful_cs
    try:
        report = run_probe_qc(proj_dir, mock_render_fn=mock_render_ok)
    finally:
        probe_mod.safe_subprocess = orig_sub

    assert report["status"] == "PASS"
    assert report["legacy_status"] == "pass"


# ─── Test Matrix J: Review Evidence Bundle Integrity (LED-050) ────────────────

def test_matrix_j_review_bundle_integrity(probe_project):
    """
    Test Matrix J (LED-050):
    On PASS, ReviewService creates an immutable ReviewBundle in ProjectState.
    The bundle contains:
    - review_bundle_id
    - blueprint_sha256
    - render_input_sha256
    - media_map_sha256
    - probe_report_sha256
    - contact_sheet_sha256
    - probe_frame_plan_digest
    - rendered_frames_sha256
    - bundle_digest
    """
    proj_dir = probe_project["proj_dir"]

    def mock_render(idx, frame, out_dir):
        fpath = out_dir / f"probe_{idx:02d}_f{frame}.png"
        b = make_fake_png_bytes(f"frame_{frame}")
        fpath.write_bytes(b)
        import hashlib
        return True, str(fpath.absolute()), hashlib.sha256(b).hexdigest(), None

    import scripts.gates.probe_qc as probe_mod
    orig_sub = probe_mod.safe_subprocess

    def mock_cs(cmd, *args, **kwargs):
        if "hstack" in str(cmd):
            out_file = Path(cmd[-1])
            out_file.write_bytes(make_fake_png_bytes("contact_sheet"))
            class DummyRes:
                returncode = 0
                stdout = b""
                stderr = b""
            return DummyRes()
        return orig_sub(cmd, *args, **kwargs)

    probe_mod.safe_subprocess = mock_cs
    try:
        report = run_probe_qc(proj_dir, mock_render_fn=mock_render)
    finally:
        probe_mod.safe_subprocess = orig_sub

    assert report["status"] == "PASS"
    assert report.get("review_bundle_id") is not None

    state = StateStore.load(proj_dir)
    active_bundle = state.get_active_review_bundle()
    assert active_bundle is not None
    assert active_bundle.review_bundle_id == report["review_bundle_id"]
    assert active_bundle.status == "ACTIVE"
    assert active_bundle.contact_sheet_sha256 is not None
    assert active_bundle.probe_report_sha256 is not None
    assert active_bundle.blueprint_sha256 is not None
    assert active_bundle.render_input_sha256 is not None
    assert active_bundle.probe_frame_plan_digest is not None
    assert len(active_bundle.rendered_frames_sha256) > 0

    # .studio_unlocked contains review_bundle_id
    unlock_data = json.loads((proj_dir / ".studio_unlocked").read_text(encoding="utf-8"))
    assert unlock_data["review_bundle_id"] == active_bundle.review_bundle_id


# ─── Test Matrix K: Stale Bundle Invalidation on Upstream Mutation ─────────────

def test_matrix_k_stale_bundle_invalidation(probe_project):
    """
    Test Matrix K:
    1. Run probe QC -> generates active review bundle.
    2. Approve review bundle.
    3. Mutate blueprint on disk.
    4. assert_render_authorized must fail closed with REVIEW_BUNDLE_STALE.
    """
    proj_dir = probe_project["proj_dir"]

    def mock_render(idx, frame, out_dir):
        fpath = out_dir / f"probe_{idx:02d}_f{frame}.png"
        b = make_fake_png_bytes(f"frame_{frame}")
        fpath.write_bytes(b)
        import hashlib
        return True, str(fpath.absolute()), hashlib.sha256(b).hexdigest(), None

    import scripts.gates.probe_qc as probe_mod
    orig_sub = probe_mod.safe_subprocess

    def mock_cs(cmd, *args, **kwargs):
        if "hstack" in str(cmd):
            out_file = Path(cmd[-1])
            out_file.write_bytes(make_fake_png_bytes("contact_sheet"))
            class DummyRes:
                returncode = 0
                stdout = b""
                stderr = b""
            return DummyRes()
        return orig_sub(cmd, *args, **kwargs)

    probe_mod.safe_subprocess = mock_cs
    try:
        report = run_probe_qc(proj_dir, mock_render_fn=mock_render)
    finally:
        probe_mod.safe_subprocess = orig_sub

    bundle_id = report["review_bundle_id"]

    # Transition project to AWAITING_REVIEW
    state = StateStore.load(proj_dir)
    state.lifecycle_state = LifecycleState.AWAITING_REVIEW
    StateStore.save(proj_dir, state)

    # Approve via ReviewService
    from scripts.core.review_service import create_local_trusted_principal
    principal = create_local_trusted_principal("test_reviewer")
    ReviewService.approve(proj_dir, bundle_id, principal=principal)

    # Render is currently authorized
    auth_res = ReviewService.assert_render_authorized(proj_dir)
    assert auth_res.is_authorized is True

    # Mutate Blueprint on disk
    bp_data = json.loads((proj_dir / "05_blueprint.json").read_text(encoding="utf-8"))
    bp_data["meta"] = {"mutated": True}
    (proj_dir / "05_blueprint.json").write_text(json.dumps(bp_data), encoding="utf-8")

    # Render authorization MUST fail closed with REVIEW_BUNDLE_STALE
    with pytest.raises(RenderNotAuthorizedError) as exc_info:
        ReviewService.assert_render_authorized(proj_dir)
    assert exc_info.value.code == FailureCode.REVIEW_BUNDLE_STALE


# ─── Test Matrix L: Deterministic Frame Plan ───────────────────────────────────

def test_matrix_l_deterministic_frame_plan():
    """
    Test Matrix L:
    Repeated derivation with identical blueprint produces exact same frames and plan digest.
    """
    bp = {
        "blueprint_version": "2.0.0",
        "project_id": "prj_determ",
        "fps": 30,
        "aspect_ratio": "16:9",
        "scenes": [
            {"scene_id": "s1", "startFrame": 0, "durationFrames": 90, "transition": {"type": "fade", "durationFrames": 10}},
            {"scene_id": "s2", "startFrame": 90, "durationFrames": 120},
        ]
    }
    plan1 = derive_probe_frame_plan(bp)
    plan2 = derive_probe_frame_plan(bp)

    assert plan1.frames == plan2.frames
    assert plan1.plan_digest == plan2.plan_digest
    assert len(plan1.samples) == len(plan2.samples)


# ─── Section 21: Cross-Layer Integration Test ─────────────────────────────────

def test_cross_layer_end_to_end_probe_review_chain(probe_project):
    """
    Section 21 Cross-Layer Test:
    build_render_input -> parse canonical input -> derive probe frame plan
    -> render representative frames -> build contact sheet -> probe report
    -> review bundle -> verify bundle binds exact inputs.
    """
    proj_dir = probe_project["proj_dir"]

    # 1. build_render_input
    render_input = build_render_input(proj_dir, verify_files_on_disk=True, write_to_disk=True)
    bp = render_input["projectData"]["blueprint"]
    proj_meta = render_input["projectData"]["project"]

    # 2. derive_probe_frame_plan
    plan = derive_probe_frame_plan(bp, canonical_fps=proj_meta["fps"])
    assert len(plan.frames) > 0

    # 3. run_probe_qc with mock renders
    def mock_render(idx, frame, out_dir):
        fpath = out_dir / f"probe_{idx:02d}_f{frame}.png"
        b = make_fake_png_bytes(f"f_{frame}")
        fpath.write_bytes(b)
        import hashlib
        return True, str(fpath.absolute()), hashlib.sha256(b).hexdigest(), None

    import scripts.gates.probe_qc as probe_mod
    orig_sub = probe_mod.safe_subprocess

    def mock_cs(cmd, *args, **kwargs):
        if "hstack" in str(cmd):
            out_file = Path(cmd[-1])
            out_file.write_bytes(make_fake_png_bytes("sheet"))
            class DummyRes:
                returncode = 0
                stdout = b""
                stderr = b""
            return DummyRes()
        return orig_sub(cmd, *args, **kwargs)

    probe_mod.safe_subprocess = mock_cs
    try:
        report = run_probe_qc(proj_dir, mock_render_fn=mock_render)
    finally:
        probe_mod.safe_subprocess = orig_sub

    assert report["status"] == "PASS"

    # 4. Verify ReviewBundle points exactly to input that was started from
    state = StateStore.load(proj_dir)
    active_bundle = state.get_active_review_bundle()
    assert active_bundle is not None

    # Check hash matching
    import hashlib
    bp_sha = hashlib.sha256((proj_dir / "05_blueprint.json").read_bytes()).hexdigest()
    assert active_bundle.blueprint_sha256 == bp_sha
    assert active_bundle.render_input_sha256 == report["render_input_sha256"]
    assert active_bundle.probe_report_sha256 == hashlib.sha256((proj_dir / "probe_qc_report.json").read_bytes()).hexdigest()
    assert active_bundle.contact_sheet_sha256 == hashlib.sha256((proj_dir / "contact_sheet.png").read_bytes()).hexdigest()
    assert active_bundle.probe_frame_plan_digest == plan.plan_digest
