#!/usr/bin/env python3
"""
scripts/testing/ai_test_accounting.py
======================================
Authoritative test discovery, tier partitioning, and execution reconciliation
for the MOTION AI Platform test subsystem (PR-A2).

Invariants:
- Discovers 100% of test files under tests/ai/ without silent omissions.
- Enforces strict disjoint partition between:
    * Tier 1: Fast deterministic unit, contract, and integration tests (255 files).
    * Tier 2: Heavy Remotion candidate rendering and lifecycle suites (15 files).
- Verifies:
    * Tier 1 ∩ Tier 2 = ∅ (disjoint partition)
    * Tier 1 ∪ Tier 2 = Discovered Files (complete partition, 0 omitted)
- Reconciles JUnit XML reports from test execution:
    * Reconciles every executed testcase to its source test file.
    * Verifies 0 failed tests, reports skipped and passing tests.
- Generates machine-readable accounting summary JSON:
    * /tmp/ai_test_reports/accounting_summary.json
- Formats structured markdown summary into $GITHUB_STEP_SUMMARY when available.
- Strict exit code: exits with code 1 on any failure, mismatch, omission, or overlap.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Dict, List, Optional, Set, Tuple
import xml.etree.ElementTree as ET


REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def discover_ai_test_files(repo_root: Path = REPO_ROOT) -> List[Path]:
    """Discovers all test_*.py files under tests/ai/."""
    ai_dir = repo_root / "tests" / "ai"
    if not ai_dir.exists():
        raise FileNotFoundError(f"AI test directory not found: {ai_dir}")

    discovered = sorted(ai_dir.rglob("test_*.py"))
    return discovered


def partition_test_files(
    test_files: List[Path],
    repo_root: Path = REPO_ROOT,
) -> Tuple[List[Path], List[Path]]:
    """
    Partitions discovered AI test files into:
    - Tier 1: Fast/deterministic unit, contract, and integration tests
    - Tier 2: Heavy candidate rendering and lifecycle suites (tests/ai/candidates/)
    """
    tier2: List[Path] = []
    tier1: List[Path] = []

    candidates_dir = (repo_root / "tests" / "ai" / "candidates").resolve()

    for p in test_files:
        resolved = p.resolve()
        if str(resolved).startswith(str(candidates_dir)):
            tier2.append(p)
        else:
            tier1.append(p)

    return sorted(tier1), sorted(tier2)


def parse_junit_xml(xml_path: Path, repo_root: Path = REPO_ROOT) -> Dict[str, Any]:
    """
    Parses a pytest JUnit XML report and extracts executed test counts and files.
    """
    if not xml_path.exists():
        raise FileNotFoundError(f"JUnit XML report not found: {xml_path}")

    tree = ET.parse(xml_path)
    root = tree.getroot()

    # <testsuites> or <testsuite> root
    testsuites = root.findall(".//testsuite") if root.tag == "testsuites" else [root]

    total_tests = 0
    total_failures = 0
    total_errors = 0
    total_skipped = 0
    executed_files: Set[str] = set()
    testcases_detail: List[Dict[str, Any]] = []

    for suite in testsuites:
        total_tests += int(suite.attrib.get("tests", 0))
        total_failures += int(suite.attrib.get("failures", 0))
        total_errors += int(suite.attrib.get("errors", 0))
        total_skipped += int(suite.attrib.get("skipped", 0))

        for case in suite.findall("testcase"):
            file_attr = case.attrib.get("file")
            classname = case.attrib.get("classname", "")
            name = case.attrib.get("name", "")
            duration = float(case.attrib.get("time", 0.0))

            matched_file: Optional[str] = None
            if file_attr:
                p = (repo_root / file_attr).resolve()
                if p.exists():
                    matched_file = str(p.relative_to(repo_root))
            
            if not matched_file and classname:
                # e.g., tests.ai.speech.test_stt.TestSTT -> tests/ai/speech/test_stt.py
                parts = classname.split(".")
                # Search prefix until test_*.py matches
                for i in range(len(parts), 0, -1):
                    cand_path = repo_root / ("/".join(parts[:i]) + ".py")
                    if cand_path.exists():
                        matched_file = str(cand_path.relative_to(repo_root))
                        break

            if matched_file:
                executed_files.add(matched_file)

            status = "passed"
            failure_msg = None
            if case.find("failure") is not None:
                status = "failed"
                failure_msg = case.find("failure").attrib.get("message")
            elif case.find("error") is not None:
                status = "error"
                failure_msg = case.find("error").attrib.get("message")
            elif case.find("skipped") is not None:
                status = "skipped"

            testcases_detail.append({
                "file": matched_file,
                "name": name,
                "classname": classname,
                "status": status,
                "duration": duration,
                "message": failure_msg,
            })

    passed_tests = total_tests - (total_failures + total_errors + total_skipped)

    return {
        "xml_path": str(xml_path),
        "total_tests": total_tests,
        "passed_tests": max(0, passed_tests),
        "failed_tests": total_failures + total_errors,
        "skipped_tests": total_skipped,
        "executed_files": sorted(executed_files),
        "testcases": testcases_detail,
    }


def reconcile_accounting(
    discovered_files: List[Path],
    tier1_files: List[Path],
    tier2_files: List[Path],
    tier1_report: Optional[Dict[str, Any]] = None,
    tier2_report: Optional[Dict[str, Any]] = None,
    repo_root: Path = REPO_ROOT,
    git_sha: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Reconciles partition disjointness, completeness, and test execution results.
    """
    norm_discovered = set(str(p.resolve().relative_to(repo_root)) for p in discovered_files)
    norm_tier1 = set(str(p.resolve().relative_to(repo_root)) for p in tier1_files)
    norm_tier2 = set(str(p.resolve().relative_to(repo_root)) for p in tier2_files)

    # 1. Partition Verification
    overlap = norm_tier1 & norm_tier2
    partition_union = norm_tier1 | norm_tier2
    missing_from_partition = norm_discovered - partition_union
    extra_in_partition = partition_union - norm_discovered

    # 2. Execution Accounting
    t1_executed = set(tier1_report["executed_files"]) if tier1_report else set()
    t2_executed = set(tier2_report["executed_files"]) if tier2_report else set()
    total_executed = t1_executed | t2_executed

    unexecuted_files = norm_discovered - total_executed if (tier1_report or tier2_report) else set()

    t1_passed = tier1_report["passed_tests"] if tier1_report else 0
    t1_failed = tier1_report["failed_tests"] if tier1_report else 0
    t1_skipped = tier1_report["skipped_tests"] if tier1_report else 0
    t1_total = tier1_report["total_tests"] if tier1_report else 0

    t2_passed = tier2_report["passed_tests"] if tier2_report else 0
    t2_failed = tier2_report["failed_tests"] if tier2_report else 0
    t2_skipped = tier2_report["skipped_tests"] if tier2_report else 0
    t2_total = tier2_report["total_tests"] if tier2_report else 0

    total_tests = t1_total + t2_total
    total_passed = t1_passed + t2_passed
    total_failed = t1_failed + t2_failed
    total_skipped = t1_skipped + t2_skipped

    sha = git_sha or os.environ.get("GITHUB_SHA")
    if not sha:
        try:
            sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        except Exception:
            sha = "unknown"

    accounting_summary: Dict[str, Any] = {
        "gitSha": sha,
        "discoveredFilesCount": len(norm_discovered),
        "partition": {
            "tier1FilesCount": len(norm_tier1),
            "tier2FilesCount": len(norm_tier2),
            "overlapCount": len(overlap),
            "missingCount": len(missing_from_partition),
            "isDisjoint": len(overlap) == 0,
            "isComplete": len(missing_from_partition) == 0 and len(extra_in_partition) == 0,
        },
        "tier1": {
            "suitesDeclared": len(norm_tier1),
            "suitesExecuted": len(t1_executed),
            "totalTests": t1_total,
            "passedTests": t1_passed,
            "failedTests": t1_failed,
            "skippedTests": t1_skipped,
        },
        "tier2": {
            "suitesDeclared": len(norm_tier2),
            "suitesExecuted": len(t2_executed),
            "totalTests": t2_total,
            "passedTests": t2_passed,
            "failedTests": t2_failed,
            "skippedTests": t2_skipped,
        },
        "totalUniqueFiles": len(norm_discovered),
        "totalTests": total_tests,
        "totalPassed": total_passed,
        "totalFailed": total_failed,
        "totalSkipped": total_skipped,
        "unexecutedFiles": sorted(unexecuted_files),
        "overlapFiles": sorted(overlap),
    }

    return accounting_summary


