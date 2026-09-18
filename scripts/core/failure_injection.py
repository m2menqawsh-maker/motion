import os
import sys

class InjectionPoint:
    BEFORE_ASSETS = "before_assets"
    AFTER_ASSETS = "after_assets"
    BEFORE_PLAN = "before_plan"
    AFTER_PLAN = "after_plan"
    BEFORE_RENDER = "before_render"
    DURING_RENDER = "during_render"
    AFTER_RENDER = "after_render"
    BEFORE_QC = "before_qc"
    
    _ALL = {
        BEFORE_ASSETS, AFTER_ASSETS,
        BEFORE_PLAN, AFTER_PLAN,
        BEFORE_RENDER, DURING_RENDER, AFTER_RENDER,
        BEFORE_QC
    }

class FailureInjector:
    
    @staticmethod
    def enabled() -> bool:
        # Safeguard 1: Must explicitly have AGY_FAILURE_INJECTION_ENABLED
        if os.environ.get("AGY_FAILURE_INJECTION_ENABLED") != "1":
            return False
            
        # Safeguard 2: Must explicitly specify a scenario
        if not os.environ.get("AGY_INJECT_FAILURE"):
            return False
            
        # Safeguard 3: Environment cannot be production
        env = os.environ.get("AGY_ENV", "dev").lower()
        if env == "production":
            print("SECURITY_ERROR: FAILURE_INJECTION_FORBIDDEN in production!")
            sys.exit(1)
            
        return True
        
    @staticmethod
    def maybe_inject(point: str, context: dict = None, attempt: int = 1) -> None:
        if not FailureInjector.enabled():
            return
            
        if point not in InjectionPoint._ALL:
            raise ValueError(f"Unknown injection point: {point}")
            
        scenario_str = os.environ.get("AGY_INJECT_FAILURE", "")
        parts = scenario_str.split(":")
        scenario = parts[0]
        
        target_attempt = None
        if len(parts) > 1:
            if parts[1] == "first_attempt":
                target_attempt = 1
            elif parts[1].startswith("attempt="):
                target_attempt = int(parts[1].split("=")[1])
                
        # If target attempt is specified and does not match, skip
        if target_attempt is not None and attempt != target_attempt:
            return
            
        # Perform injections based on scenario and point
        if scenario == "render_timeout" and point == InjectionPoint.DURING_RENDER:
            print(f"⚠️ [FailureInjector] Injecting render_timeout at attempt {attempt}!")
            # In a real timeout, the subprocess would return a specific error or raise.
            # We simulate a timeout soft crash by raising a system exit with a code that our 
            # wrapper might see as failure, or we can just raise a specific exception.
            # But the requirement says "soft_crash -> raise/SystemExit"
            # Or we can just raise an exception that gets caught and converted to FailureInfo.
            raise TimeoutError("Injected Render Timeout")
            
        if scenario == "pipeline_crash_before_plan" and point == InjectionPoint.BEFORE_PLAN:
            print("⚠️ [FailureInjector] Injecting soft pipeline_crash_before_plan!")
            sys.exit(1)
            
        if scenario == "hard_crash_after_plan" and point == InjectionPoint.AFTER_PLAN:
            print("⚠️ [FailureInjector] Injecting hard crash after plan!")
            os._exit(1)
            
        if scenario == "checkpoint_missing_artifact" and point == InjectionPoint.AFTER_RENDER:
            print("⚠️ [FailureInjector] Injecting missing artifact in checkpoint (deleting out.mp4)!")
            try:
                os.remove("projects/test_proj/out.mp4")
            except OSError:
                pass
