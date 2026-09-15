#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_project.py — سكريبت وسيط لرندر المشروع بأمان وفي المسار الصحيح
"""
import sys
from scripts.path_security import validate_project_id, safe_resolve
from pathlib import Path

# Fix python path
import asyncio
import json
import os
from api.services.pipeline_service import PipelineService

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import subprocess
from scripts.security import safe_subprocess
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
        print("❌ الاستخدام: python render_project.py <project_id> [--docker]")
        sys.exit(1)

    project_id = sys.argv[1]
    project_id = validate_project_id(project_id)

    print(f"✅ جاري التحقق من المشروع {project_id}...")
    try:
        status = asyncio.run(PipelineService.get_status(project_id))
        if status.get("status") != "locked":
            print(f"\n{'='*60}")
            print(f"🛑 [GUARDIAN BLOCK] ممنوع الرندر!")
            print(f"{'='*60}")
            print("لم يتم إصدار موافقة بشرية على المشروع (status != locked)")
            sys.exit(1)
            
        workspace_root = Path.cwd().resolve()
        project_dir = workspace_root / "projects" / project_id
            
        if not use_docker:
            env = os.environ.copy()
            env["PROJECT_ID"] = project_id
            
            out_file = project_dir / "out.mp4"
            npx_cmd = "npx.cmd" if os.name == "nt" else "npx"
            engine_dir = workspace_root / "remotion-app"
            
            props_file = project_dir / "render_props.json"
            props_file_abs = workspace_root / props_file
            
            def safe_load(name, default):
                p = project_dir / name
                return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default
                
            combined_props = {
                "projectData": {
                    "project": safe_load("project.json", {"fps": 30, "title": "Video"}),
                    "blueprint": safe_load("05_blueprint.json", {}),
                    "brand": safe_load("brand.json", {"colors": {}, "fonts": {}}),
                    "overrides": safe_load("overrides.json", {"scenes": {}})
                }
            }
            props_file.write_text(json.dumps(combined_props, ensure_ascii=False), encoding="utf-8")
            
            print(f"🎥 جاري الرندر (محلي)...")
            result = safe_subprocess(
                [npx_cmd, "remotion", "render", "src/index.ts", "BlueprintVideo", str(out_file), "--props", str(props_file_abs)],
                env=env,
                cwd=str(engine_dir),
                check=True,
                capture_output=True,
                text=True
            )
            print(result.stdout)
            print(f"✅ نجاح الرندر! تم حفظ الفيديو في: {out_file}")
        else:
            if not is_docker_running():
                print("❌ [Docker Error] محرك Docker غير يعمل أو غير مثبت في النظام. الرجاء تشغيله أولاً.")
                sys.exit(1)
                
            print(f"🐳 جاري الرندر عبر حاوية Docker (clean-video-builder)...")
            
            docker_cmd = [
                "docker", "run", "--rm",
                "-v", f"{workspace_root}:/workspace:ro",
                "-v", f"{project_dir}:/workspace/projects/{project_id}:rw",
                "-w", "/workspace/remotion-app",
                "--memory", "4g",
                "clean-video-builder",
                "bash", "-c", f"npx remotion render src/index.ts BlueprintVideo ../projects/{project_id}/out.mp4 --props ../projects/{project_id}/05_blueprint.json && chmod a+rw ../projects/{project_id}/out.mp4"
            ]
            
            proc = safe_subprocess(docker_cmd)
            if proc.returncode == 0:
                print(f"✅ نجاح الرندر عبر Docker! تم حفظ الفيديو في: {project_dir / 'out.mp4'}")
            else:
                print(f"❌ فشل الرندر عبر Docker.")
                sys.exit(proc.returncode)
                
    except Exception as e:
        print(f"❌ فشل الرندر: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
