"""
tests/architecture/test_s20_architecture_guard.py — Architecture & Structural Guards for Package S20:
- Guard 1: Dockerfile uses deterministic dependency install (npm ci), never npm install.
- Guard 2: Dockerfile copies application source & lockfiles into the image (hermetic runtime).
- Guard 3: Dockerfile enforces non-root execution (USER renderer).
- Guard 4: .dockerignore exists and strictly excludes host node_modules, virtualenvs, and project data.
- Guard 5: Docker invocation in scripts/render_project.py and scripts/open_studio.py does NOT mount full host workspace.
- Guard 6: Docker invocation preserves canonical S17 render input (render_props.json).
- Guard 7: No runtime dependency installation (npm install / pip install / apt install) in render path.
"""
from pathlib import Path
import re
import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
DOCKERFILE = ROOT / ".agents" / "docker" / "Dockerfile.remotion"
DOCKERIGNORE = ROOT / ".dockerignore"
RENDER_PROJECT_PY = ROOT / "scripts" / "render_project.py"
OPEN_STUDIO_PY = ROOT / "scripts" / "open_studio.py"


def test_guard_dockerfile_deterministic_install():
    """Guard 1: Dockerfile must use deterministic 'npm ci' to install dependencies."""
    assert DOCKERFILE.is_file(), "Dockerfile.remotion not found!"
    content = DOCKERFILE.read_text(encoding="utf-8")
    assert "npm ci" in content, "Dockerfile must use 'npm ci' for deterministic locked dependency install"
    # Ensure raw npm install is not used for installing dependencies in the build
    assert not re.search(r'RUN\s+.*npm\s+install(?!\-scripts)', content), (
        "Dockerfile must NOT use non-deterministic 'npm install'"
    )


def test_guard_dockerfile_copies_application_source():
    """Guard 2: Dockerfile must COPY manifests, contracts, registry, templates, and remotion-app source."""
    content = DOCKERFILE.read_text(encoding="utf-8")
    assert re.search(r'COPY.*package.*json', content), "Dockerfile must COPY package manifests"
    assert re.search(r'COPY.*contracts', content), "Dockerfile must COPY contracts directory"
    assert re.search(r'COPY.*registry', content), "Dockerfile must COPY registry directory"
    assert re.search(r'COPY.*templates', content), "Dockerfile must COPY templates directory"
    assert re.search(r'COPY.*remotion-app', content), "Dockerfile must COPY remotion-app directory"


def test_guard_dockerfile_non_root_user():
    """Guard 3: Dockerfile must switch to a non-root USER (renderer)."""
    content = DOCKERFILE.read_text(encoding="utf-8")
    user_match = re.search(r'^USER\s+([a-zA-Z0-9_\-]+)', content, re.MULTILINE)
    assert user_match is not None, "Dockerfile must declare a non-root USER instruction"
    user_name = user_match.group(1).strip()
    assert user_name != "root" and user_name != "0", f"Dockerfile USER must not be root (found: {user_name})"


def test_guard_dockerignore_prevents_host_dependencies():
    """Guard 4: .dockerignore must exist and exclude host node_modules, venvs, and project data."""
    assert DOCKERIGNORE.is_file(), ".dockerignore must exist"
    content = DOCKERIGNORE.read_text(encoding="utf-8")
    lines = [line.strip() for line in content.splitlines() if line.strip() and not line.startswith("#")]
    assert any("node_modules" in l for l in lines), ".dockerignore must ignore node_modules"
    assert any(".venv" in l or "venv" in l for l in lines), ".dockerignore must ignore virtualenvs"
    assert any("projects" in l for l in lines), ".dockerignore must ignore runtime project data"


def test_guard_docker_invocation_no_workspace_mount():
    """
    Guard 5: scripts/render_project.py and scripts/open_studio.py must NOT mount the full
    host workspace directory into the container. Application code must reside in the image.
    """
    for script_path in [RENDER_PROJECT_PY, OPEN_STUDIO_PY]:
        content = script_path.read_text(encoding="utf-8")
        assert not re.search(r'["\']-v["\'],\s*f?["\']\{workspace_root\}', content), (
            f"Architecture Guard Violation in {script_path.name}: Mounts full host workspace into container!"
        )
        assert not re.search(r'["\']-v["\'],\s*f?["\']\{workspace_root_abs\}', content), (
            f"Architecture Guard Violation in {script_path.name}: Mounts full host workspace into container!"
        )


def test_guard_docker_invocation_preserves_canonical_s17_payload():
    """Guard 6: Docker render & studio invocations MUST pass canonical render_props.json."""
    for script_path in [RENDER_PROJECT_PY, OPEN_STUDIO_PY]:
        content = script_path.read_text(encoding="utf-8")
        assert re.search(r'--props.*render_props\.json', content), (
            f"Architecture Guard Violation: {script_path.name} must pass render_props.json in Docker command!"
        )


def test_guard_no_runtime_package_install():
    """Guard 7: Render scripts must not invoke package managers (npm/pip) at runtime."""
    for script_path in [RENDER_PROJECT_PY, OPEN_STUDIO_PY]:
        content = script_path.read_text(encoding="utf-8")
        assert "npm install" not in content, f"{script_path.name} must not run npm install at runtime"
        assert "pip install" not in content, f"{script_path.name} must not run pip install at runtime"
