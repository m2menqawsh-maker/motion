#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
open_studio.py — سكريبت وسيط لفتح الاستوديو بأمان وفي المسار الصحيح
"""
import sys, os, subprocess, json
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import shutil

def is_docker_running():
    if not shutil.which("docker"):
        return False
    try:
        proc = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=5)
        return proc.returncode == 0
    except Exception:
        return False

def main():
    use_docker = "--docker" in sys.argv
    if use_docker:
        sys.argv.remove("--docker")
        
    if len(sys.argv) < 2:
        print("❌ الاستخدام: python open_studio.py <project_id> [--docker]")
        sys.exit(1)

    project_id = sys.argv[1]
    
    workspace_root = Path.cwd()
    if (workspace_root / "projects" / project_id).exists():
        proj_dir = workspace_root / "projects" / project_id
    elif (workspace_root.parent / "projects" / project_id).exists():
        proj_dir = workspace_root.parent / "projects" / project_id
    else:
        proj_dir = Path(f"projects/{project_id}").resolve()

    engine_dir = workspace_root / "remotion-app"
    unlock_file = proj_dir / ".studio_unlocked"

    # 1. فحص القفل الميكانيكي
    if not unlock_file.exists():
        print("🛑 [GUARDIAN BLOCK] ممنوع فتح الاستوديو!")
        print(f"السبب: ملف .studio_unlocked غير موجود في {proj_dir}.")
        print("الإجراء: يجب تشغيل probe_qc.py ونجاحه أولاً لإنشاء ملف الفتح.")
        sys.exit(1)

    # 1.5. التأكد من عدم تعديل ملف 05_blueprint.json بعد الفحص
    unlock_mtime = unlock_file.stat().st_mtime
    blueprint_file = proj_dir / "05_blueprint.json"
    if blueprint_file.exists():
        if blueprint_file.stat().st_mtime > unlock_mtime:
            print(f"🛑 [GUARDIAN BLOCK] ممنوع فتح الاستوديو! تم تعديل الملف {blueprint_file.name} بعد الفحص.")
            print("السبب: أي تعديل على ملفات JSON يتطلب إعادة تشغيل أداة probe_qc.py.")
            sys.exit(1)

    # 2. التحقق من وجود المحرك المركزي
    if not engine_dir.exists():
        print(f"❌ مجلد المحرك المركزي غير موجود: {engine_dir}")
        sys.exit(1)

    # 3. تشغيل الاستوديو عبر المحرك وتمرير بيانات المشروع
    print(f"✅ [GUARDIAN PASS] جاري فتح الاستوديو للمشروع {project_id} عبر المحرك المركزي...")
    
    def safe_load(name, default):
        p = proj_dir / name
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default
        
    combined_props = {
        "projectData": {
            "project": safe_load("project.json", {"fps": 30, "title": "Video"}),
            "blueprint": json.loads((proj_dir / "05_blueprint.json").read_text(encoding="utf-8")),
            "brand": safe_load("brand.json", {"colors": {}, "fonts": {}}),
            "overrides": safe_load("overrides.json", {"scenes": {}})
        }
    }
    
    props_file = proj_dir / "render_props.json"
    props_file.write_text(json.dumps(combined_props, ensure_ascii=False), encoding="utf-8")
    
    props_file_abs = workspace_root.resolve() / props_file

    if not use_docker:
        os.chdir(str(engine_dir))
        use_shell = os.name == "nt"
        cmd = ["npx", "remotion", "studio", "--props", str(props_file_abs)]
        subprocess.run(cmd, shell=use_shell)
    else:
        if not is_docker_running():
            print("❌ [Docker Error] محرك Docker غير يعمل أو غير مثبت في النظام. الرجاء تشغيله أولاً.")
            sys.exit(1)
            
        print(f"🐳 جاري فتح الاستوديو عبر حاوية Docker (clean-video-builder)...")
        print(f"🌐 يرجى التوجه إلى http://localhost:3000 في المتصفح بعد بدء الخادم")
        
        workspace_root_abs = workspace_root.resolve()
        
        docker_cmd = [
            "docker", "run", "--rm", "-it",
            "-p", "3000:3000",
            "-v", f"{workspace_root_abs}:/workspace:ro",
            "-w", f"/workspace/remotion-app",
            "clean-video-builder",
            "npx", "remotion", "studio", "--host", "0.0.0.0", "--props", f"../projects/{project_id}/05_blueprint.json"
        ]
        
        subprocess.run(docker_cmd)

if __name__ == "__main__":
    main()
