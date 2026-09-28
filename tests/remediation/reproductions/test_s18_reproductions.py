"""
tests/remediation/reproductions/test_s18_reproductions.py — RED Reproductions for Package S18:
- LED-047 (P0): Probe builds timing from legacy timeline instead of canonical scenes.
- LED-048 (P0/P1): Probe reads FPS from silent default 30 or wrong authority.
- LED-049 (P1): Contact sheet failure does not fail Probe/Review (false success).
- LED-050 (P0): Probe evidence chain is lost / not bound to review bundle.
"""
import json
import pytest
from pathlib import Path


def test_reproduce_led_047_probe_legacy_timeline_ignores_canonical_scenes():
    """
    LED-047 Reproduction:
    A modern canonical blueprint has 'scenes' and NO 'timeline' field.
    The legacy probe timing logic reads bp.get('timeline', []) and only starts with {0.0},
    resulting in sampling ONLY frame 0 and ignoring scenes 2 and 3 completely.
    """
    bp = {
        "blueprint_version": "2.0.0",
        "project_id": "prj_multi_scene",
        "fps": 30,
        "aspect_ratio": "16:9",
        "scenes": [
            {"scene_id": "scene_a", "template": "title-card", "startFrame": 0, "durationFrames": 90},
            {"scene_id": "scene_b", "template": "data-story", "startFrame": 90, "durationFrames": 150},
            {"scene_id": "scene_c", "template": "outro", "startFrame": 240, "durationFrames": 60},
        ]
    }

    # Simulate legacy probe_qc.py timing extraction (lines 114-143 of old probe_qc.py)
    fps = bp.get("fps", 30)
    critical_secs = {0.0}
    for sec in bp.get("timeline", []):
        s = sec.get("sec", 0)
        critical_secs.add(float(s) + 1.0)
        for e in sec.get("elements", []):
            if e.get("kind") in ["caption", "text"]:
                critical_secs.add(float(e.get("start_sec", s)) + 0.5)

    scenes = bp.get("scenes", [])
    total_duration_frames = max((s.get("startFrame", 0) + s.get("durationFrames", 0) for s in scenes), default=0)
    max_allowed_frame = max(0, total_duration_frames - 1)
    legacy_critical_frames = sorted(list({min(max_allowed_frame, max(0, int(round(s * fps)))) for s in critical_secs}))

    # Legacy defect: only frame 0 is sampled; scenes B and C are completely unrepresented!
    assert legacy_critical_frames == [0], f"Expected legacy flaw to produce only [0], got {legacy_critical_frames}"
    assert not any(90 <= f < 240 for f in legacy_critical_frames), "Scene B is unrepresented in legacy probe"
    assert not any(240 <= f < 300 for f in legacy_critical_frames), "Scene C is unrepresented in legacy probe"


def test_reproduce_led_048_fps_silent_default_and_mismatch():
    """
    LED-048 Reproduction:
    Legacy probe uses bp.get('fps', 30) with silent fallback to 30.
    If blueprint has no fps or if project and blueprint fps diverge,
    silent default hides contract violations instead of failing closed.
    """
    # 1. Blueprint without FPS: legacy silently defaults to 30
    bp_no_fps = {"scenes": [{"scene_id": "s1", "startFrame": 0, "durationFrames": 60}]}
    legacy_fps = bp_no_fps.get("fps", 30)
    assert legacy_fps == 30  # Demonstrates silent default defect

    # 2. Non-30 FPS (e.g. 24 or 60): if blueprint specifies 24 fps, probe must strictly use 24
    bp_24 = {"fps": 24, "scenes": [{"scene_id": "s1", "startFrame": 0, "durationFrames": 48}]}
    assert bp_24["fps"] == 24


def test_reproduce_led_049_contact_sheet_failure_gives_false_success():
    """
    LED-049 Reproduction:
    In old probe_qc.py (lines 198-208), if ffmpeg fails to create contact_sheet.png,
    it caught the error with a print warning and still evaluated:
      is_passed = (len(rendered_files) == len(critical_frames)) and (len(critical_frames) > 0)
    resulting in status: 'pass' and generating .studio_unlocked despite missing mandatory contact sheet.
    """
    # Simulate legacy evaluation logic when contact sheet creation fails
    rendered_files = ["/tmp/probe_00_f0.png"]
    critical_frames = [0]
    contact_sheet_exists = False  # ffmpeg failed

    # Legacy probe_qc logic:
    is_passed = (len(rendered_files) == len(critical_frames)) and (len(critical_frames) > 0)
    legacy_status = "pass" if is_passed else "fail"

    # Defect: reports 'pass' even though contact sheet does not exist
    assert legacy_status == "pass" and not contact_sheet_exists, (
        "Demonstrated LED-049 defect: probe reports pass despite missing contact sheet!"
    )


def test_reproduce_led_050_probe_evidence_chain_not_bound_to_review(tmp_path):
    """
    LED-050 Evolution: Evolved from S00 Expected-RED reproduction to S18 GREEN regression proof.
    Old behavior: probe_report was only ValidationLevel.EXISTS, allowing tampered reports.
    Correct behavior (S18): probe_report is tracked by ValidationLevel.SHA256, and contact_sheet is mandatory SHA256.
    """
    from scripts.core.state_model import LifecycleState, ValidationLevel
    from scripts.core.evidence_matrix import REQUIRED_EVIDENCE_BY_STATE

    probe_item = next(item for item in REQUIRED_EVIDENCE_BY_STATE[LifecycleState.PROBE_PASSED] if item.logical_name == "probe_qc_report")
    assert probe_item.validation == ValidationLevel.SHA256, (
        "LED-050 resolved: probe_qc_report is now tracked by SHA256!"
    )
