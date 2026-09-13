#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
open_studio.py — سكريبت وسيط لفتح الاستوديو بأمان وفي المسار الصحيح
"""
import sys, os, subprocess
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

def main():
    if len(sys.argv) < 2:
        print("❌ الاستخدام: python open_studio.py <project_id>")
        sys.exit(1)

    project_id = sys.argv[1]
    
    workspace_root = Path.cwd()
    if (workspace_root / "projects" / project_id).exists():
        proj_dir = workspace_root / "projects" / project_id
    elif (workspace_root.parent / "projects" / project_id).exists():
        proj_dir = workspace_root.parent / "projects" / project_id
    else:
        proj_dir = Path(f"projects/{project_id}").resolve()

    build_dir = proj_dir / "06_build"
    unlock_file_build = build_dir / ".studio_unlocked"
    unlock_file_root = proj_dir / ".studio_unlocked"

    # 1. فحص القفل الميكانيكي
    unlock_file = unlock_file_build if unlock_file_build.exists() else unlock_file_root
    if not unlock_file.exists():
        print("🛑 [GUARDIAN BLOCK] ممنوع فتح الاستوديو!")
        print(f"السبب: ملف .studio_unlocked غير موجود في {proj_dir}.")
        print("الإجراء: يجب تشغيل probe_qc.py ونجاحه أولاً لإنشاء ملف الفتح.")
        sys.exit(1)

    # 1.5. التأكد من عدم تعديل الملفات بعد آخر فحص
    unlock_mtime = unlock_file.stat().st_mtime
    src_dir = build_dir / "src"
    if src_dir.exists():
        for filepath in src_dir.rglob("*.tsx"):
            if filepath.stat().st_mtime > unlock_mtime:
                print(f"🛑 [GUARDIAN BLOCK] ممنوع فتح الاستوديو! تم تعديل الملف {filepath.name} بعد الفحص.")
                print("السبب: أي تعديل يدوي أو برمجي على ملفات tsx يتطلب إعادة تشغيل أداة probe_qc.py.")
                sys.exit(1)

    # 2. التحقق من وجود المجلد
    if not build_dir.exists():
        print(f"❌ مجلد البناء غير موجود: {build_dir}")
        sys.exit(1)

    # 3. تشغيل الاستوديو في المسار الصحيح
    print(f"✅ [GUARDIAN PASS] جاري فتح الاستوديو للمشروع {project_id}...")
    os.chdir(str(build_dir))
    use_shell = os.name == "nt"
    cmd = ["npx", "remotion", "studio"]
    subprocess.run(cmd, shell=use_shell)

if __name__ == "__main__":
    main()
