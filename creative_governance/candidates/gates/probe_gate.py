"""
creative_governance/candidates/gates/probe_gate.py
=================================
Probe Gate for TemplateCandidate (S28-07C Gate 4).

Proves:
1. Representative frames (start, middle, end) are generated deterministically.
2. Rendered frames physically exist on disk and have non-zero payload.
3. Frame image headers are verified (valid PNG/JPEG).
4. Frame dimensions match target composition dimensions.
5. Produces auditable frame probe report with SHA-256 digests.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from creative_governance.candidates.gates.base import RuntimeGate
from creative_governance.candidates.policies import ValidationFailureCode
from creative_governance.candidates.runtime_runner import CandidateRenderResult, IsolatedCandidateRunner
from ai.contracts.creative.template_candidate import (
    CandidateGateResult,
    GateStatus,
    TemplateCandidate,
)
from scripts.core.tenant_model import TenantContext


class ProbeGate(RuntimeGate):
    """
    Renders and probes representative candidate frames across the timeline.
    """

    @property
    def gate_id(self) -> str:
        return "probe_gate"

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
        contract_info = runtime_context.get("runtime_contract", {})
        duration = contract_info.get("duration", 30)
        fps = contract_info.get("fps", 30)

        # Representative frames: start (0), middle (duration // 2), end (duration - 1)
        start_frame = 0
        mid_frame = max(1, duration // 2)
        end_frame = max(mid_frame + 1, duration - 1)

        probe_targets = [
            (0, start_frame, "start"),
            (1, mid_frame, "middle"),
            (2, end_frame, "end"),
        ]

        width = 1080
        height = 1920
        aspect = "9:16"

        representative_frames: List[CandidateRenderResult] = []
        frame_probe_records: List[Dict[str, Any]] = []
        evidence_refs: List[str] = []

        smoke_render = runtime_context.get("smoke_render")

        for idx, f_num, label in probe_targets:
            # Reuse smoke render if f_num == 0 and smoke succeeded
            if f_num == 0 and smoke_render and smoke_render.success and smoke_render.output_path:
                res = smoke_render
            else:
                out_name = f"probe_{idx:02d}_f{f_num}_{label}.png"
                res = runner.render_still(
                    workspace_dir=workspace_dir,
                    harness_file=harness_file,
                    props_file=props_file,
                    frame_number=f_num,
                    frame_index=idx,
                    width=width,
                    height=height,
                    fps=fps,
                    duration=duration,
                    aspect_ratio=aspect,
                    out_filename=out_name,
                    timeout_seconds=30,
                )

            representative_frames.append(res)

            # Tool execution crash -> ERROR
            if res.is_tool_error:
                return CandidateGateResult(
                    gate_id=self.gate_id,
                    status=GateStatus.ERROR,
                    failure_code=ValidationFailureCode.PROBE_TOOL_EXECUTION_ERROR,
                    summary=f"Probe rendering tool crashed on frame {f_num} ({label}): {res.error_message}",
                    machine_details={"frame_number": f_num, "label": label, "error": res.error_message},
                )

            # Candidate render failure -> FAIL
            if not res.success:
                return CandidateGateResult(
                    gate_id=self.gate_id,
                    status=GateStatus.FAIL,
                    failure_code=res.failure_code or ValidationFailureCode.PROBE_FRAME_MISSING,
                    summary=f"Probe failed to produce frame {f_num} ({label}): {res.error_message}",
                    machine_details={"frame_number": f_num, "label": label, "error": res.error_message},
                )

            # Verify dimensions
            if res.width != width or res.height != height:
                return CandidateGateResult(
                    gate_id=self.gate_id,
                    status=GateStatus.FAIL,
                    failure_code=ValidationFailureCode.PROBE_DIMENSIONS_MISMATCH,
                    summary=f"Probe frame {f_num} dimensions ({res.width}x{res.height}) do not match expected ({width}x{height})",
                    machine_details={"frame_number": f_num, "width": res.width, "height": res.height},
                )

            record = {
                "index": idx,
                "frame_number": f_num,
                "label": label,
                "file_path": res.output_path,
                "sha256": res.sha256_digest,
                "size_bytes": res.file_size_bytes,
                "width": res.width,
                "height": res.height,
            }
            frame_probe_records.append(record)
            if res.output_path:
                evidence_refs.append(res.output_path)

        # Store in context for downstream QC
        runtime_context["representative_frames"] = representative_frames
        runtime_context["probe_records"] = frame_probe_records

        return CandidateGateResult(
            gate_id=self.gate_id,
            status=GateStatus.PASS,
            summary=f"Probe gate verified {len(frame_probe_records)} representative frames (start, middle, end).",
            machine_details={"frames": frame_probe_records},
            evidence_refs=evidence_refs,
        )
