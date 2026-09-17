import subprocess
import sys
import time

def main():
    suites = ["tests"] # We just run all of `tests/` which now includes scripts/tests
    
    for i in range(3):
        print(f"=== FULL CRITICAL SUITE RUN #{i+1} ===")
        start = time.time()
        res = subprocess.run(["python", "-m", "pytest", *suites, "-q"])
        elapsed = time.time() - start
        
        if res.returncode != 0:
            print(f"❌ Run #{i+1} FAILED or HUNG after {elapsed:.2f}s!")
            sys.exit(1)
        else:
            print(f"✅ Run #{i+1} PASSED in {elapsed:.2f}s")
            
    print("\n✅ All 3/3 full critical suite runs PASSED in fresh processes.")
    
if __name__ == '__main__':
    main()
