# -*- coding: utf-8 -*-
"""verify_preview.py — أداة المعاينة المتدرجة وفحص الفريمات العابرة للمنصات (المرحلة 7).
Usage:
  python verify_preview.py <project_dir_or_video_file> [options]

Options:
  --num-frames <N>       Number of frames to sample across the duration (default: 4)
  --timestamps <t1,t2>   Explicit comma-separated timestamps in seconds (e.g. 0.5,5.0,15.0,28.0)
  --out-dir <dir>        Explicit output directory (default: <project>/07_verify)
  --assert-res <WxH>     Assert expected resolution (e.g. 1080x1920)
  --assert-fps <FPS>     Assert expected FPS (e.g. 30)

Exit code: 0 = PASS, 1 = FAIL
"""
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def probe_video(video_path: Path) -> dict:
    """Probe video metadata via ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,codec_name,r_frame_rate:format=duration",
        "-of", "json",
        str(video_path)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"ffprobe failed on {video_path}: {res.stderr.strip()}")
    
    data = json.loads(res.stdout)
    stream = data.get("streams", [{}])[0]
    fmt = data.get("format", {})
    
    w = stream.get("width", 0)
    h = stream.get("height", 0)
    codec = stream.get("codec_name", "unknown")
    dur = float(fmt.get("duration", 0.0))
    
    rate_str = stream.get("r_frame_rate", "30/1")
    if "/" in rate_str:
        num, den = rate_str.split("/")
        fps = round(float(num) / float(den), 2) if float(den) != 0 else 30.0
    else:
        fps = float(rate_str)
        
    return {
        "width": w,
        "height": h,
        "resolution": f"{w}x{h}",
        "codec": codec,
        "duration_sec": dur,
        "fps": fps
    }


def extract_frame(video_path: Path, timestamp: float, out_path: Path) -> bool:
    """Extract a single clean frame at timestamp."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(max(0.0, timestamp)),
        "-i", str(video_path),
        "-frames:v", "1",
        "-q:v", "2",
        str(out_path)
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.returncode == 0 and out_path.exists() and out_path.stat().st_size > 0


def build_contact_sheet(frame_paths: list, out_sheet: Path) -> bool:
    """Tile frame images horizontally into one contact sheet image."""
    if not frame_paths:
        return False
    out_sheet.parent.mkdir(parents=True, exist_ok=True)
    
    if len(frame_paths) == 1:
        import shutil
        shutil.copy2(frame_paths[0], out_sheet)
        return True
        
    inputs = []
    for f in frame_paths:
        inputs.extend(["-i", str(f)])
        
    filter_graph = f"hstack=inputs={len(frame_paths)}"
    cmd = ["ffmpeg", "-y"] + inputs + ["-filter_complex", filter_graph, str(out_sheet)]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return res.returncode == 0 and out_sheet.exists() and out_sheet.stat().st_size > 0


