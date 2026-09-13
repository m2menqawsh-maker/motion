#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

def main():
    print("🐳 Building clean-video-builder Docker Image...")
    workspace = Path(__file__).resolve().parent.parent
    dockerfile_path = workspace / ".agents" / "docker" / "Dockerfile.remotion"
    
    if not dockerfile_path.exists():
        print(f"❌ Error: Dockerfile not found at {dockerfile_path}")
        sys.exit(1)
        
    cmd = ["docker", "build", "-t", "clean-video-builder", "-f", str(dockerfile_path), "."]
    proc = subprocess.run(cmd, cwd=str(workspace))
    if proc.returncode == 0:
        print("✅ Docker Image built successfully.")
    else:
        print("❌ Docker build failed.")
        sys.exit(proc.returncode)

if __name__ == "__main__":
    main()
