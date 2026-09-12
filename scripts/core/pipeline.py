import json
import shutil
import subprocess
from pathlib import Path
from .gates import ProjectGates, calculate_deep_hash, GateViolation

class UnifiedPipeline:
    def __init__(self, project_id: str):
        self.project_id = project_id
        self.project_dir = Path(f"projects/{project_id}")
        self.build_dir = self.project_dir / "06_build"
        self.gates = ProjectGates(project_id)
        
    def prep_and_materialize(self) -> dict:
        """Prepares the project for preview/render by locking dependencies and generating a Deep Hash"""
        self.gates.verify_plan_exists()
        bp_data = self.gates.verify_blueprint_schema()
        
        # In a real app we'd copy assets to build_dir/public/media here
        public_media = self.build_dir / "public" / "media"
        public_media.mkdir(parents=True, exist_ok=True)
        
        # Fake copy logic: just touch a manifest to simulate it
        if (self.project_dir / "02_asset_manifest.json").exists():
            shutil.copy2(self.project_dir / "02_asset_manifest.json", self.build_dir / "manifest.json")
            
        # Calculate Hash AFTER assets are supposedly prepared
        deep_hash = calculate_deep_hash(self.project_id, bp_data, self.build_dir)
        
        # Save a metadata file for the current prep state
        prep_info = {
            "version": bp_data.get("version", "1.0"),
            "hash": deep_hash,
            "status": "prepared_for_preview"
        }
        (self.project_dir / ".prep_state.json").write_text(json.dumps(prep_info, indent=2), encoding="utf-8")
        
        return prep_info
        
    def approve(self):
        """Creates the .studio_approved stamp with the exact hash of the current prep state"""
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
        current_hash = calculate_deep_hash(self.project_id, bp_data, self.build_dir)
        
        if current_hash != approved_hash:
            # Delete approval file since it's invalidated
            approval_file.unlink(missing_ok=True)
            raise GateViolation("APPROVAL_INVALIDATED", "لا يمكن التصدير: تم تعديل المشروع/الأصول بعد الموافقة", "أعد التحضير والمعاينة والموافقة على النسخة الجديدة")
            
        # Success! Trigger Remotion Render
        try:
            # For this test environment we might not have remotion set up fully, so we simulate it or run npm build
            # The test says "Check exit codes", so let's run the npm run build command from workspace root
            # with env vars.
            import os
            env = os.environ.copy()
            env["PROJECT_ID"] = self.project_id
            
            # Using npm run build which calls "remotion render remotion-app/src/index.ts BlueprintVideo out/video.mp4"
            # But the path needs to output to projects/{id}/06_build/video.mp4
            out_file = self.build_dir / "video.mp4"
            result = subprocess.run(
                ["npx", "remotion", "render", "remotion-app/src/index.ts", "BlueprintVideo", str(out_file)],
                env=env,
                check=True,
                capture_output=True,
                text=True
            )
            return {"status": "success", "output": str(out_file), "log": result.stdout}
        except subprocess.CalledProcessError as e:
            raise Exception(f"Remotion render failed: {e.stderr}")
