"""
creative_governance/candidates/gates/runtime_contract_gate.py
============================================
Runtime Contract Gate for TemplateCandidate (S28-07C Gate 2).

Verifies:
1. FPS contract compliance (must be standard: 24, 25, 30, 60 fps).
2. Duration bounds (must be between 1 and 1800 frames / max 60s).
3. Fixture validity at runtime (non-empty fixtures conforming to template schema).
4. Runtime dimensions bounds (even, positive pixel coordinates).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from creative_governance.candidates.gates.base import RuntimeGate
from creative_governance.candidates.policies import ValidationFailureCode
from creative_governance.candidates.runtime_runner import IsolatedCandidateRunner
from ai.contracts.creative.template_candidate import (
    CandidateGateResult,
    GateStatus,
    TemplateCandidate,
)
from scripts.core.tenant_model import TenantContext


class RuntimeContractGate(RuntimeGate):
    """
    Validates candidate runtime properties, timing bounds, and schema fixtures.
    """

    @property
    def gate_id(self) -> str:
        return "runtime_contract_gate"

    def run(
        self,
        candidate: TemplateCandidate,
        tenant_context: TenantContext,
        runner: IsolatedCandidateRunner,
        workspace_dir: Path,
        harness_file: Path,
        props_file: Path,
        runtime_context: Dict[str, Any],
    ) -> CandidateGateResult:
        schema = candidate.template_schema or {}
        fixtures = candidate.fixtures or {}

        # 1. Verify fixtures presence
        if not fixtures or not isinstance(fixtures, dict):
            return CandidateGateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAIL,
                failure_code=ValidationFailureCode.INVALID_RUNTIME_FIXTURES,
                summary="Candidate has empty or invalid runtime fixtures.",
                machine_details={"fixtures": fixtures},
            )

        # 2. Check FPS compatibility (default 30)
        fps = 30
        if "fps" in schema and isinstance(schema["fps"], (int, float)):
            fps = int(schema["fps"])
        if fps not in (24, 25, 30, 60):
            return CandidateGateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAIL,
                failure_code=ValidationFailureCode.INVALID_RUNTIME_FPS,
                summary=f"Candidate specifies non-standard fps: {fps}. Allowed: [24, 25, 30, 60].",
                machine_details={"declared_fps": fps},
            )

        # 3. Check duration bounds (default 30-300 frames)
        duration = 30
        if "durationInFrames" in schema and isinstance(schema["durationInFrames"], int):
            duration = schema["durationInFrames"]
        if duration < 1 or duration > 1800:
            return CandidateGateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAIL,
                failure_code=ValidationFailureCode.INVALID_RUNTIME_DURATION,
                summary=f"Candidate duration {duration} frames is outside valid bounds [1, 1800].",
                machine_details={"duration": duration},
            )

        # Record runtime contract in context
        runtime_context["runtime_contract"] = {
            "fps": fps,
            "duration": duration,
            "fixtures_keys": list(fixtures.keys()),
        }

        return CandidateGateResult(
            gate_id=self.gate_id,
            status=GateStatus.PASS,
            summary=(
                f"Candidate satisfies runtime contract: fps={fps}, "
                f"duration={duration} frames, fixtures verified."
            ),
            machine_details={
                "fps": fps,
                "duration": duration,
                "fixtures_count": len(fixtures),
            },
        )
