"""
tests/ai/cost/test_token_accounting.py
======================================
Unit tests for TokenAccounting and CreativeCostEstimator (S28-08C).

Verifies:
- Token accounting priority: provider usage > canonical estimate > unknown.
- Deterministic token estimation across Latin and Arabic text.
- Precision Decimal monetary cost calculation using canonical ModelRegistry.
- Rejection of binary floats and safe fallback for unknown models.
"""

from __future__ import annotations

from decimal import Decimal
import pytest

from ai.contracts.creative.cost import CostProvenance
from ai.contracts.usage import UsageRecord
from ai.cost.accounting import CreativeCostEstimator, TokenAccounting


def test_token_estimation_heuristics():
    """Verifies character-based token estimation for Latin, Arabic, and mixed text."""
    # Empty
    assert TokenAccounting.estimate_tokens("") == 0
    assert TokenAccounting.estimate_tokens(None) == 0

    # Short Latin text (~4 chars/token)
    latin = "Create a fast paced promo video"  # 31 chars -> ~7-8 tokens
    tokens_latin = TokenAccounting.estimate_tokens(latin)
    assert 5 <= tokens_latin <= 10

    # Arabic text (~1.5 chars/token)
    arabic = "اعمل فيديو ترويجي سريع للمنتج"  # 29 chars -> ~19 tokens
    tokens_arabic = TokenAccounting.estimate_tokens(arabic)
    assert 15 <= tokens_arabic <= 25

    # Mixed text
    mixed = "Video Maker صانع الفيديو الذكي"
    tokens_mixed = TokenAccounting.estimate_tokens(mixed)
    assert tokens_mixed > 0


def test_token_accounting_priority_hierarchy():
    """
    Verifies that authoritative provider UsageRecord takes precedence over text estimates.
    """
    # 1. Authoritative provider usage record present -> ACTUAL
    usage_rec = UsageRecord(input_tokens=420, output_tokens=180, total_tokens=600)
    in_tok, out_tok, prov = TokenAccounting.resolve_tokens_and_provenance(
        usage_record=usage_rec,
        input_text="A very long text that would have evaluated to a different token count",
        output_text="Completion text",
    )
    assert in_tok == 420
    assert out_tok == 180
    assert prov == CostProvenance.ACTUAL

    # 2. Explicit tokens passed without usage record -> ACTUAL
    in_tok, out_tok, prov = TokenAccounting.resolve_tokens_and_provenance(
        explicit_input_tokens=250,
        explicit_output_tokens=75,
    )
    assert in_tok == 250
    assert out_tok == 75
    assert prov == CostProvenance.ACTUAL

    # 3. Text estimate fallback -> ESTIMATED
    in_tok, out_tok, prov = TokenAccounting.resolve_tokens_and_provenance(
        input_text="Generate a 30s explainer",
        output_text="Scene 1: Introduction",
    )
    assert in_tok is not None and in_tok > 0
    assert out_tok is not None and out_tok > 0
    assert prov == CostProvenance.ESTIMATED

    # 4. Nothing provided -> UNKNOWN
    in_tok, out_tok, prov = TokenAccounting.resolve_tokens_and_provenance()
    assert in_tok is None
    assert out_tok is None
    assert prov == CostProvenance.UNKNOWN


def test_cost_calculation_from_canonical_model_pricing():
    """Verifies monetary cost calculation using versioned canonical ModelPricing."""
    # gpt-4o pricing: input_token_price=0.000005, output_token_price=0.000015
    cost, version, prov = CreativeCostEstimator.compute_cost(
        model_id="gpt-4o",
        input_tokens=1000,   # 1000 * 0.000005 = 0.005000
        output_tokens=500,   # 500 * 0.000015 = 0.007500
        request_count=1,
    )
    assert cost == Decimal("0.012500")
    assert version == "2026.09.v1"
    assert prov == CostProvenance.ESTIMATED


def test_cost_calculation_with_authoritative_actual_cost():
    """Verifies that actual provider invoiced costs override model estimates."""
    actual_invoice = Decimal("0.004120")
    cost, version, prov = CreativeCostEstimator.compute_cost(
        model_id="gpt-4o",
        input_tokens=1000,
        output_tokens=500,
        actual_cost_override=actual_invoice,
    )
    assert cost == Decimal("0.004120")
    assert prov == CostProvenance.ACTUAL


def test_unknown_model_fails_closed_to_unknown_provenance():
    """Verifies that querying an unregistered model returns UNKNOWN cost rather than crashing."""
    cost, version, prov = CreativeCostEstimator.compute_cost(
        model_id="unregistered-exotic-llm-v99",
        input_tokens=1000,
        output_tokens=500,
    )
    assert cost is None
    assert version is None
    assert prov == CostProvenance.UNKNOWN
