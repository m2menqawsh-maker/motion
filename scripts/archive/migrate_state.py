import json
from pathlib import Path
import sys

def migrate_project(project_id: str):
    print(f"Migrating state for project: {project_id}")
    project_dir = Path(f"projects/{project_id}")
    if not project_dir.exists():
        print(f"Project directory {project_dir} does not exist.")
        return

    old_state_path = project_dir / "state.json"
    new_state_path = project_dir / ".pipeline_state.json"
    
    if old_state_path.exists():
        try:
            # Read old state.json
            old_state = json.loads(old_state_path.read_text(encoding="utf-8"))
            
            # Map numbered gates -> named gates
            gate_mapping = {
                "1": "asset_gate",
                "2": "plan_gate",
                "3": "taste_gate"
            }
            
            current_old = str(old_state.get("current_stage", "1"))
            
            # Create legacy_gui_state
            legacy_state = {
                "current_stage": gate_mapping.get(current_old, "asset_gate"),
                "status": old_state.get("status", "started"),
                "approved_by": old_state.get("approved_by"),
                "timestamp": old_state.get("timestamp")
            }
            
            # Merge with existing .pipeline_state.json
            new_state = {}
            if new_state_path.exists():
                try:
                    new_state = json.loads(new_state_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    pass
            
            new_state["legacy_gui_state"] = legacy_state
            
            # Write new state
            new_state_path.write_text(json.dumps(new_state, indent=2, ensure_ascii=False), encoding="utf-8")
            
            # Archive old state
            old_state_path.rename(old_state_path.with_suffix(".json.deprecated"))
            print(f"✅ Successfully migrated state for {project_id}")
        except Exception as e:
            print(f"❌ Failed to migrate state for {project_id}: {e}")
    else:
        print(f"No state.json found for {project_id}, nothing to migrate.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        migrate_project(sys.argv[1])
    else:
        # Migrate all projects
        projects_dir = Path("projects")
        if projects_dir.exists():
            for proj in projects_dir.iterdir():
                if proj.is_dir():
                    migrate_project(proj.name)
