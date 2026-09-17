import subprocess
import json
import time

def run_tests(name, args):
    start = time.time()
    try:
        res = subprocess.run(['python', '-m', 'pytest'] + args, capture_output=True, text=True)
        passed = res.returncode == 0
        output = res.stdout
    except Exception as e:
        passed = False
        output = str(e)
    duration = time.time() - start
    return {
        "run": name,
        "passed": passed,
        "duration": duration,
        "log": output[-500:] # store tail
    }

def audit_flakiness():
    results = []
    
    # 1. 3 consecutive runs
    for i in range(1, 4):
        print(f"Running iteration {i}...")
        results.append(run_tests(f"Iteration_{i}", ["tests/security", "tests/architecture", "tests/api", "-q"]))
        
    # 2. Isolated test run (running individual directories)
    print("Running isolated API...")
    results.append(run_tests("Isolated_API", ["tests/api", "-q"]))
    
    print("Running isolated Security...")
    results.append(run_tests("Isolated_Security", ["tests/security", "-q"]))
    
    flaky = False
    passed_count = sum(1 for r in results if r['passed'])
    if passed_count > 0 and passed_count < len(results):
        flaky = True
        
    out = {
        "critical_flaky_tests": 0 if not flaky else 1, # approximation
        "runs": results
    }
    
    with open('.remediation/phase-9/flakiness-results.json', 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=2)
        
    print(f"Flakiness audit done. Flaky detected: {flaky}")

if __name__ == '__main__':
    audit_flakiness()
