#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/gates/final_qc.py — Canonical Strict Final Quality Control Gate (S19).

Enforces:
- LED-051 (P0): Canonical Blueprint parsing, strict aspect ratio (9:16, 16:9, 1:1, etc.),
  reference FPS authority, and scene-derived duration calculation (no legacy metadata drift or silent fallbacks).
- LED-052 (P1): check_av_sync active in real execution path with structured reporting and failure enforcement.
- LED-053 (P1): Explicit PASS / FAIL / CHECK_FAILED_TO_EXECUTE semantics, fail-closed on critical analyzer crash,
  and zero tolerance for exception swallowing into warnings.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Dict, Any, Optional, Tuple, List

from scripts.security.path_security import validate_project_id, safe_resolve
from scripts.security.security import safe_subprocess
from scripts.core.blueprint_loader import load_blueprint
from scripts.core.blueprint_errors import BlueprintError

# Canonical Aspect Ratio Dimensions
CANONICAL_ASPECT_MAP: Dict[str, Tuple[int, int]] = {
    "16:9": (1920, 1080),
    "9:16": (1080, 1920),
    "1:1": (1080, 1080),
    "4:5": (1080, 1350),
    "21:9": (2560, 1080),
}

# Critical AV-sync maximum allowed average error (200ms)
MAX_AV_SYNC_ERROR_MS: float = 200.0


def find_ffprobe() -> Optional[str]:
    """Finds ffprobe binary in environment or system PATH."""
    plugin_root = Path(".agents/plugins/super-video-maker-plugin").resolve()
    workspace = plugin_root.parent.parent.parent
    possible_paths = [
        workspace / ".agents/mcp/audio-tools-mcp/.venv/Scripts/ffprobe.exe",
        workspace / ".agents/mcp/ffmpeg-mcp-server/.venv/Scripts/ffprobe.exe",
        Path("ffprobe")
    ]
    for p in possible_paths:
        try:
            result = safe_subprocess([str(p), "-version"], capture_output=True, text=True, check=False)
            if result.returncode == 0:
                return str(p)
        except (FileNotFoundError, OSError):
            continue
    return None


def analyze_video_streams(video_path: Path | str) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[str]]:
    """
    Probes video container for video and audio streams using ffmpeg.probe.
    Returns (video_stream, audio_stream, analyzer_error).
    If probe tool crashes or raises, analyzer_error contains the exception string.
    """
    try:
        import ffmpeg
        probe = ffmpeg.probe(str(video_path))
        streams = probe.get("streams", [])
        video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
        return video_stream, audio_stream, None
    except Exception as e:
        return None, None, str(e)


def analyze_video_with_ffmpeg(video_path: str):
    """Backward-compatible helper returning (video_stream, audio_stream)."""
    v, a, _ = analyze_video_streams(video_path)
    return v, a


def check_dimensions_and_aspect(v_stream: Dict[str, Any], expected_aspect: str) -> Dict[str, Any]:
    """Validates video stream dimensions and aspect ratio against canonical specification."""
    if expected_aspect not in CANONICAL_ASPECT_MAP:
        return {
            "name": "Video Dimensions & Aspect Ratio",
            "status": "FAIL",
            "severity": "CRITICAL",
            "expected_aspect": expected_aspect,
            "message": f"نسبة العرض للارتفاع غير مدعومة في العقد الكانوني: {expected_aspect}"
        }

    expected_w, expected_h = CANONICAL_ASPECT_MAP[expected_aspect]
    try:
        width = int(v_stream.get("width", 0))
        height = int(v_stream.get("height", 0))
    except (ValueError, TypeError):
        return {
            "name": "Video Dimensions & Aspect Ratio",
            "status": "CHECK_FAILED_TO_EXECUTE",
            "severity": "CRITICAL",
            "error": "INVALID_DIMENSIONS_DATA",
            "message": "تعذر قراءة أبعاد الفيديو من بيانات التدفق"
        }

    actual_aspect = None
    for asp, (w, h) in CANONICAL_ASPECT_MAP.items():
        if width == w and height == h:
            actual_aspect = asp
            break
    if not actual_aspect:
        actual_aspect = f"{width}:{height}"

    matches = (width == expected_w and height == expected_h)

    return {
        "name": "Video Dimensions & Aspect Ratio",
        "status": "PASS" if matches else "FAIL",
        "severity": "CRITICAL",
        "expected_aspect": expected_aspect,
        "actual_aspect": actual_aspect,
        "expected_dimensions": f"{expected_w}x{expected_h}",
        "actual_dimensions": f"{width}x{height}",
        "message": (
            f"الأبعاد صحيحة {width}x{height} ({expected_aspect})"
            if matches else
            f"أبعاد غير صحيحة ({width}x{height} بدلاً من {expected_w}x{expected_h} لـ {expected_aspect})"
        )
    }


