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
