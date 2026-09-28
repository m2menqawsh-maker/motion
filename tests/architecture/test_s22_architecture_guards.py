"""
tests/architecture/test_s22_architecture_guards.py — S22 Architecture Guards:
Enforces architectural boundaries for GUI-facing domain services, transport layer purity,
optimistic concurrency, and separation of concerns.
"""

import ast
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parent.parent.parent


def test_guard_no_direct_file_writes_in_routers():
    """
    Architecture Guard:
    api/routers/* must be pure transport layers. Direct filesystem mutations
    (write_text, write_bytes, json.dump, open in write mode) are strictly forbidden in routers.
    All disk operations must occur within Domain Services and Repositories.
    """
    routers_dir = ROOT / "api" / "routers"
    router_files = list(routers_dir.glob("*.py"))
    assert len(router_files) > 0, "Router files must exist"

    violations = []
    for rpath in router_files:
        tree = ast.parse(rpath.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            # Check for .write_text, .write_bytes
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in ("write_text", "write_bytes"):
                    violations.append(f"{rpath.name}:{node.lineno} calls direct file write '{node.func.attr}'")

            # Check for json.dump(..., f)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "dump" and isinstance(node.func.value, ast.Name) and node.func.value.id == "json":
                    violations.append(f"{rpath.name}:{node.lineno} calls json.dump directly")

            # Check for open(..., "w" / "wb" / "a")
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "open":
                for arg in node.args[1:]:
                    if isinstance(arg, ast.Constant) and any(m in str(arg.value) for m in ("w", "a", "+")):
                        violations.append(f"{rpath.name}:{node.lineno} opens file in write mode")

    assert not violations, f"Direct filesystem writes found in routers:\n" + "\n".join(violations)


def test_guard_routers_delegate_to_domain_services():
    """
    Architecture Guard:
    Every domain router must delegate business operations to its corresponding Domain Service.
    """
    required_delegations = {
        "brand.py": "api.services.brand_service",
        "blueprint.py": "api.services.override_service",
        "assets.py": "api.services.asset_service",
        "artifacts.py": "api.services.domain_artifact_service",
        "outputs.py": "api.services.output_service",
        "projects.py": "api.services.project_service",
        "runs.py": "api.services.run_service",
    }

    for filename, service_module in required_delegations.items():
        router_path = ROOT / "api" / "routers" / filename
        assert router_path.exists(), f"Router file {filename} must exist"
        tree = ast.parse(router_path.read_text(encoding="utf-8"))

        imported_modules = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.append(node.module)

        assert service_module in imported_modules, (
            f"Architecture violation: {filename} must import and delegate to {service_module}"
        )


def test_guard_led_073_not_closed():
    """
    Architecture Guard:
    LED-073 (/health/live and /health/ready production readiness probes) is strictly
    deferred to S23. Ensure LED-073 is NOT prematurely marked closed or implemented.
    """
    main_py = (ROOT / "api" / "main.py").read_text(encoding="utf-8")
    # /health/ready should not be mounted or active in S22
    assert "/health/ready" not in main_py, "LED-073 (/health/ready) must not be implemented in S22; deferred to S23"


def test_guard_review_authority_principal_binding():
    """
    Architecture Guard:
    Approval and rejection endpoints must strictly pass the server-authenticated
    Principal to ReviewService. Identity cannot be taken from unauthenticated client bodies.
    """
    artifacts_router = (ROOT / "api" / "routers" / "artifacts.py").read_text(encoding="utf-8")
    assert "ReviewService.approve(" in artifacts_router, "artifacts.py must call ReviewService.approve"
    assert "ReviewService.reject(" in artifacts_router, "artifacts.py must call ReviewService.reject"
    assert "principal=principal" in artifacts_router, (
        "artifacts.py must bind principal to authenticated Principal, not client-supplied strings"
    )


def test_guard_cors_is_dynamic_and_configurable():
    """
    Architecture Guard:
    CORS origins must not be hardcoded to localhost:3000. It must be driven
    dynamically by APISettings with credential safety invariants.
    """
    main_code = (ROOT / "api" / "main.py").read_text(encoding="utf-8")
    assert "allow_origins=[\"http://localhost:3000\"]" not in main_code, (
        "Hardcoded localhost:3000 CORS must not be present in api/main.py"
    )
    assert "DynamicCORSMiddleware" in main_code, "DynamicCORSMiddleware must be installed in api/main.py"

    config_code = (ROOT / "api" / "core" / "config.py").read_text(encoding="utf-8")
    assert "APISettings" in config_code
    assert "cors_allowed_origins" in config_code
