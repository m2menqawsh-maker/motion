import ast
import pytest
from pathlib import Path

def get_python_files():
    """Return all non-test python files in api/ and scripts/"""
    base_dir = Path(__file__).parent.parent.parent
    files = []
    
    # Check api directory
    api_dir = base_dir / "api"
    if api_dir.exists():
        files.extend(api_dir.rglob("*.py"))
        
    # Check scripts directory
    scripts_dir = base_dir / "scripts"
    if scripts_dir.exists():
        files.extend(scripts_dir.rglob("*.py"))
        
    return [f for f in files if "tests" not in f.parts and ".remediation" not in f.parts]

def test_no_scripts_core_imports():
    """لا يسمح بأي استيراد من scripts.core"""
    python_files = get_python_files()
    
    for file in python_files:
        try:
            tree = ast.parse(file.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    if node.module and node.module.startswith("scripts.core"):
                        pytest.fail(
                            f"{file} يستورد من scripts.core — ممنوع! "
                            f"استخدم PipelineService بدلاً من ذلك"
                        )
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith("scripts.core"):
                            pytest.fail(
                                f"{file} يستورد من scripts.core — ممنوع! "
                                f"استخدم PipelineService بدلاً من ذلك"
                            )
        except SyntaxError:
            pass # Skip syntax errors in parsing if any

def test_no_unified_pipeline_references():
    """لا يسمح بأي إشارة لـ UnifiedPipeline"""
    python_files = get_python_files()
    
    for file in python_files:
        content = file.read_text(encoding="utf-8")
        if "UnifiedPipeline" in content:
            pytest.fail(
                f"{file} يحتوي على إشارة لـ UnifiedPipeline — ممنوع! "
                f"يجب الاعتماد كلياً على scripts/pipeline.py الجديد."
            )
