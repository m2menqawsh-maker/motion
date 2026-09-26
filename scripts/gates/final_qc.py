#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from scripts.security.path_security import validate_project_id, safe_resolve
import json
import subprocess
from scripts.security.security import safe_subprocess
from pathlib import Path

def ensure_dependencies():
    """تثبيت المكتبات المطلوبة تلقائياً"""
    required = ['librosa', 'soundfile', 'ffmpeg-python']
    for pkg in required:
        try:
            import_name = pkg.replace('-', '_')
            __import__(import_name)
        except ImportError:
            print(f"📦 تثبيت {pkg}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "--quiet"])

ensure_dependencies()

def find_ffprobe():
    """البحث عن ffprobe في مسارات MCP"""
    plugin_root = Path(".agents/plugins/super-video-maker-plugin").resolve()
    workspace = plugin_root.parent.parent.parent
    possible_paths = [
        workspace / ".agents/mcp/audio-tools-mcp/.venv/Scripts/ffprobe.exe",
        workspace / ".agents/mcp/ffmpeg-mcp-server/.venv/Scripts/ffprobe.exe",
        Path("ffprobe") # System path
    ]
    
    for p in possible_paths:
        try:
            result = safe_subprocess([str(p), "-version"], capture_output=True, text=True, check=False)
            if result.returncode == 0:
                return str(p)
        except (FileNotFoundError, OSError):
            continue
    return None

def analyze_video_with_ffmpeg(video_path: str):
    """تحليل الفيديو باستخدام ffmpeg-python أو ffprobe"""
    try:
        import ffmpeg
        probe = ffmpeg.probe(video_path)
        video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
        audio_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'audio'), None)
        return video_stream, audio_stream
    except Exception as e:
        print(f"⚠️ فشل تحليل الفيديو باستخدام ffmpeg-python: {e}")
        return None, None

def check_black_frames(video_path: str):
    """البحث عن إطارات سوداء باستخدام ffmpeg-python"""
    try:
        import ffmpeg
        out, err = (
            ffmpeg
            .input(video_path)
            .filter('blackdetect', d=0.5, pix_th=0.10)
            .output('pipe:', format='null')
            .run(capture_stdout=True, capture_stderr=True)
        )
        if b"blackdetect" in err and b"black_start" in err:
            return {"status": "fail", "message": "تم اكتشاف إطارات سوداء"}
        return {"status": "pass", "message": "لا يوجد إطارات سوداء مستمرة"}
    except Exception as e:
        return {"status": "warning", "message": f"تعذر فحص الإطارات السوداء: {e}"}

def check_av_sync(video_path: str, timings_path: Path) -> dict:
    """فحص التزامن الصوتي-البصري باستخدام librosa"""
    if not timings_path.exists():
        return {"status": "warning", "message": "ملف التوقيت غير موجود"}
        
    try:
        import librosa
        
        # استخراج peaks من الصوت
        y, sr = librosa.load(video_path, sr=None)
        onset_frames = librosa.onset.onset_detect(y=y, sr=sr)
        onset_times = librosa.frames_to_time(onset_frames, sr=sr)
        
        # مقارنة مع التوقيتات المتوقعة
        timings = json.loads(timings_path.read_text(encoding="utf-8"))
        expected_times = []
        for scene in timings.get('scenes', []):
            expected_times.append(scene.get('start', 0.0))
            for w in scene.get('words', []):
                expected_times.append(w.get('start', 0.0))
                
        if not expected_times:
            return {"status": "warning", "message": "لا توجد توقيتات صالحة في الملف"}
            
        # حساب الفرق
        diffs = []
        for expected in expected_times:
            if len(onset_times) > 0:
                closest = min(onset_times, key=lambda x: abs(x - expected))
                diffs.append(abs(closest - expected))
                
        avg_diff = sum(diffs) / len(diffs) if diffs else 0
        
        return {
            'avg_sync_error_ms': round(avg_diff * 1000, 2),
            'status': 'pass' if avg_diff < 0.2 else 'warning',
            'threshold_ms': 200,
            'message': f"متوسط الخطأ في التزامن: {avg_diff * 1000:.1f}ms"
        }
    except Exception as e:
        return {"status": "warning", "message": f"فشل فحص التزامن الصوتي-البصري: {e}"}

