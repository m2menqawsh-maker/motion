import ast
from pathlib import Path
import pytest

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
        
        # استثناء الملفات المسموحة
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
                # ابحث عن: subprocess.run, subprocess.call, subprocess.Popen
                if isinstance(node, ast.Attribute):
                    if isinstance(node.value, ast.Name):
                        if node.value.id == "subprocess":
                            if node.attr in {"run", "call", "Popen", "check_output"}:
                                pytest.fail(
                                    f"{file} يستخدم subprocess.{node.attr} مباشرة — "
                                    f"استخدم safe_subprocess بدلاً من ذلك"
                                )
                                
    def test_no_os_system_calls(self):
        """لا يسمح باستخدام os.system"""
        base_dir = Path(__file__).parent.parent.parent
        python_files = list(base_dir.rglob("*.py"))
        
        for file in python_files:
            # We skip third-party or test libraries if needed, but since it's our own code:
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
                            pytest.fail(f"{file} يستخدم os.system — ممنوع!")
                            
    def test_no_shell_true(self):
        """لا يسمح باستخدام shell=True"""
        base_dir = Path(__file__).parent.parent.parent
        python_files = []
        if (base_dir / "api").exists():
            python_files.extend((base_dir / "api").rglob("*.py"))
        if (base_dir / "scripts").exists():
            python_files.extend((base_dir / "scripts").rglob("*.py"))
        
        for file in python_files:
            try:
                content = file.read_text(encoding="utf-8")
            except Exception:
                continue
                
            # A simple textual check
            if "shell=True" in content.replace(" ", ""):
                pytest.fail(f"{file} يستخدم shell=True — ممنوع!")
                
    def test_timeout_enforced_in_safe_subprocess(self):
        """safe_subprocess يجب أن يفرض timeout"""
        from scripts.security import safe_subprocess
        import inspect
        
        source = inspect.getsource(safe_subprocess)
        assert "timeout" in source, "safe_subprocess يجب أن يفرض timeout"
