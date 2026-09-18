import ast
import pytest
from pathlib import Path

def get_python_files():
    base_dir = Path(__file__).parent.parent.parent
    files = []
    
    api_dir = base_dir / "api"
    if api_dir.exists():
        files.extend(api_dir.rglob("*.py"))
        
    return [f for f in files if "tests" not in f.parts and ".remediation" not in f.parts]

def test_routers_do_not_import_scripts_directly():
    """الـ routers يجب أن تستورد فقط من api.services ولا تصل لـ scripts مباشرة"""
    base_dir = Path(__file__).parent.parent.parent
    routers_dir = base_dir / "api" / "routers"
    
    if not routers_dir.exists():
        return
        
    for router_file in routers_dir.glob("*.py"):
        try:
            tree = ast.parse(router_file.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and node.module.startswith("scripts."):
                        if node.module not in ["scripts.security.security", "scripts.security.path_security"]:
                            pytest.fail(f"{router_file} يستورد من {node.module} مباشرة — يجب استخدام PipelineService!")
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith("scripts."):
                            if alias.name not in ["scripts.security.security", "scripts.security.path_security"]:
                                pytest.fail(f"{router_file} يستورد من {alias.name} مباشرة — يجب استخدام PipelineService!")
        except SyntaxError:
            pass