def check_audio_lufs(video_path: str) -> dict:
    """تحليل LUFS للصوت باستخدام ffmpeg"""
    try:
        import ffmpeg
        out, err = (
            ffmpeg
            .input(video_path)
            .filter('ebur128')
            .output('pipe:', format='null')
            .run(capture_stdout=True, capture_stderr=True)
        )
        lines = err.decode('utf-8').splitlines()
        integrated_lufs = None
        for line in reversed(lines):
            if "I:" in line and "LUFS" in line:
                try:
                    integrated_lufs = float(line.split("I:")[1].split("LUFS")[0].strip())
                    break
                except:
                    pass
        if integrated_lufs is not None:
            # We expect roughly -16 LUFS for typical web video (Voiceover driven)
            if -18 <= integrated_lufs <= -14:
                return {"status": "pass", "value": integrated_lufs, "message": f"مستوى الصوت ممتاز ({integrated_lufs} LUFS)"}
            else:
                return {"status": "warning", "value": integrated_lufs, "message": f"مستوى الصوت بعيد عن الهدف -16 LUFS ({integrated_lufs} LUFS)"}
        return {"status": "warning", "message": "لم يتم العثور على قراءات LUFS"}
    except Exception as e:
        return {"status": "warning", "message": f"فشل تحليل LUFS: {e}"}

def main():
    if len(sys.argv) < 2:
        print("الاستخدام: python final_qc.py <project_id>")
        sys.exit(1)
        
    project_id = sys.argv[1]
    project_id = validate_project_id(project_id)
    project_dir = Path(f"projects/{project_id}")
    video_path = project_dir / "out.mp4"
    bp_path = project_dir / "05_blueprint.json"
    
    if not video_path.exists():
        print(f"❌ الفيديو النهائي لم يُعثر عليه: {video_path}")
        sys.exit(1)
        
    if not bp_path.exists():
        print(f"❌ ملف المخطط 05_blueprint.json مفقود!")
        sys.exit(1)
        
    bp = json.loads(bp_path.read_text(encoding="utf-8"))
    meta = bp.get("meta", {})
    expected_aspect = meta.get("aspect_ratio", "16:9")
    expected_duration = meta.get("duration_sec", 0)
        
    print(f"🔍 بدء الفحص النهائي للفيديو: {video_path.name}")
    
    report = {
        "status": "pass",
        "checks": {}
    }
    
    # 1. تحليل Streams
    v_stream, a_stream = analyze_video_with_ffmpeg(str(video_path))
    
    if v_stream:
        width = int(v_stream.get('width', 0))
        height = int(v_stream.get('height', 0))
        codec = v_stream.get('codec_name', '')
        
        # Duration verification
        actual_duration = float(v_stream.get('duration', 0))
        duration_diff = abs(actual_duration - expected_duration)
        report["checks"]["duration"] = {
            "status": "pass" if duration_diff < 0.5 else "warning",
            "value": actual_duration,
            "message": f"المدة الفعلية {actual_duration:.1f}s (المتوقعة {expected_duration}s)"
        }
        
        aspect_map = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080)}
        expected_w, expected_h = aspect_map.get(expected_aspect, (1920, 1080))
        
        report["checks"]["dimensions"] = {
            "status": "pass" if (width == expected_w and height == expected_h) else "fail",
            "value": f"{width}x{height}",
            "message": f"الأبعاد صحيحة {width}x{height}" if (width == expected_w and height == expected_h) else f"أبعاد غير صحيحة ({width}x{height} بدلاً من {expected_w}x{expected_h})"
        }
        
        report["checks"]["codec_video"] = {
            "status": "pass" if codec == "h264" else "warning",
            "value": codec,
            "message": f"فيديو Codec: {codec}"
        }
    else:
        report["checks"]["video_stream"] = {"status": "fail", "message": "لا يوجد تدفق فيديو"}
        
    if a_stream:
        report["checks"]["audio_lufs"] = check_audio_lufs(str(video_path))
    else:
        report["checks"]["audio_stream"] = {"status": "fail", "message": "لا يوجد تدفق صوت"}
        
    # 2. فحص Black frames
    report["checks"]["black_frames"] = check_black_frames(str(video_path))
    
    # التحقق من وجود فشل قاطع
    has_fail = False
    for k, v in report["checks"].items():
        if v.get("status") == "fail":
            has_fail = True
            print(f"❌ [{k}]: {v.get('message')}")
        elif v.get("status") == "warning":
            print(f"⚠️ [{k}]: {v.get('message')}")
        else:
            print(f"✅ [{k}]: {v.get('message')}")
            
    if has_fail:
        report["status"] = "fail"
        
    report_file = project_dir / "final_qc_report.json"
    report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    
    import os
    if has_fail and not os.environ.get("SKIP_STRICT_QC"):
        print("❌ Final QC فشل. يرجى مراجعة التقرير.")
        sys.exit(1)
    elif has_fail:
        print("⚠️ Final QC فشل ولكن تم تخطيه بسبب SKIP_STRICT_QC.")
        sys.exit(0)
    else:
        print("🎉 Final QC نجح. الفيديو جاهز للتسليم.")
        sys.exit(0)

if __name__ == "__main__":
    main()
