#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
open_studio.py — سكريبت وسيط لفتح الاستوديو بأمان
مع حماية شاملة عبر PipelineGuard
"""
import sys
import os
import subprocess
import argparse
from pathlib import Path

# ترميز UTF-8 للنوافذ
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)

def main():
    parser = argparse.ArgumentParser(description="فتح الاستوديو بأمان")
    parser.add_argument("project_id", help="معرف المشروع")
    
    args = parser.parse_args()
    project_id = args.project_id
    
    # تحديد مسار المشروع
    workspace_root = Path.cwd()
    if (workspace_root / "projects" / project_id).exists():
        proj_dir = workspace_root / "projects" / project_id
    elif (workspace_root.parent / "projects" / project_id).exists():
        proj_dir = workspace_root.parent / "projects" / project_id
    else:
        proj_dir = Path(f"projects/{project_id}").resolve()

    build_dir = proj_dir / "06_build"
    
    print("=" * 60)
    print(f"🔓 فتح الاستوديو للمشروع: {project_id}")
    print("=" * 60)

    if not proj_dir.exists():
        print(f"❌ المشروع غير موجود: {proj_dir}")
        sys.exit(1)
        
    if not build_dir.exists():
        print(f"❌ مجلد البناء غير موجود: {build_dir}")
        print("🔧 شغّل أولاً: python scripts/materialize_project.py", project_id)
        sys.exit(1)

    try:
        scripts_dir = Path(__file__).parent.resolve()
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
            
        from pipeline_guard import PipelineGuard, GuardViolation
        
        guard = PipelineGuard(project_id)
        
        print("🔍 [PipelineGuard] جاري الفحص...")
        guard.require_probe_qc_genuine()
        print("  ✅ تقرير Probe-QC أصلي ومختوم رقمياً")
        guard.require_studio_unlocked()
        print("  ✅ القفل الميكانيكي مفتوح (.studio_unlocked)")
        guard.require_typescript_clean()
        print("  ✅ الكود خالٍ من أخطاء TypeScript")
        
    except ImportError as e:
        print(f"⚠️ خطأ في استيراد PipelineGuard: {e}")
        sys.exit(1)
    except GuardViolation as e:
        print(f"\n🛑 فشل فحص الأمان والجودة [PipelineGuard]: تم رفض فتح الاستوديو!")
        print(f"القاعدة المخالفة: {e.rule}")
        print(f"السبب: {e.reason}")
        print(f"🔧 طريقة الإصلاح: {e.fix}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n🛑 [GUARDIAN BLOCK] حدث خطأ غير متوقع: {e}")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("✅ جميع الفحوصات نجحت — جاري فتح الاستوديو...")
    print("=" * 60)
    
    os.chdir(str(build_dir))
    use_shell = os.name == "nt"
    # Note: Using exit instead of actually blocking the prompt with studio.
    subprocess.run(["npx", "remotion", "studio"], shell=use_shell)

if __name__ == "__main__":
    main()
