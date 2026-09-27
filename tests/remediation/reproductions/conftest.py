import pytest

def pytest_addoption(parser):
    try:
        parser.addoption(
            "--run-reproductions",
            action="store_true",
            default=False,
            help="Run RED reproduction tests for remediation findings"
        )
    except ValueError:
        pass

CLOSED_REPRODUCTIONS = {
    "test_asset_009_path_traversal.py",
    "test_led_019_approval_bypass.py",
    "test_led_022_skip_strict_qc.py",
}

def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-reproductions", False):
        skip_reproduction = pytest.mark.skip(
            reason="Pending Expected-RED remediation reproduction for S03+ (run with --run-reproductions)"
        )
        for item in items:
            if "reproductions" in str(item.fspath):
                if item.fspath.basename not in CLOSED_REPRODUCTIONS:
                    item.add_marker(skip_reproduction)
