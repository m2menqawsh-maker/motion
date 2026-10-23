import inspect
import tempfile
from pathlib import Path
import pytest

import scripts.run_creative_cost_audit as cost_audit_mod


def test_no_insecure_mktemp_in_creative_cost_audit():
    """
    Item C requirement:
    Insecure and deprecated tempfile.mktemp must not be used in scripts/run_creative_cost_audit.py.
    Must use tempfile.mkstemp with closed file descriptor instead.
    """
    source = inspect.getsource(cost_audit_mod)
    assert "tempfile.mktemp" not in source, "Found insecure tempfile.mktemp in scripts/run_creative_cost_audit.py"
    assert "tempfile.mkstemp" in source, "Expected secure tempfile.mkstemp in scripts/run_creative_cost_audit.py"
    assert "os.close(fd)" in source or "os.close(" in source, "Expected file descriptor to be closed after mkstemp"


def test_run_cost_audit_executes_and_cleans_up(tmp_path):
    """
    Verifies run_cost_audit successfully runs with the hardened temporary file handling
    and cleans up temporary database.
    """
    report_file = tmp_path / "creative_cost_audit.json"
    audit_run = cost_audit_mod.run_cost_audit(
        workspace_id="ws_sec_test",
        output_path=report_file,
        include_defect_checks=False,
    )
    assert audit_run.verdict == "PASS"
    assert report_file.exists()


def test_exception_in_middle_of_run_cost_audit_cleans_up_temp_db(tmp_path, monkeypatch):
    """
    Point 3 requirement:
    Verify that an unhandled exception in the middle of run_cost_audit does NOT
    leak any temporary .db file on disk, due to the enclosing try/finally block.
    """
    created_db_paths = []
    real_mkstemp = tempfile.mkstemp

    def tracking_mkstemp(*args, **kwargs):
        fd, path = real_mkstemp(*args, **kwargs)
        created_db_paths.append(path)
        return fd, path

    monkeypatch.setattr(tempfile, "mkstemp", tracking_mkstemp)

    # Monkeypatch generate_baseline_telemetry to raise in the middle of the function
    def crashing_telemetry(*args, **kwargs):
        raise RuntimeError("Simulated failure in middle of cost audit execution")

    monkeypatch.setattr(cost_audit_mod, "generate_baseline_telemetry", crashing_telemetry)

    report_file = tmp_path / "crash_report.json"
    with pytest.raises(RuntimeError, match="Simulated failure in middle of cost audit execution"):
        cost_audit_mod.run_cost_audit(
            workspace_id="ws_crash_test",
            output_path=report_file,
            include_defect_checks=False,
        )

    # Assert that the temporary database file was created and then cleaned up by finally
    assert len(created_db_paths) == 1
    temp_db = Path(created_db_paths[0])
    assert not temp_db.exists(), f"Temporary database leaked at {temp_db} despite exception!"
