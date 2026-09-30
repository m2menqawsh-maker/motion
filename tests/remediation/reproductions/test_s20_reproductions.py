"""
tests/remediation/reproductions/test_s20_reproductions.py — S20 Reproductions & Regression Suite:
- LED-055 (P1): Docker image relies on host workspace (evolved to GREEN regression proof).
  Proves that:
  1. Historical Dockerfile was non-hermetic: missing application COPY, missing deterministic npm ci, running as root.
  2. Historical invocation mounted full host workspace into container.
  3. S20 hermetic architecture embeds locked dependencies, source, non-root user, and mounts only project data.
"""
from pathlib import Path
import re
import pytest

ROOT = Path(__file__).resolve().parent.parent.parent.parent
DOCKERFILE = ROOT / ".agents" / "docker" / "Dockerfile.remotion"
RENDER_PROJECT_PY = ROOT / "scripts" / "render_project.py"
OPEN_STUDIO_PY = ROOT / "scripts" / "open_studio.py"
DOCKERIGNORE = ROOT / ".dockerignore"


def test_reproduce_led_055_dockerfile_hermetic_guarantees():
    """
    Finding: LED-055 (P1)
    Historical issue: Dockerfile.remotion did not copy codebase or install dependencies,
    relying entirely on host volume mount at runtime.
    S20 Fix Verification:
    1. Base image is versioned Node LTS on Debian bookworm.
    2. Deterministic dependency install via 'npm ci' inside image.
    3. Application source and contracts are copied into image.
    4. Execution is non-root (USER renderer).
    5. No unlocatable apt package (e.g. historical typo 'fonts-arab').
    """
    assert DOCKERFILE.is_file(), f"Dockerfile not found at {DOCKERFILE}"
    content = DOCKERFILE.read_text(encoding="utf-8")

    # 1. Base image
    assert re.search(r'FROM\s+node:20.*bookworm', content), "Must use node:20-bookworm base image"

    # 2. No invalid package typos
    assert "fonts-arab\n" not in content and "fonts-arab " not in content, (
        "LED-055: Invalid package 'fonts-arab' must be replaced by valid font packages (e.g. fonts-arabeyes, fonts-hosny-amiri)"
    )

    # 3. Deterministic npm ci
    assert "npm ci" in content, "LED-055: Must perform deterministic 'npm ci' in image build"

    # 4. Source COPY
    assert re.search(r'COPY.*remotion-app', content), "LED-055: Must COPY remotion-app into image"
    assert re.search(r'COPY.*contracts', content), "LED-055: Must COPY contracts into image"
    assert re.search(r'COPY.*registry', content), "LED-055: Must COPY registry into image"
    assert re.search(r'COPY.*templates', content), "LED-055: Must COPY templates into image"

    # 5. Non-root user
    user_match = re.search(r'^USER\s+([a-zA-Z0-9_\-]+)', content, re.MULTILINE)
    assert user_match is not None, "LED-055: Must declare non-root USER"
    assert user_match.group(1).strip() not in ("root", "0"), "LED-055: Container must not run as root"


def test_reproduce_led_055_render_invocation_mount_boundaries():
    """
    Finding: LED-055 (P1)
    Historical issue: render_project.py and open_studio.py mounted {workspace_root}:/workspace:ro,
    allowing the container to access host node_modules and host source.
    S20 Fix Verification:
    1. Neither script mounts full workspace_root.
    2. Only project_dir / project data is mounted.
    3. S17 canonical render_props.json is passed.
    """
    for script_path in [RENDER_PROJECT_PY, OPEN_STUDIO_PY]:
        content = script_path.read_text(encoding="utf-8")

        # Must not mount entire workspace
        assert not re.search(r'["\']-v["\'],\s*f?["\']\{workspace_root\}', content), (
            f"LED-055: {script_path.name} must not mount full host workspace"
        )
        assert not re.search(r'["\']-v["\'],\s*f?["\']\{workspace_root_abs\}', content), (
            f"LED-055: {script_path.name} must not mount full host workspace"
        )

        # Must pass canonical render_props.json
        assert re.search(r'--props.*render_props\.json', content), (
            f"LED-055 / S17: {script_path.name} must pass canonical render_props.json"
        )
