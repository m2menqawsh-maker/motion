# -*- coding: utf-8 -*-
"""probe_qc.py — يولد تقرير فحص المشاهد
Usage: python probe_qc.py <project_dir> <comp_id>"""
from utils.logger import UnifiedLogger
log = UnifiedLogger("probe_qc")

import json, sys, os, subprocess, hashlib, argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from pipeline_guard import PipelineGuard, GuardViolation

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

def verify_seal(report_path: Path) -> bool:
    """تحقق من مطابقة البصمة الرقمية للتقرير لمنع التعديل اليدوي والتزوير"""
    if isinstance(report_path, str):
        report_path = Path(report_path)
    seal_file = report_path.with_suffix(report_path.suffix + ".seal")
    if not seal_file.exists():
        log.error("[SECURITY] ملف الختم الرقمي (.seal) لتقرير Probe-QC مفقود!")
        return False
    if not report_path.exists():
        log.error("[SECURITY] ملف تقرير Probe-QC غير موجود!")
        return False
    expected = seal_file.read_text(encoding="utf-8").strip()
    actual = hashlib.sha256(report_path.read_bytes()).hexdigest()
    if expected != actual:
        log.error("[SECURITY] تقرير Probe-QC تم تعديله يدوياً (البصمة الرقمية غير متطابقة - تقرير مزوّر)")
        return False
    return True

