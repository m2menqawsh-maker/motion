#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_project.py — سكريبت وسيط لرندر المشروع بأمان وفي المسار الصحيح
"""
import sys, os, subprocess
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

def main():
    if len(sys.argv) < 2:
        print("❌ الاستخدام: python render_project.py <project_id>")
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
    approval_file = proj_dir / ".studio_approved"
    approval_file_build = build_dir / ".studio_approved"

    # 1. فحص موافقة المستخدم
    if not approval_file.exists() and not approval_file_build.exists():
        print("🛑 [GUARDIAN BLOCK] ممنوع الرندر!")
        print("السبب: لم تتم الموافقة على الفيديو في الاستوديو.")
        print(f"الإجراء: افتح الاستوديو، راجع الفيديو، وأنشئ ملف {approval_file}.")
        sys.exit(1)

    # 2. التحقق من وجود المجلد
    if not build_dir.exists():
        print(f"❌ مجلد البناء غير موجود: {build_dir}")
        sys.exit(1)

    # 3. تشغيل الرندر في المسار الصحيح
    print(f"✅ [GUARDIAN PASS] جاري رندر الفيديو للمشروع {project_id}...")
    os.chdir(str(build_dir))
    use_shell = os.name == "nt"
    out_dir = build_dir / "out"
    out_dir.mkdir(exist_ok=True, parents=True)
    
    cmd = ["npx", "remotion", "render", "src/index.ts", "Main", f"out/{project_id}_final.mp4", "--concurrency=4"]
    subprocess.run(cmd, shell=use_shell)

if __name__ == "__main__":
    main()
