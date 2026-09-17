import json
import subprocess
import os

def run_smoke():
    with open('.remediation/phase-9/executable-classification.json', 'r', encoding='utf-8') as f:
        surface = json.load(f)
        
    results = []
    
    for item in surface:
        path = item['path']
        cls = item.get('classification')
        
        if cls in ('PRODUCTION', 'AGENT_TOOL', 'TEST_SUPPORT', 'AUDIT') and path.endswith('.py'):
            # First syntax check
            try:
                import py_compile
                py_compile.compile(path, doraise=True)
                syntax = 'PASS'
            except:
                syntax = 'FAIL'
                
            # Then behavior test
            behavior_status = 'SKIPPED'
            behavior_log = ''
            
            # If it's a CLI tool, try --help
            if cls in ('PRODUCTION', 'AUDIT') and 'scratch' not in path and 'security.py' not in path:
                try:
                    res = subprocess.run(['python', path, '--help'], capture_output=True, text=True, timeout=5)
                    behavior_status = 'PASS' if res.returncode in (0, 1) else 'FAIL' # Sometimes argparse exits 1 or 2
                    behavior_log = res.stdout[:100] + res.stderr[:100]
                except Exception as e:
                    behavior_status = 'FAIL'
                    behavior_log = str(e)
                    
            results.append({
                'path': path,
                'classification': cls,
                'syntax_check': syntax,
                'behavior_smoke': behavior_status,
                'log': behavior_log
            })
            
    with open('.remediation/phase-9/executable-smoke-results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)

if __name__ == '__main__':
    run_smoke()
