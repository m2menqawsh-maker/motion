import os
import hmac
import hashlib
import pytest
from pathlib import Path

from scripts.gates.probe_qc import (
    get_qc_salt,
    compute_seal,
    verify_seal,
)


def test_qc_hmac_salt_missing_fails_explicitly(tmp_path, monkeypatch):
    """
    Requirement 1:
    QC_HMAC_SALT environment variable is strictly mandatory.
    Without it, probe_qc must fail explicitly (no silent fallback to file,
    no automatic salt generation).
    """
    monkeypatch.delenv("QC_HMAC_SALT", raising=False)

    report_path = tmp_path / "probe_qc_report.json"
    report_path.write_text('{"status": "PASS"}', encoding="utf-8")
    seal_path = tmp_path / "probe_qc_report.json.seal"
    seal_path.write_text("some-seal", encoding="utf-8")

    with pytest.raises(RuntimeError, match="QC_HMAC_SALT environment variable is required"):
        get_qc_salt()

    with pytest.raises(RuntimeError, match="QC_HMAC_SALT environment variable is required"):
        verify_seal(report_path)


def test_qc_hmac_seal_and_verify_success(tmp_path, monkeypatch):
    """
    Requirement:
    HMAC verification succeeds with valid QC_HMAC_SALT and untampered report.
    """
    salt_val = "secure-random-hmac-salt-test-key-32b!"
    monkeypatch.setenv("QC_HMAC_SALT", salt_val)

    report_path = tmp_path / "probe_qc_report.json"
    content = '{"status": "PASS", "project_id": "prj_valid"}'
    report_path.write_text(content, encoding="utf-8")

    salt_bytes = get_qc_salt()
    assert salt_bytes == salt_val.encode("utf-8")

    # Generate HMAC-SHA256 seal
    seal = compute_seal(report_path.read_bytes(), salt_bytes)
    seal_path = tmp_path / "probe_qc_report.json.seal"
    seal_path.write_text(seal, encoding="utf-8")

    assert verify_seal(report_path) is True


def test_qc_hmac_tampered_report_fails(tmp_path, monkeypatch):
    """
    Requirement:
    Tampered report content fails verification.
    """
    salt_val = "secure-random-hmac-salt-test-key-32b!"
    monkeypatch.setenv("QC_HMAC_SALT", salt_val)

    report_path = tmp_path / "probe_qc_report.json"
    report_path.write_text('{"status": "PASS"}', encoding="utf-8")

    salt_bytes = get_qc_salt()
    seal = compute_seal(report_path.read_bytes(), salt_bytes)
    seal_path = tmp_path / "probe_qc_report.json.seal"
    seal_path.write_text(seal, encoding="utf-8")

    # Tamper with the report file
    report_path.write_text('{"status": "PASS", "tampered": true}', encoding="utf-8")

    assert verify_seal(report_path) is False


def test_qc_hmac_tampered_seal_fails(tmp_path, monkeypatch):
    """
    Requirement:
    Forged or altered seal fails verification.
    """
    salt_val = "secure-random-hmac-salt-test-key-32b!"
    monkeypatch.setenv("QC_HMAC_SALT", salt_val)

    report_path = tmp_path / "probe_qc_report.json"
    report_path.write_text('{"status": "PASS"}', encoding="utf-8")

    seal_path = tmp_path / "probe_qc_report.json.seal"
    seal_path.write_text("invalid_forged_seal_digest", encoding="utf-8")

    assert verify_seal(report_path) is False


def test_legacy_sha256_seal_strictly_rejected_without_legacy_code(tmp_path, monkeypatch, capsys):
    """
    Requirement (Fix 1):
    Old reports using sha256(data+salt) must be rejected outright without special legacy
    detection or legacy tolerance branches in verify_seal.
    """
    import inspect
    from scripts.gates.probe_qc import verify_seal

    # Assert legacy fallback/warning logic is completely eradicated from source code
    source = inspect.getsource(verify_seal)
    assert "legacy_actual" not in source, "Legacy sha256(data+salt) check still present in verify_seal source"
    assert "تنسيق ختم قديم" not in source, "Legacy seal warning branch still present in verify_seal source"

    salt_val = "legacy-salt-string-for-backward-check"
    monkeypatch.setenv("QC_HMAC_SALT", salt_val)

    report_path = tmp_path / "probe_qc_report.json"
    data = b'{"status": "PASS", "legacy": true}'
    report_path.write_bytes(data)

    # Valid legacy computation: sha256(data + salt)
    legacy_checksum = hashlib.sha256(data + salt_val.encode("utf-8")).hexdigest()
    seal_path = tmp_path / "probe_qc_report.json.seal"
    seal_path.write_text(legacy_checksum, encoding="utf-8")

    # Must fail verification
    assert verify_seal(report_path) is False

    captured = capsys.readouterr()
    assert "تنسيق ختم قديم غير آمن" not in captured.out
    assert "تقرير مزوّر" in captured.out or "غير متطابقة" in captured.out


def test_qc_hmac_production_mode_fails_without_env_var(monkeypatch):
    """
    Fix 5: Verify production path strictly fails without QC_HMAC_SALT.
    """
    monkeypatch.setenv("MOTION_ENV", "production")
    monkeypatch.delenv("QC_HMAC_SALT", raising=False)

    with pytest.raises(RuntimeError, match="QC_HMAC_SALT environment variable is required"):
        get_qc_salt()


def test_qc_hmac_production_mode_fails_on_weak_salt(monkeypatch):
    """
    Fix 5: Verify production path rejects weak salt (<16 characters).
    """
    monkeypatch.setenv("MOTION_ENV", "production")
    monkeypatch.setenv("QC_HMAC_SALT", "too-short")

    with pytest.raises(RuntimeError, match="QC_HMAC_SALT must be at least 16 characters in production"):
        get_qc_salt()


def test_env_example_and_ci_workflows_have_qc_hmac_salt():
    """
    Fix 5: Verify that .env.example and CI workflows have QC_HMAC_SALT declared.
    """
    repo_root = Path(__file__).resolve().parent.parent.parent

    # 1. .env.example
    env_example = repo_root / ".env.example"
    assert env_example.exists()
    assert "QC_HMAC_SALT=" in env_example.read_text(encoding="utf-8")

    # 2. remediation-ci.yml
    ci_file = repo_root / ".github" / "workflows" / "remediation-ci.yml"
    assert ci_file.exists()
    assert "QC_HMAC_SALT" in ci_file.read_text(encoding="utf-8")

    # 3. real-e2e-nightly.yml
    nightly_file = repo_root / ".github" / "workflows" / "real-e2e-nightly.yml"
    assert nightly_file.exists()
    assert "QC_HMAC_SALT" in nightly_file.read_text(encoding="utf-8")
