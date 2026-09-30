"""Command Execution Policy and Subprocess Confinement Engine.

CANONICAL AUTHORITY DECLARATION:
In accordance with the Trust Model (SEC-DOC-001) and ADR-001, this module is the
SINGLE CANONICAL AUTHORITY for subprocess execution policy across the entire workspace.
The legacy module `scripts/security/security.py` is slated in S02 for transition into
either a thin backward-compatible adapter delegating to this policy or complete removal.
Maintaining two divergent, independent command allowlists is strictly prohibited.

Executable-Aware Confinement:
Policy Python != Policy Node != Policy Docker != Policy FFmpeg:
- Python: sys.executable enforcement (DISC-004), registered scripts or allowlisted '-m' modules.
  Inline code execution ('-c') is strictly forbidden.
- Node/npm/npx: 'npm run build' and 'npx remotion' only. Arbitrary evaluation ('-e', '--eval') is forbidden.
- Docker: 'docker run clean-video-builder' and 'docker info' only. '--privileged' and root mounts forbidden.
- Universal: shell=False strictly enforced, CWD confined to workspace, bounded timeouts and output caps.
"""

import sys
import os
from pathlib import Path
from typing import List, Dict, Optional, Set, Any
from pydantic import BaseModel, Field


class CommandSecurityViolation(Exception):
    """Raised when a command violates the execution policy."""
    pass


class CommandValidationResult(BaseModel):
    """Result of command policy evaluation."""
    is_allowed: bool
    sanitized_cmd: List[str]
    executable: str
    subcommand: Optional[str] = None
    sanitized_env: Dict[str, str] = Field(default_factory=dict)
    timeout_seconds: int = 900
    max_output_bytes: int = 50 * 1024 * 1024
    cwd: Path
    violations: List[str] = Field(default_factory=list)


# Allowed script targets for Python executions
ALLOWED_PYTHON_SCRIPTS: Set[str] = {
    "scripts/pipeline.py",
    "scripts/validators/validate_schemas.py",
    "scripts/render_project.py",
    "scripts/maintenance/scene_compiler.py",
    ".agents/guardian/post_executor.py",
    "scripts/scaffold_project.py",
    "scripts/archive/migrate_state.py",
    "scripts/validators/template_lint.py",
    "scripts/metrics/benchmark_guards.py",
    "scripts/gates/asset_gate.py",
    "scripts/gates/plan_gate.py",
    "scripts/gates/taste_gate.py",
    "scripts/gates/validate_blueprint.py",
    "scripts/gates/motion_validator.py",
    "scripts/gates/code_template_gate.py",
    "scripts/generators/materialize_project.py",
    "scripts/gates/probe_qc.py",
    "scripts/gates/final_qc.py",
    "scripts/open_studio.py",
}

# In Development/Test, only approved test runners are permitted via '-m'
ALLOWED_DEV_TEST_PYTHON_MODULES: Set[str] = {
    "pytest",
    "unittest",
}

# In Production, by default NO '-m' module invocations are permitted.
# Runtime package or environment manipulation tools (like pip/venv) are strictly prohibited.
ALLOWED_PRODUCTION_PYTHON_MODULES: Set[str] = set()

# Universal dangerous flags prohibited across all executables
UNIVERSAL_DANGEROUS_FLAGS: Set[str] = {
    "--interactive",
    "-i",
}

# Node-specific evaluation flags prohibited
NODE_DANGEROUS_FLAGS: Set[str] = {
    "-e",
    "--eval",
}

# Environment variables prohibited from passing into production child processes
FORBIDDEN_PRODUCTION_ENV_VARS: Set[str] = {
    "SKIP_STRICT_QC",
    "AGY_IS_MANAGED",
    "AGY_FAILURE_INJECTION_ENABLED",
    "AGY_INJECT_FAILURE",
}


