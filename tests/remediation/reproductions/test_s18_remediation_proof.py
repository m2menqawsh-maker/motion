"""
tests/remediation/reproductions/test_s18_remediation_proof.py — GREEN Remediation Proof for Package S18:
- LED-047 (P0): Probe builds timing from canonical scenes (startFrame, durationFrames), not legacy timeline.
- LED-048 (P0/P1): Probe reads FPS strictly from canonical authority, no silent default 30.
- LED-049 (P1): Contact sheet failure fails closed (mandatory review evidence, no false success).
- LED-050 (P0): Probe evidence chain immutably bound in ReviewBundle via ReviewService with hash validation.
"""
import hashlib
import json
from pathlib import Path
import pytest

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
from scripts.core.state_model import LifecycleState, ValidationLevel
from scripts.gates.probe_qc import run_probe_qc


def test_green_led_047_canonical_scenes_timing_authority():
    """
    GREEN PROOF for LED-047:
    Probe timing derives exclusively from canonical blueprint scenes.
    A 3-scene blueprint generates samples representing all scenes (start, mid, end).
    """
    bp = {
        "blueprint_version": "2.0.0",
        "project_id": "prj_green_047",
        "fps": 30,
        "aspect_ratio": "16:9",
        "scenes": [
            {"scene_id": "scene_a", "template": "title-card", "startFrame": 0, "durationFrames": 90},
            {"scene_id": "scene_b", "template": "data-story", "startFrame": 90, "durationFrames": 150},
            {"scene_id": "scene_c", "template": "outro", "startFrame": 240, "durationFrames": 60},
        ]
    }
    plan = derive_probe_frame_plan(bp)

    # 1. Total duration derives from scenes
    assert plan.total_duration_frames == 300

    # 2. Every scene has start, middle, and end represented
    for sid in ["scene_a", "scene_b", "scene_c"]:
        scene_samples = [s for s in plan.samples if s.scene_id == sid]
        reasons = {s.reason for s in scene_samples}
        assert ProbeFrameReason.SCENE_START.value in reasons, f"{sid} missing start"
        assert ProbeFrameReason.SCENE_MIDDLE.value in reasons, f"{sid} missing middle"
        assert ProbeFrameReason.SCENE_END.value in reasons, f"{sid} missing end"

    # 3. Frames are strictly sorted and within range
    assert plan.frames == sorted(list(set(plan.frames)))
    assert plan.frames[0] == 0
    assert plan.frames[-1] == 299


def test_green_led_048_fps_authority_and_fail_closed():
    """
    GREEN PROOF for LED-048:
    1. Probe respects non-30 FPS (e.g. 24 fps or 60 fps).
    2. Blueprint missing FPS fails closed (no silent fallback to 30).
    3. Render input and blueprint FPS mismatch fails closed.
    """
    # 24 FPS
    bp_24 = {
        "blueprint_version": "2.0.0",
        "project_id": "prj_green_048",
        "fps": 24,
        "aspect_ratio": "16:9",
        "scenes": [{"scene_id": "s1", "startFrame": 0, "durationFrames": 48}]
    }
    plan_24 = derive_probe_frame_plan(bp_24, canonical_fps=24)
    assert plan_24.fps == 24

    # Missing FPS fails closed
    bp_no_fps = {
        "blueprint_version": "2.0.0",
        "project_id": "prj_no_fps",
        "aspect_ratio": "16:9",
        "scenes": [{"scene_id": "s1", "startFrame": 0, "durationFrames": 60}]
    }
    with pytest.raises(ProbeInvalidBlueprintError, match="missing mandatory 'fps'"):
        derive_probe_frame_plan(bp_no_fps)

    # Mismatched FPS fails closed
    with pytest.raises(ProbeInvalidBlueprintError, match="FPS mismatch"):
        derive_probe_frame_plan(bp_24, canonical_fps=30)


def test_green_led_049_contact_sheet_mandatory_evidence(tmp_path):
    """
    GREEN PROOF for LED-049:
    Contact sheet is mandatory review evidence.
    If contact sheet creation fails or produces 0 bytes, Probe QC fails closed:
    - Status is EXECUTION_FAILURE (not pass)
    - Error code is PROBE_CONTACT_SHEET_FAILED
    - .studio_unlocked is NOT created
    """
    proj_dir = tmp_path / "prj_green_049"
    proj_dir.mkdir(parents=True, exist_ok=True)
    project_id = "prj_green_049"

    # Setup valid project files
    bp = {
        "blueprint_version": "2.0.0",
        "project_id": project_id,
        "fps": 30,
        "aspect_ratio": "16:9",
        "scenes": [{"scene_id": "s1", "template": "HeroDeviceAssembleWrapper", "startFrame": 0, "durationFrames": 30}]
    }
    (proj_dir / "05_blueprint.json").write_text(json.dumps(bp, indent=2), encoding="utf-8")
    (proj_dir / "media_map.json").write_text("{}", encoding="utf-8")
    (proj_dir / "master_plan.md").write_text("# Plan", encoding="utf-8")

    state = StateStore.create(proj_dir, project_id)
    state.lifecycle_state = LifecycleState.MATERIALIZED
    StateStore.save(proj_dir, state)

    def mock_render_ok(idx, frame, out_dir):
        fpath = out_dir / f"probe_{idx:02d}_f{frame}.png"
        fpath.write_bytes(b"\x89PNG\r\n\x1a\nfake_frame")
        return True, str(fpath.absolute()), "sha_dummy", None

    # Simulate ffmpeg failure on contact sheet
    import scripts.gates.probe_qc as probe_mod
    orig_sub = probe_mod.safe_subprocess

    def failing_cs(cmd, *args, **kwargs):
        if "hstack" in str(cmd):
            class DummyRes:
                returncode = 1
                stdout = b""
                stderr = b"FFmpeg error: filter failed"
            return DummyRes()
        return orig_sub(cmd, *args, **kwargs)

    probe_mod.safe_subprocess = failing_cs
    try:
        report = run_probe_qc(proj_dir, mock_render_fn=mock_render_ok)
    finally:
        probe_mod.safe_subprocess = orig_sub

    assert report["status"] == "EXECUTION_FAILURE"
    assert report["legacy_status"] == "fail"
    assert any(e["code"] == FailureCode.PROBE_CONTACT_SHEET_FAILED.value for e in report["errors"])
    assert not (proj_dir / ".studio_unlocked").exists()