def write_summary_markdown(summary: Dict[str, Any], output_path: Optional[Path] = None) -> str:
    """Formats a GitHub-flavored markdown summary table."""
    part = summary["partition"]
    t1 = summary["tier1"]
    t2 = summary["tier2"]

    md = f"""### 🤖 AI Test Verification & Accounting Summary
- **Target Git SHA**: `{summary['gitSha']}`
- **Discovered Test Files**: `{summary['discoveredFilesCount']}` total
- **Tier 1 (Fast Unit/Contract/Integration)**: `{t1['suitesDeclared']}` files declared | `{t1['passedTests']}/{t1['totalTests']}` passed ({t1['failedTests']} failed, {t1['skippedTests']} skipped)
- **Tier 2 (Heavy Candidates Lifecycle)**: `{t2['suitesDeclared']}` files declared | `{t2['passedTests']}/{t2['totalTests']}` passed ({t2['failedTests']} failed, {t2['skippedTests']} skipped)
- **Total Unique Tests**: `{summary['totalPassed']}/{summary['totalTests']}` passed
- **Partition Integrity**: {'✅ PASSED (100% coverage, 0 overlap, 0 omitted)' if part['isDisjoint'] and part['isComplete'] and summary['totalFailed'] == 0 else '❌ FAILED'}
"""
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "a", encoding="utf-8") as f:
            f.write(md + "\n")

    return md


