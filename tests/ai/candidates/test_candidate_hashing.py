"""
tests/ai/candidates/test_candidate_hashing.py
=============================================
Deterministic server-side content hashing tests for TemplateCandidate (S28-07A).

Invariants:
- Deterministic canonical hashing produces identical hash for identical content.
- Invariant to key ordering or dependency ordering.
- Any semantic mutation (source code, schema, dependencies, fixtures, provenance)
  produces a completely different hash.
- Server-side generated; never accepts client/model hash.
"""

from __future__ import annotations

import pytest
from creative_governance.candidates.hashing import compute_candidate_content_hash


def test_deterministic_hashing_identity():
    kwargs = {
        "source_code": "export const Button = () => <button>Click</button>;",
        "template_schema": {"type": "object", "properties": {"label": {"type": "string"}}},
        "dependencies": ["clsx@^2.0.0", "framer-motion@^11.0.0"],
        "fixtures": {"label": "Get Started"},
        "why_reuse_failed": "No button template with spring physics exists.",
        "why_compose_failed": "Primitive Lego blocks lack integrated physics hook.",
        "creative_plan_reference": "cplan_tech_001",
        "creative_tier_decision_reference": "tier_dec_001",
    }

    hash1 = compute_candidate_content_hash(**kwargs)
    hash2 = compute_candidate_content_hash(**kwargs)

    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256


def test_dependency_order_invariance():
    base_kwargs = {
        "source_code": "export const X = () => null;",
        "template_schema": {},
        "fixtures": {},
        "why_reuse_failed": "reason A",
        "why_compose_failed": "reason B",
        "creative_plan_reference": "cplan_1",
        "creative_tier_decision_reference": "dec_1",
    }

    hash1 = compute_candidate_content_hash(
        dependencies=["b-pkg", "a-pkg", "c-pkg"],
        **base_kwargs,
    )
    hash2 = compute_candidate_content_hash(
        dependencies=["a-pkg", "c-pkg", "b-pkg"],
        **base_kwargs,
    )

    assert hash1 == hash2


def test_source_code_mutation_changes_hash():
    base_kwargs = {
        "template_schema": {},
        "dependencies": [],
        "fixtures": {},
        "why_reuse_failed": "reason A",
        "why_compose_failed": "reason B",
        "creative_plan_reference": "cplan_1",
        "creative_tier_decision_reference": "dec_1",
    }

    h1 = compute_candidate_content_hash(source_code="export const A = 1;", **base_kwargs)
    h2 = compute_candidate_content_hash(source_code="export const A = 2;", **base_kwargs)

    assert h1 != h2


def test_schema_mutation_changes_hash():
    base_kwargs = {
        "source_code": "export const A = 1;",
        "dependencies": [],
        "fixtures": {},
        "why_reuse_failed": "reason A",
        "why_compose_failed": "reason B",
        "creative_plan_reference": "cplan_1",
        "creative_tier_decision_reference": "dec_1",
    }

    h1 = compute_candidate_content_hash(template_schema={"p1": "string"}, **base_kwargs)
    h2 = compute_candidate_content_hash(template_schema={"p1": "number"}, **base_kwargs)

    assert h1 != h2


def test_fixtures_mutation_changes_hash():
    base_kwargs = {
        "source_code": "export const A = 1;",
        "template_schema": {},
        "dependencies": [],
        "why_reuse_failed": "reason A",
        "why_compose_failed": "reason B",
        "creative_plan_reference": "cplan_1",
        "creative_tier_decision_reference": "dec_1",
    }

    h1 = compute_candidate_content_hash(fixtures={"theme": "dark"}, **base_kwargs)
    h2 = compute_candidate_content_hash(fixtures={"theme": "light"}, **base_kwargs)

    assert h1 != h2