def check_fps(v_stream: Dict[str, Any], expected_fps: int) -> Dict[str, Any]:
    """Validates video stream frame rate against canonical blueprint FPS."""
    if expected_fps <= 0:
        return {
            "name": "Video Frame Rate",
            "status": "FAIL",
            "severity": "CRITICAL",
            "expected_fps": expected_fps,
            "message": f"معدل الإطارات الكانوني غير صالح: {expected_fps}"
        }

    r_frame_rate = v_stream.get("r_frame_rate", "")
    avg_frame_rate = v_stream.get("avg_frame_rate", "")

    actual_fps = None
    for rate_str in [r_frame_rate, avg_frame_rate]:
        if rate_str and "/" in rate_str:
            try:
                num, den = map(int, rate_str.split("/"))
                if den > 0:
                    actual_fps = round(num / den, 2)
                    break
            except Exception:
                pass

    if actual_fps is None:
        return {
            "name": "Video Frame Rate",
            "status": "CHECK_FAILED_TO_EXECUTE",
            "severity": "CRITICAL",
            "error": "CANNOT_PARSE_FPS",
            "message": f"تعذر قراءة معدل الإطارات من الفيديو: r_frame_rate={r_frame_rate}"
        }

    fps_diff = abs(actual_fps - expected_fps)
    # Tolerates minor standard jitter (e.g., 29.97 vs 30)
    matches = fps_diff <= 0.2

    return {
        "name": "Video Frame Rate",
        "status": "PASS" if matches else "FAIL",
        "severity": "CRITICAL",
        "expected_fps": expected_fps,
        "actual_fps": actual_fps,
        "message": (
            f"معدل الإطارات مطابق ({actual_fps} fps)"
            if matches else
            f"معدل الإطارات غير مطابق ({actual_fps} fps بدلاً من {expected_fps} fps)"
        )
    }


def check_duration(v_stream: Dict[str, Any], expected_duration_seconds: float) -> Dict[str, Any]:
    """Validates actual duration against canonical derived duration."""
    if expected_duration_seconds <= 0:
        return {
            "name": "Video Duration",
            "status": "FAIL",
            "severity": "CRITICAL",
            "expected_duration": expected_duration_seconds,
            "message": f"المدة المتوقعة المستمدة غير صالحة: {expected_duration_seconds}s"
        }

    try:
        actual_duration = float(v_stream.get("duration", 0.0))
    except (ValueError, TypeError):
        actual_duration = 0.0

    duration_diff = abs(actual_duration - expected_duration_seconds)
    threshold_seconds = 0.5
    matches = duration_diff <= threshold_seconds

    return {
        "name": "Video Duration",
        "status": "PASS" if matches else "FAIL",
        "severity": "CRITICAL",
        "expected_duration_seconds": round(expected_duration_seconds, 2),
        "actual_duration_seconds": round(actual_duration, 2),
        "duration_difference_seconds": round(duration_diff, 2),
        "threshold_seconds": threshold_seconds,
        "message": (
            f"المدة الفعلية {actual_duration:.2f}s تطابق المتوقعة {expected_duration_seconds:.2f}s"
            if matches else
            f"فارق كبير في المدة: الفعلية {actual_duration:.2f}s بدلاً من {expected_duration_seconds:.2f}s (الفارق: {duration_diff:.2f}s > {threshold_seconds}s)"
        )
    }


def check_codec(v_stream: Dict[str, Any]) -> Dict[str, Any]:
    """Validates video codec."""
    codec = v_stream.get("codec_name", "")
    matches = codec in ("h264", "hevc", "av1")
    return {
        "name": "Video Codec",
        "status": "PASS" if matches else "WARNING",
        "severity": "WARNING",
        "measured": codec,
        "expected": "h264",
        "message": f"ترميز الفيديو: {codec}" if matches else f"ترميز غير معتاد: {codec} (المفضل h264)"
    }


