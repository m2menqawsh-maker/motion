#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_project.py — سكريبت وسيط لرندر المشروع بأمان وفي المسار الصحيح
"""
import sys
from pathlib import Path

# Fix python path
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.core.pipeline import UnifiedPipeline
from scripts.core.gates import GateViolation

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import subprocess
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
        print("❌ الاستخدام: python render_project.py <project_id> [--docker]")
        sys.exit(1)

    project_id = sys.argv[1]

    pipeline = UnifiedPipeline(project_id)
    print(f"✅ جاري التحقق من المشروع {project_id}...")
    try:
        if not use_docker:
            result = pipeline.render()
            print(f"✅ نجاح الرندر! تم حفظ الفيديو في: {result.get('output')}")
        else:
            if not is_docker_running():
                print("❌ [Docker Error] محرك Docker غير يعمل أو غير مثبت في النظام. الرجاء تشغيله أولاً.")
                sys.exit(1)
                
            print(f"🐳 جاري الرندر عبر حاوية Docker (clean-video-builder)...")
            workspace_root = Path.cwd().resolve()
            project_dir = workspace_root / "projects" / project_id
            
            docker_cmd = [
                "docker", "run", "--rm",
                "-v", f"{workspace_root}:/workspace:ro",
                "-v", f"{project_dir}:/workspace/projects/{project_id}:rw",
                "-w", "/workspace/remotion-app",
                "--memory", "4g",
                "clean-video-builder",
                "bash", "-c", f"npx remotion render src/index.ts BlueprintVideo ../projects/{project_id}/out.mp4 --props ../projects/{project_id}/05_blueprint.json && chmod a+rw ../projects/{project_id}/out.mp4"
            ]
            
            proc = subprocess.run(docker_cmd)
            if proc.returncode == 0:
                print(f"✅ نجاح الرندر عبر Docker! تم حفظ الفيديو في: {project_dir / 'out.mp4'}")
            else:
                print(f"❌ فشل الرندر عبر Docker.")
                sys.exit(proc.returncode)
                
    except GateViolation as e:
        print(f"\n{'='*60}")
        print(f"🛑 [GUARDIAN BLOCK] ممنوع الرندر!")
        print(f"{'='*60}")
        print(e)
        sys.exit(1)
    except Exception as e:
        print(f"❌ فشل الرندر: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
