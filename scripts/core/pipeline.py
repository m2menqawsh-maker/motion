import json
import os
import shutil
import subprocess
from pathlib import Path
from .gates import ProjectGates, calculate_deep_hash, GateViolation

class UnifiedPipeline:
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.project_dir = Path(f"projects/{project_id}")
        self.build_dir = self.project_dir # Fallback for old references
        self.gates = ProjectGates(project_id)
        
    def prep_and_materialize(self) -> dict:
        """Prepares the project for preview/render by locking dependencies and generating a Deep Hash"""
        self.gates.verify_plan_exists()
        bp_data = self.gates.verify_blueprint_schema()
        
        deep_hash = calculate_deep_hash(self.project_id, bp_data, self.project_dir)
        
        # Save a metadata file for the current prep state
        prep_info = {
            "version": bp_data.get("version", "1.0"),
            "hash": deep_hash,
            "status": "prepared_for_preview"
        }
        (self.project_dir / ".prep_state.json").write_text(json.dumps(prep_info, indent=2), encoding="utf-8")
        
        return prep_info
        
    def approve(self, test_mode: bool = False):
        """Creates the .studio_approved stamp with the exact hash of the current prep state"""
        if test_mode and not os.environ.get("TESTING"):
            raise RuntimeError("test_mode=True is only allowed in test environments (TESTING=1)")
        if not test_mode and not (self.project_dir / ".studio_unlocked").exists():
            raise RuntimeError("approve() without test_mode must be manual via Studio. No .studio_unlocked found.")
            
        prep_file = self.project_dir / ".prep_state.json"
        if not prep_file.exists():
            raise Exception("Cannot approve before materializing/prepping.")
            
        prep_info = json.loads(prep_file.read_text(encoding="utf-8"))
        
        approval_data = {
            "approved_hash": prep_info["hash"],
            "timestamp": "now" # In real code, use ISO datetime
        }
        (self.project_dir / ".studio_approved").write_text(json.dumps(approval_data, indent=2), encoding="utf-8")
        return approval_data

    def render(self):
        """Final render gate - validates that the current state exactly matches the approved state"""
        approval_file = self.project_dir / ".studio_approved"
        if not approval_file.exists():
            raise GateViolation("NOT_APPROVED", "لا يمكن التصدير: لم يتم إصدار موافقة بشرية على المشروع", "استخدم نقطة المعاينة والموافقة أولاً")
            
        approval_data = json.loads(approval_file.read_text(encoding="utf-8"))
        approved_hash = approval_data.get("approved_hash")
        
        # Verify if the blueprint is valid before render
        bp_data = self.gates.verify_blueprint_schema()
        
        # Recalculate hash of current real state
        current_hash = calculate_deep_hash(self.project_id, bp_data, self.project_dir)
        
        if current_hash != approved_hash:
            approval_file.unlink(missing_ok=True)
            raise GateViolation("APPROVAL_INVALIDATED", "لا يمكن التصدير: تم تعديل المشروع/الأصول بعد الموافقة", "أعد التحضير والمعاينة والموافقة على النسخة الجديدة")
            
        # Success! Trigger Remotion Render
        try:
            import os
            env = os.environ.copy()
            env["PROJECT_ID"] = self.project_id
            
            workspace_root = Path.cwd().resolve()
            out_file = self.project_dir / "out.mp4"
            npx_cmd = "npx.cmd" if os.name == "nt" else "npx"
            engine_dir = workspace_root / "remotion-app"
            
            props_file = self.project_dir / "render_props.json"
            props_file_abs = workspace_root / props_file
            
            def safe_load(name, default):
                p = self.project_dir / name
                return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default
                
            combined_props = {
                "projectData": {
                    "project": safe_load("project.json", {"fps": 30, "title": "Video"}),
                    "blueprint": bp_data,
                    "brand": safe_load("brand.json", {"colors": {}, "fonts": {}}),
                    "overrides": safe_load("overrides.json", {"scenes": {}})
                }
            }
            props_file.write_text(json.dumps(combined_props, ensure_ascii=False), encoding="utf-8")
            
            result = subprocess.run(
                [npx_cmd, "remotion", "render", "src/index.ts", "BlueprintVideo", str(out_file), "--props", str(props_file_abs)],
                env=env,
                cwd=str(engine_dir),
                check=True,
                capture_output=True,
                text=True
            )
            print(result.stdout)
            return {"status": "success", "output": str(out_file), "log": result.stdout}
        except subprocess.CalledProcessError as e:
            raise Exception(f"Remotion render failed: {e.stderr}")