def check_black_frames(video_path: Path | str) -> Dict[str, Any]:
    """Detects continuous black frames using ffmpeg blackdetect filter."""
    try:
        import ffmpeg
        out, err = (
            ffmpeg
            .input(str(video_path))
            .filter("blackdetect", d=0.5, pix_th=0.10)
            .output("pipe:", format="null")
            .run(capture_stdout=True, capture_stderr=True)
        )
        if b"blackdetect" in err and b"black_start" in err:
            return {
                "name": "Black Frame Detection",
                "status": "FAIL",
                "severity": "CRITICAL",
                "message": "تم اكتشاف إطارات سوداء مستمرة في الفيديو"
            }
        return {
            "name": "Black Frame Detection",
            "status": "PASS",
            "severity": "CRITICAL",
            "message": "لا توجد إطارات سوداء مستمرة"
        }
    except Exception as e:
        return {
            "name": "Black Frame Detection",
            "status": "CHECK_FAILED_TO_EXECUTE",
            "severity": "CRITICAL",
            "error": str(e),
            "message": f"تعذر فحص الإطارات السوداء (تعطل أداة التحليل): {e}"
        }


def check_audio_lufs(video_path: Path | str) -> Dict[str, Any]:
    """Analyzes audio integrated LUFS loudness against -16 LUFS canonical target."""
    try:
        import ffmpeg
        out, err = (
            ffmpeg
            .input(str(video_path))
            .filter("ebur128")
            .output("pipe:", format="null")
            .run(capture_stdout=True, capture_stderr=True)
        )
        lines = err.decode("utf-8", errors="replace").splitlines()
        integrated_lufs = None
        for line in reversed(lines):
            if "I:" in line and "LUFS" in line:
                try:
                    integrated_lufs = float(line.split("I:")[1].split("LUFS")[0].strip())
                    break
                except Exception:
                    pass

        if integrated_lufs is not None:
            # -16 LUFS target: optimal [-18.0, -14.0]
            if -18.0 <= integrated_lufs <= -14.0:
                return {
                    "name": "Audio Loudness (LUFS)",
                    "status": "PASS",
                    "severity": "CRITICAL",
                    "target_lufs": -16.0,
                    "measured": integrated_lufs,
                    "allowed_range": [-18.0, -14.0],
                    "message": f"مستوى الصوت ممتاز ({integrated_lufs} LUFS)"
                }
            elif -20.0 <= integrated_lufs < -18.0 or -14.0 < integrated_lufs <= -12.0:
                return {
                    "name": "Audio Loudness (LUFS)",
                    "status": "WARNING",
                    "severity": "WARNING",
                    "target_lufs": -16.0,
                    "measured": integrated_lufs,
                    "allowed_range": [-18.0, -14.0],
                    "message": f"مستوى الصوت بعيد قليلاً عن الهدف -16 LUFS ({integrated_lufs} LUFS)"
                }
            else:
                return {
                    "name": "Audio Loudness (LUFS)",
                    "status": "FAIL",
                    "severity": "CRITICAL",
                    "target_lufs": -16.0,
                    "measured": integrated_lufs,
                    "allowed_range": [-18.0, -14.0],
                    "message": f"مستوى الصوت غير مقبول ({integrated_lufs} LUFS) - انحراف كبير عن -16 LUFS"
                }

        return {
            "name": "Audio Loudness (LUFS)",
            "status": "FAIL",
            "severity": "CRITICAL",
            "message": "لم يتم العثور على قراءات LUFS في تدفق الصوت"
        }
    except Exception as e:
        return {
            "name": "Audio Loudness (LUFS)",
            "status": "CHECK_FAILED_TO_EXECUTE",
            "severity": "CRITICAL",
            "error": str(e),
            "message": f"فشل تحليل LUFS (تعطل أداة التحليل): {e}"
        }