class CommandPolicy:
    """Canonical evaluator for command line execution safety."""

    DEFAULT_TIMEOUT_SECONDS: int = 900
    MAX_TIMEOUT_SECONDS: int = 1800
    MIN_TIMEOUT_SECONDS: int = 5
    DEFAULT_MAX_OUTPUT_BYTES: int = 50 * 1024 * 1024  # 50 MB

    @classmethod
    def get_canonical_python_executable(cls) -> str:
        """Return the running Python interpreter path (sys.executable).
        
        Resolves DISC-004: Never use loose 'python' from PATH.
        """
        return str(Path(sys.executable).resolve())

    @classmethod
    def sanitize_environment(
        cls,
        base_env: Optional[Dict[str, str]] = None,
        workspace_root: Optional[Path] = None,
        is_production: bool = True
    ) -> Dict[str, str]:
        """Construct a sanitized environment dict for child processes."""
        raw = os.environ.copy() if base_env is None else base_env.copy()
        clean: Dict[str, str] = {}

        # Allowlist of safe runtime environment keys
        safe_keys = {
            "PATH", "SYSTEMROOT", "HOME", "USER", "LANG", "LC_ALL",
            "PYTHONPATH", "TMPDIR", "TEMP", "TMP", "NODE_ENV", "VIRTUAL_ENV",
            "AGY_RUN_ID", "AGY_SPAN_ID", "AGY_ATTEMPT", "AGY_PROJECT_ID", "AGY_IS_MANAGED",
            "DISPLAY", "SVM_DATA_DIR", "SVM_PLUGIN_ROOT", "WHISPER_DEVICE",
        }

        if not is_production:
            safe_keys.update({"SKIP_STRICT_QC", "DEBUG_SECURITY"})

        for k, v in raw.items():
            if k in safe_keys or k.endswith("_API_KEY") or k.endswith("_TOKEN") or k.startswith("MOTION_"):
                if is_production and k in FORBIDDEN_PRODUCTION_ENV_VARS:
                    # Strip bypass flags in production
                    continue
                clean[k] = v

        # Enforce canonical PYTHONPATH to workspace and active virtual environment packages
        pythonpath_parts = []
        if workspace_root:
            pythonpath_parts.append(str(Path(workspace_root).resolve()))
        else:
            pythonpath_parts.append(str(Path.cwd().resolve()))
        existing_pp = raw.get("PYTHONPATH", "")
        if existing_pp:
            for p in existing_pp.split(os.pathsep):
                if p and p not in pythonpath_parts:
                    pythonpath_parts.append(p)
        for p in sys.path:
            if "site-packages" in p and p not in pythonpath_parts:
                pythonpath_parts.append(p)
        clean["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)

        return clean

    @classmethod
    def validate_command(
        cls,
        cmd: List[str],
        cwd: Optional[Path] = None,
        workspace_root: Optional[Path] = None,
        timeout: Optional[int] = None,
        is_production: bool = True
    ) -> CommandValidationResult:
        """Validate a command against the executable-aware canonical policy."""
        violations: List[str] = []

        if not cmd or not isinstance(cmd, (list, tuple)):
            raise CommandSecurityViolation("Command must be a non-empty list of string arguments.")

        cmd_list = [str(arg) for arg in cmd]
        raw_exe = cmd_list[0]
        exe_name = Path(raw_exe).name.lower()
        if exe_name.endswith(".exe"):
            exe_name = exe_name[:-4]

        # Determine target working directory
        root = Path(workspace_root or Path.cwd()).resolve()
        effective_cwd = Path(cwd).resolve() if cwd else root

        # Check CWD confinement
        try:
            effective_cwd.relative_to(root.resolve())
        except ValueError:
            violations.append(f"CWD '{effective_cwd}' escapes workspace root '{root}'.")

        # Universal dangerous flags check
        for arg in cmd_list[1:]:
            if arg in UNIVERSAL_DANGEROUS_FLAGS:
                # In ffmpeg/ffprobe, '-i' specifies input file, not interactive mode
                if arg == "-i" and exe_name in ("ffmpeg", "ffprobe"):
                    continue
                violations.append(f"Dangerous flag '{arg}' is strictly prohibited.")

        # Timeout validation
        effective_timeout = timeout or cls.DEFAULT_TIMEOUT_SECONDS
        if effective_timeout < cls.MIN_TIMEOUT_SECONDS or effective_timeout > cls.MAX_TIMEOUT_SECONDS:
            violations.append(
                f"Timeout {effective_timeout}s outside allowed range "
                f"[{cls.MIN_TIMEOUT_SECONDS}s - {cls.MAX_TIMEOUT_SECONDS}s]."
            )

        sanitized_cmd = list(cmd_list)
        subcommand: Optional[str] = None

        # ─── Executable-Aware Policy Branches ───

        # 1. PYTHON POLICY
        if exe_name in ("python", "python3") or raw_exe == sys.executable:
            # Enforce sys.executable resolution (DISC-004)
            sanitized_cmd[0] = cls.get_canonical_python_executable()

            # Inline code execution '-c' is strictly forbidden anywhere in arguments
            if "-c" in cmd_list[1:]:
                violations.append("Dangerous flag '-c' (inline code execution) is strictly prohibited.")

            if len(cmd_list) < 2:
                violations.append("Python command must specify a target script or module (-m).")
            else:
                first_arg = cmd_list[1]
                
                # Check for module invocation (-m)
                if first_arg == "-m":
                    if len(cmd_list) < 3:
                        violations.append("Python '-m' requires a target module name.")
                    else:
                        module_name = cmd_list[2]
                        if is_production:
                            # In Production, all python -m invocations are denied by default
                            if module_name not in ALLOWED_PRODUCTION_PYTHON_MODULES:
                                violations.append(
                                    f"Python module '-m {module_name}' is DENIED in production. "
                                    "Runtime module execution via -m is prohibited in production to preserve hermetic execution."
                                )
                            else:
                                subcommand = f"-m {module_name}"
                        else:
                            # In Development / Test, only explicitly approved test modules are allowed
                            if module_name not in ALLOWED_DEV_TEST_PYTHON_MODULES:
                                violations.append(
                                    f"Python module '-m {module_name}' is not in the allowed development modules registry. "
                                    f"Allowed: {sorted(list(ALLOWED_DEV_TEST_PYTHON_MODULES))}. "
                                    "Runtime package or environment manipulation tools (like pip/venv) are prohibited from runtime execution."
                                )
                            else:
                                subcommand = f"-m {module_name}"
                else:
                    script_arg = first_arg.replace("\\", "/")
                    if script_arg.startswith("./"):
                        script_arg = script_arg[2:]

                    subcommand = script_arg
                    # Match against allowed scripts
                    matched = any(script_arg == allowed or script_arg.endswith("/" + allowed) for allowed in ALLOWED_PYTHON_SCRIPTS)
                    if not matched:
                        violations.append(f"Python script '{script_arg}' is not in the allowed scripts registry.")

        # 2. NODE / NPM / NPX POLICY
        elif exe_name in ("npm", "npm.cmd", "npx", "npx.cmd", "node", "node.exe"):
            # Check for node eval flags
            for arg in cmd_list[1:]:
                if arg in NODE_DANGEROUS_FLAGS:
                    violations.append(f"Dangerous flag / Node flag '{arg}' (arbitrary evaluation) is strictly prohibited.")

            if exe_name in ("npm", "npm.cmd"):
                if len(cmd_list) < 3 or cmd_list[1] != "run" or cmd_list[2] != "build":
                    violations.append(f"NPM only allows 'npm run build'. Received: {' '.join(cmd_list)}")
                subcommand = "run build"
            elif exe_name in ("npx", "npx.cmd"):
                if len(cmd_list) < 2 or cmd_list[1] != "remotion":
                    violations.append(f"NPX only allows 'npx remotion'. Received: {' '.join(cmd_list)}")
                subcommand = "remotion"
            elif exe_name in ("node", "node.exe"):
                violations.append("Direct 'node' execution is not permitted; use npm or npx remotion.")

        # 3. FFMPEG / FFPROBE POLICY
        elif exe_name in ("ffmpeg", "ffprobe"):
            subcommand = cmd_list[1] if len(cmd_list) > 1 else None

        # 4. DOCKER POLICY
        elif exe_name == "docker":
            if len(cmd_list) < 2:
                violations.append("Docker command missing subcommand.")
            else:
                subcommand = cmd_list[1]
                if subcommand not in ("run", "info", "build"):
                    violations.append(f"Docker subcommand '{subcommand}' is forbidden. Allowed: ['run', 'info', 'build']")

                if subcommand == "run":
                    full_str = " ".join(cmd_list)
                    if "--privileged" in cmd_list:
                        violations.append("Docker --privileged is forbidden.")
                    if "-v /:" in full_str or "--volume /:" in full_str:
                        violations.append("Docker root filesystem mount is forbidden.")

                if subcommand == "build":
                    if "--privileged" in cmd_list:
                        violations.append("Docker --privileged is forbidden.")

        else:
            violations.append(f"Executable '{raw_exe}' is not in the allowed executables registry.")

        sanitized_env = cls.sanitize_environment(workspace_root=root, is_production=is_production)

        is_allowed = len(violations) == 0
        return CommandValidationResult(
            is_allowed=is_allowed,
            sanitized_cmd=sanitized_cmd,
            executable=sanitized_cmd[0],
            subcommand=subcommand,
            sanitized_env=sanitized_env,
            timeout_seconds=effective_timeout,
            max_output_bytes=cls.DEFAULT_MAX_OUTPUT_BYTES,
            cwd=effective_cwd,
            violations=violations
        )
