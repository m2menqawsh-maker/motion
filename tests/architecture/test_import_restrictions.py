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

def test_no_legacy_gates_imports():
    """يمنع استيراد بوابات النظام القديم (مثل plan_gate, stage_gate)"""
    python_files = get_python_files()
    legacy_gates = {"plan_gate", "stage_gate", "code_template_gate"}
    
    for file in python_files:
        try:
            content = file.read_text(encoding="utf-8")
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and any(gate in node.module for gate in legacy_gates):
                        pytest.fail(f"{file} يستورد بوابة قديمة {node.module} — ممنوع!")
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if any(gate in alias.name for gate in legacy_gates):
                            pytest.fail(f"{file} يستورد بوابة قديمة {alias.name} — ممنوع!")
        except SyntaxError:
            pass
