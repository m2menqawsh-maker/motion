import subprocess
from pathlib import Path

def create_project(name: str, aspect: str, fps: int, language: str) -> str:
    cmd = [
        "python", "scripts/scaffold_project.py",
        "--name", name,
        "--aspect", aspect,
        "--fps", str(fps),
        "--language", language
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        raise Exception(f"Failed to create project: {result.stderr}")
    return result.stdout.strip()
