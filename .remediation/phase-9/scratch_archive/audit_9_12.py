import os
import sys
import json
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

PHASE_DIR = Path(".remediation/phase-9")
PHASE_DIR.mkdir(parents=True, exist_ok=True)

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {cmd}\nError: {e.stderr}")
        return ""

def capture_baseline():
    print("Capturing baseline...")
    baseline = {
        "timestamp": datetime.now().isoformat(),
        "commit_sha": run_cmd("git rev-parse HEAD"),
        "branch": run_cmd("git branch --show-current"),
        "tracked_count": len(run_cmd("git ls-files").splitlines()),
        "untracked_count": len(run_cmd("git ls-files --others --exclude-standard").splitlines()),
        "ignored_count": len(run_cmd("git ls-files --ignored --exclude-standard --others").splitlines())
    }
    with open(PHASE_DIR / "hygiene-baseline.json", "w", encoding="utf-8") as f:
        json.dump(baseline, f, indent=2)
    return baseline

def get_git_status():
    status_lines = run_cmd("git status --short").splitlines()
    status_map = {}
    for line in status_lines:
        if len(line) < 3: continue
        state = line[:2]
        path = line[3:].strip().strip('"')
        status_map[path] = state
    return status_map

def get_tracked_files():
    return set(run_cmd("git ls-files").splitlines())

