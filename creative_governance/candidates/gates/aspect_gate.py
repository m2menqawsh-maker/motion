"""
creative_governance/candidates/gates/aspect_gate.py
==================================
Aspect Ratio Gate for TemplateCandidate (S28-07C Gate 3).

Guarantees:
1. Candidate is tested against all declared supported aspect ratios.
2. Declared supported aspects are mapped to canonical dimensions (9:16, 16:9, 1:1, etc.).
3. Actual frame still is rendered and tested for each declared aspect.
4. If candidate declares support for an aspect but fails to render -> FAIL.
5. If candidate declares an unsupported or uncanonical aspect -> FAIL.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from creative_governance.candidates.gates.base import RuntimeGate
from creative_governance.candidates.policies import (
    CANONICAL_ASPECT_RATIOS,
    ValidationFailureCode,
)
from creative_governance.candidates.runtime_runner import CandidateRenderResult, IsolatedCandidateRunner
from ai.contracts.creative.template_candidate import (
    CandidateGateResult,
    GateStatus,
    TemplateCandidate,
)
from scripts.core.tenant_model import TenantContext


def extract_declared_aspect_ratios(candidate: TemplateCandidate) -> List[str]:
    """
    Extracts declared supported aspect ratios from candidate schema or tags.
    Defaults to ['9:16'] if none explicitly declared.
    """
    schema = candidate.template_schema or {}
    declared: List[str] = []

    # 1. From schema explicit fields
    for field in ("aspect_ratios", "supported_aspect_ratios", "aspectRatio", "aspect_ratio"):
        val = schema.get(field)
        if isinstance(val, list):
            for v in val:
                if isinstance(v, str) and v.strip() and v.strip() not in declared:
                    declared.append(v.strip())
        elif isinstance(val, str) and val.strip() and val.strip() not in declared:
            declared.append(val.strip())

    # 2. From candidate tags if any
    for tag in candidate.proposed_tags or []:
        tag_str = str(tag).strip()
        if tag_str in CANONICAL_ASPECT_RATIOS and tag_str not in declared:
            declared.append(tag_str)

    # 3. Default to primary 9:16 if omitted
    if not declared:
        declared = ["9:16"]

    return declared


class AspectGate(RuntimeGate):
    """
    Renders and verifies the candidate against all declared aspect ratios.
    """

    @property
    def gate_id(self) -> str:
        return "aspect_gate"

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
        declared_aspects = extract_declared_aspect_ratios(candidate)
        aspect_renders: Dict[str, CandidateRenderResult] = {}
        aspect_failures: List[str] = []
        evidence_refs: List[str] = []

        for aspect in declared_aspects:
            if aspect not in CANONICAL_ASPECT_RATIOS:
                return CandidateGateResult(
                    gate_id=self.gate_id,
                    status=GateStatus.FAIL,
                    failure_code=ValidationFailureCode.UNSUPPORTED_ASPECT_RATIO,
                    summary=f"Candidate declares unsupported aspect ratio '{aspect}'. Allowed: {list(CANONICAL_ASPECT_RATIOS.keys())}",
                    machine_details={"declared_aspects": declared_aspects, "invalid_aspect": aspect},
                )

            expected_w, expected_h = CANONICAL_ASPECT_RATIOS[aspect]
            sanitized_name = aspect.replace(":", "_")
            out_filename = f"aspect_{sanitized_name}.png"

            # Render test frame for this aspect
            res = runner.render_still(
                workspace_dir=workspace_dir,
                harness_file=harness_file,
                props_file=props_file,
                frame_number=0,
                frame_index=0,
                width=expected_w,
                height=expected_h,
                fps=30,
                duration=30,
                aspect_ratio=aspect,
                out_filename=out_filename,
                timeout_seconds=30,
            )

            aspect_renders[aspect] = res

            if res.is_tool_error:
                return CandidateGateResult(
                    gate_id=self.gate_id,
                    status=GateStatus.ERROR,
                    failure_code=ValidationFailureCode.RENDER_TOOL_EXECUTION_ERROR,
                    summary=f"Aspect ratio '{aspect}' test crashed: {res.error_message}",
                    machine_details={"aspect": aspect, "error": res.error_message},
                )

            if not res.success:
                aspect_failures.append(f"{aspect}: {res.error_message}")
                continue

            if res.width != expected_w or res.height != expected_h:
                aspect_failures.append(
                    f"{aspect}: rendered dimensions ({res.width}x{res.height}) "
                    f"do not match canonical ({expected_w}x{expected_h})"
                )
                continue

            if res.output_path:
                evidence_refs.append(res.output_path)

        runtime_context["aspect_renders"] = aspect_renders

        if aspect_failures:
            return CandidateGateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAIL,
                failure_code=ValidationFailureCode.ASPECT_RENDER_FAILED,
                summary=f"Candidate failed aspect ratio tests: {'; '.join(aspect_failures)}",
                machine_details={
                    "declared_aspects": declared_aspects,
                    "failures": aspect_failures,
                },
                evidence_refs=evidence_refs,
            )

        return CandidateGateResult(
            gate_id=self.gate_id,
            status=GateStatus.PASS,
            summary=f"Candidate successfully rendered all declared aspect ratios: {', '.join(declared_aspects)}.",
            machine_details={
                "tested_aspects": declared_aspects,
                "aspect_dimensions": {
                    asp: CANONICAL_ASPECT_RATIOS[asp] for asp in declared_aspects
                },
            },
            evidence_refs=evidence_refs,
        )
