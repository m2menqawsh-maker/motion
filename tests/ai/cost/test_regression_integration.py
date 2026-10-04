"""
tests/ai/cost/test_regression_integration.py
============================================
Integration tests uniting S28-08C Cost & Efficiency with the S28-08B Trace Grader.

Verifies:
- Reusing canonical TOOL_INVOCATION_COUNT_IN_RANGE to enforce tool execution bounds.
- Detecting duplicate planner calls via trace assertions.
- Enforcing zero generation under REUSE via trace assertions.
- Catching CREATE tier bypass via trace value equality.
"""

from __future__ import annotations

import pytest

from ai.contracts.creative.regression import (
    TraceAssertion,
    TraceAssertionType,
)
from ai.regression.trace_grader import CreativeTraceGrader


@pytest.fixture
def trace_grader():
    return CreativeTraceGrader()


def test_trace_grader_bounds_duplicate_planner_calls(trace_grader: CreativeTraceGrader):
    """
    Verifies that TOOL_INVOCATION_COUNT_IN_RANGE flags duplicate planner invocations.
    """
    assertion = TraceAssertion(
        assertion_type=TraceAssertionType.TOOL_INVOCATION_COUNT_IN_RANGE,
        target_event_or_span="creative_planner",
        min_count=1,
        max_count=1,
    )

    # Valid trace: 1 planner call
    valid_trace = [
        {"name": "intent_parsed", "video_type": "Product Ad"},
        {"name": "creative_planner", "plan_id": "plan_01"},
    ]
    res_valid = trace_grader.grade_assertion(assertion, valid_trace)
    assert res_valid.passed is True
    assert "invoked 1 time(s)" in res_valid.details

    # Defective trace: 2 duplicate planner calls
    defective_trace = [
        {"name": "intent_parsed", "video_type": "Product Ad"},
        {"name": "creative_planner", "plan_id": "plan_01"},
        {"name": "creative_planner", "plan_id": "plan_01"},
    ]
    res_defective = trace_grader.grade_assertion(assertion, defective_trace)
    assert res_defective.passed is False
    assert "invoked 2 time(s)" in res_defective.details


def test_trace_grader_forbids_generation_under_reuse(trace_grader: CreativeTraceGrader):
    """
    Verifies that TOOL_INVOCATION_COUNT_IN_RANGE enforces zero generation calls under REUSE.
    """
    assertion = TraceAssertion(
        assertion_type=TraceAssertionType.TOOL_INVOCATION_COUNT_IN_RANGE,
        target_event_or_span="media_generator",
        min_count=0,
        max_count=0,
    )

    # Trace A: Pure REUSE, zero media generation
    trace_clean = [
        {"name": "tier_selection", "selected_tier": "REUSE"},
        {"name": "template_resolved", "template_id": "tmpl_bold"},
    ]
    res_clean = trace_grader.grade_assertion(assertion, trace_clean)
    assert res_clean.passed is True

    # Trace B: Defective execution invoking generation despite REUSE
    trace_defective = [
        {"name": "tier_selection", "selected_tier": "REUSE"},
        {"name": "media_generator", "operation": "generate_scene_video"},
    ]
    res_defective = trace_grader.grade_assertion(assertion, trace_defective)
    assert res_defective.passed is False
    assert "invoked 1 time(s)" in res_defective.details


def test_trace_grader_bounds_excessive_tool_invocations(trace_grader: CreativeTraceGrader):
    """
    Verifies that excessive external tool calls are caught by TOOL_INVOCATION_COUNT_IN_RANGE.
    """
    assertion = TraceAssertion(
        assertion_type=TraceAssertionType.TOOL_INVOCATION_COUNT_IN_RANGE,
        target_event_or_span="knowledge_search",
        min_count=1,
        max_count=3,
    )

    # Excessive trace: 5 searches
    excessive_trace = [{"name": "knowledge_search", "query_id": f"q_{i}"} for i in range(5)]
    res = trace_grader.grade_assertion(assertion, excessive_trace)
    assert res.passed is False
    assert "invoked 5 time(s)" in res.details


def test_trace_grader_catches_create_bypass_of_reuse(trace_grader: CreativeTraceGrader):
    """
    Verifies that SELECTED_VALUE_EQUALS catches tier selection regression
    when CREATE is illegally picked instead of REUSE.
    """
    assertion = TraceAssertion(
        assertion_type=TraceAssertionType.SELECTED_VALUE_EQUALS,
        target_event_or_span="tier_decision",
        field_path="selected_tier",
        expected_value="REUSE",
    )

    # Trace with CREATE defect
    defective_trace = [
        {"name": "tier_decision", "selected_tier": "CREATE", "reason": "ai_hallucination"},
    ]
    res = trace_grader.grade_assertion(assertion, defective_trace)
    assert res.passed is False
    assert "expected 'REUSE', got 'CREATE'" in res.details
