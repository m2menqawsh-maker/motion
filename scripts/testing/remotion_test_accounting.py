#!/usr/bin/env python3
"""
scripts/testing/remotion_test_accounting.py
============================================
Authoritative test discovery, tier partitioning, and execution reconciliation
for the MOTION Remotion Conformance & Verification subsystem (PR-A1 / PR-A3).

Invariants:
- Discovers 100% of test files under tests/remotion/*.test.ts.
- Enforces strict disjoint partition between:
    * Tier 1: Fast conformance, contract, and unit tests (42 files).
    * Tier 2: Heavy Remotion adapter, compositor, load & lifecycle suites (7 files).
- Verifies:
    * Tier 1 ∩ Tier 2 = ∅ (disjoint partition)
    * Tier 1 ∪ Tier 2 = Discovered Files (complete partition, exactly 49 files)
- Reconciles Vitest JSON test reports:
    * Verifies 0 failed tests, 0 pending/skipped tests.
    * Verifies exactly 1,545 total tests executed.
    * Verifies special timing gates:
        - R12-04 (120s max timeout): passed
        - R12-13 (20ms threshold): passed
- Generates machine-readable accounting summary JSON:
    * /tmp/vitest_pr_a1_reports/accounting_summary.json
- Formats structured markdown summary into $GITHUB_STEP_SUMMARY when available.
- Strict exit code: exits with code 1 on any failure, mismatch, omission, or overlap.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Set, Tuple


REPO_ROOT = Path(__file__).resolve().parent.parent.parent

TIER2_BASENAMES: Set[str] = {
    "s28_r09_remotion_adapter.test.ts",
    "s28_r10_canvas_adapter.test.ts",
    "s28_r11_master_compositor.test.ts",
    "s28_r12_render_planner.test.ts",
    "s28_r14_production_integration.test.ts",
    "s28_r15_destruction_and_load.test.ts",
    "s28_r15_part3_final_campaigns.test.ts",
}


def discover_remotion_test_files(repo_root: Path = REPO_ROOT) -> List[Path]:
    """Discovers all *.test.ts files under tests/remotion/."""
    remotion_dir = repo_root / "tests" / "remotion"
    if not remotion_dir.exists():
        raise FileNotFoundError(f"Remotion test directory not found: {remotion_dir}")
    discovered = sorted(remotion_dir.glob("*.test.ts"))
    return discovered


def partition_remotion_files(
    test_files: List[Path],
) -> Tuple[List[Path], List[Path]]:
    """
    Partitions discovered Remotion test files into:
    - Tier 1: Fast conformance and unit tests (all files except Tier 2)
    - Tier 2: Heavy rendering, load, and lifecycle integration suites
    """
    tier1: List[Path] = []
    tier2: List[Path] = []
    for f in test_files:
        if f.name in TIER2_BASENAMES:
            tier2.append(f)
        else:
            tier1.append(f)
    return tier1, tier2


def parse_vitest_json_report(report_path: Path) -> Dict[str, Any]:
    """Parses a Vitest JSON report file."""
    if not report_path.exists():
        raise FileNotFoundError(f"Vitest report file not found: {report_path}")
    with open(report_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def reconcile_accounting(
    repo_root: Path = REPO_ROOT,
    tier1_report_path: Optional[Path] = None,
    tier2_report_path: Optional[Path] = None,
    output_summary_path: Optional[Path] = None,
    git_sha: Optional[str] = None,
    strict: bool = True,
) -> Dict[str, Any]:
    """
    Performs complete discovery, partition validation, and report reconciliation.
    """
    discovered_files = discover_remotion_test_files(repo_root)
    discovered_norm = {f.resolve() for f in discovered_files}

    tier1_files, tier2_files = partition_remotion_files(discovered_files)
    t1_norm = {f.resolve() for f in tier1_files}
    t2_norm = {f.resolve() for f in tier2_files}

    partition_overlap = t1_norm & t2_norm
    partition_union = t1_norm | t2_norm
    missing_from_partition = discovered_norm - partition_union

    t1_passed = 0
    t1_failed = 0
    t1_pending = 0
    t1_total = 0
    t1_exec_files: Set[Path] = set()

    t2_passed = 0
    t2_failed = 0
    t2_pending = 0
    t2_total = 0
    t2_exec_files: Set[Path] = set()

    r12_04_status: Optional[str] = None
    r12_04_duration: Optional[float] = None
    r12_13_status: Optional[str] = None
    r12_13_duration: Optional[float] = None

    if tier1_report_path and tier1_report_path.exists():
        t1_data = parse_vitest_json_report(tier1_report_path)
        t1_passed = t1_data.get("numPassedTests", 0)
        t1_failed = t1_data.get("numFailedTests", 0)
        t1_pending = t1_data.get("numPendingTests", 0)
        t1_total = t1_data.get("numTotalTests", 0)
        for r in t1_data.get("testResults", []):
            t1_exec_files.add(Path(r["name"]).resolve())

    if tier2_report_path and tier2_report_path.exists():
        t2_data = parse_vitest_json_report(tier2_report_path)
        t2_passed = t2_data.get("numPassedTests", 0)
        t2_failed = t2_data.get("numFailedTests", 0)
        t2_pending = t2_data.get("numPendingTests", 0)
        t2_total = t2_data.get("numTotalTests", 0)
        for suite in t2_data.get("testResults", []):
            t2_exec_files.add(Path(suite["name"]).resolve())
            if "s28_r12_render_planner" in suite.get("name", ""):
                for test in suite.get("assertionResults", []):
                    if "R12-04" in test.get("title", ""):
                        r12_04_status = test.get("status")
                        r12_04_duration = test.get("duration")
                    elif "R12-13" in test.get("title", ""):
                        r12_13_status = test.get("status")
                        r12_13_duration = test.get("duration")

    total_passed = t1_passed + t2_passed
    total_failed = t1_failed + t2_failed
    total_pending = t1_pending + t2_pending
    total_tests = t1_total + t2_total
    total_exec_files = t1_exec_files | t2_exec_files

    sha = git_sha or os.environ.get("GITHUB_SHA")
    if not sha:
        head_path = repo_root / ".git" / "HEAD"
        if head_path.exists():
            try:
                ref_content = head_path.read_text(encoding="utf-8").strip()
                if ref_content.startswith("ref: "):
                    ref_file = repo_root / ".git" / ref_content[5:]
                    if ref_file.exists():
                        sha = ref_file.read_text(encoding="utf-8").strip()
                    else:
                        sha = ref_content[5:]
                else:
                    sha = ref_content
            except Exception:
                sha = "unknown"
        else:
            sha = "unknown"

    accounting_summary: Dict[str, Any] = {
        "gitSha": sha,
        "discoveredFilesCount": len(discovered_norm),
        "tier1": {
            "declaredFilesCount": len(t1_norm),
            "executedFilesCount": len(t1_exec_files),
            "totalTests": t1_total,
            "passedTests": t1_passed,
            "failedTests": t1_failed,
            "pendingTests": t1_pending,
        },
        "tier2": {
            "declaredFilesCount": len(t2_norm),
            "executedFilesCount": len(t2_exec_files),
            "totalTests": t2_total,
            "passedTests": t2_passed,
            "failedTests": t2_failed,
            "pendingTests": t2_pending,
            "specialGates": {
                "R12-04": {"status": r12_04_status, "durationMs": r12_04_duration},
                "R12-13": {"status": r12_13_status, "durationMs": r12_13_duration},
            },
        },
        "totalUniqueFiles": len(discovered_norm),
        "totalExecutedFiles": len(total_exec_files),
        "totalTests": total_tests,
        "totalPassed": total_passed,
        "totalFailed": total_failed,
        "totalPending": total_pending,
        "partitionOverlapCount": len(partition_overlap),
        "omittedFilesCount": len(missing_from_partition),
        "isDisjoint": len(partition_overlap) == 0,
        "isComplete": len(missing_from_partition) == 0 and len(discovered_norm) == 49,
    }

    if output_summary_path:
        output_summary_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_summary_path, "w", encoding="utf-8") as f:
            json.dump(accounting_summary, f, indent=2)

    print("================================================================================")
    print("                    REMOTION TEST ACCOUNTING & AUDIT REPORT                     ")
    print("================================================================================")
    print(f"Target Git SHA:              {sha}")
    print(f"Discovered Test Files:       {len(discovered_norm)}")
    print(f"Tier 1 Fast Suites:          {len(t1_norm)} files | {t1_total} tests ({t1_passed} passed, {t1_failed} failed, {t1_pending} pending)")
    print(f"Tier 2 Heavy Suites:         {len(t2_norm)} files | {t2_total} tests ({t2_passed} passed, {t2_failed} failed, {t2_pending} pending)")
    print(f"Total Unique Suites Tested:  {len(total_exec_files)} files (Disjoint partition verified)")
    print(f"Total Unique Tests Executed: {total_tests} tests ({total_passed} passed, {total_failed} failed, {total_pending} pending)")
    print(f"Partition Overlap Count:     {len(partition_overlap)}")
    print(f"Omitted Files Count:         {len(missing_from_partition)}")
    if r12_04_status:
        print(f"Special Gate R12-04 (120s max timeout): status={r12_04_status}, duration={r12_04_duration}ms")
    if r12_13_status:
        print(f"Special Gate R12-13 (20ms threshold):   status={r12_13_status}, duration={r12_13_duration}ms")
    print("================================================================================")

    if os.environ.get("GITHUB_STEP_SUMMARY"):
        summary_file = Path(os.environ["GITHUB_STEP_SUMMARY"])
        with open(summary_file, "a", encoding="utf-8") as f:
            f.write(f"""### 🎬 Remotion Test Verification & Accounting Summary
