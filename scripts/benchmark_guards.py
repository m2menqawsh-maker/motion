#!/usr/bin/env python3
import time
import subprocess
import json
import sys

def run_guard(guard_script, payload):
    proc = subprocess.Popen(
        ["python", guard_script],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8"
    )
    stdout, stderr = proc.communicate(json.dumps(payload))
    return stdout

def benchmark():
    payload = {"toolCall": {"args": {"TargetFile": "projects/proj_1/valid.txt"}}}
    start = time.perf_counter()
    iterations = 50
    for _ in range(iterations):
        run_guard(".agents/guardian/write_guard.py", payload)
    end = time.perf_counter()
    
    avg_time = (end - start) / iterations * 1000
    print(f"Average time per run: {avg_time:.2f} ms")

if __name__ == "__main__":
    benchmark()
