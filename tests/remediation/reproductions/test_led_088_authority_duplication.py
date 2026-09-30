"""
Reproduction test for LED-088: Source of Truth scattered across Domains without a
machine-readable Contract Authority Matrix.
"""
import pytest
from pathlib import Path


def test_led_088_authority_duplication_detectable():
    """
    Finding: LED-088 (Source of Truth scattered across Domains)
    Prior to S10, the system lacks a machine-readable Contract Authority Matrix.
    There is no authoritative API to answer:
      - What is the canonical authority for a given domain?
      - What are the generated representations?
      - What is the unknown-field policy?
      - Who is the migration owner?
    """
    try:
        from scripts.core.authority_matrix import ContractAuthorityMatrix, GovernedDomain
        matrix_available = True
    except ImportError:
        matrix_available = False

    # This assertion verifies that prior to S10 implementation, the matrix API does not exist.
    assert matrix_available, (
        "DEFECT PROVEN (LED-088): No machine-readable ContractAuthorityMatrix exists on HEAD. "
        "Domain authorities and generated representations are scattered across TS/Python/Schemas "
        "without an executable single source of truth."
    )
