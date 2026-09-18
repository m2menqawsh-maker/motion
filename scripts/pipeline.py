#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smart Orchestrator Pipeline (المنسق الذكي)
يقوم بتتبع حالة المشروع عبر البصمة الرقمية (Hash) ولا يشغل سوى البوابات الضرورية.
الاستخدام: python scripts/pipeline.py <project_id>
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.path_security import validate_project_id, safe_resolve
import os
import json
import hashlib
import subprocess
from scripts.security import safe_subprocess

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import uuid
import time
from scripts.runtime_logger import RuntimeLogger, RunContext
from scripts.retry_policy import RetryPolicyEngine, IdempotencyClass
from scripts.failure_injection import FailureInjector, InjectionPoint

def run_script(logger, stage: str, component: str, script_name: str, idempotency: IdempotencyClass, *args, expected_artifacts=None) -> bool:
    script_path = Path("scripts") / script_name
    if not script_path.exists():
        print(f"❌ خطأ: لم يتم العثور على السكربت {script_name}")
        return False
        
    cmd = [sys.executable, str(script_path)] + list(args)
    print(f"   ⏳ تشغيل {script_name}...")
    
    current_attempt_ctx = logger.context.derive(component)
    
    while True:
        child_logger = RuntimeLogger(current_attempt_ctx)
        
        start_time = time.time()
        child_logger.event("gate.execution", status="started", stage=stage, component=component)
        
        # Propagate trace via environment
        env = os.environ.copy()
        env["AGY_RUN_ID"] = current_attempt_ctx.run_id
        env["AGY_SPAN_ID"] = current_attempt_ctx.span_id
        env["AGY_ATTEMPT"] = str(current_attempt_ctx.attempt)
        if current_attempt_ctx.project_id:
            env["AGY_PROJECT_ID"] = current_attempt_ctx.project_id
        env["AGY_IS_MANAGED"] = "1"
        workspace_dir = str(Path(__file__).resolve().parent.parent)
        existing_pythonpath = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{workspace_dir}{os.pathsep}{existing_pythonpath}" if existing_pythonpath else workspace_dir
        
        # Determine injection point based on stage/component
        injection_point = None
        if stage == "assets": injection_point = InjectionPoint.BEFORE_ASSETS
        elif stage == "plan": injection_point = InjectionPoint.BEFORE_PLAN
        elif stage == "render": injection_point = InjectionPoint.BEFORE_RENDER
        elif stage == "qc": injection_point = InjectionPoint.BEFORE_QC
        
        try:
            if injection_point:
                FailureInjector.maybe_inject(injection_point, attempt=current_attempt_ctx.attempt)
                if injection_point == InjectionPoint.BEFORE_RENDER:
                    FailureInjector.maybe_inject(InjectionPoint.DURING_RENDER, attempt=current_attempt_ctx.attempt)
                    
            result = safe_subprocess(cmd, capture_output=True, text=True, encoding="utf-8", env=env)
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Postcondition Check
            silent_failure_msg = None
            if result.returncode == 0 and expected_artifacts:
                for artifact_path in expected_artifacts:
                    if not Path(artifact_path).exists():
                        silent_failure_msg = f"Silent failure detected: {artifact_path} was not created despite exit code 0"
                        break
                        
            if result.returncode != 0 or silent_failure_msg:
                raise RuntimeError(silent_failure_msg or f"{script_name} exited with code {result.returncode}")
                
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            from scripts.failure_model import FailureInfo, FailureCode
            failure = FailureInfo(
                code=FailureCode.GATE_EXECUTION_FAILED,
                message=str(e),
                cause_type=type(e).__name__,
                stage=stage,
                component=component
            )
            child_logger.event(
                "gate.execution", 
                status="failure",
                duration_ms=duration_ms,
                failure_info=failure
            )
            print(f"   ❌ فشل في {script_name}")
            print("\n" + "="*40 + f" تفاصيل الخطأ (محاولة {current_attempt_ctx.attempt}) " + "="*40)
            print(f"   💬 السبب: {str(e)}")
            try:
                if result.stdout:
                    print(result.stdout.strip())
                if result.stderr:
                    print(result.stderr.strip())
            except NameError:
                pass # result might not be defined
            print("="*94 + "\n")
            
            decision = RetryPolicyEngine.evaluate(failure, idempotency, current_attempt_ctx.attempt)
            
            if decision.should_retry:
                child_logger.event(
                    "retry.scheduled",
                    status="scheduled",
                    stage=stage,
                    component=component,
                    failure_info=FailureInfo(
                        code=failure.code,
                        message=f"Attempt {current_attempt_ctx.attempt} failed. Retrying in {decision.delay_seconds}s...",
                        stage=stage,
                        component=component
                    )
                )
                print(f"   🔄 إعادة محاولة {script_name} (محاولة {decision.next_attempt}/{decision.max_attempts}) بعد {decision.delay_seconds} ثواني...")
                RetryPolicyEngine.delay_for(decision)
                current_attempt_ctx = current_attempt_ctx.derive_retry(component)
                continue
            else:
                child_logger.event(
                    "retry.exhausted" if decision.reason.startswith("Max attempts") else "retry.aborted",
                    status="exhausted" if decision.reason.startswith("Max attempts") else "aborted",
                    stage=stage,
                    component=component,
                    failure_info=FailureInfo(
                        code=failure.code,
                        message=decision.reason,
                        stage=stage,
                        component=component
                    )
                )
                print(f"   🛑 تم إيقاف المحاولات لـ {script_name}: {decision.reason}")
                return False
            
        child_logger.event("gate.execution", status="success", stage=stage, component=component, duration_ms=duration_ms)
        if current_attempt_ctx.attempt > 1:
            child_logger.event("retry.success", status="success", stage=stage, component=component)
            
        print(f"   ✅ نجاح: {script_name} (بعد {current_attempt_ctx.attempt} محاولات)" if current_attempt_ctx.attempt > 1 else f"   ✅ نجاح: {script_name}")
        return True

