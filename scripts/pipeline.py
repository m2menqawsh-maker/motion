#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Smart Orchestrator Pipeline (المنسق الذكي)
يقوم بتتبع حالة المشروع عبر البصمة الرقمية (Hash) ولا يشغل سوى البوابات الضرورية.
الاستخدام: python scripts/pipeline.py <project_id>
"""

import sys
from scripts.path_security import validate_project_id, safe_resolve
import os
import json
import hashlib
import subprocess
from scripts.security import safe_subprocess
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

def get_file_hash(filepath: Path) -> str:
    if not filepath.exists():
        return None
    hasher = hashlib.sha256()
    hasher.update(filepath.read_bytes())
    return hasher.hexdigest()

def load_state(state_file: Path) -> dict:
    if state_file.exists():
        try:
            return json.loads(state_file.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def print_state_marker(state: dict):
    print(f"__PIPELINE_STATE__{json.dumps(state)}__PIPELINE_STATE__")

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
            
            # Postcondition Check (Process success != Operation success)
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
                pass # result might not be defined if exception happened before it
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
        
    state_file = proj_dir / ".pipeline_state.json"
    state = load_state(state_file)
    
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
    from scripts.checkpoint_store import CheckpointStore
    from scripts.checkpoint_model import CheckpointStage, CheckpointRecord, ValidationLevel
    from scripts.recovery_engine import RecoveryEngine
    import time
    
    decision = RecoveryEngine.evaluate(proj_dir)
    
    if decision.can_resume:
        logger.event("recovery.resumed", status="resumed") # Using same run_id for now as it's passed or generated
        next_stage = decision.next_stage
        print(f"\n✅ استئناف من نقطة الحفظ: {decision.reason} -> المرحلة التالية: {next_stage.value}")
    else:
        if decision.recommended_action and decision.recommended_action.startswith("restart_from_stage"):
            logger.event("recovery.rejected", status="rejected")
            print(f"\n⚠️ الاستئناف مرفوض: {decision.reason}. سيتم إعادة تشغيل بعض المراحل...")
            if "PLAN" in decision.recommended_action:
                next_stage = CheckpointStage.ASSETS_READY
            elif "BLUEPRINT" in decision.recommended_action:
                next_stage = CheckpointStage.PLAN_READY
            elif "RENDER" in decision.recommended_action:
                next_stage = CheckpointStage.BLUEPRINT_READY
            elif "QC" in decision.recommended_action:
                next_stage = CheckpointStage.RENDERED
            else:
                next_stage = CheckpointStage.INITIALIZED
        else:
            logger.event("recovery.detected", status="detected")
            next_stage = CheckpointStage.INITIALIZED
            print(f"\n🔍 [المنسق الذكي] بداية جديدة للمشروع: {project_id}...")

    # Helper for saving checkpoints
    def save_checkpoint(stage: CheckpointStage, artifacts: list):
        refs = []
        for path, val_level in artifacts:
            refs.append(CheckpointStore.create_artifact_record(proj_dir, path, val_level))
        
        record = CheckpointRecord(
            project_id=project_id,
            run_id=ctx.run_id,
            checkpoint=stage,
            timestamp=time.time(),
            artifact_references=refs
        )
        CheckpointStore.save(proj_dir, record)

    # ==========================================
    # Phase 1: Asset Gate
    # ==========================================
    if next_stage == CheckpointStage.INITIALIZED:
        print(f"\n➔ المرحلة الأولى (Assets):")
        if not run_script(logger, "assets", "asset_gate", "asset_gate.py", IdempotencyClass.SAFE_TO_RETRY, project_id):
            print("🛑 توقف التنفيذ بسبب أخطاء في المرحلة الأولى. أصلح المشاكل وأعد التشغيل.")
            sys.exit(1)
        save_checkpoint(CheckpointStage.ASSETS_READY, [])
        next_stage = CheckpointStage.ASSETS_READY
    else:
        print(f"\n➔ المرحلة الأولى (Assets): تخطي (منجز ✅)")

    # ==========================================
    # Phase 2: Plan & Taste
    # ==========================================
    if next_stage == CheckpointStage.ASSETS_READY:
        print(f"\n➔ المرحلة الثانية (Plan):")
        # plan_gate.py expects <project_id>
        if not run_script(logger, "plan", "plan_gate", "plan_gate.py", IdempotencyClass.SAFE_TO_RETRY, project_id):
            print("🛑 فشل الفحص! يرجى تصحيح الأخطاء في الخطة ثم إعادة تشغيل المنسق.")
            sys.exit(1)
            
        plan_file = proj_dir / "master_plan.md"
        # taste_gate.py expects <scene_plan.md> path
        if not run_script(logger, "plan", "taste_gate", "taste_gate.py", IdempotencyClass.SAFE_TO_RETRY, str(plan_file)):
            print("🛑 فشل الفحص! يرجى تصحيح الأخطاء الفنية (Taste) ثم إعادة تشغيل المنسق.")
            sys.exit(1)
            
        save_checkpoint(CheckpointStage.PLAN_READY, [("master_plan.md", ValidationLevel.SHA256)])
        FailureInjector.maybe_inject(InjectionPoint.AFTER_PLAN)
        next_stage = CheckpointStage.PLAN_READY
    else:
        print(f"\n➔ المرحلة الثانية (Plan): تخطي (منجز ✅)")

    # ==========================================
    # Phase 3: Blueprint
    # ==========================================
    if next_stage == CheckpointStage.PLAN_READY:
        print(f"\n➔ المرحلة الثالثة (Blueprint):")
        blueprint_file = proj_dir / "05_blueprint.json"
        
        if not run_script(logger, "blueprint", "validate_blueprint", "validate_blueprint.py", IdempotencyClass.SAFE_TO_RETRY, str(blueprint_file)):
            print("🛑 توقف التنفيذ. أصلح المشاكل الهيكلية في Blueprint وأعد التشغيل.")
            sys.exit(1)
            
        if not run_script(logger, "blueprint", "motion_validator", "motion_validator.py", IdempotencyClass.SAFE_TO_RETRY, str(blueprint_file)):
            print("🛑 توقف التنفيذ. شخصية الحركة غير مطابقة للشروط.")
            sys.exit(1)
            
        if not run_script(logger, "blueprint", "code_template_gate", "code_template_gate.py", IdempotencyClass.SAFE_TO_RETRY, project_id):
            print("🛑 توقف التنفيذ. قوالب الكود بها مشاكل.")
            sys.exit(1)
            
        save_checkpoint(CheckpointStage.BLUEPRINT_READY, [
            ("master_plan.md", ValidationLevel.SHA256),
            ("05_blueprint.json", ValidationLevel.SHA256)
        ])
        next_stage = CheckpointStage.BLUEPRINT_READY
    else:
        print(f"\n➔ المرحلة الثالثة (Blueprint): تخطي (منجز ✅)")

    # ==========================================
    # Phase 4: Render
    # ==========================================
    if next_stage == CheckpointStage.BLUEPRINT_READY:
        print(f"\n➔ المرحلة الرابعة (Render):")
        # render_project.py generates out.mp4
        FailureInjector.maybe_inject(InjectionPoint.BEFORE_RENDER)
        if not run_script(logger, "render", "remotion", "render_project.py", IdempotencyClass.CONDITIONALLY_RETRYABLE, project_id, expected_artifacts=[str(proj_dir / "out.mp4")]):
            print("🛑 توقف التنفيذ. عملية الرندر فشلت.")
            sys.exit(1)
            
        FailureInjector.maybe_inject(InjectionPoint.AFTER_RENDER)
        save_checkpoint(CheckpointStage.RENDERED, [
            ("master_plan.md", ValidationLevel.SHA256),
            ("05_blueprint.json", ValidationLevel.SHA256),
            ("out.mp4", ValidationLevel.SIZE)
        ])
        next_stage = CheckpointStage.RENDERED
    else:
        print(f"\n➔ المرحلة الرابعة (Render): تخطي (منجز ✅)")
        
    # ==========================================
    # Phase 5: QC
    # ==========================================
    if next_stage == CheckpointStage.RENDERED:
        print(f"\n➔ المرحلة الخامسة (QC):")
        # probe_qc.py expects <project_id>
        if not run_script(logger, "qc", "probe_qc", "probe_qc.py", IdempotencyClass.SAFE_TO_RETRY, project_id):
            print("🛑 توقف التنفيذ. الجودة النهائية (QC) فشلت.")
            sys.exit(1)
            
        save_checkpoint(CheckpointStage.QC_PASSED, [
            ("master_plan.md", ValidationLevel.SHA256),
            ("05_blueprint.json", ValidationLevel.SHA256),
            ("out.mp4", ValidationLevel.SIZE)
        ])
        next_stage = CheckpointStage.COMPLETE
    else:
        print(f"\n➔ المرحلة الخامسة (QC): تخطي (منجز ✅)")

    logger.event("pipeline.execution", status="success", stage="pipeline", component="pipeline")
    print("\n🎉 انتهى الفحص بنجاح! جميع ملفاتك وحالتك الحالية سليمة 100%.")

if __name__ == "__main__":
    main()
