import subprocess
import json
from pathlib import Path

def run_gate_command(project_id: str, *args) -> dict:
    project_dir = Path(f"projects/{project_id}")
    cmd = ["python", "scripts/gates/stage_gate.py", str(project_dir)] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    return {
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr
    }

def get_status(project_id: str) -> dict:
    state_path = Path(f"projects/{project_id}/state.json")
    if not state_path.exists():
        return {}
    return json.loads(state_path.read_text(encoding="utf-8"))

def start_stage(project_id: str, stage: int) -> dict:
    return run_gate_command(project_id, "start", str(stage))

def finish_stage(project_id: str, stage: int) -> dict:
    return run_gate_command(project_id, "finish", str(stage))

def approve_gate(project_id: str, gate: int, by: str = "gui") -> dict:
    return run_gate_command(project_id, "approve", str(gate), by)

def reject_gate(project_id: str, gate: int, by: str, note: str) -> dict:
    return run_gate_command(project_id, "reject", str(gate), by, note)
