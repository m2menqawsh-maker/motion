import pytest
from pathlib import Path
from scripts.path_security import validate_project_id, safe_resolve

def test_validate_project_id_valid():
    assert validate_project_id("valid-project_123") == "valid-project_123"
    assert validate_project_id("demo_brand") == "demo_brand"

def test_validate_project_id_invalid():
    with pytest.raises(ValueError, match="Invalid project_id"):
        validate_project_id("../demo_brand")
    with pytest.raises(ValueError, match="Invalid project_id"):
        validate_project_id("demo brand")
    with pytest.raises(ValueError, match="Invalid project_id"):
        validate_project_id("my-project/foo")

def test_safe_resolve_valid(tmp_path):
    # tmp_path is a pytest fixture that provides a temporary directory
    base = tmp_path / "projects"
    base.mkdir()
    
    # Resolving a valid sub-path
    resolved = safe_resolve(base, "my-project")
    assert resolved == base / "my-project"

def test_safe_resolve_traversal(tmp_path):
    base = tmp_path / "projects"
    base.mkdir()
    
    with pytest.raises(ValueError, match="Path traversal detected"):
        safe_resolve(base, "../my-project")
        
    with pytest.raises(ValueError, match="Path traversal detected"):
        safe_resolve(base, "../../etc/passwd")

def test_safe_resolve_absolute(tmp_path):
    base = tmp_path / "projects"
    base.mkdir()
    
    # Absolute path traversal (both Windows and Unix)
    with pytest.raises(ValueError, match="Path traversal detected"):
        safe_resolve(base, "C:\\Windows\\System32")
    with pytest.raises(ValueError, match="Path traversal detected"):
        safe_resolve(base, "/etc/passwd")
