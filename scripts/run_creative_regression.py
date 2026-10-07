#!/usr/bin/env python3
"""
scripts/run_creative_regression.py
==================================
CLI Runner for the Canonical Creative Regression Suite & Trace Grading (S28-08B).

Usage:
    python scripts/run_creative_regression.py [--category CATEGORY] [--severity SEVERITY] [--output PATH] [--fast]

Examples:
    # Run full regression suite across all 13 categories
    python scripts/run_creative_regression.py

    # Filter to critical / blocker cases only
    python scripts/run_creative_regression.py --severity CRITICAL

    # Filter to specific category
    python scripts/run_creative_regression.py --category AUDIO_MODE

    # Save output to custom path
    python scripts/run_creative_regression.py --output documentation/audits/creative_regression_run.json
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from ai.regression.runner import CreativeRegressionRunner
from ai.contracts.creative.regression import EvalCategory, EvalSeverity

DEFAULT_REPORT_PATH = WORKSPACE_ROOT / "documentation" / "audits" / "creative_regression_run.json"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run S28 Creative Regression Suite and Trace Grading."
    )
    parser.add_argument(
        "--category",
        choices=[c.value for c in EvalCategory],
        default=None,
        help="Filter execution to a specific creative evaluation category.",
    )
    parser.add_argument(
        "--severity",
        choices=[s.value for s in EvalSeverity],
        default=None,
        help="Filter execution to a specific severity level (BLOCKER, CRITICAL, MAJOR, MINOR).",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Fast deterministic mode: runs core assertions without non-deterministic sampling.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help=f"File path to save the JSON evaluation report (default: {DEFAULT_REPORT_PATH}).",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose debug logging.",
    )

    args = parser.parse_args()

    # Logging setup
    level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    print("================================================================================")
    print("S28-08B Creative Regression Suite & Trace Grading")
    print("================================================================================")
    print(f"Workspace Root:   {WORKSPACE_ROOT}")
    print(f"Category Filter:  {args.category or 'ALL (13 categories)'}")
    print(f"Severity Filter:  {args.severity or 'ALL'}")
    print(f"Mode:             {'FAST' if args.fast else 'STANDARD'}")
    print(f"Output Report:    {args.output}")
    print("--------------------------------------------------------------------------------")

    runner = CreativeRegressionRunner(workspace_root=WORKSPACE_ROOT)
    run_result = runner.run_all(
        category_filter=args.category,
        severity_filter=args.severity,
    )

    # Ensure parent output directory exists
    args.output.parent.mkdir(parents=True, exist_ok=True)
    report_dict = run_result.model_dump(mode="json")
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=2, ensure_ascii=False)

    print("\n--------------------------------- RESULTS --------------------------------------")
    print(f"Verdict:              {run_result.verdict}")
    print(f"Total Cases:          {run_result.cases_total}")
    print(f"Passed:               {run_result.passed_count}")
    print(f"Failed:               {run_result.failed_count}")
    print(f"Pass Rate:            {run_result.pass_rate * 100:.1f}%")
    print(f"Negative Gates:       {run_result.deliberately_bad_detected_count}/{run_result.deliberately_bad_total_count} caught")

    if run_result.judge_calibration:
        jc = run_result.judge_calibration
        print(f"Judge Calibration:    {jc.agreement_rate * 100:.1f}% agreement ({jc.agreement_count}/{jc.total_calibration_pairs})")

    print("\nCategory Breakdown:")
    for cat_name, metrics in run_result.by_category.items():
        total = metrics.get("total", 0)
        passed = metrics.get("passed", 0)
        p_rate = metrics.get("pass_rate", 0.0) * 100
        print(f"  • {cat_name:<22}: {passed}/{total} passed ({p_rate:.0f}%)")

    print("\nSeverity Breakdown:")
    for sev_name, metrics in run_result.by_severity.items():
        total = metrics.get("total", 0)
        passed = metrics.get("passed", 0)
        p_rate = metrics.get("pass_rate", 0.0) * 100
        print(f"  • {sev_name:<10}: {passed}/{total} passed ({p_rate:.0f}%)")

    if run_result.regressions:
        print("\n[!] REGRESSIONS DETECTED:")
        for reg in run_result.regressions:
            print(f"  - Case: {reg.get('case_id')} [{reg.get('severity')}] in {reg.get('category')}")
            for reason in reg.get("reasons", []):
                print(f"      Reason: {reason}")

    print("================================================================================")
    print(f"Machine-readable report written to: {args.output}")

    return 0 if run_result.verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
