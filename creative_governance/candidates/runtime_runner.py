"""
creative_governance/candidates/runtime_runner.py
===============================
Adapter delegating isolated candidate runtime execution to scripts.validators.candidate_runtime_runner.
Complying strictly with ADR-004 DEC-01 (zero raw filesystem writes in creative_governance/candidates/).
"""

from __future__ import annotations

from scripts.validators.candidate_runtime_runner import (
    CandidateRenderResult,
    IsolatedCandidateRunner,
)

__all__ = [
    "CandidateRenderResult",
    "IsolatedCandidateRunner",
]
