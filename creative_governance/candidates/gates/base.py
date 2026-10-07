"""
creative_governance/candidates/gates/base.py
===========================
Base interface for Static Validation Gates (S28-07B).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from ai.contracts.creative.template_candidate import (
    CandidateGateResult,
    GateStatus,
    TemplateCandidate,
)
from scripts.core.tenant_model import TenantContext


class StaticGate(ABC):
    """
    Abstract contract for an isolated, deterministic static validation gate (S28-07B).
    """

    @property
    @abstractmethod
    def gate_id(self) -> str:
        """Unique gate identifier."""
        raise NotImplementedError

    @abstractmethod
    def run(
        self,
        candidate: TemplateCandidate,
        tenant_context: TenantContext,
        ast_analysis: Optional[Dict[str, Any]] = None,
    ) -> CandidateGateResult:
        """
        Executes gate checks against the candidate and returns a CandidateGateResult.
        """
        raise NotImplementedError


class RuntimeGate(ABC):
    """
    Abstract contract for an isolated, deterministic runtime validation gate (S28-07C).
    """

    @property
    @abstractmethod
    def gate_id(self) -> str:
        """Unique gate identifier."""
        raise NotImplementedError

    @abstractmethod
    def run(
        self,
        candidate: TemplateCandidate,
        tenant_context: TenantContext,
        runner: Any,
        workspace_dir: Any,
        harness_file: Any,
        props_file: Any,
        runtime_context: Dict[str, Any],
    ) -> CandidateGateResult:
        """
        Executes runtime check against candidate and returns CandidateGateResult.
        """
        raise NotImplementedError

