import os
import json
import subprocess
from pathlib import Path
import re

def discover_static_tests():
    test_files = []
    
    exclude_dirs = {'.git', 'node_modules', '.venv', 'dist', 'build', '__pycache__', '.pytest_cache'}
    
    for root, dirs, files in os.walk('.'):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            path = Path(root) / file
            str_path = str(path).replace('\\', '/')
            
            # Match python test files
            if file.startswith('test_') and file.endswith('.py'):
                test_files.append(str_path)
            elif file.endswith('_test.py'):
                test_files.append(str_path)
            # Match TS/JS test files
            elif re.search(r'\.(test|spec)\.(ts|tsx|js|jsx)$', file):
                test_files.append(str_path)
                
    return test_files

def parse_pytest_collection():
    try:
        res = subprocess.run(['python', '-m', 'pytest', '--collect-only', '-q'], capture_output=True, text=True)
        lines = res.stdout.split('\n')
        collected_files = set()
        for line in lines:
            # Pytest -q output often looks like: 
            # tests/api/test_gates.py::test_status_initial
            # or just file paths if they are failing to collect properly
            if '::' in line:
                collected_files.add(line.split('::')[0].replace('\\', '/'))
        return collected_files
    except Exception:
        return set()

def main():
    static_files = discover_static_tests()
    pytest_collected = parse_pytest_collection()
    
    surface = []
    for f in static_files:
        ext = os.path.splitext(f)[1]
        framework = 'pytest' if ext == '.py' else 'vitest/jest'
        
        # Dead test detection
        is_dead = False
        if framework == 'pytest' and f not in pytest_collected:
            is_dead = True
            
        surface.append({
            "path": f,
            "framework": framework,
            "category": "UNKNOWN",
            "tests": 0,
            "production_area": "",
            "critical_path": False,
            "skip_count": 0,
            "xfail_count": 0,
            "mock_level": "",
            "status": "DEAD" if is_dead else "ACTIVE",
            "evidence": []
        })
        
    out_dir = Path('.remediation/phase-9')
    out_dir.mkdir(parents=True, exist_ok=True)
    
    with open(out_dir / 'test-surface.json', 'w', encoding='utf-8') as f:
        json.dump(surface, f, indent=2)
        
    print(f"Found {len(static_files)} test files statically.")
    print(f"Pytest collected {len(pytest_collected)} files.")
    
    dead = [x for x in surface if x['status'] == 'DEAD']
    print(f"Dead tests: {len(dead)}")
    for d in dead:
        print(f" - {d['path']}")

if __name__ == '__main__':
    main()