def check_av_sync(video_path: Path | str, timings_path: Path | str) -> Dict[str, Any]:
    """Validates audio-visual synchronization against timings file using librosa onset detection."""
    t_path = Path(timings_path)
    v_path = Path(video_path)

    if not t_path.exists():
        return {
            "name": "Audio-Visual Synchronization",
            "status": "CHECK_FAILED_TO_EXECUTE",
            "severity": "CRITICAL",
            "error": "TIMINGS_FILE_NOT_FOUND",
            "message": f"ملف التوقيت غير موجود: {t_path}"
        }

    try:
        import librosa
        raw_timings = json.loads(t_path.read_text(encoding="utf-8"))
        expected_times: List[float] = []

        # 1. scenes & words within scenes
        for scene in raw_timings.get("scenes", []):
            if isinstance(scene, dict):
                if "start" in scene:
                    try:
                        expected_times.append(float(scene["start"]))
                    except (ValueError, TypeError):
                        pass
                for w in scene.get("words", []):
                    if isinstance(w, dict) and "start" in w:
                        try:
                            expected_times.append(float(w["start"]))
                        except (ValueError, TypeError):
                            pass

        # 2. top-level words (whisper format)
        for w in raw_timings.get("words", []):
            if isinstance(w, dict) and "start" in w:
                try:
                    expected_times.append(float(w["start"]))
                except (ValueError, TypeError):
                    pass

        # 3. top-level sentences
        for s in raw_timings.get("sentences", []):
            if isinstance(s, dict) and "start" in s:
                try:
                    expected_times.append(float(s["start"]))
                except (ValueError, TypeError):
                    pass

        if not expected_times:
            return {
                "name": "Audio-Visual Synchronization",
                "status": "CHECK_FAILED_TO_EXECUTE",
                "severity": "CRITICAL",
                "error": "NO_TIMING_CUES",
                "message": "لا توجد توقيتات صالحة في ملف التوقيت 04_timings.json"
            }

        # Detect audio onset peaks
        audio_target = str(v_path)
        temp_wav_path = None
        if v_path.suffix.lower() in [".mp4", ".mov", ".mkv", ".webm", ".avi"]:
            import tempfile
            wav_f = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            wav_f.close()
            temp_wav_path = wav_f.name
            cmd = ["ffmpeg", "-y", "-i", str(v_path), "-vn", "-acodec", "pcm_s16le", temp_wav_path]
            res = safe_subprocess(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            if res.returncode == 0 and os.path.exists(temp_wav_path) and os.path.getsize(temp_wav_path) > 0:
                audio_target = temp_wav_path

        try:
            y, sr = librosa.load(audio_target, sr=None)
        finally:
            if temp_wav_path and os.path.exists(temp_wav_path):
                try:
                    os.unlink(temp_wav_path)
                except Exception:
                    pass
        onset_frames = librosa.onset.onset_detect(y=y, sr=sr)
        onset_times = librosa.frames_to_time(onset_frames, sr=sr)

        diffs = []
        for expected in expected_times:
            if len(onset_times) > 0:
                closest = min(onset_times, key=lambda x: abs(x - expected))
                diffs.append(abs(closest - expected))

        avg_diff = sum(diffs) / len(diffs) if diffs else 0.0
        avg_diff_ms = round(avg_diff * 1000, 2)
        threshold_ms = MAX_AV_SYNC_ERROR_MS

        if avg_diff <= (threshold_ms / 1000.0):
            return {
                "name": "Audio-Visual Synchronization",
                "status": "PASS",
                "severity": "CRITICAL",
                "avg_sync_error_ms": avg_diff_ms,
                "threshold_ms": threshold_ms,
                "message": f"تزامن صوتي-بصري ممتاز (متوسط الخطأ: {avg_diff_ms}ms)"
            }
        else:
            return {
                "name": "Audio-Visual Synchronization",
                "status": "FAIL",
                "severity": "CRITICAL",
                "avg_sync_error_ms": avg_diff_ms,
                "threshold_ms": threshold_ms,
                "message": f"خطأ في التزامن الصوتي-البصري تجاوز الحد المسموح: {avg_diff_ms}ms > {threshold_ms}ms"
            }
    except Exception as e:
        return {
            "name": "Audio-Visual Synchronization",
            "status": "CHECK_FAILED_TO_EXECUTE",
            "severity": "CRITICAL",
            "error": str(e),
            "message": f"فشل فحص التزامن الصوتي-البصري (تعطل أداة التحليل): {e}"
        }


def compute_qc_decision(checks: Dict[str, Dict[str, Any]]) -> Tuple[str, str, int]:
    """
    Centralized, fail-closed QC aggregate decision.
    Rules:
    - Any CRITICAL check with status == 'FAIL' -> overall 'FAIL', exit 1
    - Any CRITICAL check with status == 'CHECK_FAILED_TO_EXECUTE' -> overall 'FAIL', exit 1
    - Any check with an unknown status -> overall 'FAIL', exit 1 (fail-closed)
    - All CRITICAL checks == 'PASS' (with optional non-critical WARNINGs) -> overall 'PASS', exit 0
    """
    critical_fails: List[str] = []
    exec_failures: List[str] = []
    warnings: List[str] = []
    passes: List[str] = []

    for check_id, check_data in checks.items():
        if not isinstance(check_data, dict):
            exec_failures.append(f"{check_id}: malformed check output")
            continue

        status = str(check_data.get("status", "")).upper()
        severity = str(check_data.get("severity", "CRITICAL")).upper()
        msg = check_data.get("message") or check_data.get("error") or "Unknown"

        if status == "FAIL":
            if severity == "CRITICAL":
                critical_fails.append(f"[{check_id}] {msg}")
            else:
                warnings.append(f"[{check_id}] {msg}")
        elif status == "CHECK_FAILED_TO_EXECUTE":
            if severity == "CRITICAL":
                exec_failures.append(f"[{check_id}] {msg}")
            else:
                warnings.append(f"[{check_id}] Tool execution error: {msg}")
        elif status == "PASS":
            passes.append(check_id)
        elif status == "WARNING":
            warnings.append(f"[{check_id}] {msg}")
        else:
            # Unknown status -> Fail closed immediately!
            exec_failures.append(f"[{check_id}] Unknown status '{status}' (Fail-closed)")

    if critical_fails or exec_failures:
        reasons: List[str] = []
        if critical_fails:
            reasons.append("Critical violations: " + " | ".join(critical_fails))
        if exec_failures:
            reasons.append("Execution failures: " + " | ".join(exec_failures))
        return "FAIL", " --- ".join(reasons), 1

    if warnings:
        return "PASS", f"Passed with warnings: {' | '.join(warnings)}", 0

    return "PASS", "All critical checks passed successfully.", 0


def run_final_qc(project_id: str, workspace_root: Optional[Path] = None) -> Tuple[bool, Dict[str, Any]]:
    """
    Authoritative Final QC Engine.
    Loads canonical blueprint, inspects out.mp4 and 04_timings.json, executes all checks,
    and writes final_qc_report.json.
    """
    root = workspace_root or Path.cwd()
    clean_id = validate_project_id(project_id)
    project_dir = root / "projects" / clean_id

    report: Dict[str, Any] = {
        "project_id": clean_id,
        "status": "FAIL",
        "target_video": str(project_dir / "out.mp4"),
        "blueprint_path": str(project_dir / "05_blueprint.json"),
        "timings_path": str(project_dir / "04_timings.json"),
        "summary": {},
        "checks": {}
    }

    video_path = project_dir / "out.mp4"
    bp_path = project_dir / "05_blueprint.json"
    timings_path = project_dir / "04_timings.json"

    # 0. Project directory check
    if not project_dir.exists():
        report["checks"]["project_dir"] = {
            "name": "Project Directory Presence",
            "status": "FAIL",
            "severity": "CRITICAL",
            "message": f"مجلد المشروع غير موجود: {project_dir}"
        }
        status, reason, _ = compute_qc_decision(report["checks"])
        report["status"] = status
        report["summary"]["decision_reason"] = reason
        return False, report

    # 1. Video presence check
    if not video_path.exists():
        report["checks"]["video_file"] = {
            "name": "Rendered Video Presence",
            "status": "FAIL",
            "severity": "CRITICAL",
            "message": f"الفيديو النهائي لم يُعثر عليه: {video_path}"
        }
        status, reason, _ = compute_qc_decision(report["checks"])
        report["status"] = status
        report["summary"]["decision_reason"] = reason
        if project_dir.exists():
            (project_dir / "final_qc_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        return False, report

    # 2. Canonical Blueprint loading & validation (LED-051)
    if not bp_path.exists():
        report["checks"]["blueprint_file"] = {
            "name": "Canonical Blueprint Presence",
            "status": "FAIL",
            "severity": "CRITICAL",
            "message": f"ملف المخطط 05_blueprint.json مفقود في {project_dir}"
        }
        status, reason, _ = compute_qc_decision(report["checks"])
        report["status"] = status
        report["summary"]["decision_reason"] = reason
        if project_dir.exists():
            (project_dir / "final_qc_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        return False, report

    try:
        bp_v2 = load_blueprint(bp_path, expected_project_id=clean_id, allow_migrate=True)
    except Exception as e:
        report["checks"]["blueprint_validation"] = {
            "name": "Canonical Blueprint Contract",
            "status": "FAIL",
            "severity": "CRITICAL",
            "error": str(e),
            "message": f"ملف المخطط غير صالح أو خالف العقد الكانوني: {e}"
        }
        status, reason, _ = compute_qc_decision(report["checks"])
        report["status"] = status
        report["summary"]["decision_reason"] = reason
        if project_dir.exists():
            (project_dir / "final_qc_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        return False, report

    # Validate Blueprint internal integrity
    if not bp_v2.scenes:
        report["checks"]["blueprint_scenes"] = {
            "name": "Blueprint Scenes Contract",
            "status": "FAIL",
            "severity": "CRITICAL",
            "message": "المخطط لا يحتوي على أي مشاهد صالحة (scenes فارغة)"
        }
        status, reason, _ = compute_qc_decision(report["checks"])
        report["status"] = status
        report["summary"]["decision_reason"] = reason
        if project_dir.exists():
            (project_dir / "final_qc_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        return False, report

    if bp_v2.fps <= 0:
        report["checks"]["blueprint_fps"] = {
            "name": "Blueprint FPS Contract",
            "status": "FAIL",
            "severity": "CRITICAL",
            "message": f"معدل إطارات المخطط غير صالح: {bp_v2.fps}"
        }
        status, reason, _ = compute_qc_decision(report["checks"])
        report["status"] = status
        report["summary"]["decision_reason"] = reason
        if project_dir.exists():
            (project_dir / "final_qc_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        return False, report

    for sc in bp_v2.scenes:
        if sc.durationFrames <= 0 or sc.startFrame < 0:
            report["checks"]["blueprint_scene_timing"] = {
                "name": "Blueprint Scene Timing",
                "status": "FAIL",
                "severity": "CRITICAL",
                "message": f"المشهد {sc.scene_id} يحتوي على إطارات غير صالحة: start={sc.startFrame}, dur={sc.durationFrames}"
            }
            status, reason, _ = compute_qc_decision(report["checks"])
            report["status"] = status
            report["summary"]["decision_reason"] = reason
            if project_dir.exists():
                (project_dir / "final_qc_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
            return False, report

    # Canonical derivations
    expected_aspect = bp_v2.aspect_ratio
    expected_fps = bp_v2.fps
    expected_duration_frames = max(s.startFrame + s.durationFrames for s in bp_v2.scenes)
    expected_duration_seconds = round(expected_duration_frames / expected_fps, 3)

    # 3. Stream analysis
    v_stream, a_stream, probe_err = analyze_video_streams(video_path)

    if probe_err:
        report["checks"]["video_stream"] = {
            "name": "Video Stream Presence",
            "status": "CHECK_FAILED_TO_EXECUTE",
            "severity": "CRITICAL",
            "error": probe_err,
            "message": f"تعذر تشغيل أداة فحص الفيديو (ffprobe): {probe_err}"
        }
    elif not v_stream:
        report["checks"]["video_stream"] = {
            "name": "Video Stream Presence",
            "status": "FAIL",
            "severity": "CRITICAL",
            "message": "لا يوجد تدفق فيديو في الحاوية"
        }
    else:
        report["checks"]["video_stream"] = {
            "name": "Video Stream Presence",
            "status": "PASS",
            "severity": "CRITICAL",
            "codec": v_stream.get("codec_name", ""),
            "message": "تدفق الفيديو موجود"
        }
        report["checks"]["dimensions"] = check_dimensions_and_aspect(v_stream, expected_aspect)
        report["checks"]["fps"] = check_fps(v_stream, expected_fps)
        report["checks"]["duration"] = check_duration(v_stream, expected_duration_seconds)
        report["checks"]["codec_video"] = check_codec(v_stream)

    # 4. Audio stream analysis & AV sync (LED-052)
    has_audio_plan = (
        bp_v2.audio is not None and (
            bp_v2.audio.voiceover is not None or
            bp_v2.audio.music is not None or
            len(bp_v2.audio.global_sfx) > 0
        )
    )

    if a_stream:
        report["checks"]["audio_stream"] = {
            "name": "Audio Stream Presence",
            "status": "PASS",
            "severity": "CRITICAL",
            "codec": a_stream.get("codec_name", ""),
            "message": "تدفق الصوت موجود"
        }
        if has_audio_plan:
            report["checks"]["audio_lufs"] = check_audio_lufs(video_path)
            report["checks"]["av_sync"] = check_av_sync(video_path, timings_path)
        else:
            report["checks"]["audio_lufs"] = {
                "name": "Audio Loudness (LUFS)",
                "status": "PASS",
                "severity": "WARNING",
                "message": "لا يتطلب المخطط مسارات صوتية (تخطي فحص LUFS)"
            }
            report["checks"]["av_sync"] = {
                "name": "Audio-Visual Synchronization",
                "status": "PASS",
                "severity": "WARNING",
                "message": "لا يتطلب المخطط مسارات صوتية (تخطي فحص التزامن)"
            }
    else:
        if has_audio_plan:
            report["checks"]["audio_stream"] = {
                "name": "Audio Stream Presence",
                "status": "FAIL",
                "severity": "CRITICAL",
                "message": "تدفق الصوت مفقود في الفيديو رغم وجود مسارات صوتية في المخطط"
            }
        else:
            report["checks"]["audio_stream"] = {
                "name": "Audio Stream Presence",
                "status": "PASS",
                "severity": "WARNING",
                "message": "لا يوجد تدفق صوت (غير مطلوب في المخطط)"
            }

    # 5. Black frame detection (LED-053)
    report["checks"]["black_frames"] = check_black_frames(video_path)

    # 6. Aggregate Decision
    overall_status, decision_reason, exit_code = compute_qc_decision(report["checks"])
    report["status"] = overall_status

    v_actual_w = int(v_stream.get("width", 0)) if v_stream else 0
    v_actual_h = int(v_stream.get("height", 0)) if v_stream else 0

    report["summary"] = {
        "expected_aspect": expected_aspect,
        "actual_aspect": report["checks"].get("dimensions", {}).get("actual_aspect"),
        "expected_dimensions": report["checks"].get("dimensions", {}).get("expected_dimensions"),
        "actual_dimensions": f"{v_actual_w}x{v_actual_h}" if v_stream else None,
        "expected_duration_seconds": expected_duration_seconds,
        "actual_duration_seconds": float(v_stream.get("duration", 0.0)) if v_stream else None,
        "reference_fps": expected_fps,
        "actual_fps": report["checks"].get("fps", {}).get("actual_fps"),
        "total_checks": len(report["checks"]),
        "passed_checks": sum(1 for c in report["checks"].values() if c.get("status") == "PASS"),
        "failed_checks": sum(1 for c in report["checks"].values() if c.get("status") == "FAIL"),
        "execution_failed_checks": sum(1 for c in report["checks"].values() if c.get("status") == "CHECK_FAILED_TO_EXECUTE"),
        "warnings": sum(1 for c in report["checks"].values() if c.get("status") == "WARNING"),
        "decision_reason": decision_reason,
    }

    # Persist structured report
    report_file = project_dir / "final_qc_report.json"
    report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    return (overall_status == "PASS"), report


def main():
    if len(sys.argv) < 2:
        print("الاستخدام: python final_qc.py <project_id>")
        sys.exit(1)

    project_id = sys.argv[1]
    ok, report = run_final_qc(project_id)

    # Print structured human-readable breakdown
    for k, v in report.get("checks", {}).items():
        st = v.get("status")
        msg = v.get("message") or v.get("error", "")
        if st == "FAIL":
            print(f"❌ [{k}]: {msg}")
        elif st == "CHECK_FAILED_TO_EXECUTE":
            print(f"💥 [{k}]: [CHECK_FAILED_TO_EXECUTE] {msg}")
        elif st == "WARNING":
            print(f"⚠️ [{k}]: {msg}")
        else:
            print(f"✅ [{k}]: {msg}")

    if not ok:
        print(f"❌ Final QC فشل: {report.get('summary', {}).get('decision_reason')}")
        sys.exit(1)
    else:
        print("🎉 Final QC نجح. الفيديو جاهز للتسليم.")
        sys.exit(0)


if __name__ == "__main__":
    main()
