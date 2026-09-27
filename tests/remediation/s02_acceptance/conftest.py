"""Pytest configuration for S02 Acceptance Contracts."""

import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "acceptance: mark test as S02 acceptance contract test")


def pytest_addoption(parser):
    try:
        parser.addoption(
            "--run-acceptance",
            action="store_true",
            default=False,
            help="Run RED acceptance contract tests for S02 security enforcement"
        )
    except ValueError:
        pass


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--run-acceptance", False):
        skip_acceptance = pytest.mark.skip(
            reason="Expected-RED S02 Acceptance Contract. Run explicitly with --run-acceptance"
        )
        for item in items:
            if "s02_acceptance" in str(item.fspath):
                item.add_marker(skip_acceptance)
