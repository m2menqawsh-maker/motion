#!/usr/bin/env python3
"""
process_media.py — أدوات معالجة وفحص الميديا
"""
import sys, subprocess, argparse
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

def validate_media_quality(file_path: Path):
    """يفحص جودة الميديا قبل البناء"""
    
    # فحص الفيديو: هل هو صالح؟
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", 
         "-show_entries", "stream=codec_name,width,height", 
         "-of", "csv=p=0", str(file_path)],
        capture_output=True, text=True
    )
    
    if result.returncode != 0:
        return False, "الفيديو خربان أو غير صالح"
    
    # فحص: هل المدة كافية؟
    duration_result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", str(file_path)],
        capture_output=True, text=True
    )
    
    try:
        duration = float(duration_result.stdout.strip())
        if duration < 1.0:
            return False, "الفيديو قصير جداً (أقل من ثانية)"
    except ValueError:
        pass # Could not parse duration, assume ok or let other tools handle it
    
    return True, "الميديا صالحة"

def main():
    parser = argparse.ArgumentParser(description="أدوات معالجة وفحص الميديا")
    parser.add_argument("file_path", nargs="?", help="مسار الملف لفحصه")
    args = parser.parse_args()
    
    if args.file_path:
        valid, msg = validate_media_quality(Path(args.file_path))
        print(f"{'✅' if valid else '❌'} {msg}")

if __name__ == "__main__":
    main()
