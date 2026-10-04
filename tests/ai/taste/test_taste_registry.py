"""
tests/ai/taste/test_taste_registry.py
=====================================
Tests for TasteRuleRegistry (S28-04 Part B).

Verifies:
1. Canonical rules loaded and structured with full provenance.
2. Provenance invariants: rules missing citation or source knowledge are rejected.
3. Severity semantics: MUST, SHOULD, PREFER, AVOID supported and validated.
4. Priority ordering: list_all returns rules sorted by priority descending.
5. Exception representation: rules specify explicit waiver conditions.
"""

import pytest
from ai.contracts.creative.taste import TasteRule, TasteRuleSeverity
from ai.taste.contracts import InvalidTasteRuleError
from ai.taste.registry import TasteRuleRegistry


@pytest.fixture
def registry():
    return TasteRuleRegistry()


def test_canonical_rules_seeded_with_provenance(registry):
    rules = registry.list_all()
    assert len(rules) >= 14, f"Expected at least 14 canonical rules, got {len(rules)}"

    # Every single rule must have valid provenance
    for rule in rules:
        assert rule.rule_id, "Rule must have a non-empty rule_id"
        assert rule.citation_source, f"Rule {rule.rule_id} missing citation_source"
        assert len(rule.source_knowledge_ids) > 0, f"Rule {rule.rule_id} missing source_knowledge_ids"
        assert rule.version == "1.0.0"
        assert 1 <= rule.priority <= 100


def test_rule_priority_sorting(registry):
    rules = registry.list_all()
    priorities = [r.priority for r in rules]
    # Verify sorted descending
    assert priorities == sorted(priorities, reverse=True)


def test_severity_levels_present(registry):
    rules = registry.list_all()
    severities = {r.severity for r in rules}
    assert TasteRuleSeverity.MUST in severities
    assert TasteRuleSeverity.SHOULD in severities
    assert TasteRuleSeverity.PREFER in severities
    assert TasteRuleSeverity.AVOID in severities


def test_missing_provenance_rejected(registry):
    """Anonymous rules without provenance cannot enter the registry."""
    with pytest.raises(InvalidTasteRuleError, match="missing citation_source"):
        registry.register(
            TasteRule(
                rule_id="anonymous_rule",
                category="test",
                name="Anon",
                description="desc",
                rationale="rat",
                citation_source="",  # Missing
                source_knowledge_ids=["know_test"],
            )
        )

    with pytest.raises(InvalidTasteRuleError, match="missing source_knowledge_ids"):
        registry.register(
            TasteRule(
                rule_id="anonymous_rule_2",
                category="test",
                name="Anon 2",
                description="desc",
                rationale="rat",
                citation_source="references/test.md",
                source_knowledge_ids=[],  # Missing
            )
        )


def test_rule_exception_representation(registry):
    rule = registry.get("taste_avoid_constant_motion")
    assert rule is not None
    assert "explosive_celebration_burst" in rule.exceptions
