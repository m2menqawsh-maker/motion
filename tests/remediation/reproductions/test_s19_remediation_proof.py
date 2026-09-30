"""
tests/remediation/reproductions/test_s19_remediation_proof.py — S19 Remediation Proof Suite:
- LED-051 (P0): Canonical Blueprint aspect ratios (9:16, 16:9, 1:1), reference FPS, and derived duration.
- LED-052 (P1): check_av_sync active in real Final QC orchestration, structured reporting, threshold enforcement.
- LED-053 (P1): Strict PASS / FAIL / CHECK_FAILED_TO_EXECUTE semantics, fail-closed on critical analyzer crash, CLI non-zero exit.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Dict, Any
from unittest.mock import patch, MagicMock

import pytest

from scripts.gates.final_qc import (
    run_final_qc,
    check_dimensions_and_aspect,
    check_fps,
    check_duration,
    check_black_frames,
    check_audio_lufs,
    check_av_sync,
    compute_qc_decision,
    CANONICAL_ASPECT_MAP,
)


@pytest.fixture
def test_project(tmp_path: Path):
    """Creates a temporary canonical project structure for Final QC tests."""
    project_id = "prj_s19_test"
    project_dir = tmp_path / "projects" / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    return project_id, project_dir, tmp_path


def create_canonical_blueprint(
    project_id: str,
    aspect_ratio: str = "16:9",
    fps: int = 30,
    scenes: list | None = None,
    with_audio: bool = True
) -> dict:
    if scenes is None:
        scenes = [
            {
                "scene_id": "scene_01",
                "template": "ShowcaseWrapper",
                "startFrame": 0,
                "durationFrames": 90,
            }
        ]
    bp = {
        "blueprint_version": "2.0.0",
        "project_id": project_id,
        "fps": fps,
        "aspect_ratio": aspect_ratio,
        "scenes": scenes,
    }
    if with_audio:
        bp["audio"] = {
            "voiceover": {
                "asset_ref": "vo_1",
                "volume": 1.0,
                "startFrame": 0
            }
        }
    return bp


# ==============================================================================
# LED-051 Tests: Canonical Blueprint, Aspect Ratios, FPS, and Derived Duration
# ==============================================================================

@pytest.mark.parametrize("aspect_ratio,expected_dim", [
    ("16:9", (1920, 1080)),
    ("9:16", (1080, 1920)),
    ("1:1", (1080, 1080)),
])
def test_proof_led_051_canonical_aspect_ratios(test_project, aspect_ratio, expected_dim):
    """
    LED-051 PROOF:
    Final QC enforces canonical aspect ratios (16:9, 9:16, 1:1) from Blueprint v2,
    and validates video stream dimensions against the exact canonical resolution without fallback.
    """
    project_id, project_dir, workspace = test_project
    w, h = expected_dim

    # Write canonical blueprint
    bp = create_canonical_blueprint(project_id, aspect_ratio=aspect_ratio, fps=30)
    (project_dir / "05_blueprint.json").write_text(json.dumps(bp), encoding="utf-8")
    (project_dir / "out.mp4").touch()
    (project_dir / "04_timings.json").write_text(json.dumps({"words": []}), encoding="utf-8")

    # Mock analyze_video_streams with matching resolution
    mock_v_stream = {
        "codec_type": "video",
        "codec_name": "h264",
        "width": w,
        "height": h,
        "r_frame_rate": "30/1",
        "duration": "3.0"
    }

    with patch("scripts.gates.final_qc.analyze_video_streams", return_value=(mock_v_stream, None, None)), \
         patch("scripts.gates.final_qc.check_black_frames", return_value={"status": "PASS", "severity": "CRITICAL", "message": "Clean"}):
        ok, report = run_final_qc(project_id, workspace_root=workspace)

        assert report["summary"]["expected_aspect"] == aspect_ratio
        assert report["summary"]["actual_aspect"] == aspect_ratio
        assert report["summary"]["expected_dimensions"] == f"{w}x{h}"
        assert report["summary"]["actual_dimensions"] == f"{w}x{h}"
        assert report["checks"]["dimensions"]["status"] == "PASS"


def test_proof_led_051_aspect_mismatch_fails_closed(test_project):
    """
    LED-051 PROOF:
    If Blueprint specifies 9:16 but video was rendered at 1920x1080 (16:9),
    Final QC fails with dimensions mismatch and does NOT fall back silently to 16:9.
    """
    project_id, project_dir, workspace = test_project
    bp = create_canonical_blueprint(project_id, aspect_ratio="9:16", fps=30)
    (project_dir / "05_blueprint.json").write_text(json.dumps(bp), encoding="utf-8")
    (project_dir / "out.mp4").touch()

    # Video stream rendered at 1920x1080 (wrong for 9:16)
    mock_v_stream = {
        "codec_type": "video",
        "codec_name": "h264",
        "width": 1920,
        "height": 1080,
        "r_frame_rate": "30/1",
        "duration": "3.0"
    }

    with patch("scripts.gates.final_qc.analyze_video_streams", return_value=(mock_v_stream, None, None)), \
         patch("scripts.gates.final_qc.check_black_frames", return_value={"status": "PASS", "severity": "CRITICAL", "message": "Clean"}):
        ok, report = run_final_qc(project_id, workspace_root=workspace)

        assert ok is False
        assert report["status"] == "FAIL"
        dim_check = report["checks"]["dimensions"]
        assert dim_check["status"] == "FAIL"
        assert dim_check["expected_aspect"] == "9:16"
        assert dim_check["actual_aspect"] == "16:9"


def test_proof_led_051_derived_duration_and_non_30_fps(test_project):
    """
    LED-051 PROOF:
    1. FPS is not always 30 (e.g. 24 fps).
    2. Expected duration is derived from max(scene.startFrame + scene.durationFrames) / fps,
       NOT by blindly summing scene durations or reading legacy meta.duration_sec.
       Scene 1: start 0, dur 48 (ends at 48)
       Scene 2: start 24, dur 72 (ends at 96, overlaps scene 1)
       Scene 3: start 96, dur 24 (ends at 120)
       max(startFrame + durationFrames) = 120 frames
       expected_duration_seconds = 120 / 24 = 5.0 seconds (sum would be 144 frames = 6.0s).
    """
    project_id, project_dir, workspace = test_project

    scenes = [
        {"scene_id": "s1", "template": "t1", "startFrame": 0, "durationFrames": 48},
        {"scene_id": "s2", "template": "t2", "startFrame": 24, "durationFrames": 72},
        {"scene_id": "s3", "template": "t3", "startFrame": 96, "durationFrames": 24},
    ]

    bp = create_canonical_blueprint(project_id, aspect_ratio="16:9", fps=24, scenes=scenes, with_audio=False)
    # Add misleading legacy meta to prove it is completely ignored
    bp["meta"] = {"duration_sec": 99.0, "fps": 60}
    (project_dir / "05_blueprint.json").write_text(json.dumps(bp), encoding="utf-8")
    (project_dir / "out.mp4").touch()

    # Video stream rendered at 24 fps, actual duration 5.02s
    mock_v_stream = {
        "codec_type": "video",
        "codec_name": "h264",
        "width": 1920,
        "height": 1080,
        "r_frame_rate": "24/1",
        "duration": "5.02"
    }

    with patch("scripts.gates.final_qc.analyze_video_streams", return_value=(mock_v_stream, None, None)), \
         patch("scripts.gates.final_qc.check_black_frames", return_value={"status": "PASS", "severity": "CRITICAL", "message": "Clean"}):
        ok, report = run_final_qc(project_id, workspace_root=workspace)

        assert ok is True
        assert report["summary"]["reference_fps"] == 24
        assert report["summary"]["actual_fps"] == 24.0
        assert report["summary"]["expected_duration_seconds"] == 5.0
        assert report["checks"]["fps"]["status"] == "PASS"
        assert report["checks"]["duration"]["status"] == "PASS"


def test_proof_led_051_duration_mismatch_fails_closed(test_project):
    """
    LED-051 PROOF:
    Duration difference > 0.5s is a critical FAIL that fails Final QC,
    never converting into a warning or false pass.
    """
    project_id, project_dir, workspace = test_project
    bp = create_canonical_blueprint(project_id, aspect_ratio="16:9", fps=30)
    (project_dir / "05_blueprint.json").write_text(json.dumps(bp), encoding="utf-8")
    (project_dir / "out.mp4").touch()

    # Video duration is 10.0s while expected is 3.0s (diff = 7.0s > 0.5s)
    mock_v_stream = {
        "codec_type": "video",
        "codec_name": "h264",
        "width": 1920,
        "height": 1080,
        "r_frame_rate": "30/1",
        "duration": "10.0"
    }

    with patch("scripts.gates.final_qc.analyze_video_streams", return_value=(mock_v_stream, None, None)), \
         patch("scripts.gates.final_qc.check_black_frames", return_value={"status": "PASS", "severity": "CRITICAL", "message": "Clean"}):
        ok, report = run_final_qc(project_id, workspace_root=workspace)

        assert ok is False
        assert report["status"] == "FAIL"
        dur_check = report["checks"]["duration"]
        assert dur_check["status"] == "FAIL"
        assert dur_check["severity"] == "CRITICAL"


def test_proof_led_051_corrupt_or_empty_blueprint_fails_closed(test_project):
    """
    LED-051 PROOF:
    Empty scenes list, missing blueprint, or invalid schema fails closed without default fallbacks.
    """
    project_id, project_dir, workspace = test_project
    (project_dir / "out.mp4").touch()

    # 1. Missing blueprint
    ok, report = run_final_qc(project_id, workspace_root=workspace)
    assert ok is False
    assert report["checks"]["blueprint_file"]["status"] == "FAIL"

    # 2. Empty scenes list
    bp_empty = {
        "blueprint_version": "2.0.0",
        "project_id": project_id,
        "fps": 30,
        "aspect_ratio": "16:9",
        "scenes": []
    }
    (project_dir / "05_blueprint.json").write_text(json.dumps(bp_empty), encoding="utf-8")
    ok, report = run_final_qc(project_id, workspace_root=workspace)
    assert ok is False
    assert report["checks"]["blueprint_scenes"]["status"] == "FAIL"


# ==============================================================================
# LED-052 Tests: AV-Sync Wired into Real Execution Path & Policy Enforcement
# ==============================================================================

def test_proof_led_052_av_sync_wired_into_real_execution_path(test_project):
    """
    LED-052 PROOF:
    check_av_sync is actively called during run_final_qc execution path,
    and its result is recorded in the structured QC report.
    """
    project_id, project_dir, workspace = test_project
    bp = create_canonical_blueprint(project_id, with_audio=True)
    (project_dir / "05_blueprint.json").write_text(json.dumps(bp), encoding="utf-8")
    (project_dir / "out.mp4").touch()
    (project_dir / "04_timings.json").write_text(json.dumps({
        "words": [{"word": "Hello", "start": 0.5, "end": 1.0}]
    }), encoding="utf-8")

    mock_v_stream = {"codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080, "r_frame_rate": "30/1", "duration": "3.0"}
    mock_a_stream = {"codec_type": "audio", "codec_name": "aac"}

    # Mock librosa inside check_av_sync
    with patch("scripts.gates.final_qc.analyze_video_streams", return_value=(mock_v_stream, mock_a_stream, None)), \
         patch("scripts.gates.final_qc.check_audio_lufs", return_value={"status": "PASS", "severity": "CRITICAL", "message": "Optimal LUFS"}), \
         patch("scripts.gates.final_qc.check_black_frames", return_value={"status": "PASS", "severity": "CRITICAL", "message": "Clean"}), \
         patch("librosa.load", return_value=(MagicMock(), 44100)), \
         patch("librosa.onset.onset_detect", return_value=[10]), \
         patch("librosa.frames_to_time", return_value=[0.52]):  # 0.52 vs expected 0.50 -> 20ms sync error

        ok, report = run_final_qc(project_id, workspace_root=workspace)

        assert "av_sync" in report["checks"], "AV-sync check must be present in report['checks']!"
        av_check = report["checks"]["av_sync"]
        assert av_check["status"] == "PASS"
        assert av_check["severity"] == "CRITICAL"
        assert av_check["avg_sync_error_ms"] == 20.0
        assert av_check["threshold_ms"] == 200.0
        assert ok is True


def test_proof_led_052_av_sync_critical_offset_fails_final_qc(test_project):
    """
    LED-052 PROOF:
    When AV-sync offset exceeds 200ms threshold, check status is FAIL (CRITICAL)
    and overall Final QC fails.
    """
    project_id, project_dir, workspace = test_project
    bp = create_canonical_blueprint(project_id, with_audio=True)
    (project_dir / "05_blueprint.json").write_text(json.dumps(bp), encoding="utf-8")
    (project_dir / "out.mp4").touch()
    (project_dir / "04_timings.json").write_text(json.dumps({
        "words": [{"word": "Hello", "start": 0.5, "end": 1.0}]
    }), encoding="utf-8")

    mock_v_stream = {"codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080, "r_frame_rate": "30/1", "duration": "3.0"}
    mock_a_stream = {"codec_type": "audio", "codec_name": "aac"}

    with patch("scripts.gates.final_qc.analyze_video_streams", return_value=(mock_v_stream, mock_a_stream, None)), \
         patch("scripts.gates.final_qc.check_audio_lufs", return_value={"status": "PASS", "severity": "CRITICAL", "message": "Optimal LUFS"}), \
         patch("scripts.gates.final_qc.check_black_frames", return_value={"status": "PASS", "severity": "CRITICAL", "message": "Clean"}), \
         patch("librosa.load", return_value=(MagicMock(), 44100)), \
         patch("librosa.onset.onset_detect", return_value=[10]), \
         patch("librosa.frames_to_time", return_value=[0.85]):  # 0.85 vs 0.50 -> 350ms sync error (> 200ms)

        ok, report = run_final_qc(project_id, workspace_root=workspace)

        assert ok is False
        assert report["status"] == "FAIL"
        av_check = report["checks"]["av_sync"]
        assert av_check["status"] == "FAIL"
        assert av_check["severity"] == "CRITICAL"
        assert av_check["avg_sync_error_ms"] == 350.0


def test_proof_led_052_av_sync_analyzer_crash_is_check_failed_to_execute(test_project):
    """
    LED-052 PROOF:
    If AV-sync analyzer crashes (e.g. librosa throws exception), status is
    CHECK_FAILED_TO_EXECUTE (CRITICAL) and overall Final QC fails. It is never treated as passed.
    """
    project_id, project_dir, workspace = test_project
    bp = create_canonical_blueprint(project_id, with_audio=True)
    (project_dir / "05_blueprint.json").write_text(json.dumps(bp), encoding="utf-8")
    (project_dir / "out.mp4").touch()
    (project_dir / "04_timings.json").write_text(json.dumps({
        "words": [{"word": "Hello", "start": 0.5, "end": 1.0}]
    }), encoding="utf-8")

    mock_v_stream = {"codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080, "r_frame_rate": "30/1", "duration": "3.0"}
    mock_a_stream = {"codec_type": "audio", "codec_name": "aac"}

    with patch("scripts.gates.final_qc.analyze_video_streams", return_value=(mock_v_stream, mock_a_stream, None)), \
         patch("scripts.gates.final_qc.check_audio_lufs", return_value={"status": "PASS", "severity": "CRITICAL", "message": "Optimal LUFS"}), \
         patch("scripts.gates.final_qc.check_black_frames", return_value={"status": "PASS", "severity": "CRITICAL", "message": "Clean"}), \
         patch("librosa.load", side_effect=RuntimeError("librosa soundfile decoder crash")):

        ok, report = run_final_qc(project_id, workspace_root=workspace)

        assert ok is False
        assert report["status"] == "FAIL"
        av_check = report["checks"]["av_sync"]
        assert av_check["status"] == "CHECK_FAILED_TO_EXECUTE"
        assert av_check["severity"] == "CRITICAL"
        assert "librosa soundfile decoder crash" in av_check["error"]


# ==============================================================================
# LED-053 Tests: CHECK_FAILED_TO_EXECUTE Semantics & Analyzer Crash Fail-Closed
# ==============================================================================

def test_proof_led_053_black_frame_analyzer_crash_is_check_failed_to_execute(test_project):
    """
    LED-053 PROOF:
    When black-frame analyzer throws an exception (e.g. ffmpeg pipe broken),
    status is CHECK_FAILED_TO_EXECUTE (CRITICAL), report overall status is FAIL,
    and the video is NOT declared passed.
    """
    project_id, project_dir, workspace = test_project
    bp = create_canonical_blueprint(project_id, with_audio=False)
    (project_dir / "05_blueprint.json").write_text(json.dumps(bp), encoding="utf-8")
    (project_dir / "out.mp4").touch()

    mock_v_stream = {"codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080, "r_frame_rate": "30/1", "duration": "3.0"}

    # Mock ffmpeg in check_black_frames to raise Exception
    with patch("scripts.gates.final_qc.analyze_video_streams", return_value=(mock_v_stream, None, None)), \
         patch("ffmpeg.input", side_effect=Exception("SIGPIPE: broken ffmpeg filtergraph")):

        ok, report = run_final_qc(project_id, workspace_root=workspace)

        assert ok is False
        assert report["status"] == "FAIL"
        bf_check = report["checks"]["black_frames"]
        assert bf_check["status"] == "CHECK_FAILED_TO_EXECUTE"
        assert bf_check["severity"] == "CRITICAL"
        assert "SIGPIPE: broken ffmpeg filtergraph" in bf_check["error"]


def test_proof_led_053_audio_lufs_analyzer_crash_is_check_failed_to_execute(test_project):
    """
    LED-053 PROOF:
    When audio LUFS analyzer throws an exception,
    status is CHECK_FAILED_TO_EXECUTE (CRITICAL), not 'warning', and Final QC fails closed.
    """
    project_id, project_dir, workspace = test_project
    bp = create_canonical_blueprint(project_id, with_audio=True)
    (project_dir / "05_blueprint.json").write_text(json.dumps(bp), encoding="utf-8")
    (project_dir / "out.mp4").touch()
    (project_dir / "04_timings.json").write_text(json.dumps({"words": []}), encoding="utf-8")

    mock_v_stream = {"codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080, "r_frame_rate": "30/1", "duration": "3.0"}
    mock_a_stream = {"codec_type": "audio", "codec_name": "aac"}

    with patch("scripts.gates.final_qc.analyze_video_streams", return_value=(mock_v_stream, mock_a_stream, None)), \
         patch("scripts.gates.final_qc.check_black_frames", return_value={"status": "PASS", "severity": "CRITICAL", "message": "Clean"}), \
         patch("scripts.gates.final_qc.check_av_sync", return_value={"status": "PASS", "severity": "CRITICAL", "message": "In sync"}), \
         patch("ffmpeg.input", side_effect=Exception("ebur128 filter memory fault")):

        ok, report = run_final_qc(project_id, workspace_root=workspace)

        assert ok is False
        assert report["status"] == "FAIL"
        lufs_check = report["checks"]["audio_lufs"]
        assert lufs_check["status"] == "CHECK_FAILED_TO_EXECUTE"
        assert lufs_check["severity"] == "CRITICAL"
        assert "ebur128 filter memory fault" in lufs_check["error"]


def test_proof_led_053_distinction_between_violation_and_execution_failure():
    """
    LED-053 PROOF:
    Clear structural distinction in report between:
    - Video violation (analyzer ran and found fault -> FAIL)
    - Analyzer tool failure (analyzer could not run -> CHECK_FAILED_TO_EXECUTE)
    """
    # 1. Video violation: black frames detected
    mock_fail_check = {
        "black_frames": {
            "name": "Black Frame Detection",
            "status": "FAIL",
            "severity": "CRITICAL",
            "message": "Black frames detected at 00:01.500"
        }
    }
    status, reason, exit_code = compute_qc_decision(mock_fail_check)
    assert status == "FAIL"
    assert exit_code == 1
    assert "Critical violations" in reason
    assert "Execution failures" not in reason

    # 2. Tool failure: analyzer crashed
    mock_exec_error_check = {
        "black_frames": {
            "name": "Black Frame Detection",
            "status": "CHECK_FAILED_TO_EXECUTE",
            "severity": "CRITICAL",
            "error": "Binary missing",
            "message": "ffprobe binary not found"
        }
    }
    status, reason, exit_code = compute_qc_decision(mock_exec_error_check)
    assert status == "FAIL"
    assert exit_code == 1
    assert "Execution failures" in reason
    assert "Critical violations" not in reason


def test_proof_led_053_cli_exit_code_non_zero_on_critical_failure(test_project):
    """
    LED-053 PROOF:
    CLI entrypoint (python scripts/gates/final_qc.py <project_id>) returns non-zero
    exit code when a critical check fails or fails to execute.
    """
    project_id, project_dir, workspace = test_project
    (project_dir / "out.mp4").touch()
    # Corrupt blueprint
    (project_dir / "05_blueprint.json").write_text("INVALID_JSON", encoding="utf-8")

    script_path = Path.cwd() / "scripts" / "gates" / "final_qc.py"
    proc = subprocess.run(
        [sys.executable, str(script_path), project_id],
        cwd=str(workspace),
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(Path.cwd())}
    )

    assert proc.returncode != 0, f"Expected non-zero exit code on failure, got {proc.returncode}"
    assert "Final QC فشل" in proc.stdout or "Final QC فشل" in proc.stderr
