import ast
from pathlib import Path
import pytest
from unittest.mock import patch
from scripts.security import safe_subprocess

class TestSubprocessSecurity:
    """أمان الـ Subprocess"""
    
    def test_no_direct_subprocess_calls(self):
        """لا يسمح باستخدام subprocess مباشرة"""
        base_dir = Path(__file__).parent.parent.parent
        
        python_files = []
        if (base_dir / "api").exists():
            python_files.extend((base_dir / "api").rglob("*.py"))
        if (base_dir / "scripts").exists():
            python_files.extend((base_dir / "scripts").rglob("*.py"))
        
        allowed_files = {
            str(base_dir / "scripts" / "security.py"), 
            str(base_dir / "scripts" / "path_security.py"),
            str(base_dir / "scripts" / "benchmark_guards.py")
        }
        
        for file in python_files:
            if str(file) in allowed_files:
                continue
            
            try:
                tree = ast.parse(file.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
                
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute):
                    if isinstance(node.value, ast.Name):
                        if node.value.id == "subprocess":
                            if node.attr in {"run", "call", "Popen", "check_output"}:
                                pytest.fail(f"{file} uses direct subprocess.{node.attr}")
                                
    def test_no_os_system_calls(self):
        """لا يسمح باستخدام os.system"""
        base_dir = Path(__file__).parent.parent.parent
        python_files = list(base_dir.rglob("*.py"))
        
        for file in python_files:
            if "node_modules" in file.parts or ".venv" in file.parts or ".pytest_cache" in file.parts:
                continue
                
            try:
                tree = ast.parse(file.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
                
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute):
                    if isinstance(node.value, ast.Name):
                        if node.value.id == "os" and node.attr == "system":
                            pytest.fail(f"{file} uses os.system")
                            
    @patch('scripts.security.subprocess.run')
    def test_safe_subprocess_forces_shell_false(self, mock_run):
        """يجب أن يجبر safe_subprocess shell=False حتى لو تم طلب True"""
        # Call with shell=True explicitly
        safe_subprocess(["ffmpeg", "-version"], shell=True)
        
        # Verify it was forced to False
        mock_run.assert_called_once()
        _, kwargs = mock_run.call_args
        assert kwargs.get('shell') is False, "Security guard MUST force shell=False"
        
    @patch('scripts.security.subprocess.run')
    def test_safe_subprocess_enforces_timeout(self, mock_run):
        """يجب أن يحقن timeout افتراضي إذا لم يتم توفيره"""
        # Call without timeout
        safe_subprocess(["ffmpeg", "-version"])
        
        # Verify timeout was injected
        mock_run.assert_called_once()
        _, kwargs = mock_run.call_args
        assert kwargs.get('timeout') is not None, "Security guard MUST enforce timeout"
        assert kwargs['timeout'] > 0
