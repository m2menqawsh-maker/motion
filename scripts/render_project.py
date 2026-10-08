#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_project.py — سكريبت وسيط لرندر المشروع بأمان وفي المسار الصحيح
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.security.path_security import validate_project_id, safe_resolve
import asyncio
from datetime import datetime, timezone
import json
import os
from api.services.pipeline_service import PipelineService

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import subprocess
from scripts.security.security import safe_subprocess
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
    from scripts.core.runtime_logger import RuntimeLogger, RunContext
    from scripts.core.failure_model import FailureInfo, FailureCode
    
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
        from scripts.core.review_service import assert_render_authorized, RenderNotAuthorizedError
        workspace_root = Path.cwd().resolve()
        project_dir = workspace_root / "projects" / project_id
        
        try:
            auth_result = assert_render_authorized(project_dir)
        except RenderNotAuthorizedError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            failure = FailureInfo(
                code=e.code,
                message=f"Project is not approved (gate_3) for rendering: {e.message}",
                cause_type="Validation",
                stage="render",
                component="remotion"
            )
            logger.event("render.execution", status="failure", duration_ms=duration_ms, failure_info=failure)
            print(f"\n{'='*60}")
            print(f"🛑 [GUARDIAN BLOCK] ممنوع الرندر!")
            print(f"{'='*60}")
            print(f"لم يتم إصدار موافقة بشرية على المشروع (gate_3 != APPROVED) - السبب: {e.message}")
            sys.exit(1)
            
        workspace_root = Path.cwd().resolve()
        project_dir = workspace_root / "projects" / project_id

        from scripts.core.render_input import build_render_input, get_render_props_path, RenderInputError
        try:
            build_render_input(
                project_dir,
                workspace_root=workspace_root,
                verify_files_on_disk=True,
                write_to_disk=True,
            )
        except RenderInputError as e:
            print(f"🛑 خطأ فادح في تجهيز مدخلات الرندر: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"🛑 خطأ فادح: فشل تجهيز مدخلات الرندر: {e}")
            sys.exit(1)

        props_file = get_render_props_path(project_dir, workspace_root=workspace_root)
        props_file_abs = props_file.resolve()
            
        if not use_docker:
            env = os.environ.copy()
            env["PROJECT_ID"] = project_id
            
            final_out_file = project_dir / "out.mp4"
            tmp_out_file = project_dir / f"out.attempt-{attempt}.tmp.mp4"
            
            npx_cmd = "npx.cmd" if os.name == "nt" else "npx"
            engine_dir = workspace_root / "remotion-app"
            
            # S28-R14: Primary execution through RenderPlanner -> Multi-Engine RenderGraph -> Master Compositor
            use_legacy = os.environ.get("USE_LEGACY_RENDER_PATH") == "1" or "--legacy-cli" in sys.argv
            planner_script = workspace_root / "scripts" / "render_via_planner.ts"
            adapter_script = workspace_root / "scripts" / "render_via_adapter.ts"
            render_success = False

            ws_id = os.environ.get("AGY_WORKSPACE_ID", "ws_default")
            input_rev = os.environ.get("AGY_INPUT_REVISION", "1")

            active_render_path = "legacy_cli"
            if not use_legacy and planner_script.exists():
                print(f"🎥 جاري الرندر عبر Multi-Engine RenderPlanner & MasterCompositor (S28-R14)...")
                try:
                    cmd_planner = [
                        npx_cmd, "tsx", str(planner_script), project_id,
                        "--out", str(tmp_out_file),
                        "--run-id", run_id,
                        "--workspace", ws_id,
                        "--revision", input_rev,
                    ]
                    res = safe_subprocess(
                        cmd_planner,
                        env=env,
                        cwd=str(workspace_root),
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                    print(res.stdout)
                    render_success = True
                    active_render_path = "Multi-Engine RenderPlanner & MasterCompositor"
                except Exception as ex:
                    detail = getattr(ex, "stderr", None) or getattr(ex, "output", None) or str(ex)
                    sys.stderr.write(f"\n[DIAGNOSTIC] Planner execution failed:\n{detail}\n")
                    sys.stderr.flush()
                    with open("/tmp/render_planner_err.log", "w", encoding="utf-8") as f_err:
                        f_err.write(f"Planner failed:\nEX: {ex}\nSTDERR: {getattr(ex, 'stderr', None)}\nSTDOUT: {getattr(ex, 'stdout', None)}\n")
                    print(f"⚠️ فشل مسار Multi-Engine Planner ({detail}) — تجربة مسار Adapter الفردي...")

            if not render_success and not use_legacy and adapter_script.exists():
                print(f"🎥 جاري الرندر عبر RemotionRendererAdapter (S28-R09)...")
                try:
                    res = safe_subprocess(
                        [npx_cmd, "tsx", str(adapter_script), project_id, "--out", str(tmp_out_file)],
                        env=env,
                        cwd=str(workspace_root),
                        check=True,
                        capture_output=True,
                        text=True
                    )
                    print(res.stdout)
                    render_success = True
                except Exception as ex:
                    detail = getattr(ex, "stderr", None) or getattr(ex, "output", None) or str(ex)
                    print(f"⚠️ فشل مسار Adapter ({detail}) — تفعيل جسر التوافق (Legacy Remotion CLI)...")

            if not render_success:
                print(f"🎥 جاري الرندر عبر مسار التوافق (Remotion CLI)...")
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
                
            receipt_file = project_dir / "render_receipt.json"
            receipt_data = {
                "project_id": project_id,
                "active_render_path": active_render_path,
                "rendered_at": datetime.now(timezone.utc).isoformat(),
                "duration_ms": duration_ms,
            }
            receipt_file.write_text(json.dumps(receipt_data, indent=2), encoding="utf-8")

            logger.event("render.execution", status="success", stage="render", component="remotion", duration_ms=duration_ms)
            print(f"✅ نجاح الرندر ({active_render_path})! تم حفظ الفيديو في: {final_out_file}")
        else:
            if not is_docker_running():
                print("❌ [Docker Error] محرك Docker غير يعمل أو غير مثبت في النظام. الرجاء تشغيله أولاً.")
                sys.exit(1)
                
            print(f"🐳 جاري الرندر عبر حاوية Docker (clean-video-builder)...")

            final_out_file = project_dir / "out.mp4"
            tmp_out_file = project_dir / f"out.attempt-{attempt}.tmp.mp4"

            project_dir_abs = project_dir.resolve()
            public_proj_dir = workspace_root / "remotion-app" / "public" / "projects" / project_id

            mount_flag = ":rw,z" if os.name != "nt" else ":rw"
            ro_mount_flag = ":ro,z" if os.name != "nt" else ":ro"

            docker_cmd = [
                "docker", "run", "--rm",
            ]
            if shutil.which("podman"):
                docker_cmd.extend(["--userns=keep-id"])

            docker_cmd.extend([
                "-e", f"AGY_RUN_ID={ctx.run_id}",
                "-e", f"PROJECT_ID={project_id}",
                "-v", f"{project_dir_abs}:/app/projects/{project_id}{mount_flag}",
            ])
            if public_proj_dir.exists():
                docker_cmd.extend(["-v", f"{public_proj_dir.resolve()}:/app/remotion-app/public/projects/{project_id}{ro_mount_flag}"])

            docker_cmd.extend([
                "-w", "/app/remotion-app",
                "--memory", "4g",
                "clean-video-builder",
                "npx", "remotion", "render", "src/index.ts", "BlueprintVideo",
                f"../projects/{project_id}/out.attempt-{attempt}.tmp.mp4",
                "--props", f"../projects/{project_id}/render_props.json"
            ])

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
