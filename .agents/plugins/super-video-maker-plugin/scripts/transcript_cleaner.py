import sys
from utils.logger import UnifiedLogger
log = UnifiedLogger("transcript_cleaner")

import os
import json
import argparse
import shutil
from datetime import datetime, timezone, timedelta

sys.stdout.reconfigure(encoding="utf-8")

def get_transcript_path(session_id, custom_path=None):
    if custom_path:
        return custom_path
    base = r"C:\Users\momen\.gemini\antigravity-ide\brain"
    return os.path.join(base, session_id, ".system_generated", "logs", "transcript.jsonl")

def get_stats(transcript_path):
    if not os.path.exists(transcript_path):
        return None
    lines = []
    with open(transcript_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    size_mb = os.path.getsize(transcript_path) / (1024 * 1024)
    mtime = datetime.fromtimestamp(os.path.getmtime(transcript_path)).strftime('%Y-%m-%d %H:%M:%S')
    
    return {
        "turns": len(lines),
        "size_mb": round(size_mb, 2),
        "last_modified": mtime,
        "lines": lines
    }

def print_stats(session_id, transcript_path):
    stats = get_stats(transcript_path)
    if not stats:
        log.info(f"السجل غير موجود: {transcript_path}")
        return
    log.info(f"إحصائيات السجل ({session_id}):")
    log.info(f"- عدد الجولات: {stats['turns']}")
    log.info(f"- الحجم: {stats['size_mb']} MB")
    log.info(f"- آخر تعديل: {stats['last_modified']}")

def show_last(session_id, transcript_path, n):
    stats = get_stats(transcript_path)
    if not stats:
        log.info(f"السجل غير موجود: {transcript_path}")
        return
    lines = stats['lines']
    last_n = lines[-n:] if n <= len(lines) else lines
    log.info(f"عرض آخر {len(last_n)} جولات:")
    for idx, line in enumerate(last_n):
        try:
            data = json.loads(line)
            step_type = data.get("type", "UNKNOWN")
            source = data.get("source", "UNKNOWN")
            log.info(f"[{idx+1}] {source} -> {step_type}")
        except:
            log.info(f"[{idx+1}] سطور غير صالحة للتحليل")

def archive_transcript(session_id, transcript_path):
    if not os.path.exists(transcript_path):
        log.info(f"السجل غير موجود: {transcript_path}")
        return None
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    dir_name = os.path.dirname(transcript_path)
    archive_path = os.path.join(dir_name, f"transcript_archive_{timestamp}.jsonl")
    
    shutil.copy2(transcript_path, archive_path)
    log.info(f"تم أرشفة السجل إلى: {archive_path}")
    return archive_path

def check_recent_clean(transcript_path):
    dir_name = os.path.dirname(transcript_path)
    stats_file = os.path.join(dir_name, ".transcript_stats.json")
    if os.path.exists(stats_file):
        with open(stats_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            last_cleaned = data.get("last_cleaned")
            if last_cleaned:
                cleaned_time = datetime.fromisoformat(last_cleaned)
                if datetime.now(timezone.utc) - cleaned_time < timedelta(minutes=30):
                    return True
    return False

def record_clean_time(transcript_path):
    dir_name = os.path.dirname(transcript_path)
    stats_file = os.path.join(dir_name, ".transcript_stats.json")
    data = {}
    if os.path.exists(stats_file):
        with open(stats_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    data["last_cleaned"] = datetime.now(timezone.utc).isoformat()
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def clean_transcript(session_id, transcript_path, force=False):
    stats = get_stats(transcript_path)
    if not stats:
        log.info(f"السجل غير موجود: {transcript_path}")
        return
    
    if not force and check_recent_clean(transcript_path):
        log.info("️ تم التنظيف مؤخراً (أقل من 30 دقيقة). تم تخطي التنظيف.")
        return

    turns = stats['turns']
    if turns < 30:
        log.info(f"️ السجل يحتوي على {turns} جولة فقط (أقل من 30). تم حظر التنظيف لحماية البيانات.")
        return
    
    # 1. النسخ الاحتياطي والأرشفة
    log.info("جاري إنشاء نسخة احتياطية...")
    archive_path = archive_transcript(session_id, transcript_path)
    
    # 2. الاحتفاظ بآخر 20 جولة
    lines = stats['lines']
    keep_lines = lines[-20:]
    
    with open(transcript_path, 'w', encoding='utf-8') as f:
        f.writelines(keep_lines)
    
    record_clean_time(transcript_path)
    log.info(f"تم تنظيف السجل. تم الاحتفاظ بـ 20 جولة وأرشفة الباقي.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Transcript Cleaner")
    parser.add_argument("command", choices=["clean", "archive", "stats", "show"])
    parser.add_argument("session_id", help="معرف الجلسة (أو اسم المشروع للاختبار)")
    parser.add_argument("--path", help="مسار مخصص لملف transcript.jsonl")
    parser.add_argument("--last", type=int, default=5, help="عدد الجولات لعرضها في أمر show")
    parser.add_argument("--force", action="store_true", help="تخطي فحص الوقت")
    
    args = parser.parse_args()
    t_path = get_transcript_path(args.session_id, args.path)
    
    if args.command == "clean":
        clean_transcript(args.session_id, t_path, args.force)
    elif args.command == "archive":
        archive_transcript(args.session_id, t_path)
    elif args.command == "stats":
        print_stats(args.session_id, t_path)
    elif args.command == "show":
        show_last(args.session_id, t_path, args.last)
