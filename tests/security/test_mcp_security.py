import pytest
from pathlib import Path
import json

class TestMCPSecurity:
    """أمان MCP Servers"""
    
    def test_no_execute_command_tools(self):
        """لا يسمح بأدوات تنفيذ أوامر في MCP"""
        # We need to find the MCP servers directory
        base_dir = Path(__file__).parent.parent.parent
        mcp_servers_dir = base_dir / ".agents" / "plugins" / "super-video-maker-plugin" / "mcp"
        if not mcp_servers_dir.exists():
            # If the specific plugin is not found, maybe search the whole project
            pass
            
        for py_file in base_dir.rglob("*.py"):
            # Limit search to mcp directories
            if "mcp" not in str(py_file).lower():
                continue
                
            try:
                # Exclude virtual environments and node_modules
                if ".venv" in py_file.parts or "node_modules" in py_file.parts:
                    continue
                    
                content = py_file.read_text(encoding="utf-8")
                # Exclude this test file itself
                if "test_mcp_security.py" in str(py_file):
                    continue
                    
                if "execute_command" in content or "run_shell" in content:
                    pytest.fail(f"{py_file} يحتوي على أداة تنفيذ أوامر ('execute_command' أو 'run_shell') وهذا ممنوع!")
            except Exception:
                pass
