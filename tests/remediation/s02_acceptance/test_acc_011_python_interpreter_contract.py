"""S02 Acceptance Contract 011: Python Subprocess Interpreter Drift (DISC-004).

Vulnerability: DISC-004 / Python Interpreter Policy
Contract:
Internal Python subprocess invocations (specifically in api/services/scaffold_service.py)
must use sys.executable or a configured Python interpreter path, NEVER hardcoded 'python'.
Hardcoded 'python' causes catastrophic ModuleNotFoundError outside activated virtualenvs
and creates vulnerability to PATH hijacking.
"""

import pytest
import sys
from unittest.mock import patch
from api.services.scaffold_service import create_project


@pytest.mark.acceptance
def test_scaffold_service_must_use_sys_executable_not_bare_python():
    """create_project() must invoke sys.executable, not hardcoded 'python'."""
    with patch("api.services.scaffold_service.safe_subprocess") as mock_subprocess:
        mock_subprocess.return_value.returncode = 0
        mock_subprocess.return_value.stdout = "proj_test_id"
        
        create_project("Test Project", "en")
        
        # Verify the command list passed to safe_subprocess
        assert mock_subprocess.called, "safe_subprocess was not invoked"
        called_cmd = mock_subprocess.call_args[0][0]
        
        executable = called_cmd[0]
        assert executable != "python", (
            "Architecture Defect (DISC-004): scaffold_service.py invoked hardcoded 'python'. "
            f"Must use sys.executable ('{sys.executable}') or configured interpreter path."
        )
        assert executable == sys.executable or executable.endswith("/python")
