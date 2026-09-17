import os
import shutil
import hashlib
import subprocess
import json
import time

def hash_file(path):
    if not os.path.exists(path): return None
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

def apply_mutation(path, find_str, replace_str):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    if find_str not in content:
        raise ValueError(f"Mutation target string '{find_str}' not found in {path}")
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
        
        print(f"Executing: {' '.join(test_command)}")
        res = subprocess.run(test_command, capture_output=True, text=True)
        caught = res.returncode != 0
        print(f"Mutation Caught: {caught}")
        if not caught:
            print("--- FAILED TO CATCH MUTATION ---")
            print(res.stdout)
            print(res.stderr)
            
    finally:
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
    
    # 1. Registry Ghost Entry
    # Removes RENDER_TIMEOUT from registry
    results.append(run_mutation_test(
        "registry_ghost",
        lambda: apply_mutation("scripts/failure_model.py", "FailureCode.RENDER_TIMEOUT: FailureMetadata", "# FailureCode.RENDER_TIMEOUT: FailureMetadata"),
        "scripts/failure_model.py",
        ["python", "-m", "pytest", "tests/test_failure_classification.py"]
    ))
    
    # 2. Invalid Schema Acceptance
    # Mutates the project schema to allow arbitrary additional properties
    results.append(run_mutation_test(
        "invalid_schema_acceptance",
        lambda: apply_mutation("schemas/project.schema.json", '"additionalProperties": false', '"additionalProperties": true'),
        "schemas/project.schema.json",
        ["python", "-m", "pytest", "tests/test_schemas_validation.py"]
    ))
    
    # 3. Failure-Injection Production Bypass
    # Mutates the protection in pipeline.py or security.py so it runs failure_injection in production
    results.append(run_mutation_test(
        "failure_injection_bypass",
        lambda: apply_mutation("scripts/failure_injection.py", 'if env == "production":', 'if False:'),
        "scripts/failure_injection.py",
        ["python", "-m", "pytest", "tests/test_failure_injection.py"]
    ))
    
    # 4. Alternate API Pipeline Path
    # Mutates API to call render_project.py directly instead of pipeline.py
    results.append(run_mutation_test(
        "alternate_api_pipeline_path",
        lambda: apply_mutation("api/services/pipeline_service.py", '"scripts/pipeline.py"', '"scripts/render_project.py"'),
        "api/services/pipeline_service.py",
        ["python", "-m", "pytest", "tests/api/test_pipeline_service.py"]
    ))
    
    with open(".remediation/phase-9/mutation-test-results-final.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
        
    caught_count = sum(1 for r in results if r["caught"])
    print(f"Final Mutations Caught: {caught_count}/{len(results)}")

if __name__ == '__main__':
    main()
