import pytest
from scripts.path_security import validate_project_id, safe_resolve
from pathlib import Path

class TestPathTraversal:
    """حماية من Path Traversal"""
    
    def test_valid_project_ids_accepted(self):
        """project_id الصالح يجب أن يُقبل"""
        valid_ids = [
            "my-project",
            "project_123",
            "ABC",
            "test-project-001",
            "a" * 50,  # طويل لكن صالح
        ]
        
        for id in valid_ids:
            # Should not raise exception
            assert validate_project_id(id) == id, f"{id} يجب أن يُقبل"
    
    def test_path_traversal_rejected(self):
        """هجمات Path Traversal يجب أن تُرفض"""
        malicious_ids = [
            "../etc/passwd",
            "../../etc/passwd",
            "..\\..\\etc\\passwd",
            "project/foo",
            "project\\foo",
            "project bar",  # مسافات (if not allowed by validate_project_id regex)
            "project;rm -rf /",  # حقن أوامر
            "project$(whoami)",  # حقن أوامر
            "project`id`",  # حقن أوامر
            "%2e%2e%2fetc%2fpasswd",
        ]
        
        for id in malicious_ids:
            with pytest.raises(ValueError):
                validate_project_id(id)
    
    def test_safe_resolve_prevents_escape(self):
        """safe_resolve يجب أن يمنع الخروج من المجلد الجذر"""
        base_dir = Path("/tmp/test-project").resolve()
        
        # مسارات صالحة
        valid_paths = [
            "projects/test/file.txt",
            "projects/test/subdir/file.txt",
        ]
        
        for path in valid_paths:
            resolved = safe_resolve(base_dir, path)
            assert str(resolved).startswith(str(base_dir))
        
        # مسارات خبيثة
        malicious_paths = [
            "../etc/passwd",
            "../../etc/passwd",
            "/etc/passwd",  # مسار مطلق
            "..\\..\\Windows\\System32",
        ]
        
        for path in malicious_paths:
            with pytest.raises(ValueError):
                safe_resolve(base_dir, path)
    
    def test_symlink_attacks_blocked(self, tmp_path):
        """هجمات Symlink يجب أن تُحظر"""
        base_dir = tmp_path / "base"
        base_dir.mkdir()
        
        # Create a file outside the base dir
        secret_file = tmp_path / "secret.txt"
        secret_file.write_text("top secret")
        
        # Create a symlink inside base_dir pointing outside
        symlink_path = base_dir / "malicious_link"
        try:
            # On Windows, symlink creation might require admin privileges or Developer Mode.
            import os
            os.symlink(str(secret_file), str(symlink_path))
        except OSError:
            pytest.skip("لا توجد صلاحيات لإنشاء Symlink (Windows)")
            
        with pytest.raises(ValueError):
            safe_resolve(base_dir, "malicious_link")
