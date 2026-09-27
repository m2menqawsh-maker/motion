"""S02 Acceptance Contract 008: Dangerous Subprocess Flags Rejection.

Vulnerability: SEC-003 / Command Policy
Contract:
safe_subprocess must inspect all arguments in the command list, not merely the first script argument.
Flags enabling inline evaluation or dangerous options (such as '-c', '--eval', '--interactive')
must be rejected with PermissionError, even if an allowed script is present in the command list.
"""

import pytest
from unittest.mock import patch
from scripts.security.security import safe_subprocess


@pytest.mark.acceptance
def test_dangerous_flags_in_arguments_must_be_rejected():
    """Passing dangerous flags like '-c' after an allowed script must raise PermissionError."""
    # In current main, only cmd_list[1] is checked against ALLOWED_SCRIPTS.
    # Subsequent dangerous flags like '-c' pass through uninspected!
    cmd = ["python", "scripts/pipeline.py", "-c", "import os; os.system('echo compromised')"]
    
    with patch("subprocess.run") as mock_run:
        with pytest.raises(PermissionError, match="Dangerous flag|-c|not allowed"):
            safe_subprocess(cmd)


@pytest.mark.acceptance
def test_npm_eval_must_be_rejected():
    """Passing '--eval' to npm must raise PermissionError."""
    cmd = ["npm", "run", "build", "--eval", "console.log(process.env)"]
    with patch("subprocess.run") as mock_run:
        with pytest.raises(PermissionError, match="Dangerous flag|--eval|not allowed"):
            safe_subprocess(cmd)
