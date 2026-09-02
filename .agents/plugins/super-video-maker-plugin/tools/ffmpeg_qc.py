#!/usr/bin/env python3
"""Basic FFmpeg/ffprobe quality checks for rendered videos.

Usage:
    python3 ffmpeg_qc.py output.mp4
"""

import json
import os
import subprocess
import sys
from pathlib import Path


def emit(payload):
    print("RESULT: " + json.dumps(payload), flush=True)


def run_json(cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or f"Command failed: {' '.join(cmd)}")
    return json.loads(proc.stdout)


def probe_video(path):
    return run_json([
        "ffprobe",
        "-v",
        "error",
        "-show_streams",
        "-show_format",
        "-of",
        "json",
        str(path),
    ])


def detect_black_frames(path):
    proc = subprocess.run(
        [
            "ffmpeg",
            "-i",
            str(path),
            "-vf",
            "blackdetect=d=0.5:pix_th=0.10",
            "-an",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
    )
    lines = [
        line.strip()
        for line in (proc.stderr or "").splitlines()
        if "black_start:" in line
    ]
    return lines[:20]


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("video_path")
    parser.add_argument("--job-dir", required=False)
    args = parser.parse_args()

    path = Path(args.video_path).expanduser().resolve()
    if not path.exists():
        emit({"status": "failed", "error": f"File not found: {path}"})
        sys.exit(2)

    job_dir = Path(args.job_dir).resolve() if args.job_dir else None

    try:
        data = probe_video(path)
        streams = data.get("streams", [])
        video_streams = [s for s in streams if s.get("codec_type") == "video"]
        audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
        fmt = data.get("format", {})
        duration = float(fmt.get("duration") or 0)
        size_mb = os.path.getsize(path) / (1024 * 1024)

        warnings = []
        if not video_streams:
            warnings.append("No video stream found.")
        if duration <= 0:
            warnings.append("Duration is zero or missing.")

        v0 = video_streams[0] if video_streams else {}
        pix_fmt = v0.get("pix_fmt")
        codec = v0.get("codec_name")
        width = int(v0.get("width") or 0)
        height = int(v0.get("height") or 0)

        if pix_fmt and pix_fmt != "yuv420p":
            warnings.append(f"Pixel format is {pix_fmt}; yuv420p is safest for social uploads.")
        if codec and codec not in {"h264", "hevc"}:
            warnings.append(f"Video codec is {codec}; h264 is safest.")

        black_frames = detect_black_frames(path)
        if black_frames:
            warnings.append(f"Black-frame detector reported {len(black_frames)} possible segment(s).")

        report = {
            "status": "succeeded" if not warnings else "warning",
            "path": str(path),
            "metrics": {
                "duration_seconds": round(duration, 3),
                "size_mb": round(size_mb, 2),
                "width": width,
                "height": height,
                "video_codec": codec,
                "pix_fmt": pix_fmt,
                "has_audio": bool(audio_streams),
                "audio_codec": audio_streams[0].get("codec_name") if audio_streams else None,
            },
            "warnings": warnings,
            "black_frame_samples": black_frames,
        }
        
        if job_dir:
            job_dir.mkdir(parents=True, exist_ok=True)
            (job_dir / "ffmpeg_qc_report.json").write_text(json.dumps(report, indent=2))
            
        emit(report)
    except Exception as exc:
        emit({"status": "failed", "error": str(exc), "path": str(path)})
        sys.exit(1)


if __name__ == "__main__":
    main()
