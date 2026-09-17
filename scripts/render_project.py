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
    
    import uuid
    import time
    import os
    from scripts.runtime_logger import RuntimeLogger, RunContext
    from scripts.failure_model import FailureInfo, FailureCode
    
    run_id = os.environ.get("AGY_RUN_ID")
    is_managed = os.environ.get("AGY_IS_MANAGED") == "1"
    attempt = int(os.environ.get("AGY_ATTEMPT", "1"))
    
    if not run_id:
        if is_managed:
            print("🛑 [TRACE ERROR] Missing AGY_RUN_ID in managed execution. Trace propagation failed.")
            sys.exit(1)
        run_id = str(uuid.uuid4())
        
    parent_span_id = os.environ.get("AGY_SPAN_ID")
    span_id = f"render-{uuid.uuid4().hex[:6]}"
    
    ctx = RunContext(run_id=run_id, project_id=project_id, span_id=span_id, parent_span_id=parent_span_id, attempt=attempt)
    logger = RuntimeLogger(ctx)
    
    start_time = time.time()
    logger.event("render.execution", status="started", stage="render", component="remotion")
    
    try:
        from scripts.state_store import StateStore
        from scripts.state_model import GateStatus
        workspace_root = Path.cwd().resolve()
        project_dir = workspace_root / "projects" / project_id
        
        state = StateStore.load(project_dir)
        is_approved = state and state.gates["gate_3"].status == GateStatus.APPROVED
        
        if not is_approved and not is_managed:
            duration_ms = int((time.time() - start_time) * 1000)
            failure = FailureInfo(
                code=FailureCode.PROJECT_NOT_LOCKED,
                message="Project is not approved (gate_3) for rendering",
                cause_type="Validation",
                stage="render",
                component="remotion"
            )
            logger.event("render.execution", status="failure", duration_ms=duration_ms, failure_info=failure)
            print(f"\n{'='*60}")
            print(f"🛑 [GUARDIAN BLOCK] ممنوع الرندر!")
            print(f"{'='*60}")
            print("لم يتم إصدار موافقة بشرية على المشروع (gate_3 != APPROVED)")
            sys.exit(1)
            
        workspace_root = Path.cwd().resolve()
        project_dir = workspace_root / "projects" / project_id
            
        if not use_docker:
            env = os.environ.copy()
            env["PROJECT_ID"] = project_id
            
            final_out_file = project_dir / "out.mp4"
            tmp_out_file = project_dir / f"out.attempt-{attempt}.tmp.mp4"
            
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
                    "overrides": safe_load("overrides.json", {"scenes": {}}),
                    "media_map": safe_load("media_map.json", {})
                }
            }
            props_file.write_text(json.dumps(combined_props, ensure_ascii=False), encoding="utf-8")
            
            print(f"🎥 جاري الرندر (محلي)...")
            result = safe_subprocess(
                [npx_cmd, "remotion", "render", "src/index.ts", "BlueprintVideo", str(tmp_out_file), "--props", str(props_file_abs)],
                env=env,
                cwd=str(engine_dir),
                check=True,
                capture_output=True,
                text=True
            )
            print(result.stdout)
            duration_ms = int((time.time() - start_time) * 1000)
            
            if tmp_out_file.exists():
                os.replace(tmp_out_file, final_out_file)
            else:
                raise FileNotFoundError("Render finished but tmp_out_file not found")
                
            logger.event("render.execution", status="success", stage="render", component="remotion", duration_ms=duration_ms)
            print(f"✅ نجاح الرندر! تم حفظ الفيديو في: {final_out_file}")
        else:
            if not is_docker_running():
                print("❌ [Docker Error] محرك Docker غير يعمل أو غير مثبت في النظام. الرجاء تشغيله أولاً.")
                sys.exit(1)
                
            print(f"🐳 جاري الرندر عبر حاوية Docker (clean-video-builder)...")
            
            final_out_file = project_dir / "out.mp4"
            tmp_out_file = project_dir / f"out.attempt-{attempt}.tmp.mp4"
            
            docker_cmd = [
                "docker", "run", "--rm",
                "-e", f"AGY_RUN_ID={ctx.run_id}",
                "-v", f"{workspace_root}:/workspace:ro",
                "-v", f"{project_dir}:/workspace/projects/{project_id}:rw",
                "-w", "/workspace/remotion-app",
                "--memory", "4g",
                "clean-video-builder",
                "bash", "-c", f"npx remotion render src/index.ts BlueprintVideo ../projects/{project_id}/out.attempt-{attempt}.tmp.mp4 --props ../projects/{project_id}/05_blueprint.json && chmod a+rw ../projects/{project_id}/out.attempt-{attempt}.tmp.mp4"
            ]
            
            proc = safe_subprocess(docker_cmd)
            duration_ms = int((time.time() - start_time) * 1000)
            if proc.returncode == 0:
                if tmp_out_file.exists():
                    os.replace(tmp_out_file, final_out_file)
                else:
                    raise FileNotFoundError("Docker Render finished but tmp_out_file not found")
                    
                logger.event("render.execution", status="success", stage="render", component="docker", duration_ms=duration_ms)
                print(f"✅ نجاح الرندر عبر Docker! تم حفظ الفيديو في: {final_out_file}")
            else:
                failure = FailureInfo(
                    code=FailureCode.RENDER_DOCKER_FAILED,
                    message=f"Exit code {proc.returncode}",
                    cause_type="SubprocessError",
                    stage="render",
                    component="docker"
                )
                logger.event("render.execution", status="failure", duration_ms=duration_ms, failure_info=failure)
                print(f"❌ فشل الرندر عبر Docker.")
                sys.exit(proc.returncode)
                
    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        failure = FailureInfo(
            code=FailureCode.UNEXPECTED_INTERNAL_ERROR,
            message=str(e),
            cause_type=type(e).__name__,
            stage="render",
            component="remotion",
            is_fallback=True
        )
        logger.event("render.execution", status="failure", duration_ms=duration_ms, failure_info=failure)
        print(f"❌ فشل الرندر: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
