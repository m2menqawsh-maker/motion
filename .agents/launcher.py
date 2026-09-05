#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Launcher script to run plugin scripts centrally.
Usage: python .agents/launcher.py <script_name> [args...]
"""
import sys
import subprocess
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("Usage: python .agents/launcher.py <script_name> [args...]")
        sys.exit(1)
        
    script_name = sys.argv[1]
    if not script_name.endswith(".py"):
        script_name += ".py"
        
    plugin_scripts_dir = Path(__file__).resolve().parent / "plugins" / "super-video-maker-plugin" / "scripts"
    target_script = plugin_scripts_dir / script_name
    
    if not target_script.exists():
        print(f"❌ Script not found: {target_script}")
        sys.exit(1)
        
    cmd = [sys.executable, str(target_script)] + sys.argv[2:]
    
    try:
        result = subprocess.run(cmd)
        sys.exit(result.returncode)
    except KeyboardInterrupt:
        sys.exit(130)

if __name__ == "__main__":
    main()
