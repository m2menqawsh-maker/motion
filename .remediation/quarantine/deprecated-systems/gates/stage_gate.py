import subprocess
from scripts.security import safe_subprocess
import sys
from scripts.path_security import validate_project_id, safe_resolve
import json
from pathlib import Path

def main():
    if len(sys.argv) < 3:
        sys.exit(1)
        
    project_dir = Path(sys.argv[1])
    action = sys.argv[2]
    
    state_file = project_dir / "state.json"
    state = {"current_stage": 0, "stages": {}}
    if state_file.exists():
        state = json.loads(state_file.read_text())
        
    stage = "0"
    if len(sys.argv) > 3:
        stage = sys.argv[3]

    if action == "start":
        if stage == "1" and state.get("stages", {}).get("1", {}).get("status") != "approved":
            print("Cannot start stage 1 without approval")
            sys.exit(1)
        state["current_stage"] = int(stage)
        state["stages"][stage] = {"status": "running"}
        print(f"Stage started for {project_dir}")
    elif action == "finish":
        state["current_stage"] = int(stage)
        state["stages"][stage] = {"status": "finished"}
        print(f"Stage finished for {project_dir}")
    elif action == "approve":
        if stage not in ["0", "1", "2", "3"]:
            sys.exit(1)
        state["stages"][stage] = {"status": "approved"}
        print(f"Gate approved for {project_dir}")
    elif action == "reject":
        state["stages"][stage] = {"status": "rejected"}
        print(f"Gate rejected for {project_dir}")
    else:
        sys.exit(1)
        
    state_file.write_text(json.dumps(state))
    sys.exit(0)

if __name__ == "__main__":
    main()