def analyze_debug_markers(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            if "print(" in content or "console.log(" in content or "debugger" in content:
                return True
    except Exception:
        pass
    return False

def scan_repository():
    print("Scanning repository...")
    git_status = get_git_status()
    tracked_files = get_tracked_files()
    
    inventory = []
    mutation_plan = []
    
    # Exclude heavy directories from deep file-by-file audit if they are purely vendors or caches
    EXCLUDE_DIRS = {".git", "node_modules", "__pycache__", ".pytest_cache", ".venv", "venv", "env"}
    
    # Identify known standard root files (approximate)
    STANDARD_ROOT = {
        ".gitignore", "package.json", "package-lock.json", "tsconfig.json", "README.md",
        "pytest.ini", "requirements.txt", "ARCHITECTURE_TRUTH.md", "conftest.py"
    }

    for root, dirs, files in os.walk("."):
        # modify dirs in-place to skip excluded
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        
        rel_root = Path(root).relative_to(".")
        
        for file in files:
            filepath = (rel_root / file).as_posix()
            if filepath.startswith("./"):
                filepath = filepath[2:]
            if filepath == file and str(rel_root) == ".":
                filepath = file
                
            is_tracked = filepath in tracked_files
            status = git_status.get(filepath, "CLEAN")
            
            classification = "UNCLASSIFIED"
            disposition = "UNKNOWN"
            action = "NONE"
            dest = None
            confidence = "LOW"
            reason = ""
            
            # Logic for categorization
            if str(rel_root) == ".":
                if file not in STANDARD_ROOT and not is_tracked:
                    classification = "ROOT_UNTRACKED_CLUTTER"
                    disposition = "DELETE"
                    action = "DELETE"
                    reason = "Untracked unknown root file"
                elif file.endswith(".py") and file not in ["setup.py", "conftest.py", "manage.py"]:
                    classification = "ROOT_SCRIPT"
                    disposition = "MOVE_REMEDIATION"
                    action = "MOVE"
                    dest = f".remediation/phase-9/quarantine/{file}"
                    reason = "Root script likely from previous phase"
                    
            elif filepath.startswith("scratch/"):
                classification = "SCRATCH_ARTIFACT"
                if "phase9" in file or "audit" in file or "phase_" in file:
                    classification = "CERTIFICATION_EVIDENCE"
                    disposition = "KEEP_UNTIL_CERTIFICATION_COMPLETE"
                    confidence = "HIGH"
                else:
                    action = "DELETE"
                    disposition = "DELETE"
                    reason = "Obsolete scratch artifact"
                    
            elif filepath.startswith(".remediation/quarantine/"):
                classification = "QUARANTINE_ARTIFACT"
                disposition = "KEEP_QUARANTINED"
                confidence = "HIGH"
                
            elif file == "TestEngine.tsx":
                classification = "TEST_FIXTURE"
                disposition = "DELETE_IF_OBSOLETE"
                action = "DELETE"
                reason = "Needs manual confirmation, currently flagged for deletion."
                
            elif filepath.startswith("out/") or filepath.startswith("renders/"):
                classification = "RENDER_OUTPUT"
                disposition = "GENERATED_RUNTIME"
                if is_tracked:
                    action = "DELETE"
                    reason = "Render output should not be tracked"
                else:
                    confidence = "HIGH"
                    
            elif file.endswith((".bak", ".old", ".copy", ".orig")):
                classification = "BACKUP_ARTIFACT"
                disposition = "DELETE"
                action = "DELETE"
                confidence = "HIGH"
                reason = "Obsolete backup file"
            
            # Basic Source classification
            if action == "NONE" and is_tracked:
                classification = "SOURCE_CODE"
                disposition = "KEEP_ACTIVE"
                confidence = "HIGH"
                
            # Check for debug markers
            if classification == "SOURCE_CODE" and file.endswith((".py", ".ts", ".tsx", ".js")):
                if analyze_debug_markers(filepath):
                    classification = "SOURCE_WITH_DEBUG_MARKERS"
                    reason = "Contains print/console.log, requires contextual review."
                    confidence = "LOW"
            
            inventory.append({
                "path": filepath,
                "tracked": is_tracked,
                "generated": "out/" in filepath or "renders/" in filepath,
                "classification": classification,
                "final_disposition": disposition,
                "action": action,
                "confidence": confidence,
                "reason": reason,
                "production_reachable": classification == "SOURCE_CODE" or classification == "SOURCE_WITH_DEBUG_MARKERS",
                "evidence": []
            })
            
            if action != "NONE":
                mutation_plan.append({
                    "original_path": filepath,
                    "action": action,
                    "destination": dest,
                    "tracked": is_tracked,
                    "reason": reason,
                    "confidence": confidence,
                    "git_status_before": status
                })

    with open(PHASE_DIR / "repository-artifact-inventory.json", "w", encoding="utf-8") as f:
        json.dump(inventory, f, indent=2)
        
    with open(PHASE_DIR / "hygiene-mutation-plan.json", "w", encoding="utf-8") as f:
        json.dump(mutation_plan, f, indent=2)
        
    print(f"Scan complete. Inventory: {len(inventory)} items.")
    print(f"Proposed mutations: {len(mutation_plan)} items.")
    print(f"High confidence mutations: {len([m for m in mutation_plan if m['confidence'] == 'HIGH'])}")

def apply_mutations():
    print("Applying mutations...")
    plan_file = PHASE_DIR / "hygiene-mutation-plan.json"
    if not plan_file.exists():
        print("No mutation plan found. Run --scan first.")
        return
        
    with open(plan_file, "r", encoding="utf-8") as f:
        mutation_plan = json.load(f)
        
    results = []
    
    for mutation in mutation_plan:
        if mutation.get("confidence") != "HIGH":
            print(f"Skipping {mutation['original_path']} (LOW confidence or unreviewed)")
            continue
            
        action = mutation["action"]
        path = Path(mutation["original_path"])
        dest = mutation.get("destination")
        
        success = False
        error_msg = ""
        
        try:
            if action == "DELETE":
                if path.exists():
                    if mutation["tracked"]:
                        run_cmd(f"git rm -f {path.as_posix()}")
                    else:
                        path.unlink()
                    success = True
                else:
                    success = True
            elif action == "MOVE" and dest:
                if path.exists():
                    dest_path = Path(dest)
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    if mutation["tracked"]:
                        run_cmd(f"git mv {path.as_posix()} {dest_path.as_posix()}")
                    else:
                        path.rename(dest_path)
                    success = True
                else:
                    success = True
        except Exception as e:
            error_msg = str(e)
            
        results.append({
            "original_path": mutation["original_path"],
            "action": action,
            "destination": dest,
            "success": success,
            "error": error_msg
        })
        
        if success:
            print(f"Applied {action}: {mutation['original_path']}")
            
    with open(PHASE_DIR / "hygiene-mutation-results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
        
    print(f"Apply complete. Applied {len([r for r in results if r['success']])} actions.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 9.12 Repository Hygiene Audit")
    parser.add_argument("--scan", action="store_true", help="Scan repository and propose mutations")
    parser.add_argument("--apply", action="store_true", help="Apply HIGH confidence mutations")
    
    args = parser.parse_args()
    
    if args.scan:
        capture_baseline()
        scan_repository()
    elif args.apply:
        apply_mutations()
    else:
        print("Please specify --scan or --apply")
