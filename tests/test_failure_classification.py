import pytest
import os
import sys
from pathlib import Path

# Add root directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from scripts.failure_model import FailureInfo, FailureCode, FailureCategory, Severity, get_failure_metadata

def test_consistency_of_defined_codes():
    """Every defined FailureCode must have corresponding metadata in the registry."""
    for code in FailureCode:
        meta = get_failure_metadata(code)
        # Should not fall back to INTERNAL_ERROR for known codes unless it IS INTERNAL_ERROR
        if code != FailureCode.UNEXPECTED_INTERNAL_ERROR and code != FailureCode.GATE_EXECUTION_FAILED:
            assert meta.category != FailureCategory.INTERNAL_ERROR, f"Code {code.name} is missing from metadata registry and fell back to INTERNAL_ERROR."
        
        assert isinstance(meta.retryable, bool)
        assert isinstance(meta.recoverable, bool)
        assert isinstance(meta.user_action_required, bool)
        assert isinstance(meta.severity, Severity)

def test_timeout_retryable():
    meta = get_failure_metadata(FailureCode.RENDER_TIMEOUT)
    assert meta.category == FailureCategory.TIMEOUT
    assert meta.retryable is True
    assert meta.recoverable is True
    assert meta.severity == Severity.WARNING

def test_validation_error_not_retryable():
    meta = get_failure_metadata(FailureCode.PROJECT_NOT_LOCKED)
    assert meta.category == FailureCategory.VALIDATION_ERROR
    assert meta.retryable is False
    assert meta.recoverable is True

def test_unknown_exception_fallback():
    info = FailureInfo(
        code=FailureCode.UNEXPECTED_INTERNAL_ERROR,
        message="Something went completely wrong",
        cause_type="ZeroDivisionError",
        is_fallback=True
    )
    
    assert info.is_fallback is True
    assert info.metadata.category == FailureCategory.INTERNAL_ERROR
    assert info.metadata.severity == Severity.CRITICAL
    
    data = info.to_dict()
    assert data["is_fallback"] is True
    assert data["error_category"] == "INTERNAL_ERROR"

def test_failure_info_dict():
    info = FailureInfo(
        code=FailureCode.PLAN_GATE_REJECTED,
        message="Plan invalid",
        cause_type="ValueError",
        stage="plan",
        component="plan_gate"
    )
    data = info.to_dict()
    assert data["error_code"] == "PLAN_GATE_REJECTED"
    assert data["error_category"] == "GATE_FAILURE"
    assert data["severity"] == "WARNING"
    assert data["retryable"] is False
    assert data["recoverable"] is True
    assert data["user_action_required"] is True
    assert data["error_message"] == "Plan invalid"
    assert data["cause_type"] == "ValueError"
    assert data["is_fallback"] is False
