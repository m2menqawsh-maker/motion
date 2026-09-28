import subprocess
from scripts.security.security import safe_subprocess
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
open_studio.py — سكريبت وسيط لفتح الاستوديو بأمان وفي المسار الصحيح
"""
import sys
from scripts.security.path_security import validate_project_id, safe_resolve, os, subprocess, json
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
        proc = safe_subprocess(["docker", "info"], capture_output=True, text=True, timeout=5)
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
    project_id = validate_project_id(project_id)
    
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

    # 1.5. التأكد من عدم تعديل ملف 05_blueprint.json بعد الفحص عبر SHA-256
    blueprint_file = proj_dir / "05_blueprint.json"
    if blueprint_file.exists():
        from scripts.core.state_store import StateStore
        state = StateStore.load(proj_dir)
        if state:
            bp_rec = state.get_artifact_record("05_blueprint.json")
            if bp_rec and bp_rec.sha256:
                current_sha = StateStore._compute_sha256(blueprint_file)
                if current_sha != bp_rec.sha256:
                    print(f"🛑 [GUARDIAN BLOCK] ممنوع فتح الاستوديو! تم تعديل الملف {blueprint_file.name} بعد الفحص (بصمة SHA-256 غير متطابقة).")
                    print("السبب: أي تعديل على ملفات JSON يتطلب إعادة تشغيل أداة probe_qc.py.")
                    sys.exit(1)

    # 2. التحقق من وجود المحرك المركزي
    if not engine_dir.exists():
        print(f"❌ مجلد المحرك المركزي غير موجود: {engine_dir}")
        sys.exit(1)

    # 3. تشغيل الاستوديو عبر المحرك وتمرير بيانات المشروع
    print(f"✅ [GUARDIAN PASS] جاري فتح الاستوديو للمشروع {project_id} عبر المحرك المركزي...")
    
    from scripts.core.render_input import build_render_input, get_render_props_path, RenderInputError
    try:
        build_render_input(
            proj_dir,
            workspace_root=workspace_root,
            verify_files_on_disk=True,
            write_to_disk=True,
        )
    except RenderInputError as e:
        print(f"❌ خطأ فادح في تجهيز مدخلات الاستوديو: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ خطأ غير متوقع في تجهيز مدخلات الاستوديو: {e}")
        sys.exit(1)

    props_file = get_render_props_path(proj_dir, workspace_root=workspace_root)
    props_file_abs = props_file.resolve()

    if not use_docker:
        os.chdir(str(engine_dir))
        use_shell = os.name == "nt"
        cmd = ["npx", "remotion", "studio", "--props", str(props_file_abs)]
        safe_subprocess(cmd, shell=False)
    else:
        if not is_docker_running():
            print("❌ [Docker Error] محرك Docker غير يعمل أو غير مثبت في النظام. الرجاء تشغيله أولاً.")
            sys.exit(1)
            
        print(f"🐳 جاري فتح الاستوديو عبر حاوية Docker (clean-video-builder)...")
        print(f"🌐 يرجى التوجه إلى http://localhost:3000 في المتصفح بعد بدء الخادم")
        
        proj_dir_abs = proj_dir.resolve()
        public_proj_dir = workspace_root / "remotion-app" / "public" / "projects" / project_id

        mount_flag = ":rw,z" if os.name != "nt" else ":rw"
        ro_mount_flag = ":ro,z" if os.name != "nt" else ":ro"

        docker_cmd = [
            "docker", "run", "--rm", "-it",
            "-p", "3000:3000",
        ]
        if shutil.which("podman"):
            docker_cmd.extend(["--userns=keep-id"])

        docker_cmd.extend([
            "-e", f"PROJECT_ID={project_id}",
            "-v", f"{proj_dir_abs}:/app/projects/{project_id}{mount_flag}",
        ])
        if public_proj_dir.exists():
            docker_cmd.extend(["-v", f"{public_proj_dir.resolve()}:/app/remotion-app/public/projects/{project_id}{ro_mount_flag}"])

        docker_cmd.extend([
            "-w", "/app/remotion-app",
            "clean-video-builder",
            "npx", "remotion", "studio", "--host", "0.0.0.0", "--props", f"../projects/{project_id}/render_props.json"
        ])

        safe_subprocess(docker_cmd)

if __name__ == "__main__":
    main()
