#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess
from scripts.security import safe_subprocess
import sys
from scripts.path_security import validate_project_id, safe_resolve
import shutil

CHECKS = [
    (["python", "-m", "pytest", "tests/"], "Unit Tests"),
    (["npx.cmd" if sys.platform == "win32" else "npx", "tsc", "--noEmit"], "TypeScript Build"),
    (["python", "scripts/template_lint.py", "templates"], "Template Lint"),
    (["python", ".agents/plugins/super-video-maker-plugin/verify.py"], "Plugin Verify"),
    (["python", "scripts/benchmark_guards.py"], "Performance Benchmark"),
]

def run_check(cmd, name):
    print(f"⏳ Running {name}...")
    # Adjust npx path for cwd
    kwargs = {}
    if name == "TypeScript Build":
        kwargs["cwd"] = "remotion-app"
    
    try:
        proc = safe_subprocess(cmd, capture_output=True, text=True, **kwargs)
        if proc.returncode == 0:
            print(f"✅ {name}: PASS")
            return True, ""
        else:
            print(f"❌ {name}: FAIL")
            return False, proc.stdout + "\n" + proc.stderr
    except Exception as e:
        print(f"❌ {name}: FAIL (Exception)")
        return False, str(e)

def is_docker_available():
    if not shutil.which("docker"):
        return False
    try:
        proc = safe_subprocess(["docker", "info"], capture_output=True, text=True, timeout=5)
        return proc.returncode == 0
    except Exception:
        return False

def main():
    use_docker = "--docker-render" in sys.argv
    print("=== CI/CD Master Script ===")
    
    all_passed = True
    results = []
    for cmd, name in CHECKS:
        passed, out = run_check(cmd, name)
        results.append((name, passed, out))
        if not passed:
            all_passed = False
            
    # Optional Docker Test
    if use_docker:
        if is_docker_available():
            print("⏳ Running Docker Render Test...")
            proc = safe_subprocess(["python", "scripts/render_project.py", "demo_brand", "--docker"], capture_output=True, text=True)
            if proc.returncode == 0:
                print("✅ Docker Render: PASS")
                results.append(("Docker Render", True, ""))
            else:
                print("❌ Docker Render: FAIL")
                results.append(("Docker Render", False, proc.stdout + "\n" + proc.stderr))
                all_passed = False
        else:
            print("⚠️ Docker Render: SKIPPED (Docker not available)")
            results.append(("Docker Render", None, "Docker not available"))
            
    print("\n=== SUMMARY ===")
    for name, passed, out in results:
        if passed is True:
            print(f"✅ {name}")
        elif passed is False:
            print(f"❌ {name}")
            print(out.strip())
        else:
            print(f"⚠️ {name}: SKIPPED")
            
    if all_passed:
        print("=== ALL CHECKS PASSED ===")
        sys.exit(0)
    else:
        print("=== SOME CHECKS FAILED ===")
        sys.exit(1)

if __name__ == "__main__":
    main()

