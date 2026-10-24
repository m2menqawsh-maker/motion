"""
tests/security/test_command_policy_qc_salt.py
=============================================
Authoritative Security Verification for QC_HMAC_SALT propagation:
- probe_qc.py and final_qc.py must selectively receive QC_HMAC_SALT.
- General rendering and untrusted subprocesses must have QC_HMAC_SALT stripped.
"""

from scripts.core.security.command_policy import CommandPolicy


def test_sanitize_environment_preserves_qc_hmac_salt_for_probe_qc():
    """Authorized QC gate scripts/gates/probe_qc.py must receive QC_HMAC_SALT."""
    base_env = {
        "PATH": "/usr/bin",
        "QC_HMAC_SALT": "a" * 64,
        "OTHER_SECRET": "secret_val",
    }
    clean = CommandPolicy.sanitize_environment(
        base_env=base_env,
        target_script="scripts/gates/probe_qc.py",
        is_production=True,
    )
    assert "QC_HMAC_SALT" in clean, "QC_HMAC_SALT must be preserved for scripts/gates/probe_qc.py"
    assert clean["QC_HMAC_SALT"] == "a" * 64
    assert "OTHER_SECRET" not in clean


def test_sanitize_environment_preserves_qc_hmac_salt_for_final_qc():
    """Authorized QC gate scripts/gates/final_qc.py must receive QC_HMAC_SALT."""
    base_env = {
        "PATH": "/usr/bin",
        "QC_HMAC_SALT": "b" * 64,
    }
    clean = CommandPolicy.sanitize_environment(
        base_env=base_env,
        target_script="scripts/gates/final_qc.py",
        is_production=True,
    )
    assert "QC_HMAC_SALT" in clean, "QC_HMAC_SALT must be preserved for scripts/gates/final_qc.py"
    assert clean["QC_HMAC_SALT"] == "b" * 64


def test_sanitize_environment_preserves_qc_hmac_salt_for_pipeline():
    """Authorized pipeline orchestrator scripts/pipeline.py must receive QC_HMAC_SALT."""
    base_env = {
        "PATH": "/usr/bin",
        "QC_HMAC_SALT": "c" * 64,
    }
    clean = CommandPolicy.sanitize_environment(
        base_env=base_env,
        target_script="scripts/pipeline.py",
        is_production=True,
    )
    assert "QC_HMAC_SALT" in clean, "QC_HMAC_SALT must be preserved for scripts/pipeline.py"
    assert clean["QC_HMAC_SALT"] == "c" * 64


def test_sanitize_environment_strips_qc_hmac_salt_for_render_scripts():
    """Regular render scripts must have QC_HMAC_SALT stripped."""
    base_env = {
        "PATH": "/usr/bin",
        "QC_HMAC_SALT": "a" * 64,
    }
    clean = CommandPolicy.sanitize_environment(
        base_env=base_env,
        target_script="scripts/render_project.py",
        is_production=True,
    )
    assert "QC_HMAC_SALT" not in clean, "QC_HMAC_SALT must be stripped for scripts/render_project.py"


def test_sanitize_environment_strips_qc_hmac_salt_when_no_script():
    """Subprocesses without an authorized target script must have QC_HMAC_SALT stripped."""
    base_env = {
        "PATH": "/usr/bin",
        "QC_HMAC_SALT": "a" * 64,
    }
    clean = CommandPolicy.sanitize_environment(
        base_env=base_env,
        target_script=None,
        is_production=True,
    )
    assert "QC_HMAC_SALT" not in clean, "QC_HMAC_SALT must be stripped when target_script is None"