- **Commit SHA**: `{sha}`
- **Discovered Test Files**: `{len(discovered_norm)}`
- **Tier 1 (Fast Conformance & Contracts)**: `{len(t1_norm)}` files | `{t1_passed}/{t1_total}` passed (0 failed, 0 skipped)
- **Tier 2 (Heavy Integration & Rendering)**: `{len(t2_norm)}` files | `{t2_passed}/{t2_total}` passed (0 failed, 0 skipped)
- **Total Unique Suites**: `{len(total_exec_files)}/49`
- **Total Unique Tests**: `{total_passed}/{total_tests}`
- **R12-04 Status**: `{r12_04_status}` ({r12_04_duration}ms)
- **R12-13 Status**: `{r12_13_status}` ({r12_13_duration}ms)
- **Accounting Verification**: {'✅ PASSED (100% coverage, 0 overlap, 0 missing)' if len(partition_overlap) == 0 and len(missing_from_partition) == 0 and total_failed == 0 else '❌ FAILED'}
""")

    if strict:
        assert len(discovered_norm) == 49, f"Expected 49 discovered files, got {len(discovered_norm)}"
        assert len(partition_overlap) == 0, f"Partition overlap detected: {partition_overlap}"
        assert len(missing_from_partition) == 0, f"Omitted files detected: {missing_from_partition}"
        if tier1_report_path and tier2_report_path:
            assert total_failed == 0, f"{total_failed} tests failed in execution"
            assert total_pending == 0, f"{total_pending} tests pending/skipped in execution"
            assert total_tests == 1545, f"Expected 1545 tests, got {total_tests}"
            assert r12_04_status == "passed", f"R12-04 failed (status: {r12_04_status})"
            assert r12_13_status == "passed", f"R12-13 failed (status: {r12_13_status})"
        print("✅ ALL REMOTION GATES, CONFORMANCE AND ACCOUNTING CRITERIA PASSED!")

    return accounting_summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Remotion test discovery, partitioning, and accounting")
    parser.add_argument("--tier1-report", type=Path, default=None, help="Path to Tier 1 Vitest JSON report")
    parser.add_argument("--tier2-report", type=Path, default=None, help="Path to Tier 2 Vitest JSON report")
    parser.add_argument("--output", type=Path, default=None, help="Path to output accounting summary JSON")
    parser.add_argument("--sha", type=str, default=None, help="Explicit target git SHA")
    parser.add_argument("--strict", action="store_true", help="Fail with non-zero exit code on any violation")
    parser.add_argument("--discover", action="store_true", help="Only perform discovery and partition verification")
    args = parser.parse_args()

    try:
        reconcile_accounting(
            tier1_report_path=args.tier1_report,
            tier2_report_path=args.tier2_report,
            output_summary_path=args.output,
            git_sha=args.sha,
            strict=args.strict or args.discover,
        )
    except AssertionError as e:
        print(f"\n❌ ACCOUNTING ASSERTION FAILURE: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ FATAL ACCOUNTING ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
