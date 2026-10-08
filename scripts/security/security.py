"""Single Authority Subprocess Confinement Adapter.

In accordance with S01 Trust Model, ADR-001, and S02 Security Enforcement:
This module acts strictly as a thin backward-compatible adapter delegating all execution
policy evaluations to the canonical authority: `scripts.core.security.command_policy.CommandPolicy`.
Independent, duplicated allowlists are completely removed.
"""

import os
import subprocess
from pathlib import Path
from typing import List, Union
from scripts.core.security.command_policy import CommandPolicy, CommandSecurityViolation

# Legacy constant references kept for backward-compatibility with tests/callers that inspect them
ALLOWED_COMMANDS = {"ffmpeg", "ffprobe"}
ALLOWED_SCRIPTS = {
    "npm": ["run", "build"],
    "docker": ["info", "run", "build"],
    "npx": ["remotion"],
    "npx.cmd": ["remotion"],
}


def safe_subprocess(cmd_list: Union[str, List[str]], **kwargs):
    """Safely execute a subprocess, rigorously enforced by canonical CommandPolicy."""
    if isinstance(cmd_list, str):
        cmd_list = cmd_list.split()

    if not cmd_list:
        raise PermissionError("Empty command")

    cwd = kwargs.get("cwd")
    timeout = kwargs.get("timeout")

    is_prod = os.environ.get("MOTION_ENV", "development").lower() == "production"

    validation = CommandPolicy.validate_command(
        cmd=list(cmd_list),
        cwd=cwd,
        timeout=timeout,
        is_production=is_prod
    )

    if not validation.is_allowed:
        raise PermissionError(f"Command not allowed: {'; '.join(validation.violations)}")

    # Force safe execution defaults
    kwargs["shell"] = False
    if "timeout" not in kwargs:
        kwargs["timeout"] = validation.timeout_seconds

    # Use sanitized command (e.g. sys.executable instead of bare python)
    exec_cmd = validation.sanitized_cmd

    allow_db_env = kwargs.pop("allow_database_env", False)
    target_script = validation.subcommand

    # Ensure environment is sanitized
    kwargs["env"] = CommandPolicy.sanitize_environment(
        base_env=kwargs.get("env"),
        workspace_root=Path(cwd) if cwd else None,
        is_production=is_prod,
        target_script=target_script,
        allow_database_env=allow_db_env,
    )

    return subprocess.run(exec_cmd, **kwargs)


def safe_popen(cmd_list: Union[str, List[str]], **kwargs) -> subprocess.Popen:
    """Safely start an asynchronous subprocess, enforced by CommandPolicy."""
    if isinstance(cmd_list, str):
        cmd_list = cmd_list.split()

    if not cmd_list:
        raise PermissionError("Empty command")

    cwd = kwargs.get("cwd")
    is_prod = os.environ.get("MOTION_ENV", "development").lower() == "production"

    validation = CommandPolicy.validate_command(
        cmd=list(cmd_list),
        cwd=cwd,
        is_production=is_prod
    )

    if not validation.is_allowed:
        raise PermissionError(f"Command not allowed: {'; '.join(validation.violations)}")

    kwargs["shell"] = False
    exec_cmd = validation.sanitized_cmd
    allow_db_env = kwargs.pop("allow_database_env", False)
    target_script = validation.subcommand

    kwargs["env"] = CommandPolicy.sanitize_environment(
        base_env=kwargs.get("env"),
        workspace_root=Path(cwd) if cwd else None,
        is_production=is_prod,
        target_script=target_script,
        allow_database_env=allow_db_env,
    )

    return subprocess.Popen(exec_cmd, **kwargs)
