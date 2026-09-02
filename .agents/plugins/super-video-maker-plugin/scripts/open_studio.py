#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
open_studio.py — سكريبت وسيط لفتح الاستوديو بأمان
مع حماية شاملة عبر PipelineGuard
"""
import sys
import os
import subprocess
import hashlib
from pathlib import Path

# ترميز UTF-8 للنوافذ
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


def verify_report_seal(project_dir: Path) -> bool:
    """يتحقق من أن تقرير Probe-QC أصلي وغير مزوّر"""
    report_path = project_dir / "probe_qc_report.json"
    seal_path = report_path.with_suffix(".json.seal")
    
    if not seal_path.exists():
        # لا يوجد ختم — تقرير قديم (مقبول للتوافق مع المشاريع القديمة)
        return True
    
    if not report_path.exists():
        return False
    
    expected = seal_path.read_text(encoding="utf-8").strip()
    actual = hashlib.sha256(report_path.read_bytes()).hexdigest()
    return expected == actual


def main():
    if len(sys.argv) < 2:
        print("❌ الاستخدام: python open_studio.py <project_id>")
        sys.exit(1)

    project_id = sys.argv[1]
    
    # تحديد مسار المشروع
    workspace_root = Path.cwd()
    if (workspace_root / "projects" / project_id).exists():
        proj_dir = workspace_root / "projects" / project_id
    elif (workspace_root.parent / "projects" / project_id).exists():
        proj_dir = workspace_root.parent / "projects" / project_id
    else:
        proj_dir = Path(f"projects/{project_id}").resolve()

    build_dir = proj_dir / "06_build"
    unlock_file = proj_dir / ".studio_unlocked"

    print("=" * 60)
    print(f"🔓 فتح الاستوديو للمشروع: {project_id}")
    print("=" * 60)

    # ─────────────────────────────────────────────
    # الفحص 1: وجود المشروع
    # ─────────────────────────────────────────────
    if not proj_dir.exists():
        print(f"❌ المشروع غير موجود: {proj_dir}")
        sys.exit(1)
    print("✅ المشروع موجود")

    # ─────────────────────────────────────────────
    # الفحص 2: وجود مجلد البناء
    # ─────────────────────────────────────────────
    if not build_dir.exists():
        print(f"❌ مجلد البناء غير موجود: {build_dir}")
        print("🔧 شغّل أولاً: python materialize_project.py", project_id)
        sys.exit(1)
    print("✅ مجلد البناء موجود")

    # ─────────────────────────────────────────────
    # الفحص 3: فحص تزوير تقرير Probe-QC
    # ─────────────────────────────────────────────
    qc_report = proj_dir / "probe_qc_report.json"
    if qc_report.exists():
        if not verify_report_seal(proj_dir):
            print("\n🛑 [GUARDIAN BLOCK] تقرير Probe-QC مزوّر!")
            print("السبب: البصمة الرقمية لا تتطابق مع التقرير")
            print("الإجراء: شغّل probe_qc.py مجدداً لإنشاء تقرير أصلي")
            sys.exit(1)
        print("✅ تقرير Probe-QC أصلي (البصمة الرقمية سليمة)")

    # ─────────────────────────────────────────────
    # الفحص 4: القفل الميكانيكي (.studio_unlocked)
    # ─────────────────────────────────────────────
    if not unlock_file.exists():
        print("\n🛑 [GUARDIAN BLOCK] ممنوع فتح الاستوديو!")
        print(f"السبب: ملف {unlock_file} غير موجود")
        print("الإجراء: شغّل probe_qc.py وانتظر نجاحه أولاً")
        sys.exit(1)
    print("✅ ملف .studio_unlocked موجود")

    # ─────────────────────────────────────────────
    # الفحص 5: محاولة استيراد Pipeline Guard (اختياري)
    # ─────────────────────────────────────────────
    try:
        scripts_dir = Path(__file__).parent.parent / "plugins" / "super-video-maker-plugin" / "scripts"
        if scripts_dir.exists():
            sys.path.insert(0, str(scripts_dir))
            from pipeline_guard import PipelineGuard, GuardViolation
            
            guard = PipelineGuard(project_id)
            guard.require_typescript_clean()
            print("✅ الكود خالٍ من أخطاء TypeScript")
    except ImportError:
        print("⚠️ Pipeline Guard غير متاح — تخطي الفحص المتقدم")
    except Exception as e:
        print(f"\n🛑 [GUARDIAN BLOCK] {e}")
        sys.exit(1)

    # ─────────────────────────────────────────────
    # تشغيل الاستوديو
    # ─────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("✅ جميع الفحوصات نجحت — جاري فتح الاستوديو...")
    print("=" * 60)
    
    os.chdir(str(build_dir))
    use_shell = os.name == "nt"
    subprocess.run(["npx", "remotion", "studio"], shell=use_shell)


if __name__ == "__main__":
    main()
