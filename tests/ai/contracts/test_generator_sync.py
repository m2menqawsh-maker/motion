"""
tests/ai/contracts/test_generator_sync.py
=========================================
Verifies determinism and CI check-mode enforcement for the AI contract generator.

Guarantees:
- `python scripts/generate_ai_contracts.py --check` passes cleanly when artifacts are in sync.
- Staleness or drift in generated artifacts causes an immediate failure (exit code 1).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent.parent
GENERATOR_SCRIPT = ROOT / "scripts" / "generate_ai_contracts.py"


class TestGeneratorSync:

    def test_generator_check_mode_passes(self):
        """Verifies that the generated artifacts on disk match current Python contract authority."""
        result = subprocess.run(
            [sys.executable, str(GENERATOR_SCRIPT), "--check"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Generator check failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        assert "fully synchronized" in result.stdout

    def test_generator_detects_schema_drift(self, tmp_path):
        """Simulates staleness by verifying the generator detects any content divergence."""
        from scripts.generate_ai_contracts import check_artifacts, TS_OUTPUT_CONTRACTS

        original_content = TS_OUTPUT_CONTRACTS.read_text(encoding="utf-8")
        try:
            # Inject simulated drift
            TS_OUTPUT_CONTRACTS.write_text(original_content + "\n// DRIFT_INJECTION\n", encoding="utf-8")
            synced, errors = check_artifacts()
            assert synced is False
            assert len(errors) >= 1
            assert any("Stale TypeScript contract" in err for err in errors)
        finally:
            # Restore original content
            TS_OUTPUT_CONTRACTS.write_text(original_content, encoding="utf-8")

        # Confirm restored state is synced
        synced_after, errors_after = check_artifacts()
        assert synced_after is True
        assert len(errors_after) == 0