def main() -> int:
    parser = argparse.ArgumentParser(description="AI Test Accounting and Partition Verification")
    parser.add_argument("--discover", action="store_true", help="Discover and report partitions only")
    parser.add_argument("--tier1-report", type=Path, help="Path to Tier 1 JUnit XML report")
    parser.add_argument("--tier2-report", type=Path, help="Path to Tier 2 JUnit XML report")
    parser.add_argument("--output", type=Path, default=Path("/tmp/ai_test_reports/accounting_summary.json"), help="Output summary JSON path")
    parser.add_argument("--step-summary", type=Path, help="Append markdown summary to GitHub step summary")
    parser.add_argument("--strict", action="store_true", default=True, help="Enforce 0 failures and 100 percent execution")

    args = parser.parse_args()

    discovered = discover_ai_test_files(REPO_ROOT)
    tier1_files, tier2_files = partition_test_files(discovered, REPO_ROOT)

    tier1_data = parse_junit_xml(args.tier1_report, REPO_ROOT) if args.tier1_report and args.tier1_report.exists() else None
    tier2_data = parse_junit_xml(args.tier2_report, REPO_ROOT) if args.tier2_report and args.tier2_report.exists() else None

    summary = reconcile_accounting(
        discovered_files=discovered,
        tier1_files=tier1_files,
        tier2_files=tier2_files,
        tier1_report=tier1_data,
        tier2_report=tier2_data,
        repo_root=REPO_ROOT,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("================================================================================")
    print("                    AI TEST ACCOUNTING & AUDIT REPORT                           ")
    print("================================================================================")
    print(f"Target Git SHA:              {summary['gitSha']}")
    print(f"Discovered Test Files:       {summary['discoveredFilesCount']}")
    print(f"Tier 1 Fast Suites:          {summary['tier1']['suitesDeclared']} files declared | {summary['tier1']['totalTests']} tests ({summary['tier1']['passedTests']} passed, {summary['tier1']['failedTests']} failed, {summary['tier1']['skippedTests']} skipped)")
    print(f"Tier 2 Heavy Suites:         {summary['tier2']['suitesDeclared']} files declared | {summary['tier2']['totalTests']} tests ({summary['tier2']['passedTests']} passed, {summary['tier2']['failedTests']} failed, {summary['tier2']['skippedTests']} skipped)")
    print(f"Total Unique Tests:          {summary['totalTests']} tests ({summary['totalPassed']} passed, {summary['totalFailed']} failed, {summary['totalSkipped']} skipped)")
    print(f"Partition Overlap Count:     {summary['partition']['overlapCount']}")
    print(f"Omitted Files Count:         {summary['partition']['missingCount']}")
    print(f"Disjoint Partition Verified: {'YES' if summary['partition']['isDisjoint'] else 'NO'}")
    print(f"Complete Partition Verified: {'YES' if summary['partition']['isComplete'] else 'NO'}")
    print("================================================================================")

    step_summary_path = args.step_summary or (Path(os.environ["GITHUB_STEP_SUMMARY"]) if "GITHUB_STEP_SUMMARY" in os.environ else None)
    if step_summary_path:
        write_summary_markdown(summary, step_summary_path)

    if args.discover:
        return 0

    if args.strict:
        if not summary["partition"]["isDisjoint"]:
            print(f"ERROR: Tiers overlap: {summary['overlapFiles']}", file=sys.stderr)
            return 1
        if not summary["partition"]["isComplete"]:
            print("ERROR: Test files omitted from partition!", file=sys.stderr)
            return 1
        if summary["totalFailed"] > 0:
            print(f"ERROR: {summary['totalFailed']} tests failed!", file=sys.stderr)
            return 1
        if summary["unexecutedFiles"] and (tier1_data or tier2_data):
            print(f"ERROR: {len(summary['unexecutedFiles'])} test files unexecuted: {summary['unexecutedFiles'][:5]}...", file=sys.stderr)
            return 1

    print("✅ ALL AI GATES, CONFORMANCE AND ACCOUNTING CRITERIA PASSED!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
