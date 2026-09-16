import os
import sys
import json
import subprocess
from pathlib import Path
import pytest
from scripts.security import safe_subprocess

GUARDIAN_DIR = Path("c:/video/clean-video-workspace/.agents/guardian")

def check_command(cmd_str: str) -> bool:
    if not GUARDIAN_DIR.exists():
        return True # Skip if guardian is not installed
    data = {
        "toolCall": {
            "name": "run_command",
            "args": {"CommandLine": cmd_str}
        }
    }
    result = subprocess.run(
        [sys.executable, str(GUARDIAN_DIR / "command_guard.py")],
        input=json.dumps(data),
        text=True,
        capture_output=True,
        cwd=str(GUARDIAN_DIR.parent.parent)
    )
    try:
        out = json.loads(result.stdout)
        return out.get("decision") == "allow"
    except json.JSONDecodeError:
        return False

class TestGuardianAndSecurity:
    
    # 1. MCP Guardian Checks
    def test_mcp_allowed_safe_command(self):
        if GUARDIAN_DIR.exists():
            assert check_command("python scripts/pipeline.py project_1") is True

    def test_mcp_forbidden_arbitrary_command(self):
        if GUARDIAN_DIR.exists():
            assert check_command("npm install unknown-malicious-package") is False

    def test_mcp_shell_chaining(self):
        if GUARDIAN_DIR.exists():
            assert check_command("python scripts/pipeline.py && echo Hacked") is False
            assert check_command("python scripts/pipeline.py ; rm -rf /") is False
            assert check_command("echo test | grep t") is False

    def test_mcp_direct_bypass_attempt(self):
        if GUARDIAN_DIR.exists():
            assert check_command("python scripts/render_project.py") is False
            assert check_command("python scripts/asset_gate.py") is False

    # 2. Python safe_subprocess Checks (The actual Runtime Guard)
    def test_safe_subprocess_rejects_arbitrary_commands(self):
        with pytest.raises(PermissionError, match="Command not allowed"):
            safe_subprocess(["echo", "Hello"])
            
        with pytest.raises(PermissionError, match="Command not allowed"):
            safe_subprocess(["git", "status"])
            
    def test_safe_subprocess_rejects_unauthorized_scripts(self):
        with pytest.raises(PermissionError, match="Command not allowed"):
            safe_subprocess(["python", "some_random_script.py"])
            
        with pytest.raises(PermissionError, match="Command not allowed"):
            safe_subprocess(["python", "scripts/fake_gate.py"])

    def test_safe_subprocess_allows_authorized_scripts(self):
        # We use a mock so we don't actually run it during testing
        from unittest.mock import patch
        with patch('scripts.security.subprocess.run') as mock_run:
            safe_subprocess(["python", "scripts/pipeline.py", "proj_1"])
            mock_run.assert_called_once()
            
            safe_subprocess(["npm", "run", "build"])
            assert mock_run.call_count == 2
