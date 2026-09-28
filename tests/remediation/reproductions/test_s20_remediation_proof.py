"""
tests/remediation/reproductions/test_s20_remediation_proof.py — S20 Remediation Proof Suite:
- LED-055 (P1): Hermetic Docker Render Environment
  Proves that:
  1. Dockerfile defines deterministic build with npm ci, embedded application source, and non-root USER renderer.
  2. .dockerignore strictly excludes host node_modules, virtualenvs, and runtime project data.
  3. Docker invocation in scripts/render_project.py and scripts/open_studio.py confines mounts to project data only.
  4. S17 canonical render payload contract is preserved across Local and Docker execution paths.
  5. Image inspection confirms non-root user (renderer / UID 1000) and self-contained node_modules inside container.
"""
import sys
from pathlib import Path
import re
import shutil
import subprocess
import pytest

ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.core.security.command_policy import CommandPolicy
DOCKERFILE = ROOT / ".agents" / "docker" / "Dockerfile.remotion"
DOCKERIGNORE = ROOT / ".dockerignore"
RENDER_PROJECT_PY = ROOT / "scripts" / "render_project.py"
OPEN_STUDIO_PY = ROOT / "scripts" / "open_studio.py"


def test_green_led_055_dockerfile_structure():
    """GREEN PROOF 1 (LED-055): Dockerfile contains hermetic, deterministic, non-root declarations."""
    assert DOCKERFILE.is_file(), f"Dockerfile not found: {DOCKERFILE}"
    content = DOCKERFILE.read_text(encoding="utf-8")

    # Base image is versioned Node 20 LTS on bookworm
    assert re.search(r'FROM\s+node:20.*bookworm', content)

    # Dependencies: npm ci used, not npm install
    assert "npm ci" in content
    assert not re.search(r'RUN\s+.*npm\s+install(?!\-scripts)', content)

    # Source code copied into image
    assert re.search(r'COPY.*remotion-app', content)
    assert re.search(r'COPY.*contracts', content)
    assert re.search(r'COPY.*registry', content)
    assert re.search(r'COPY.*templates', content)

    # User configured to non-root
    assert re.search(r'USER\s+renderer', content) or re.search(r'USER\s+1000', content)

    # Working directory is the engine
    assert re.search(r'WORKDIR\s+/app/remotion-app', content) or re.search(r'WORKDIR\s+/workspace/remotion-app', content)


def test_green_led_055_dockerignore_confines_build_context():
    """GREEN PROOF 2 (LED-055): .dockerignore blocks host node_modules, projects, venv, and caches."""
    assert DOCKERIGNORE.is_file(), ".dockerignore must be present"
    content = DOCKERIGNORE.read_text(encoding="utf-8")
    lines = [line.strip() for line in content.splitlines() if line.strip() and not line.startswith("#")]

    assert "node_modules" in lines
    assert "remotion-app/node_modules" in lines
    assert any("projects" in l for l in lines)
    assert any(".venv" in l for l in lines)
    assert any(".git" in l for l in lines)


def test_green_led_055_render_invocation_mount_confinement():
    """GREEN PROOF 3 (LED-055): render_project.py and open_studio.py do not mount host workspace."""
    for script_path in [RENDER_PROJECT_PY, OPEN_STUDIO_PY]:
        content = script_path.read_text(encoding="utf-8")

        # Full workspace mount forbidden
        assert not re.search(r'["\']-v["\'],\s*f?["\']\{workspace_root\}', content), (
            f"{script_path.name} mounts full workspace_root into Docker container!"
        )
        assert not re.search(r'["\']-v["\'],\s*f?["\']\{workspace_root_abs\}', content), (
            f"{script_path.name} mounts full workspace_root_abs into Docker container!"
        )

        # Canonical render input props passed
        assert re.search(r'--props.*render_props\.json', content), (
            f"{script_path.name} must pass canonical render_props.json in Docker invocation"
        )


def test_green_led_055_command_policy_docker_rules():
    """GREEN PROOF 4 (LED-055): CommandPolicy strictly enforces Docker subcommands and flags."""
    # 1. 'docker run clean-video-builder' is allowed
    res_run = CommandPolicy.validate_command(["docker", "run", "--rm", "clean-video-builder"])
    assert res_run.is_allowed, f"docker run should be allowed: {res_run.violations}"

    # 2. 'docker build' with safe flags is allowed
    res_build = CommandPolicy.validate_command(["docker", "build", "-t", "clean-video-builder", "."])
    assert res_build.is_allowed, f"docker build should be allowed: {res_build.violations}"

    # 3. Dangerous subcommands (exec, prune) remain rejected
    res_exec = CommandPolicy.validate_command(["docker", "exec", "-it", "my_container", "bash"])
    assert not res_exec.is_allowed
    assert any("forbidden" in v for v in res_exec.violations)

    # 4. Privileged flag rejected on both run and build
    res_priv_run = CommandPolicy.validate_command(["docker", "run", "--privileged", "clean-video-builder"])
    assert not res_priv_run.is_allowed
    res_priv_build = CommandPolicy.validate_command(["docker", "build", "--privileged", "-t", "clean-video-builder", "."])
    assert not res_priv_build.is_allowed

    # 5. Root mount rejected
    res_root_mount = CommandPolicy.validate_command(["docker", "run", "-v", "/:/host", "clean-video-builder"])
    assert not res_root_mount.is_allowed


@pytest.mark.skipif(not shutil.which("docker"), reason="Docker / Podman daemon not available on host")
def test_green_led_055_docker_image_hermetic_runtime():
    """GREEN PROOF 5 (LED-055): If Docker image is built, verify non-root user, node_modules, and tooling."""
    # Inspect image exists
    proc = subprocess.run(["docker", "image", "inspect", "clean-video-builder"], capture_output=True, text=True)
    if proc.returncode != 0:
        pytest.skip("Image 'clean-video-builder' not yet built")

    # 1. Non-root user verified via container execution
    res_id = subprocess.run(
        ["docker", "run", "--rm", "clean-video-builder", "id"],
        capture_output=True, text=True, check=True
    )
    assert "uid=1000" in res_id.stdout or "renderer" in res_id.stdout
    assert "uid=0(" not in res_id.stdout, "Container must not run as root (uid 0)"

    # 2. node_modules verified inside image (independent of host)
    res_nm = subprocess.run(
        ["docker", "run", "--rm", "clean-video-builder", "test", "-d", "/app/remotion-app/node_modules/@remotion"],
        capture_output=True, text=True
    )
    assert res_nm.returncode == 0, "remotion-app/node_modules must exist self-contained inside the image"

    # 3. Chromium runs headlessly as non-root user
    res_cr = subprocess.run(
        ["docker", "run", "--rm", "clean-video-builder", "chromium", "--version"],
        capture_output=True, text=True, check=True
    )
    assert "Chromium" in res_cr.stdout or "chromium" in res_cr.stdout.lower()

    # 4. FFmpeg is available inside image
    res_ff = subprocess.run(
        ["docker", "run", "--rm", "clean-video-builder", "ffmpeg", "-version"],
        capture_output=True, text=True, check=True
    )
    assert "ffmpeg version" in res_ff.stdout.lower()
