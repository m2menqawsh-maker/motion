from scripts.path_security import validate_project_id
import subprocess
from scripts.security import safe_subprocess
from pathlib import Path

def create_project(name: str, aspect: str, fps: int, language: str) -> str:
    cmd = [
        "python", "scripts/scaffold_project.py",
        "--name", name,
        "--aspect", aspect,
        "--fps", str(fps),
        "--language", language
    ]
    result = safe_subprocess(cmd, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        raise Exception(f"Failed to create project: {result.stderr}")
    return result.stdout.strip()