def main():
    if len(sys.argv) < 2:
        print("الاستخدام: python scripts/pipeline.py <project_id>")
        sys.exit(1)
        
    project_id = sys.argv[1]
    project_id = validate_project_id(project_id)
    proj_dir = Path("projects") / project_id
    
    if not proj_dir.exists():
        print(f"❌ المشروع {project_id} غير موجود في المجلد projects/")
        sys.exit(1)
        
    run_id = os.environ.get("AGY_RUN_ID")
    if not run_id:
        run_id = str(uuid.uuid4())
    parent_span_id = os.environ.get("AGY_SPAN_ID")
    span_id = f"pipeline-{uuid.uuid4().hex[:6]}"
    
    ctx = RunContext(run_id=run_id, project_id=project_id, span_id=span_id, parent_span_id=parent_span_id)
    logger = RuntimeLogger(ctx)
    logger.event("pipeline.execution", status="started", component="pipeline", stage="pipeline")
    
    # ==========================================
    # Initialization & Recovery
    # ==========================================
    from scripts.state_store import StateStore
    from scripts.state_model import LifecycleState, ValidationLevel, ProjectState, StateMachine
    from scripts.recovery_engine import RecoveryEngine
    import time
    
    decision = RecoveryEngine.evaluate(proj_dir)
    
    if decision.can_resume:
        logger.event("recovery.resumed", status="resumed")
        next_state = decision.next_state
        print(f"\n✅ استئناف من نقطة الحفظ: {decision.reason} -> المرحلة الحالية: {next_state}")
    else:
        logger.event("recovery.detected", status="detected")
        next_state = LifecycleState.DRAFT
        print(f"\n🔍 [المنسق الذكي] بداية جديدة للمشروع: {project_id}...")

    def save_state(target_state: LifecycleState, artifacts: list):
        refs = []
        for path, val_level in artifacts:
            refs.append(StateStore.create_artifact_record(proj_dir, path, val_level))
        
        state = StateStore.load(proj_dir)
        if not state:
            state = ProjectState(project_id=project_id)
            
        state.artifact_records = refs
        StateMachine.transition(state, target_state)
        StateStore.save(proj_dir, state)

    def mark_failed():
        state = StateStore.load(proj_dir)
        if state:
            state.lifecycle_state = LifecycleState.FAILED
            StateStore.save(proj_dir, state)

    # State Machine Loop
    while next_state != LifecycleState.COMPLETE:
        
        if next_state == LifecycleState.FAILED:
            print("🛑 حالة المشروع FAILED. يجب حل المشكلة يدوياً أو عبر الاسترجاع.")
            sys.exit(1)
            
        if next_state == LifecycleState.CANCELLED:
            print("🛑 حالة المشروع CANCELLED.")
            sys.exit(1)

        # 1. DRAFT -> ASSETS_READY
        if next_state == LifecycleState.DRAFT:
            print(f"\n➔ الانتقال من DRAFT إلى ASSETS_READY:")
            if not run_script(logger, "assets", "asset_gate", "asset_gate.py", IdempotencyClass.SAFE_TO_RETRY, project_id):
                mark_failed()
                sys.exit(1)
            save_state(LifecycleState.ASSETS_READY, [("02_asset_manifest.json", ValidationLevel.EXISTS)])
            next_state = LifecycleState.ASSETS_READY

        # 2. ASSETS_READY -> PLAN_READY
        elif next_state == LifecycleState.ASSETS_READY:
            print(f"\n➔ الانتقال من ASSETS_READY إلى PLAN_READY:")
            if not run_script(logger, "plan", "plan_gate", "plan_gate.py", IdempotencyClass.SAFE_TO_RETRY, project_id):
                mark_failed()
                sys.exit(1)
            plan_file = proj_dir / "master_plan.md"
            if not run_script(logger, "plan", "taste_gate", "taste_gate.py", IdempotencyClass.SAFE_TO_RETRY, str(plan_file)):
                mark_failed()
                sys.exit(1)
            save_state(LifecycleState.PLAN_READY, [("master_plan.md", ValidationLevel.SHA256)])
            next_state = LifecycleState.PLAN_READY

        # 3. PLAN_READY -> BLUEPRINT_READY
        elif next_state == LifecycleState.PLAN_READY:
            print(f"\n➔ الانتقال من PLAN_READY إلى BLUEPRINT_READY:")
            blueprint_file = proj_dir / "05_blueprint.json"
            if not run_script(logger, "blueprint", "validate_blueprint", "validate_blueprint.py", IdempotencyClass.SAFE_TO_RETRY, str(blueprint_file)):
                mark_failed()
                sys.exit(1)
            if not run_script(logger, "blueprint", "motion_validator", "motion_validator.py", IdempotencyClass.SAFE_TO_RETRY, str(blueprint_file)):
                mark_failed()
                sys.exit(1)
            if not run_script(logger, "blueprint", "code_template_gate", "code_template_gate.py", IdempotencyClass.SAFE_TO_RETRY, project_id):
                mark_failed()
                sys.exit(1)
            save_state(LifecycleState.BLUEPRINT_READY, [
                ("master_plan.md", ValidationLevel.SHA256),
                ("05_blueprint.json", ValidationLevel.SHA256)
            ])
            next_state = LifecycleState.BLUEPRINT_READY

        # 4. BLUEPRINT_READY -> MATERIALIZED
        elif next_state == LifecycleState.BLUEPRINT_READY:
            print(f"\n➔ الانتقال من BLUEPRINT_READY إلى MATERIALIZED:")
            if not run_script(logger, "blueprint", "materialize_project", "materialize_project.py", IdempotencyClass.SAFE_TO_RETRY, str(proj_dir)):
                mark_failed()
                sys.exit(1)
            save_state(LifecycleState.MATERIALIZED, [
                ("master_plan.md", ValidationLevel.SHA256),
                ("05_blueprint.json", ValidationLevel.SHA256),
                ("media_map.json", ValidationLevel.SHA256)
            ])
            next_state = LifecycleState.MATERIALIZED

        # 5. MATERIALIZED -> PROBE_PASSED
        elif next_state == LifecycleState.MATERIALIZED:
            print(f"\n➔ الانتقال من MATERIALIZED إلى PROBE_PASSED:")
            if not run_script(logger, "qc", "probe_qc", "probe_qc.py", IdempotencyClass.SAFE_TO_RETRY, project_id):
                mark_failed()
                sys.exit(1)
            save_state(LifecycleState.PROBE_PASSED, [
                ("master_plan.md", ValidationLevel.SHA256),
                ("05_blueprint.json", ValidationLevel.SHA256),
                ("probe_qc_report.json", ValidationLevel.EXISTS)
            ])
            next_state = LifecycleState.PROBE_PASSED

        # 6. PROBE_PASSED -> AWAITING_REVIEW
        elif next_state == LifecycleState.PROBE_PASSED:
            print(f"\n➔ الانتقال التلقائي لانتظار المراجعة (AWAITING_REVIEW)...")
            save_state(LifecycleState.AWAITING_REVIEW, [])
            next_state = LifecycleState.AWAITING_REVIEW

        # 7. AWAITING_REVIEW -> REVIEW_APPROVED
        elif next_state == LifecycleState.AWAITING_REVIEW:
            approved_marker = proj_dir / ".studio_approved"
            if approved_marker.exists():
                print(f"\n✅ تم العثور على الموافقة البشرية (.studio_approved). ننتقل لـ REVIEW_APPROVED.")
                save_state(LifecycleState.REVIEW_APPROVED, [])
                next_state = LifecycleState.REVIEW_APPROVED
            else:
                print(f"\n⏸️ المنسق متوقف مؤقتاً.")
                print(f"المشروع جاهز للمعاينة في الاستوديو (AWAITING_REVIEW). يرجى مراجعة الفيديو وإنشاء ملف .studio_approved قبل الرندر النهائي.")
                sys.exit(0)

        # 8. REVIEW_APPROVED -> RENDERED
        elif next_state == LifecycleState.REVIEW_APPROVED:
            print(f"\n➔ الانتقال من REVIEW_APPROVED إلى RENDERED (الرندر النهائي):")
            FailureInjector.maybe_inject(InjectionPoint.BEFORE_RENDER)
            if not run_script(logger, "render", "remotion", "render_project.py", IdempotencyClass.CONDITIONALLY_RETRYABLE, project_id, expected_artifacts=[str(proj_dir / "out.mp4")]):
                mark_failed()
                sys.exit(1)
            FailureInjector.maybe_inject(InjectionPoint.AFTER_RENDER)
            save_state(LifecycleState.RENDERED, [
                ("master_plan.md", ValidationLevel.SHA256),
                ("05_blueprint.json", ValidationLevel.SHA256),
                ("out.mp4", ValidationLevel.SIZE)
            ])
            next_state = LifecycleState.RENDERED

        # 9. RENDERED -> FINAL_QC_PASSED
        elif next_state == LifecycleState.RENDERED:
            print(f"\n➔ الانتقال من RENDERED إلى FINAL_QC_PASSED:")
            if not run_script(logger, "qc", "final_qc", "final_qc.py", IdempotencyClass.SAFE_TO_RETRY, project_id):
                mark_failed()
                sys.exit(1)
            save_state(LifecycleState.FINAL_QC_PASSED, [
                ("master_plan.md", ValidationLevel.SHA256),
                ("05_blueprint.json", ValidationLevel.SHA256),
                ("out.mp4", ValidationLevel.SIZE)
            ])
            next_state = LifecycleState.FINAL_QC_PASSED

        # 10. FINAL_QC_PASSED -> COMPLETE
        elif next_state == LifecycleState.FINAL_QC_PASSED:
            print(f"\n➔ إنهاء المشروع...")
            save_state(LifecycleState.COMPLETE, [])
            next_state = LifecycleState.COMPLETE

    logger.event("pipeline.execution", status="success", stage="pipeline", component="pipeline")
    print("\n🎉 انتهى الفحص بنجاح! جميع ملفاتك وحالتك الحالية سليمة 100%. (الحالة: COMPLETE)")

if __name__ == "__main__":
    main()
