"""Pytest configuration for S02 Acceptance Contracts."""

import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "acceptance: mark test as S02 acceptance contract test")
