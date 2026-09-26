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

def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-reproductions", False):
        skip_reproduction = pytest.mark.skip(
            reason="Expected-RED remediation reproduction. Run explicitly with --run-reproductions"
        )
        for item in items:
            if "reproductions" in str(item.fspath):
                item.add_marker(skip_reproduction)
