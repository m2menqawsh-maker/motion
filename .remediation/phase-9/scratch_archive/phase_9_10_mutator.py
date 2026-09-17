import os
import shutil
import hashlib
import subprocess
import json

def hash_file(path):
    if not os.path.exists(path): return None
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

def apply_mutation(path, find_str, replace_str):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    if find_str not in content:
        raise ValueError(f"Mutation target string not found in {path}")
    content = content.replace(find_str, replace_str)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

def run_mutation_test(name, mutate_fn, target_file, test_command):
    print(f"--- Running Mutation: {name} ---")
    orig_hash = hash_file(target_file)
    backup_file = target_file + '.bak'
    
    if orig_hash:
        shutil.copy2(target_file, backup_file)
        
    try:
        mutate_fn()
        
        # Run test
        print(f"Executing: {' '.join(test_command)}")
        res = subprocess.run(test_command, capture_output=True, text=True)
        # If the test FAILS (non-zero), the mutation was CAUGHT -> PASS
        caught = res.returncode != 0
        print(f"Mutation Caught: {caught}")
        
    finally:
        # Restore
        if orig_hash:
            shutil.copy2(backup_file, target_file)
            os.remove(backup_file)
            new_hash = hash_file(target_file)
            restored = (new_hash == orig_hash)
            if not restored:
                print(f"CRITICAL: Restore failed for {target_file}")
        else:
            if os.path.exists(target_file):
                os.remove(target_file)
            restored = True
            
    return {
        "mutation": name,
        "caught": caught,
        "restored": restored
    }

def main():
    results = []
    
    # 1. Shell Enforcement
    results.append(run_mutation_test(
        "shell_enforcement",
        lambda: apply_mutation("scripts/security.py", 'kwargs["shell"] = False', 'kwargs["shell"] = True'),
        "scripts/security.py",
        ["python", "-m", "pytest", "tests/security/test_subprocess_security.py"]
    ))
    
    # 2. Guardian Command Bypass
    results.append(run_mutation_test(
        "guardian_command_bypass",
        lambda: apply_mutation("scripts/security.py", 'ALLOWED_COMMANDS = {"ffmpeg", "ffprobe"}', 'ALLOWED_COMMANDS = {"ffmpeg", "ffprobe", "echo"}'),
        "scripts/security.py",
        ["python", "-m", "pytest", "tests/security/test_guardian.py"]
    ))
    
    # 3. Canonical State Writer (Architecture Test)
    def mutate_writer():
        with open("scripts/fake_writer.py", "w") as f:
            f.write("import json\ndef write_state():\n    with open('.pipeline_state.json', 'w') as f:\n        json.dump({}, f)\n")
    results.append(run_mutation_test(
        "canonical_state_writer",
        mutate_writer,
        "scripts/fake_writer.py",
        ["python", "-m", "pytest", "tests/architecture/test_state_file_integrity.py"]
    ))
    
    # 4. Gate Bypass
    # Mutate approve_gate to NOT raise exception on invalid gate
    results.append(run_mutation_test(
        "gate_bypass",
        lambda: apply_mutation("api/services/pipeline_service.py", "raise InvalidGateException", "pass # MUTATED"),
        "api/services/pipeline_service.py",
        ["python", "-m", "pytest", "tests/api/test_gates.py"]
    ))
    
    with open(".remediation/phase-9/mutation-test-results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
        
    caught_count = sum(1 for r in results if r["caught"])
    restore_count = sum(1 for r in results if r["restored"])
    print(f"Mutations Caught: {caught_count}/{len(results)}")
    print(f"Restorations Successful: {restore_count}/{len(results)}")

if __name__ == '__main__':
    main()
