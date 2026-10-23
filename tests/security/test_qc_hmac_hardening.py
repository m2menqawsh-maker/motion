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


def test_legacy_sha256_seal_fails_with_clear_message(tmp_path, monkeypatch, capsys):
    """
    Requirement:
    Old reports using sha256(data+salt) fail verification in an understandable way,
    warning about legacy non-HMAC format.
    """
    salt_val = "legacy-salt-string-for-backward-check"
    monkeypatch.setenv("QC_HMAC_SALT", salt_val)

    report_path = tmp_path / "probe_qc_report.json"
    data = b'{"status": "PASS", "legacy": true}'
    report_path.write_bytes(data)

    # Legacy vulnerable format: sha256(data + salt)
    legacy_checksum = hashlib.sha256(data + salt_val.encode("utf-8")).hexdigest()
    seal_path = tmp_path / "probe_qc_report.json.seal"
    seal_path.write_text(legacy_checksum, encoding="utf-8")

    # Must fail verification
    assert verify_seal(report_path) is False

    captured = capsys.readouterr()
    assert "تنسيق ختم قديم غير آمن" in captured.out or "HMAC" in captured.out
