#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from utils.logger import UnifiedLogger
log = UnifiedLogger("final_qc")
from utils.config import Config
config = Config()

import json
import subprocess
import argparse
from pathlib import Path

def ensure_dependencies():
    """تثبيت المكتبات المطلوبة تلقائياً"""
    required = ['librosa', 'soundfile', 'ffmpeg-python']
    for pkg in required:
        try:
            import_name = pkg.replace('-', '_')
            __import__(import_name)
        except ImportError:
            log.info(f"📦 تثبيت {pkg}...")
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
            result = subprocess.run([str(p), "-version"], capture_output=True, text=True, check=False)
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
        log.info(f"️ فشل تحليل الفيديو باستخدام ffmpeg-python: {e}")
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
        import tempfile
        
        # استخراج الصوت إلى ملف مؤقت
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            temp_audio_path = tmp.name
            
        subprocess.run([
            'ffmpeg', '-y', '-i', str(video_path), 
            '-vn', '-acodec', 'pcm_s16le', '-ar', '44100', '-ac', '2', 
            temp_audio_path
        ], capture_output=True, check=True)
        
        # استخراج peaks من الصوت
        y, sr = librosa.load(temp_audio_path, sr=None)
        
        # حذف الملف المؤقت
        Path(temp_audio_path).unlink(missing_ok=True)
        
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

from utils.performance import track_performance

@track_performance("final_qc")
def main():
    parser = argparse.ArgumentParser(description="الفحص النهائي للفيديو (Final QC)")
    parser.add_argument("project_id", help="معرف المشروع")
    args = parser.parse_args()
    
    project_id = args.project_id
    global log
    log = UnifiedLogger("final_qc", project_id)
    
    project_dir = Path(project_id).resolve()
    if not project_dir.exists() and Path(f"projects/{project_id}").exists():
        project_dir = Path(f"projects/{project_id}").resolve()
    elif Path("06_build").exists():
        project_dir = Path(".").resolve()
        
    video_path = project_dir / "06_build" / "out" / f"{project_id}_final.mp4"
    timings_path = project_dir / "04_timings.json"
    
    if not video_path.exists():
        log.error(f"الفيديو النهائي لم يُعثر عليه: {video_path}")
        sys.exit(1)
        
    log.debug(f"بدء الفحص النهائي للفيديو: {video_path.name}")
    
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
        
        fps_str = v_stream.get('r_frame_rate', '0/1')
        
        expected_w = config.get('video.width', 1080)
        expected_h = config.get('video.height', 1920)
        report["checks"]["dimensions"] = {
            "status": "pass" if (width == expected_w and height == expected_h) else "fail",
            "value": f"{width}x{height}",
            "message": f"الأبعاد صحيحة {expected_w}x{expected_h}" if (width == expected_w and height == expected_h) else f"أبعاد غير صحيحة ({width}x{height})"
        }
        
        report["checks"]["codec_video"] = {
            "status": "pass" if codec == "h264" else "warning",
            "value": codec,
            "message": f"فيديو Codec: {codec}"
        }
        
        expected_fps = config.get('video.fps', 30)
        
        # Accept variations like 30, 30.00, or 30000/1001 for 29.97
        is_fps_correct = False
        try:
            # Handle fraction strings like "30/1"
            if '/' in fps_str:
                num, den = map(float, fps_str.split('/'))
                fps_val = num / den
            else:
                fps_val = float(fps_str)
            is_fps_correct = (abs(fps_val - float(expected_fps)) < 0.1)
        except Exception:
            fps_val = fps_str
            pass

        report["checks"]["fps"] = {
            "value": fps_str,
            "status": "pass" if is_fps_correct else "fail",
            "message": f"معدل الإطارات: {fps_val:.2f}fps" if isinstance(fps_val, float) else f"معدل الإطارات: {fps_str}"
        }
    else:
        report["checks"]["video_stream"] = {"status": "fail", "message": "لا يوجد تدفق فيديو"}
        
    if a_stream:
        codec = a_stream.get('codec_name', '')
        report["checks"]["codec_audio"] = {
            "status": "pass" if codec == "aac" else "warning",
            "value": codec,
            "message": f"صوت Codec: {codec}"
        }
    else:
        report["checks"]["audio_stream"] = {"status": "fail", "message": "لا يوجد تدفق صوت"}
        
    # 2. فحص Black frames
    report["checks"]["black_frames"] = check_black_frames(str(video_path))
    
    # 3. فحص التزامن AV
    report["checks"]["av_sync"] = check_av_sync(str(video_path), timings_path)
    
    # التحقق من وجود فشل قاطع
    has_fail = False
    for k, v in report["checks"].items():
        if v.get("status") == "fail":
            has_fail = True
            log.error(f"[{k}]: {v.get('message')}")
        elif v.get("status") == "warning":
            log.info(f"️ [{k}]: {v.get('message')}")
        else:
            log.success(f"[{k}]: {v.get('message')}")
            
    if has_fail:
        report["status"] = "fail"
        
    report_file = project_dir / "final_qc_report.json"
    report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    
    if has_fail:
        log.error("Final QC فشل. يرجى مراجعة التقرير.")
        sys.exit(1)
    else:
        log.success("Final QC نجح. الفيديو جاهز للتسليم.")
        sys.exit(0)

if __name__ == "__main__":
    main()
