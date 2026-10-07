"""
creative_governance/candidates/gates/render_smoke_gate.py
========================================
Render Smoke Gate for TemplateCandidate (S28-07C Gate 1).

Proves:
1. Candidate loads into Remotion runtime without crashing.
2. Component mounts cleanly with sample props/fixtures.
3. Runtime imports resolve successfully.
4. Frame renders and produces valid visual output.
5. No runtime exceptions or timeouts occur.

Distinguishes:
- CANDIDATE_RUNTIME_FAILURE (mount error, unhandled exception, syntax failure) -> FAIL
- RENDER_TOOL_EXECUTION_ERROR (subprocess spawn error, missing tool) -> ERROR
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


class RenderSmokeGate(RuntimeGate):
    """
    Executes a bounded smoke render (frame 0) to ensure the candidate mounts cleanly.
    """

    @property
    def gate_id(self) -> str:
        return "render_smoke_gate"

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
        # Determine initial aspect ratio and dimensions for smoke render
        aspect = "9:16"
        width = 1080
        height = 1920

        # Execute bounded smoke render on frame 0
        render_result = runner.render_still(
            workspace_dir=workspace_dir,
            harness_file=harness_file,
            props_file=props_file,
            frame_number=0,
            frame_index=0,
            width=width,
            height=height,
            fps=30,
            duration=30,
            aspect_ratio=aspect,
            out_filename="smoke_frame_0.png",
            timeout_seconds=30,
        )

        runtime_context["smoke_render"] = render_result

        # Handle tool execution error -> ERROR (never PASS)
        if render_result.is_tool_error:
            return CandidateGateResult(
                gate_id=self.gate_id,
                status=GateStatus.ERROR,
                failure_code=render_result.failure_code or ValidationFailureCode.RENDER_TOOL_EXECUTION_ERROR,
                summary=f"Render smoke execution crashed: {render_result.error_message}",
                machine_details={
                    "error_message": render_result.error_message,
                    "raw_stderr": render_result.raw_stderr[:500],
                },
            )

        # Handle candidate runtime failure -> FAIL
        if not render_result.success:
            return CandidateGateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAIL,
                failure_code=render_result.failure_code or ValidationFailureCode.CANDIDATE_RUNTIME_FAILURE,
                summary=f"Candidate failed render smoke check: {render_result.error_message}",
                machine_details={
                    "error_message": render_result.error_message,
                    "failure_code": render_result.failure_code,
                    "raw_stderr": render_result.raw_stderr[:500],
                },
            )

        # Success: smoke frame rendered cleanly
        return CandidateGateResult(
            gate_id=self.gate_id,
            status=GateStatus.PASS,
            summary=(
                f"Candidate rendered smoke frame 0 successfully without exception "
                f"({render_result.width}x{render_result.height}, {render_result.file_size_bytes} bytes)."
            ),
            machine_details={
                "frame_number": 0,
                "width": render_result.width,
                "height": render_result.height,
                "digest": render_result.sha256_digest,
                "file_size": render_result.file_size_bytes,
            },
            evidence_refs=[render_result.output_path] if render_result.output_path else [],
        )
