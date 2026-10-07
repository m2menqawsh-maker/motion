"""
tests/ai/regression/test_trace_grader.py
========================================
Comprehensive verification of CreativeTraceGrader assertion capabilities.
"""

import pytest

from ai.contracts.creative.regression import (
    TraceAssertion,
    TraceAssertionType,
)
from ai.regression.trace_grader import CreativeTraceGrader


@pytest.fixture
def grader() -> CreativeTraceGrader:
    return CreativeTraceGrader()


def test_event_exists_assertion(grader: CreativeTraceGrader):
    """Verifies EVENT_EXISTS passes when event is present with expected attributes."""
    trace = [
        {"name": "brief_parsed", "video_type": "SAAS_DEMO"},
        {"name": "recipe_selected", "selected_value": "rec_01"},
    ]
    assertion = TraceAssertion(
        assertion_type=TraceAssertionType.EVENT_EXISTS,
        target_event_or_span="recipe_selected",
        expected_value="rec_01",
    )
    passed, results = grader.grade_trace(trace, [assertion])
    assert passed
    assert len(results) == 1
    assert results[0].passed

    # Fails when expected value does not match
    bad_assertion = TraceAssertion(
        assertion_type=TraceAssertionType.EVENT_EXISTS,
        target_event_or_span="recipe_selected",
        expected_value="rec_wrong",
    )
    passed, results = grader.grade_trace(trace, [bad_assertion])
    assert not passed
    assert not results[0].passed


def test_event_absent_assertion(grader: CreativeTraceGrader):
    """Verifies EVENT_ABSENT passes when target event does NOT occur."""
    trace = [
        {"name": "brief_parsed"},
        {"name": "music_only_applied"},
    ]
    assertion = TraceAssertion(
        assertion_type=TraceAssertionType.EVENT_ABSENT,
        target_event_or_span="voiceover_synthesized",
    )
    passed, results = grader.grade_trace(trace, [assertion])
    assert passed

    # Fails when forbidden event is present
    bad_trace = trace + [{"name": "voiceover_synthesized"}]
    passed, results = grader.grade_trace(bad_trace, [assertion])
    assert not passed
    assert not results[0].passed


def test_ordered_before_assertion(grader: CreativeTraceGrader):
    """Verifies ORDERED_BEFORE enforces sequential occurrence order."""
    trace = [
        {"name": "reuse_evaluated", "timestamp": 100},
        {"name": "compose_evaluated", "timestamp": 200},
        {"name": "tier_selected", "timestamp": 300},
    ]
    assertion = TraceAssertion(
        assertion_type=TraceAssertionType.ORDERED_BEFORE,
        target_event_or_span="reuse_evaluated",
        secondary_target="compose_evaluated",
    )
    passed, results = grader.grade_trace(trace, [assertion])
    assert passed

    # Reverse order should fail
    reversed_assertion = TraceAssertion(
        assertion_type=TraceAssertionType.ORDERED_BEFORE,
        target_event_or_span="compose_evaluated",
        secondary_target="reuse_evaluated",
    )
    passed, results = grader.grade_trace(trace, [reversed_assertion])
    assert not passed
    assert not results[0].passed


def test_selected_value_equals_assertion(grader: CreativeTraceGrader):
    """Verifies SELECTED_VALUE_EQUALS matches extracted field paths."""
    trace = [
        {"name": "tier_decision", "selected_value": "REUSE", "aspect": "9:16"},
    ]
    assertion = TraceAssertion(
        assertion_type=TraceAssertionType.SELECTED_VALUE_EQUALS,
        target_event_or_span="tier_decision",
        field_path="selected_value",
        expected_value="REUSE",
    )
    passed, results = grader.grade_trace(trace, [assertion])
    assert passed

    assertion_wrong = TraceAssertion(
        assertion_type=TraceAssertionType.SELECTED_VALUE_EQUALS,
        target_event_or_span="tier_decision",
        field_path="selected_value",
        expected_value="CREATE",
    )
    passed, results = grader.grade_trace(trace, [assertion_wrong])
    assert not passed


def test_selected_value_in_set_assertion(grader: CreativeTraceGrader):
    """Verifies SELECTED_VALUE_IN_SET validates membership."""
    trace = [
        {"name": "recipe_chosen", "selected_value": "rec_saas_quick"},
    ]
    assertion = TraceAssertion(
        assertion_type=TraceAssertionType.SELECTED_VALUE_IN_SET,
        target_event_or_span="recipe_chosen",
        allowed_values=["rec_saas_quick", "rec_saas_deep"],
    )
    passed, results = grader.grade_trace(trace, [assertion])
    assert passed

    bad_assertion = TraceAssertion(
        assertion_type=TraceAssertionType.SELECTED_VALUE_IN_SET,
        target_event_or_span="recipe_chosen",
        allowed_values=["rec_avatar_01", "rec_podcast_01"],
    )
    passed, results = grader.grade_trace(trace, [bad_assertion])
    assert not passed


def test_forbidden_transition_absent(grader: CreativeTraceGrader):
    """Verifies FORBIDDEN_TRANSITION_ABSENT catches illegal state jumps."""
    clean_trace = [
        {"name": "state_changed", "from_state": "DRAFT", "to_state": "SUBMITTED"},
        {"name": "state_changed", "from_state": "SUBMITTED", "to_state": "VALIDATED"},
    ]
    assertion = TraceAssertion(
        assertion_type=TraceAssertionType.FORBIDDEN_TRANSITION_ABSENT,
        target_event_or_span="state_changed",
        field_path="to_state",
        forbidden_values=["PROMOTED"],  # Direct DRAFT -> PROMOTED forbidden
    )
    passed, results = grader.grade_trace(clean_trace, [assertion])
    assert passed

    bad_trace = [
        {"name": "state_changed", "from_state": "DRAFT", "to_state": "PROMOTED"},
    ]
    passed, results = grader.grade_trace(bad_trace, [assertion])
    assert not passed


def test_tool_invocation_count_in_range(grader: CreativeTraceGrader):
    """Verifies TOOL_INVOCATION_COUNT_IN_RANGE checks event frequency bounds."""
    trace = [
        {"name": "tool_invoked", "tool": "image_search"},
        {"name": "tool_invoked", "tool": "image_search"},
        {"name": "tool_invoked", "tool": "audio_preview"},
    ]
    assertion = TraceAssertion(
        assertion_type=TraceAssertionType.TOOL_INVOCATION_COUNT_IN_RANGE,
        target_event_or_span="tool_invoked",
        min_count=1,
        max_count=4,
    )
    passed, results = grader.grade_trace(trace, [assertion])
    assert passed

    exceeded_assertion = TraceAssertion(
        assertion_type=TraceAssertionType.TOOL_INVOCATION_COUNT_IN_RANGE,
        target_event_or_span="tool_invoked",
        min_count=4,
        max_count=10,
    )
    passed, results = grader.grade_trace(trace, [exceeded_assertion])
    assert not passed
