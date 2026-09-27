"""S02 Acceptance Contract 007: Docker Subcommand and Argument Validation.

Vulnerability: SEC-002 / Subprocess Confinement
Contract:
safe_subprocess must inspect Docker commands. Arbitrary subcommands (such as 'exec',
'volume rm', 'system prune') and dangerous flags (such as '--privileged' or root volume mounts)
must be rejected with PermissionError.
"""

import pytest
from unittest.mock import patch
from scripts.security.security import safe_subprocess


@pytest.mark.acceptance
def test_docker_exec_must_be_rejected():
    """safe_subprocess(['docker', 'exec', ...]) must raise PermissionError."""
    # In current main, 'docker' triggers `pass` for any subcommand in security.py line 56
    with patch("subprocess.run") as mock_run:
        with pytest.raises(PermissionError, match="Command not allowed"):
            safe_subprocess(["docker", "exec", "target_container", "bash"])


@pytest.mark.acceptance
def test_docker_privileged_must_be_rejected():
    """safe_subprocess(['docker', 'run', '--privileged', ...]) must raise PermissionError."""
    with patch("subprocess.run") as mock_run:
        with pytest.raises(PermissionError, match="Command not allowed|privileged"):
            safe_subprocess(["docker", "run", "--privileged", "clean-video-builder"])