def find_preview_video(target_path: Path) -> Path:
    """Find preview video inside project or return target if file."""
    if target_path.is_file():
        return target_path
        
    # Search common preview locations in order
    candidates = [
        target_path / "06_build" / "out" / "preview.mp4",
        target_path / "06_build" / "out" / "short.mp4",
        target_path / "out" / "preview.mp4",
        target_path / "preview.mp4",
    ]
    for c in candidates:
        if c.exists():
            return c
            
    # Search any mp4 in 06_build/out or out
    for search_dir in [target_path / "06_build" / "out", target_path / "out"]:
        if search_dir.exists():
            mp4s = list(search_dir.glob("*.mp4"))
            if mp4s:
                return mp4s[0]
                
    raise FileNotFoundError(f"لم يتم العثور على ملف فيديو preview.mp4 داخل {target_path}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
        
    target_arg = Path(sys.argv[1])
    num_frames = 4
    custom_timestamps = None
    out_dir = None
    assert_res = None
    assert_fps = None
    
    # Parse CLI flags
    args = sys.argv[2:]
    idx = 0
    while idx < len(args):
        flag = args[idx]
        if flag == "--num-frames" and idx + 1 < len(args):
            num_frames = int(args[idx + 1])
            idx += 2
        elif flag == "--timestamps" and idx + 1 < len(args):
            custom_timestamps = [float(x.strip()) for x in args[idx + 1].split(",") if x.strip()]
            idx += 2
        elif flag == "--out-dir" and idx + 1 < len(args):
            out_dir = Path(args[idx + 1])
            idx += 2
        elif flag == "--assert-res" and idx + 1 < len(args):
            assert_res = args[idx + 1].strip()
            idx += 2
        elif flag == "--assert-fps" and idx + 1 < len(args):
            assert_fps = float(args[idx + 1])
            idx += 2
        else:
            idx += 1

    try:
        video_path = find_preview_video(target_arg)
    except Exception as e:
        print(f"❌ خطأ: {e}")
        sys.exit(1)
        
    if out_dir is None:
        if target_arg.is_dir():
            out_dir = target_arg / "07_verify"
        else:
            out_dir = target_arg.parent / "07_verify"
            
    out_dir.mkdir(parents=True, exist_ok=True)
    frames_dir = out_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"🎬 فحص الفيديو للمعاينة المتدرجة: {video_path.name}")
    meta = probe_video(video_path)
    dur = meta["duration_sec"]
    print(f"  • المواصفات: {meta['resolution']} | {meta['codec']} | {meta['fps']} FPS | المدة: {dur:.2f}s")
    
    # Assertions
    errors = []
    if assert_res and meta["resolution"] != assert_res:
        errors.append(f"دقة الفيديو {meta['resolution']} لا تطابق المطلوب {assert_res}")
    if assert_fps and abs(meta["fps"] - assert_fps) > 0.5:
        errors.append(f"معدل الإطارات {meta['fps']} لا يطابق المطلوب {assert_fps}")
        
    # Calculate sample timestamps
    if custom_timestamps:
        timestamps = custom_timestamps
    else:
        if dur <= 1.0:
            timestamps = [0.1]
        elif dur <= 5.0:
            timestamps = [0.5, dur * 0.5, max(0.6, dur - 0.5)]
        else:
            # e.g. Hook (0.5s), 33%, 66%, End (dur - 0.5s)
            timestamps = [
                0.5,
                round(dur * 0.33, 2),
                round(dur * 0.66, 2),
                round(max(0.5, dur - 0.5), 2)
            ]
            
    # Extract frames
    extracted = []
    for i, t in enumerate(timestamps, 1):
        frame_name = f"frame_{i:02d}_{t}s.png"
        frame_file = frames_dir / frame_name
        ok = extract_frame(video_path, t, frame_file)
        if ok:
            extracted.append({"index": i, "timestamp_sec": t, "path": str(frame_file.relative_to(out_dir.parent))})
            print(f"  ✓ استخراج الفريم {i}: t={t}s -> {frame_file.name}")
        else:
            errors.append(f"فشل استخراج الفريم عند t={t}s")
            
    # Tile into contact sheet
    sheet_file = out_dir / "contact_sheet.png"
    frame_paths = [frames_dir / f"frame_{x['index']:02d}_{x['timestamp_sec']}s.png" for x in extracted]
    sheet_ok = build_contact_sheet(frame_paths, sheet_file)
    
    if sheet_ok:
        print(f"  ✓ تم توليد شبكة المعاينة: {sheet_file}")
    else:
        errors.append("فشل دمج شبكة المعاينة contact_sheet.png")
        
    # Write report
    status = "passed" if not errors and sheet_ok else "failed"
    report = {
        "project": target_arg.name if target_arg.is_dir() else target_arg.parent.name,
        "stage": "07_verify",
        "status": status,
        "generated_at": datetime.now().isoformat(),
        "video_path": str(video_path),
        "meta": meta,
        "extracted_frames": extracted,
        "contact_sheet": str(sheet_file.relative_to(out_dir.parent)) if sheet_ok else None,
        "errors": errors
    }
    
    report_file = out_dir / "verify_report.json"
    report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  ✓ تقرير المعاينة: {report_file}")
    
    if errors:
        print("❌ VERIFY FAIL:")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
        
    print(f"✅ STAGE 7 VERIFY PASSED: تم التحقق البصري والميكانيكي بنجاح")
    sys.exit(0)


if __name__ == "__main__":
    main()
