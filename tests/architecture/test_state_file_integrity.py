import ast
import pytest
from pathlib import Path

def get_python_files():
    """Return all non-test python files in api/ and scripts/"""
    base_dir = Path(__file__).parent.parent.parent
    files = []
    
    api_dir = base_dir / "api"
    if api_dir.exists():
        files.extend(api_dir.rglob("*.py"))
        
    scripts_dir = base_dir / "scripts"
    if scripts_dir.exists():
        files.extend(scripts_dir.rglob("*.py"))
        
    return [f for f in files if "tests" not in f.parts and ".remediation" not in f.parts]

def test_no_state_json_writes():
    """لا يسمح لأي ملف بكتابة state.json القديم"""
    python_files = get_python_files()
    
    for file in python_files:
        try:
            content = file.read_text(encoding="utf-8")
            
            # Simple text checks as a first pass
            if 'state.json' not in content:
                continue
                
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    # Check for open("state.json", "w")
                    if isinstance(node.func, ast.Name) and node.func.id == "open":
                        if len(node.args) > 0 and isinstance(node.args[0], ast.Constant) and node.args[0].value == "state.json":
                            if len(node.args) > 1 and isinstance(node.args[1], ast.Constant) and "w" in node.args[1].value:
                                pytest.fail(f"{file} يحاول كتابة state.json — ممنوع!")
                    # Check for Path("state.json").write_text()
                    elif isinstance(node.func, ast.Attribute) and node.func.attr == "write_text":
                        if isinstance(node.func.value, ast.Call) and getattr(node.func.value.func, "id", "") == "Path":
                            if len(node.func.value.args) > 0 and isinstance(node.func.value.args[0], ast.Constant) and node.func.value.args[0].value == "state.json":
                                pytest.fail(f"{file} يحاول كتابة state.json — ممنوع!")
        except SyntaxError:
            pass

def test_pipeline_service_is_only_writer_of_pipeline_state():
    """PipelineService هو الوحيد المسموح له بكتابة .pipeline_state.json"""
    python_files = get_python_files()
    
    for file in python_files:
        # Allow pipeline_service.py to write the file
        if file.name == "pipeline_service.py":
            continue
            
        try:
            content = file.read_text(encoding="utf-8")
            if '.pipeline_state.json' not in content:
                continue
                
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name) and node.func.id == "open":
                        if len(node.args) > 0 and isinstance(node.args[0], ast.Constant) and ".pipeline_state.json" in str(node.args[0].value):
                            if len(node.args) > 1 and isinstance(node.args[1], ast.Constant) and "w" in node.args[1].value:
                                pytest.fail(f"{file} يحاول كتابة .pipeline_state.json — مسموح فقط لـ PipelineService!")
        except SyntaxError:
            pass
