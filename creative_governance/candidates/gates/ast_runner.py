"""
creative_governance/candidates/gates/ast_runner.py
=================================
Hermetic subprocess runner invoking candidate_ast_worker.cjs for
exact TypeScript AST inspection and diagnostic compilation.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
WORKER_SCRIPT = WORKSPACE_ROOT / "scripts" / "validators" / "candidate_ast_worker.cjs"


def run_candidate_ast_worker(
    source_code: str,
    dependencies: Optional[List[str]] = None,
    template_schema: Optional[Dict[str, Any]] = None,
    skip_tsc: bool = False,
    timeout_seconds: int = 20,
) -> Dict[str, Any]:
    """
    Executes candidate_ast_worker.cjs via node with bounded timeout.
    Returns structured dictionary with static_code, security, dependencies,
    and typescript analysis.
    """
    payload = {
        "source_code": source_code,
        "dependencies": dependencies or [],
        "template_schema": template_schema or {},
        "skip_tsc": skip_tsc,
    }
    input_str = json.dumps(payload)

    if not WORKER_SCRIPT.exists():
        return {
            "success": False,
            "error": f"AST worker script not found at {WORKER_SCRIPT}",
        }

    try:
        proc = subprocess.run(
            ["node", str(WORKER_SCRIPT)],
            input=input_str,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            cwd=str(WORKSPACE_ROOT),
        )

        if proc.returncode != 0:
            return {
                "success": False,
                "error": f"AST worker failed with exit code {proc.returncode}: {proc.stderr}",
            }

        data = json.loads(proc.stdout)
        return data

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"AST worker timed out after {timeout_seconds} seconds",
            "timeout": True,
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"AST worker execution exception: {str(e)}",
        }
