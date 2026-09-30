#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/validators/check_ground_truth_sync.py — Ground Truth Synchronization & Drift Checker (S23 - LED-083).

Can be run:
1. In check mode: python scripts/validators/check_ground_truth_sync.py --check
   Fails if ground-truth/ has drifted from the generator.
2. In sync mode: python scripts/validators/check_ground_truth_sync.py
   Regenerates ground-truth/ artifacts deterministically.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
GENERATOR = ROOT / "scripts" / "generators" / "build_ground_truth.py"
GROUND_TRUTH_DIR = ROOT / "ground-truth"


def run_ground_truth_check(check_mode: bool = False) -> int:
    if not GENERATOR.exists():
        print(f"❌ FATAL: Ground truth generator missing at {GENERATOR}", file=sys.stderr)
        return 1

    # Execute generator
    res = subprocess.run([sys.executable, str(GENERATOR)], cwd=str(ROOT), capture_output=True, text=True)
    if res.returncode != 0:
        print(f"❌ FATAL: build_ground_truth.py failed:\n{res.stderr}\n{res.stdout}", file=sys.stderr)
        return res.returncode

    if check_mode:
        diff_res = subprocess.run(
            ["git", "status", "--porcelain", str(GROUND_TRUTH_DIR)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        if diff_res.stdout.strip():
            print(f"❌ FAIL: Ground truth is out of sync with generator. Modified files:\n{diff_res.stdout}", file=sys.stderr)
            return 1
        print("✅ Ground truth is synchronized and clean.")
    else:
        print("✅ Ground truth successfully regenerated.")

    return 0


if __name__ == "__main__":
    check = "--check" in sys.argv
    sys.exit(run_ground_truth_check(check_mode=check))
