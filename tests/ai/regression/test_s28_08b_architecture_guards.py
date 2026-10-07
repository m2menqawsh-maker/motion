"""
tests/ai/regression/test_s28_08b_architecture_guards.py
======================================================
Architectural boundaries and invariant enforcement for S28-08B.

Enforces:
1. Zero Runtime Authority: Regression runner and graders are purely observational.
2. Zero Registry Mutation: Running evals does not add, remove, or modify registered skills or knowledge.
3. Zero Memory Pollution: Running evals leaves tenant memory and candidate state intact.
4. Strict separation of concerns: Evals observe, grade, and report; production runtime decides and executes.
"""

import inspect
import pytest

from ai.regression.runner import CreativeRegressionRunner
from ai.regression.trace_grader import CreativeTraceGrader
from ai.regression.retrieval_grader import RetrievalGrader
from ai.regression.rubric_grader import RubricGrader


def test_graders_and_runner_have_no_mutation_methods():
    """Verifies that evaluation classes do not contain mutation or write methods."""
    prohibited_substrings = [
        "promote",
        "publish",
        "delete_template",
        "approve_candidate",
        "write_tenant_style",
        "mutate",
        "override_production",
    ]

    classes_to_check = [
        CreativeRegressionRunner,
        CreativeTraceGrader,
        RetrievalGrader,
        RubricGrader,
    ]

    for cls in classes_to_check:
        methods = inspect.getmembers(cls, predicate=inspect.isfunction)
        for name, _ in methods:
            for bad_word in prohibited_substrings:
                assert bad_word not in name.lower(), (
                    f"Class {cls.__name__} violates zero-runtime-authority boundary with method '{name}'"
                )


def test_runner_execution_leaves_skill_registry_intact():
    """Verifies executing full regression does not mutate or pollute SkillRegistry."""
    runner = CreativeRegressionRunner()
    initial_skills_count = len(runner.skill_registry.list_all())
    assert initial_skills_count > 0

    # Run full regression
    runner.run_all()

    final_skills_count = len(runner.skill_registry.list_all())
    assert initial_skills_count == final_skills_count, (
        f"Skill registry size changed from {initial_skills_count} to {final_skills_count} during eval!"
    )


def test_runner_execution_leaves_knowledge_catalog_intact():
    """Verifies executing full regression does not mutate or pollute KnowledgeRegistry."""
    runner = CreativeRegressionRunner()
    initial_docs_count = len(runner.knowledge_router.registry.list_all())
    assert initial_docs_count > 0

    # Run full regression
    runner.run_all()

    final_docs_count = len(runner.knowledge_router.registry.list_all())
    assert initial_docs_count == final_docs_count, (
        f"Knowledge catalog size changed from {initial_docs_count} to {final_docs_count} during eval!"
    )


def test_trace_grader_never_alters_input_traces():
    """Verifies CreativeTraceGrader does not mutate input trace event records."""
    grader = CreativeTraceGrader()
    original_trace = [
        {"name": "event_a", "val": 10},
        {"name": "event_b", "val": 20},
    ]
    # Pass a shallow copy of the list with original dicts
    trace_to_grade = list(original_trace)
    from ai.contracts.creative.regression import TraceAssertion, TraceAssertionType

    assertion = TraceAssertion(
        assertion_type=TraceAssertionType.EVENT_EXISTS,
        target_event_or_span="event_a",
        expected_value=10,
        field_path="val",
    )
    grader.grade_trace(trace_to_grade, [assertion])

    assert original_trace[0] == {"name": "event_a", "val": 10}
    assert original_trace[1] == {"name": "event_b", "val": 20}
