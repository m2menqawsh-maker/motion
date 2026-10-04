"""
creative_governance/candidates/gates/candidate_qc_gate.py
========================================
Candidate Quality Control Gate (S28-07C Gate 5).

Evaluates representative frames against CANDIDATE_RUNTIME_QC_PROFILE:
1. Black output detection (mean luminance below threshold).
2. Empty/blank output detection (zero visual variance).
3. Corrupt render detection (unparseable image data).
4. Invalid dimensions detection.
5. Distinction between QC violation (FAIL) vs tool execution crash (ERROR).
Strictly forbids SKIP_STRICT_QC bypass.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
from PIL import Image

from creative_governance.candidates.gates.base import RuntimeGate
from creative_governance.candidates.policies import (
    CANDIDATE_RUNTIME_QC_PROFILE,
    ValidationFailureCode,
)
from creative_governance.candidates.runtime_runner import CandidateRenderResult, IsolatedCandidateRunner
from ai.contracts.creative.template_candidate import (
    CandidateGateResult,
    GateStatus,
    TemplateCandidate,
)
from scripts.core.tenant_model import TenantContext


class CandidateQCGate(RuntimeGate):
    """
    Evaluates visual quality of rendered candidate frames according to QC policy.
    """

    @property
    def gate_id(self) -> str:
        return "qc_gate"

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
        # Anti-bypass guard: ensure strict candidate QC profile is active
        profile = CANDIDATE_RUNTIME_QC_PROFILE
        if not profile or not profile.get("check_black_frame"):
            return CandidateGateResult(
                gate_id=self.gate_id,
                status=GateStatus.ERROR,
                failure_code=ValidationFailureCode.QC_TOOL_EXECUTION_ERROR,
                summary="CANDIDATE_RUNTIME_QC_PROFILE is missing or invalid. SKIP_STRICT_QC is forbidden.",
            )

        frames: List[CandidateRenderResult] = runtime_context.get("representative_frames", [])
        if not frames:
            return CandidateGateResult(
                gate_id=self.gate_id,
                status=GateStatus.FAIL,
                failure_code=ValidationFailureCode.QC_EMPTY_OUTPUT,
                summary="No representative frames provided to QC gate for visual inspection.",
            )

        qc_metrics: List[Dict[str, Any]] = []
        evidence_refs: List[str] = []

        black_threshold = float(profile.get("black_threshold_mean", 2.0))
        empty_threshold = float(profile.get("empty_variance_threshold", 0.5))

        for frame in frames:
            if not frame.output_path or not os.path.exists(frame.output_path):
                return CandidateGateResult(
                    gate_id=self.gate_id,
                    status=GateStatus.FAIL,
                    failure_code=ValidationFailureCode.QC_EMPTY_OUTPUT,
                    summary=f"Frame file {frame.frame_number} missing on disk during visual QC.",
                )

            evidence_refs.append(frame.output_path)

            try:
                # Open and verify image data
                with Image.open(frame.output_path) as img:
                    width, height = img.size
                    if width <= 0 or height <= 0:
                        return CandidateGateResult(
                            gate_id=self.gate_id,
                            status=GateStatus.FAIL,
                            failure_code=ValidationFailureCode.QC_INVALID_DIMENSIONS,
                            summary=f"Frame {frame.frame_number} has non-positive dimensions ({width}x{height}).",
                        )

                    # Convert to grayscale luminance array
                    gray_img = img.convert("L")
                    arr = np.array(gray_img, dtype=np.float32)

                    mean_luminance = float(np.mean(arr))
                    variance_luminance = float(np.var(arr))

                    # 1. Pure black output check
                    if mean_luminance < black_threshold:
                        return CandidateGateResult(
                            gate_id=self.gate_id,
                            status=GateStatus.FAIL,
                            failure_code=ValidationFailureCode.QC_BLACK_OUTPUT,
                            summary=(
                                f"Frame {frame.frame_number} failed QC: pure black or near-black output "
                                f"(mean luminance {mean_luminance:.2f} < {black_threshold})."
                            ),
                            machine_details={
                                "frame_number": frame.frame_number,
                                "mean_luminance": mean_luminance,
                                "threshold": black_threshold,
                            },
                            evidence_refs=[frame.output_path],
                        )

                    # 2. Empty / uniform solid output check
                    if variance_luminance < empty_threshold:
                        return CandidateGateResult(
                            gate_id=self.gate_id,
                            status=GateStatus.FAIL,
                            failure_code=ValidationFailureCode.QC_EMPTY_OUTPUT,
                            summary=(
                                f"Frame {frame.frame_number} failed QC: uniform blank or solid output "
                                f"(variance {variance_luminance:.4f} < {empty_threshold})."
                            ),
                            machine_details={
                                "frame_number": frame.frame_number,
                                "variance": variance_luminance,
                                "threshold": empty_threshold,
                            },
                            evidence_refs=[frame.output_path],
                        )

                    qc_metrics.append({
                        "frame_number": frame.frame_number,
                        "width": width,
                        "height": height,
                        "mean_luminance": round(mean_luminance, 2),
                        "variance": round(variance_luminance, 2),
                        "status": "PASS",
                    })

            except (IOError, ValueError) as img_err:
                # Corrupt image format
                return CandidateGateResult(
                    gate_id=self.gate_id,
                    status=GateStatus.FAIL,
                    failure_code=ValidationFailureCode.QC_CORRUPT_FRAME,
                    summary=f"Frame {frame.frame_number} is corrupted or cannot be decoded: {img_err}",
                    evidence_refs=[frame.output_path],
                )
            except Exception as e:
                # Analysis tool execution error -> ERROR (never PASS)
                return CandidateGateResult(
                    gate_id=self.gate_id,
                    status=GateStatus.ERROR,
                    failure_code=ValidationFailureCode.QC_TOOL_EXECUTION_ERROR,
                    summary=f"Visual QC analysis tool failed unexpectedly: {e}",
                    machine_details={"error": str(e)},
                )

        qc_report = {
            "qc_profile": "CANDIDATE_RUNTIME_QC_PROFILE",
            "frames_inspected": len(qc_metrics),
            "metrics": qc_metrics,
            "overall_status": "PASS",
        }
        runtime_context["qc_report"] = qc_report

        return CandidateGateResult(
            gate_id=self.gate_id,
            status=GateStatus.PASS,
            summary=f"Visual QC gate passed: {len(qc_metrics)} representative frames verified non-black, non-empty, and integral.",
            machine_details=qc_report,
            evidence_refs=evidence_refs,
        )
