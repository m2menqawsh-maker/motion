import json
import os

critical_path = [
    {
        "segment": "Agent / API CLI",
        "evidence": ["tests/api/test_pipeline_service.py", "tests/api/test_projects.py", "tests/e2e/test_full_pipeline.py"]
    },
    {
        "segment": "Pipeline Service & Gates",
        "evidence": ["tests/api/test_gates.py", "tests/architecture/test_architecture_guards.py"]
    },
    {
        "segment": "State Management (Canonical)",
        "evidence": ["tests/contracts/test_state_schema.py", "tests/architecture/test_state_file_integrity.py"]
    },
    {
        "segment": "Rendering & Engine",
        "evidence": ["tests/api/test_render.py"]
    },
    {
        "segment": "Security / Quality Control",
        "evidence": ["tests/security/test_guardian.py", "tests/security/test_path_traversal.py", "tests/security/test_subprocess_security.py"]
    }
]

with open('.remediation/phase-9/critical-path-test-map.json', 'w', encoding='utf-8') as f:
    json.dump(critical_path, f, indent=2)

print("Critical Path test map generated.")
