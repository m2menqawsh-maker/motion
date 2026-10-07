#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tests/e2e/true_e2e_suite.py — Authoritative Production True E2E Suite (S24).

Enforces:
- LED-074 (P0): Complete elimination of strict QC bypass. Strict Final QC runs in real execution path.
- LED-075 (P0): All fixtures generated exclusively through canonical Manifest v2 factory.
- LED-076 (P1): Multi-family template matrix representing text, ui-block, and composition families across 16:9, 9:16, and 1:1 aspect ratios.
- Negative Proof: Guaranteed fail-closed enforcement when Final QC detects defects.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

workspace_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(workspace_root))

from scripts.core.review_service import ReviewService, create_local_trusted_principal
from scripts.core.state_store import StateStore
from tests.factories.canonical_factory import create_canonical_e2e_project


def run_pipeline(project_id: str) -> subprocess.CompletedProcess:
    """Executes the canonical orchestrator in strict production QC mode."""
    # Ensure no QC bypass flags exist in execution environment
    env = {k: v for k, v in os.environ.items() if not k.startswith("SKIP_")}
    env["MOTION_ENV"] = "test"
    proc = subprocess.run(
        [sys.executable, "scripts/pipeline.py", project_id],
        cwd=str(workspace_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )
    return proc


def run_positive_scenario(
    name: str,
    aspect: str,
    template: str,
    duration_frames: int = 60,
    fps: int = 30,
    content_override: Optional[Dict[str, Any]] = None,
    with_audio: bool = False,
) -> bool:
    print(f"\n{'='*60}\nStarting E2E Scenario: {name} (Template: {template}, Aspect: {aspect})\n{'='*60}")
    project_id = f"e2e_{name.lower()}_{int(time.time())}"
    project_dir = workspace_root / "projects" / project_id

    if project_dir.exists():
        shutil.rmtree(project_dir)

    try:
        # 1. Setup project via canonical factory (LED-075)
        create_canonical_e2e_project(
            project_dir=project_dir,
            project_id=project_id,
            template=template,
            aspect=aspect,
            fps=fps,
            duration_frames=duration_frames,
            with_audio=with_audio,
            content_override=content_override,
        )

        # 2. Run Pipeline Pass 1 -> Advance to Studio Review (AWAITING_REVIEW)
        proc1 = run_pipeline(project_id)
        if proc1.returncode != 0:
            print(f"❌ [E2E FAIL] Pipeline Pass 1 failed for {project_id} (code: {proc1.returncode})")
            print("--- STDOUT ---\n", proc1.stdout)
            print("--- STDERR ---\n", proc1.stderr)
            return False

        if "المشروع جاهز للمعاينة في الاستوديو" not in proc1.stdout and "AWAITING_REVIEW" not in proc1.stdout:
            print(f"❌ [E2E FAIL] Pipeline did not stop at Studio Review for {project_id}!")
            return False

        print("✅ Pass 1 cleanly stopped at Studio Review.")

        # 3. Canonical Approval via ReviewService (LED-077)
        state = StateStore.load(project_dir)
        bundle = state.get_active_review_bundle() if state else None
        if not bundle:
            print(f"❌ [E2E FAIL] No active ReviewBundle created by Probe QC for {project_id}!")
            return False

        principal = create_local_trusted_principal(actor_id="e2e_trusted_reviewer")
        ReviewService.approve(
            project_dir=project_dir,
            bundle_id=bundle.review_bundle_id,
            principal=principal,
            reason=f"Approved during E2E scenario {name}",
        )
        print(f"✅ Approved ReviewBundle: {bundle.review_bundle_id}")

        # 4. Run Pipeline Pass 2 -> Render and strict Final QC
        proc2 = run_pipeline(project_id)
        if proc2.returncode != 0:
            print(f"❌ [E2E FAIL] Pipeline Pass 2 failed for {project_id} (code: {proc2.returncode})")
            print("--- STDOUT ---\n", proc2.stdout)
            print("--- STDERR ---\n", proc2.stderr)
            return False

        # 5. Verify physical outputs and Final QC report
        out_mp4 = project_dir / "out.mp4"
        qc_report = project_dir / "final_qc_report.json"

        if not out_mp4.exists():
            print(f"❌ [E2E FAIL] out.mp4 was not generated for {project_id}!")
            return False

        if not qc_report.exists():
            print(f"❌ [E2E FAIL] final_qc_report.json was not generated for {project_id}!")
            return False

        qc_data = json.loads(qc_report.read_text(encoding="utf-8"))
        if qc_data.get("status") != "PASS":
            print(f"❌ [E2E FAIL] final_qc status is not PASS: {qc_data.get('status')}")
            return False

        print(f"🎉 Scenario {name} ({aspect}) PASSED! Video generated and verified at: {out_mp4}")
        return True

    finally:
        if project_dir.exists():
            shutil.rmtree(project_dir, ignore_errors=True)


def run_negative_qc_scenario() -> bool:
    """
    LED-074 Negative Proof:
    Deliberately introduces a critical defect (e.g. aspect ratio mismatch) and proves
    that Final QC fails closed and the pipeline rejects completion.
    """
    print(f"\n{'='*60}\nStarting E2E Negative Scenario: Defect Detection Proof\n{'='*60}")
    project_id = f"e2e_neg_qc_{int(time.time())}"
    project_dir = workspace_root / "projects" / project_id

    if project_dir.exists():
        shutil.rmtree(project_dir)

    try:
        # Create valid project with 16:9
        create_canonical_e2e_project(
            project_dir=project_dir,
            project_id=project_id,
            template="animatedtext-element",
            aspect="16:9",
            fps=30,
            duration_frames=60,
        )

        # Pass 1
        proc1 = run_pipeline(project_id)
        if proc1.returncode != 0:
            print("❌ Negative test setup failed at Pass 1")
            return False

        # Approve
        state = StateStore.load(project_dir)
        bundle = state.get_active_review_bundle()
        principal = create_local_trusted_principal(actor_id="e2e_trusted_reviewer")
        ReviewService.approve(project_dir, bundle.review_bundle_id, principal=principal)

        # Render valid 16:9 output
        sub_env = dict(os.environ, PYTHONPATH=str(workspace_root))
        res_render = subprocess.run(
            [sys.executable, "scripts/render_project.py", project_id],
            cwd=str(workspace_root),
            env=sub_env,
            capture_output=True,
            text=True,
        )
        if res_render.returncode != 0 or not (project_dir / "out.mp4").exists():
            print("❌ Negative test setup failed at render step")
            return False

        # Inject defect: Mutate blueprint aspect ratio to 9:16 (mismatch against actual 16:9 video)
        bp_path = project_dir / "05_blueprint.json"
        bp_data = json.loads(bp_path.read_text(encoding="utf-8"))
        bp_data["aspect_ratio"] = "9:16"
        bp_path.write_text(json.dumps(bp_data), encoding="utf-8")

        # Run Final QC directly -> Must FAIL closed on aspect mismatch
        proc_qc = subprocess.run(
            [sys.executable, "scripts/gates/final_qc.py", project_id],
            cwd=str(workspace_root),
            env=sub_env,
            capture_output=True,
            text=True,
        )
        report_file = project_dir / "final_qc_report.json"
        if not report_file.exists():
            print("❌ Final QC report missing after execution")
            return False

        report = json.loads(report_file.read_text(encoding="utf-8"))
        if proc_qc.returncode != 0 and report.get("status") == "FAIL":
            dim_status = report.get("checks", {}).get("dimensions", {}).get("status")
            print(f"✅ Negative Proof Success: Final QC failed closed on aspect defect (dimensions: {dim_status}).")
            return True
        else:
            print("❌ [CRITICAL] Final QC succeeded despite corrupted defect! Defect bypassed!")
            return False

    finally:
        if project_dir.exists():
            shutil.rmtree(project_dir, ignore_errors=True)


def run_unknown_template_negative_scenario() -> bool:
    """LED-076: Proves unknown template is rejected fail-closed during pipeline validation."""
    print(f"\n{'='*60}\nStarting E2E Negative Scenario: Unknown Template Rejection\n{'='*60}")
    project_id = f"e2e_neg_tpl_{int(time.time())}"
    project_dir = workspace_root / "projects" / project_id

    if project_dir.exists():
        shutil.rmtree(project_dir)

    try:
        create_canonical_e2e_project(
            project_dir=project_dir,
            project_id=project_id,
            template="completely_nonexistent_template_xyz",
            aspect="16:9",
            fps=30,
            duration_frames=60,
        )

        proc = run_pipeline(project_id)
        if proc.returncode != 0:
            print("✅ Negative Proof Success: Unknown template was rejected fail-closed.")
            return True
        else:
            print("❌ [CRITICAL] Unknown template was accepted!")
            return False

    finally:
        if project_dir.exists():
            shutil.rmtree(project_dir, ignore_errors=True)


if __name__ == "__main__":
    matrix = [
        # Family 1: text-centric (16:9)
        ("Scenario_16_9_Text", "16:9", "animatedtext-element", 60, {"text": "مرحباً بكم في Clean Video Workspace!"}),
        # Family 2: ui-block (9:16)
        ("Scenario_9_16_UIBlock", "9:16", "animatedcounter-element", 60, {"to": 100, "from": 0, "numbers": [100]}),
        # Family 3: composition/story (1:1)
        ("Scenario_1_1_Composition", "1:1", "rui-title-card", 60, {"text": "Title Card", "lines": ["Title Card"]}),
    ]

    all_passed = True

    # 1. Positive Multi-Family Matrix (LED-076)
    for name, aspect, template, duration, content in matrix:
        success = run_positive_scenario(
            name=name,
            aspect=aspect,
            template=template,
            duration_frames=duration,
            content_override=content,
            with_audio=False,
        )
        if not success:
            all_passed = False
            break

    # 2. Negative Final QC Proof (LED-074)
    if all_passed:
        if not run_negative_qc_scenario():
            all_passed = False

    # 3. Unknown Template Rejection (LED-076)
    if all_passed:
        if not run_unknown_template_negative_scenario():
            all_passed = False

    if all_passed:
        print("\n" + "="*60)
        print("🎉 [ALL PASSED] All True E2E Scenarios (Multi-Family + Negative Proofs) Succeeded!")
        print("="*60)
        sys.exit(0)
    else:
        print("\n" + "="*60)
        print("❌ [E2E SUITE FAILED] One or more E2E scenarios failed.")
        print("="*60)
        sys.exit(1)
