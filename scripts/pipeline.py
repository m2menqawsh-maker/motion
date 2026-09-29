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

from scripts.security.path_security import validate_project_id, safe_resolve
import os
import json
import hashlib
import subprocess
from scripts.security.security import safe_subprocess

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import uuid
import time
from scripts.core.runtime_logger import RuntimeLogger, RunContext
from scripts.core.retry_policy import RetryPolicyEngine, IdempotencyClass
from scripts.core.failure_injection import FailureInjector, InjectionPoint

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
            from scripts.core.failure_model import FailureInfo, FailureCode, FailureClassifier
            from scripts.core.retry_policy import RetryPolicyEngine, RetryContext
            from scripts.core.state_store import StateStore

            res_returncode = result.returncode if 'result' in locals() and result else 1
            res_stdout = result.stdout if 'result' in locals() and result else ""
            res_stderr = result.stderr if 'result' in locals() and result else ""

            failure = FailureClassifier.classify(
                script_name=script_name,
                returncode=res_returncode,
                stdout=res_stdout,
                stderr=res_stderr,
                exception=e,
                stage=stage,
                component=component,
            )

            child_logger.event(
                "gate.execution", 
                status="failure",
                duration_ms=duration_ms,
                failure_info=failure
            )
            print(f"   ❌ فشل في {script_name} [{failure.code.value}]")
            print("\n" + "="*40 + f" تفاصيل الخطأ (محاولة {current_attempt_ctx.attempt}) " + "="*40)
            print(f"   💬 الكود: {failure.code.value} | التصنيف: {failure.metadata.category.value}")
            print(f"   💬 السبب: {failure.message}")
            try:
                if result.stdout:
                    print(result.stdout.strip())
                if result.stderr:
                    print(result.stderr.strip())
            except NameError:
                pass # result might not be defined
            print("="*94 + "\n")
            
            # Precondition validation for conditional retries
            is_valid = True
            if current_attempt_ctx.project_id:
                proj_dir = Path("projects") / current_attempt_ctx.project_id
                state_file = proj_dir / StateStore.STATE_FILE
                if state_file.is_file():
                    input_fps = {}
                    for arg in args:
                        if isinstance(arg, str):
                            p = Path(arg)
                            if p.is_file():
                                try:
                                    input_fps[p.name] = StateStore._compute_sha256(p)
                                except Exception:
                                    pass
                    
                    try:
                        st = StateStore.load(proj_dir)
                    except Exception:
                        st = None

                    if st:
                        curr_rev = st.revision
                        retry_ctx = RetryContext(
                            project_id=current_attempt_ctx.project_id,
                            stage=stage,
                            operation=component,
                            attempt=current_attempt_ctx.attempt,
                            expected_revision=curr_rev,
                            input_fingerprints=input_fps,
                            evidence_paths=list(expected_artifacts) if expected_artifacts else [],
                            idempotency=idempotency,
                        )
                        is_valid, val_reason = RetryPolicyEngine.validate_retry_preconditions(retry_ctx, proj_dir)
                        if not is_valid:
                            print(f"   ⚠️ شروط إعادة المحاولة غير مستوفاة: {val_reason}")

            decision = RetryPolicyEngine.evaluate(failure, idempotency, current_attempt_ctx.attempt, is_state_valid=is_valid)

            # Persist failure attempt into ProjectState
            if current_attempt_ctx.project_id:
                proj_dir = Path("projects") / current_attempt_ctx.project_id
                state_file = proj_dir / StateStore.STATE_FILE
                if state_file.is_file():
                    try:
                        RetryPolicyEngine.record_failure_attempt(
                            project_dir=proj_dir,
                            failure=failure,
                            attempt=current_attempt_ctx.attempt,
                            will_retry=decision.should_retry,
                            operation_id=current_attempt_ctx.span_id,
                        )
                    except Exception as ex:
                        print(f"   ⚠️ تعذر تسجيل محاولة الفشل في الحالة: {ex}")
            
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
    # Cross-Process Execution Lock (LED-061)
    # ==========================================
    import atexit
    from scripts.core.project_lock import ProjectExecutionLock, ProjectExecutionConflictError
    is_managed = os.environ.get("AGY_IS_MANAGED") == "1"
    execution_lock = None
    if not is_managed:
        execution_lock = ProjectExecutionLock(
            project_dir=proj_dir,
            owner_id=os.environ.get("AGY_WORKER_ID", "cli"),
            run_id=run_id,
        )
        try:
            execution_lock.acquire()
            atexit.register(execution_lock.release)
        except ProjectExecutionConflictError as e:
            print(f"\n🛑 [CONCURRENCY CONFLICT] {e}")
            logger.event("pipeline.conflict", status="failed", error=str(e))
            sys.exit(1)
    
    # ==========================================
    # Initialization & Recovery
    # ==========================================
    from scripts.core.state_store import StateStore, StateCorruptedError, StateIOError
    from scripts.core.state_model import LifecycleState, ValidationLevel, ProjectState, StateMachine
    from scripts.core.lifecycle_service import LifecycleService
    from scripts.core.recovery_engine import RecoveryEngine, RecoveryPlanner, RecoveryService
    import time
    
    try:
        current_state_record = StateStore.load(proj_dir)
    except StateCorruptedError as e:
        print(f"\n🛑 [خطأ أمني فادح] ملف حالة المشروع تالف وغير قابل للقراءة: {e}")
        logger.event("state.corrupted", status="failed", error=str(e))
        sys.exit(1)
    except StateIOError as e:
        print(f"\n🛑 [خطأ إدخال/إخراج] تعذر قراءة ملف حالة المشروع: {e}")
        logger.event("state.io_error", status="failed", error=str(e))
        sys.exit(1)

    if current_state_record is None:
        logger.event("recovery.detected", status="detected")
        next_state = LifecycleState.DRAFT
        current_revision = 1
        print(f"\n🔍 [المنسق الذكي] بداية جديدة للمشروع: {project_id}...")
    else:
        decision = RecoveryEngine.evaluate(proj_dir)
        if decision.can_resume:
            logger.event("recovery.resumed", status="resumed")
            next_state = decision.next_state
            current_revision = current_state_record.revision
            print(f"\n✅ استئناف من نقطة الحفظ: {decision.reason} -> المرحلة الحالية: {next_state}")
        else:
            logger.event("recovery.plan_required", status="plan_required", reason=decision.reason)
            print(f"\n⚠️ [الاسترجاع والتسوية] تعذر الاستئناف المباشر: {decision.reason}")

            plan = decision.recovery_plan or RecoveryPlanner.create_plan(proj_dir, state=current_state_record)
            if plan.requires_manual_action:
                print(f"🛑 [توقف أمان] يتطلب المشروع تدخلاً يدوياً: {plan.reason}")
                sys.exit(1)

            print(f"   📋 تطبيق خطة الاسترجاع: {plan.current_state.value} ➔ {plan.target_state.value}")
            if plan.invalidated_evidence_paths:
                print(f"   🗑️ أدلة تم إبطالها: {plan.invalidated_evidence_paths}")
            if plan.stale_disk_paths:
                print(f"   🧹 إزالة علامات غير صالحة: {plan.stale_disk_paths}")

            reconciled_state = RecoveryService.apply_plan(proj_dir, plan)
            next_state = plan.target_state
            current_revision = reconciled_state.revision
            print(f"   ✅ تمت تسوية حالة القرص بنجاح (المراجعة: {current_revision}) -> استئناف من {next_state.value}\n")

    def save_state(target_state: LifecycleState, artifacts: list):
        nonlocal current_revision
        disk_state = StateStore.load(proj_dir)
        if disk_state and disk_state.revision > current_revision:
            current_revision = disk_state.revision

        st = LifecycleService.transition(
            project_dir=proj_dir,
            target_state=target_state,
            artifacts=artifacts,
            expected_revision=current_revision,
        )
        current_revision = st.revision

    def mark_failed(reason: str = "Pipeline execution failed"):
        nonlocal current_revision
        disk_state = StateStore.load(proj_dir)
        if disk_state and disk_state.revision > current_revision:
            current_revision = disk_state.revision

        st = LifecycleService.transition(
            project_dir=proj_dir,
            target_state=LifecycleState.FAILED,
            reason=reason,
            expected_revision=current_revision,
        )
        current_revision = st.revision

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
            if not run_script(logger, "assets", "asset_gate", "gates/asset_gate.py", IdempotencyClass.SAFE_TO_RETRY, project_id):
                mark_failed()
                sys.exit(1)
            save_state(LifecycleState.ASSETS_READY, [("02_asset_manifest.json", ValidationLevel.EXISTS)])
            next_state = LifecycleState.ASSETS_READY

        # 2. ASSETS_READY -> PLAN_READY
        elif next_state == LifecycleState.ASSETS_READY:
            print(f"\n➔ الانتقال من ASSETS_READY إلى PLAN_READY:")
            if not run_script(logger, "plan", "plan_gate", "gates/plan_gate.py", IdempotencyClass.SAFE_TO_RETRY, project_id):
                mark_failed()
                sys.exit(1)
            plan_file = proj_dir / "master_plan.md"
            if not run_script(logger, "plan", "taste_gate", "gates/taste_gate.py", IdempotencyClass.SAFE_TO_RETRY, str(plan_file)):
                mark_failed()
                sys.exit(1)
            save_state(LifecycleState.PLAN_READY, [("master_plan.md", ValidationLevel.SHA256)])
            next_state = LifecycleState.PLAN_READY

        # 3. PLAN_READY -> BLUEPRINT_READY
        elif next_state == LifecycleState.PLAN_READY:
            print(f"\n➔ الانتقال من PLAN_READY إلى BLUEPRINT_READY:")
            blueprint_file = proj_dir / "05_blueprint.json"
            if not run_script(logger, "blueprint", "validate_blueprint", "gates/validate_blueprint.py", IdempotencyClass.SAFE_TO_RETRY, str(blueprint_file)):
                mark_failed()
                sys.exit(1)
            if not run_script(logger, "blueprint", "motion_validator", "gates/motion_validator.py", IdempotencyClass.SAFE_TO_RETRY, str(blueprint_file)):
                mark_failed()
                sys.exit(1)
            if not run_script(logger, "blueprint", "code_template_gate", "gates/code_template_gate.py", IdempotencyClass.SAFE_TO_RETRY, project_id):
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
            if not run_script(logger, "blueprint", "materialize_project", "generators/materialize_project.py", IdempotencyClass.SAFE_TO_RETRY, str(proj_dir)):
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
            if not run_script(logger, "qc", "probe_qc", "gates/probe_qc.py", IdempotencyClass.SAFE_TO_RETRY, project_id):
                mark_failed()
                sys.exit(1)
            save_state(LifecycleState.PROBE_PASSED, [
                ("master_plan.md", ValidationLevel.SHA256),
                ("05_blueprint.json", ValidationLevel.SHA256),
                ("probe_qc_report.json", ValidationLevel.SHA256),
                ("contact_sheet.png", ValidationLevel.SHA256),
            ])
            next_state = LifecycleState.PROBE_PASSED

        # 6. PROBE_PASSED -> AWAITING_REVIEW
        elif next_state == LifecycleState.PROBE_PASSED:
            print(f"\n➔ الانتقال التلقائي لانتظار المراجعة (AWAITING_REVIEW)...")
            save_state(LifecycleState.AWAITING_REVIEW, [])
            next_state = LifecycleState.AWAITING_REVIEW

        # 7. AWAITING_REVIEW -> REVIEW_APPROVED
        elif next_state == LifecycleState.AWAITING_REVIEW:
            from scripts.core.review_service import ReviewService, ReviewDecisionType, create_local_trusted_principal
            state = StateStore.load(proj_dir)
            active_bundle = state.get_active_review_bundle() if state else None
            active_decision = state.get_active_review_decision() if state else None

            # Auto-create bundle if not yet created so reviewer has snapshot ready
            if not active_bundle or active_bundle.status != "ACTIVE":
                try:
                    active_bundle = ReviewService.create_review_bundle(proj_dir)
                    print(f"📦 تم إنشاء حزمة المراجعة: {active_bundle.review_bundle_id}")
                except Exception as e:
                    print(f"⚠️ تعذر إنشاء حزمة المراجعة: {e}")

            if active_decision and active_decision.decision == ReviewDecisionType.APPROVED:
                print(f"\n✅ تم التحقق من اعتماد المراجعة الرسمي ({active_decision.decision_id}). ننتقل لـ REVIEW_APPROVED.")
                next_state = LifecycleState.REVIEW_APPROVED
            else:
                approved_marker = proj_dir / ".studio_approved"
                if approved_marker.exists() and active_bundle and active_bundle.status == "ACTIVE":
                    try:
                        principal = create_local_trusted_principal("local_studio_reviewer")
                        active_decision = ReviewService.approve(
                            proj_dir,
                            active_bundle.review_bundle_id,
                            principal=principal,
                            reason="Approved via local studio session"
                        )
                        current_revision = active_decision.state_revision
                        print(f"\n✅ تم توثيق الاعتماد البشري عبر ReviewService ({active_decision.decision_id}). ننتقل لـ REVIEW_APPROVED.")
                        next_state = LifecycleState.REVIEW_APPROVED
                    except Exception as e:
                        print(f"\n❌ فشل توثيق الاعتماد البشري: {e}")
                        sys.exit(1)
                else:
                    print(f"\n⏸️ المنسق متوقف مؤقتاً.")
                    print(f"المشروع جاهز للمعاينة في الاستوديو (AWAITING_REVIEW).")
                    print(f"حزمة المراجعة: {active_bundle.review_bundle_id if active_bundle else 'N/A'}")
                    print(f"يرجى مراجعة الفيديو وإنشاء ملف .studio_approved أو اعتماد حزمة المراجعة عبر ReviewService قبل الرندر النهائي.")
                    sys.exit(0)

        # 8. REVIEW_APPROVED -> RENDERED
        elif next_state == LifecycleState.REVIEW_APPROVED:
            print(f"\n➔ الانتقال من REVIEW_APPROVED إلى RENDERED (الرندر النهائي):")
            from scripts.core.review_service import assert_render_authorized, RenderNotAuthorizedError
            try:
                assert_render_authorized(proj_dir)
            except RenderNotAuthorizedError as e:
                print(f"\n🛑 [GUARDIAN BLOCK] ممنوع الرندر: {e}")
                mark_failed()
                sys.exit(1)
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
            if not run_script(logger, "qc", "final_qc", "gates/final_qc.py", IdempotencyClass.SAFE_TO_RETRY, project_id):
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
    if execution_lock is not None:
        execution_lock.release()

if __name__ == "__main__":
    main()
