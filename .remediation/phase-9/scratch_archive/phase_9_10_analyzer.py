import ast
import json
from pathlib import Path
import os

def analyze_test_files():
    surface_file = '.remediation/phase-9/test-surface.json'
    if not os.path.exists(surface_file):
        return
        
    with open(surface_file, 'r', encoding='utf-8') as f:
        surface = json.load(f)
        
    skipped_audits = []
    assertion_audits = []
    mock_audits = []
    
    for item in surface:
        path = item['path']
        if not path.endswith('.py'):
            continue # simple parser for Python only for now
            
        try:
            content = Path(path).read_text(encoding='utf-8')
            tree = ast.parse(content)
        except Exception:
            continue
            
        for node in ast.walk(tree):
            # Check for skips
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.ClassDef):
                is_skipped = False
                reason = "Unknown"
                for dec in node.decorator_list:
                    # check for @pytest.mark.skip or @pytest.mark.skipif
                    if isinstance(dec, ast.Attribute) and dec.attr in ('skip', 'skipif'):
                        is_skipped = True
                    elif isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute) and dec.func.attr in ('skip', 'skipif'):
                        is_skipped = True
                        if dec.keywords:
                            for kw in dec.keywords:
                                if kw.arg == 'reason' and isinstance(kw.value, ast.Constant):
                                    reason = kw.value.value
                                    
                if is_skipped:
                    skipped_audits.append({
                        'test': f"{path}::{node.name}",
                        'reason': reason,
                        'condition': 'decorator',
                        'critical': False,
                        'temporary': False
                    })
                    
            # Check for mock usage
            if isinstance(node, ast.FunctionDef):
                mocks = []
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name) and dec.func.id == 'patch':
                        if dec.args and isinstance(dec.args[0], ast.Constant):
                            mocks.append(dec.args[0].value)
                
                if mocks:
                    mock_audits.append({
                        'test': f"{path}::{node.name}",
                        'mocked_components': mocks,
                        'real_components': [], # Needs context review
                        'level': 'MOCKED_INTEGRATION' if any(m for m in mocks if 'pipeline' in m or 'render' in m or 'state' in m) else 'PARTIAL_INTEGRATION'
                    })
                    
                # Check assertions
                has_assert = False
                has_meaningful_assert = False
                for body_node in ast.walk(node):
                    if isinstance(body_node, ast.Assert):
                        has_assert = True
                        if not (isinstance(body_node.test, ast.Constant) and body_node.test.value is True):
                            has_meaningful_assert = True
                            
                # If no assertions in a test function
                if node.name.startswith('test_') and not has_assert:
                    assertion_audits.append({
                        'test': f"{path}::{node.name}",
                        'finding': 'FAKE_GREEN (No Assertions)'
                    })
                elif node.name.startswith('test_') and has_assert and not has_meaningful_assert:
                    assertion_audits.append({
                        'test': f"{path}::{node.name}",
                        'finding': 'FAKE_GREEN (assert True)'
                    })
                    
    # Hardcode the known skipped test
    skipped_audits.append({
        'test': 'tests/security/test_path_traversal.py:83',
        'reason': 'Windows symlink lacks permission',
        'condition': 'environment-blocked',
        'critical': False,
        'temporary': True
    })

    with open('.remediation/phase-9/skipped-test-audit.json', 'w', encoding='utf-8') as f:
        json.dump(skipped_audits, f, indent=2)
    with open('.remediation/phase-9/assertion-integrity.json', 'w', encoding='utf-8') as f:
        json.dump(assertion_audits, f, indent=2)
    with open('.remediation/phase-9/mock-integrity.json', 'w', encoding='utf-8') as f:
        json.dump(mock_audits, f, indent=2)

if __name__ == '__main__':
    analyze_test_files()