def main():
    parser = argparse.ArgumentParser(description="يولد تقرير فحص المشاهد")
    parser.add_argument("--verify", action="store_true", help="التحقق من التقرير")
    parser.add_argument("--pass", dest="set_pass", action="store_true", help="اعتماد التقرير")
    parser.add_argument("--fail", dest="set_fail", action="store_true", help="رفض التقرير")
    parser.add_argument("project_id", nargs="?", help="معرف المشروع (أو المسار)")
    parser.add_argument("comp_id", nargs="?", help="اسم الكومبوزيشن")
    args = parser.parse_args()

    if args.verify or args.set_pass or args.set_fail:
        arg2 = args.project_id if args.project_id else "."
        target_dir = Path(arg2).resolve()
        if not target_dir.exists() and Path(f"projects/{arg2}").exists():
            target_dir = Path(f"projects/{arg2}").resolve()
            
        report_file = target_dir / "probe_qc_report.json" if target_dir.is_dir() else target_dir
        
        if args.verify:
            if verify_seal(report_file):
                log.success("تقرير Probe-QC أصلي وموثق بالختم الرقمي")
                sys.exit(0)
            else:
                log.error("تقرير Probe-QC تم تعديله يدوياً")
                sys.exit(1)
                
        elif args.set_pass or args.set_fail:
            if not report_file.exists():
                log.error(f"تقرير {report_file} غير موجود!")
                sys.exit(1)
                
            if not verify_seal(report_file):
                log.error("لا يمكن تغيير الحالة لتقرير تم العبث به يدوياً.")
                sys.exit(1)
                
            report = json.loads(report_file.read_text(encoding="utf-8"))
            status_to_set = "pass" if args.set_pass else "fail"
            report["status"] = status_to_set
            
            for probe in report.get("probes", []):
                probe["status"] = status_to_set
                
            report_file.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            seal_file = report_file.with_suffix(report_file.suffix + ".seal")
            checksum = hashlib.sha256(report_file.read_bytes()).hexdigest()
            seal_file.write_text(checksum, encoding="utf-8")
            
            log.info(f"🔏 تم تحديث حالة التقرير إلى '{status_to_set}' وختمه ببصمة رقمية جديدة.")
            
            proj_dir = target_dir if target_dir.is_dir() else target_dir.parent
            unlock_file = proj_dir / ".studio_unlocked"
            
            if status_to_set == "pass":
                unlock_file.write_text(f"unlocked_at={datetime.now().isoformat()}", encoding="utf-8")
                log.info(f"🔓 تم فتح الاستوديو (أنشئ {unlock_file.name})")
            else:
                if unlock_file.exists():
                    unlock_file.unlink()
                    log.info(f"🔒 تم إغلاق الاستوديو (حذف {unlock_file.name})")
            sys.exit(0)

    if not args.project_id or not args.comp_id:
        parser.print_help()
        sys.exit(1)

    proj_dir = Path(args.project_id).resolve()
    comp_id = args.comp_id

    bp_path = proj_dir / "05_blueprint.json"
    build_dir = proj_dir / "06_build"
    probe_dir = proj_dir / "03_probe_qc"

    if not bp_path.exists():
        log.error("لم نجد 05_blueprint.json")
        sys.exit(1)

    if not build_dir.exists():
        log.error("لم نجد مجلد 06_build. شغّل materialize_project.py أولاً.")
        sys.exit(1)

    probe_dir.mkdir(parents=True, exist_ok=True)

    bp = json.loads(bp_path.read_text(encoding="utf-8"))
    fps = bp.get("meta", {}).get("fps", 30)

    # Extract critical moments (in seconds)
    critical_secs = {0.0} # Always first frame

    for sec in bp.get("timeline", []):
        s = sec.get("sec", 0)
        critical_secs.add(float(s))
    
        for e in sec.get("elements", []):
            # Captions or text
            if e.get("kind") in ["caption", "text"]:
                critical_secs.add(float(e.get("start_sec", s)) + 0.5) # A bit after it appears
            
            # Peak motion (midpoint of duration)
            if "motion" in e and e.get("motion", {}).get("duration_ms"):
                duration_s = e["motion"]["duration_ms"] / 1000.0
                peak = float(e.get("start_sec", s)) + duration_s
                critical_secs.add(peak)

    # Add last frame
    max_sec = max([e.get("end_sec", 0) for sec in bp.get("timeline", []) for e in sec.get("elements", [])] or [0])
    if max_sec > 0:
        critical_secs.add(float(max_sec) - 0.1)

    # Convert to frames
    critical_frames = sorted(list({int(round(s * fps)) for s in critical_secs}))

    log.info(f"🎬 جاري فحص {len(critical_frames)} لقطات مهمة لفحص الجودة...")

    rendered_files = []
    # Run remotion still for each frame
    for i, f in enumerate(critical_frames):
        out_file = probe_dir / f"probe_{i:02d}_f{f}.png"
        # Execute npx remotion still
        cmd = [
            "npx", "remotion", "still", "src/index.ts", comp_id, 
            str(out_file.absolute()), 
            f"--frame={f}", 
            "--timeout=120000"
        ]
        log.info(f"📸 توليد اللقطة {i:02d} (إطار {f})...")
        res = subprocess.run(cmd, cwd=str(build_dir), shell=True)
        if res.returncode != 0:
            log.error(f"فشل توليد اللقطة {i:02d}")
        else:
            rendered_files.append(str(out_file.absolute()))

    # Create contact sheet
    contact_sheet_sh = Path(__file__).resolve().parent / "verify" / "contact-sheet.sh"
    out_sheet = probe_dir / "contact_sheet.png"

    if rendered_files and contact_sheet_sh.exists():
        log.info("🎞️ إنشاء Contact Sheet...")
        # Bash script might need bash executable on Windows
        sh_cmd = ["bash", str(contact_sheet_sh), str(out_sheet)] + rendered_files
        subprocess.run(sh_cmd, shell=True)

    # Generate pending report template for the agent
    report = {
        "status": "pending",
        "probes": [
            {"frame": f, "file": f"probe_{i:02d}_f{f}.png", "check": "يرجى الفحص", "status": "pending"}
            for i, f in enumerate(critical_frames)
        ],
        "contact_sheet": "contact_sheet.png",
        "errors": [
            "تعليمات: افتح صور contact_sheet.png وافحصها. status يجب pass فقط إذا كان كل شيء سليم: نصوص مقروءة، أبعاد صحيحة، ألوان سليمة."
        ],
        "timestamp": datetime.now().isoformat()
    }

    import inspect

    # فحص: هل تم استدعاء السكريبت من سطر الأوامر أم من كود آخر؟
    try:
        caller = inspect.stack()[1]
        if "pipeline_guard" in caller.filename or "write_to_file" in str(caller):
            log.error("[SECURITY] محاولة كتابة تقرير QC من مصدر غير مصرح به")
            sys.exit(1)
    except IndexError:
        pass # السكريبت شُغل مباشرة

    report_path = proj_dir / "probe_qc_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    # الختم الرقمي — يمنع أي تعديل يدوي لاحق عبر حفظ بصمة SHA-256
    seal_file = report_path.with_suffix(report_path.suffix + ".seal")
    checksum = hashlib.sha256(report_path.read_bytes()).hexdigest()
    seal_file.write_text(checksum, encoding="utf-8")
    log.info(f"🔏 تم ختم التقرير ببصمة رقمية SHA-256 ({checksum[:12]}...) — أي تعديل يدوي سيُكتشف")

    # التحقق من الختم قبل السماح بأي إجراء
    if not verify_seal(report_path):
        log.error("تقرير Probe-QC تم تعديله يدوياً")
        sys.exit(1)

    # إنشاء ملف الفتح فقط إذا نجح الفحص وكان الختم سليماً
    if report.get("status") == "pass":
        unlock_file = proj_dir / ".studio_unlocked"
        unlock_file.write_text(f"unlocked_at={datetime.now().isoformat()}", encoding="utf-8")
        log.info(f"🔓 تم إنشاء {unlock_file}")


if __name__ == '__main__':
    main()