def test_green_led_050_review_evidence_bundle_bound(tmp_path):
    """
    GREEN PROOF for LED-050:
    On probe success:
    1. ReviewService registers an immutable ReviewBundle in ProjectState.
    2. ReviewBundle stores SHA256 of blueprint, render_input, media_map, probe_report, contact_sheet, frame plan digest.
    3. .studio_unlocked contains review_bundle_id and bundle_digest.
    4. Modifying blueprint after approval invalidates review and blocks render.
    """
    proj_dir = tmp_path / "prj_green_050"
    proj_dir.mkdir(parents=True, exist_ok=True)
    project_id = "prj_green_050"

    bp = {
        "blueprint_version": "2.0.0",
        "project_id": project_id,
        "fps": 30,
        "aspect_ratio": "16:9",
        "scenes": [
            {"scene_id": "s1", "template": "HeroDeviceAssembleWrapper", "startFrame": 0, "durationFrames": 60, "transition": {"type": "fade", "durationFrames": 15}},
            {"scene_id": "s2", "template": "SplitScreenComparisonWrapper", "startFrame": 60, "durationFrames": 60},
        ]
    }
    (proj_dir / "05_blueprint.json").write_text(json.dumps(bp, indent=2), encoding="utf-8")
    (proj_dir / "media_map.json").write_text("{}", encoding="utf-8")
    (proj_dir / "master_plan.md").write_text("# Plan", encoding="utf-8")

    state = StateStore.create(proj_dir, project_id)
    state.lifecycle_state = LifecycleState.MATERIALIZED
    state.record_evidence(StateStore.create_artifact_record(proj_dir, "05_blueprint.json", ValidationLevel.SHA256))
    state.record_evidence(StateStore.create_artifact_record(proj_dir, "media_map.json", ValidationLevel.EXISTS))
    StateStore.save(proj_dir, state)

    def mock_render(idx, frame, out_dir):
        fpath = out_dir / f"probe_{idx:02d}_f{frame}.png"
        b = b"\x89PNG\r\n\x1a\n" + f"frame_{frame}".encode("utf-8")
        fpath.write_bytes(b)
        return True, str(fpath.absolute()), hashlib.sha256(b).hexdigest(), None

    import scripts.gates.probe_qc as probe_mod
    orig_sub = probe_mod.safe_subprocess

    def mock_cs(cmd, *args, **kwargs):
        if "hstack" in str(cmd):
            out_file = Path(cmd[-1])
            out_file.write_bytes(b"\x89PNG\r\n\x1a\nfake_contact_sheet")
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

    # Verify bundle in state
    state = StateStore.load(proj_dir)
    active_bundle = state.get_active_review_bundle()
    assert active_bundle is not None
    assert active_bundle.status == "ACTIVE"
    assert active_bundle.blueprint_sha256 == hashlib.sha256((proj_dir / "05_blueprint.json").read_bytes()).hexdigest()
    assert active_bundle.contact_sheet_sha256 is not None
    assert active_bundle.probe_report_sha256 is not None
    assert active_bundle.probe_frame_plan_digest is not None
    assert len(active_bundle.rendered_frames_sha256) > 0

    # Verify .studio_unlocked contains review_bundle_id
    unlock_data = json.loads((proj_dir / ".studio_unlocked").read_text(encoding="utf-8"))
    assert unlock_data["review_bundle_id"] == active_bundle.review_bundle_id

    # Move to AWAITING_REVIEW and approve
    state.lifecycle_state = LifecycleState.AWAITING_REVIEW
    StateStore.save(proj_dir, state)

    from scripts.core.review_service import create_local_trusted_principal
    reviewer = create_local_trusted_principal("reviewer_1")
    ReviewService.approve(proj_dir, active_bundle.review_bundle_id, principal=reviewer)

    # Render authorized
    res = ReviewService.assert_render_authorized(proj_dir)
    assert res.is_authorized is True

    # Mutate Blueprint -> invalidate bundle
    bp_mutated = dict(bp)
    bp_mutated["scenes"][0]["durationFrames"] = 99
    (proj_dir / "05_blueprint.json").write_text(json.dumps(bp_mutated), encoding="utf-8")

    # Render authorization fails closed
    with pytest.raises(RenderNotAuthorizedError) as exc:
        ReviewService.assert_render_authorized(proj_dir)
    assert exc.value.code == FailureCode.REVIEW_BUNDLE_STALE
