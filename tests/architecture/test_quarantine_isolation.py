import ast
import pytest
from pathlib import Path

def get_python_files():
    base_dir = Path(__file__).parent.parent.parent
    files = []
    
    api_dir = base_dir / "api"
    if api_dir.exists():
        files.extend(api_dir.rglob("*.py"))
        
    scripts_dir = base_dir / "scripts"
    if scripts_dir.exists():
        files.extend(scripts_dir.rglob("*.py"))
        
    return [f for f in files if "tests" not in f.parts and ".remediation" not in f.parts]

def test_no_quarantine_imports():
    """لا يسمح باستيراد أي شيء من مجلد العزل (.remediation/quarantine)"""
    python_files = get_python_files()
    
    for file in python_files:
        try:
            content = file.read_text(encoding="utf-8")
            if "quarantine" not in content and ".remediation" not in content:
                continue
                
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and ("quarantine" in node.module or "remediation" in node.module):
                        pytest.fail(f"{file} يستورد من العزل — ممنوع!")
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if "quarantine" in alias.name or "remediation" in alias.name:
                            pytest.fail(f"{file} يستورد من العزل — ممنوع!")
        except SyntaxError:
            pass
