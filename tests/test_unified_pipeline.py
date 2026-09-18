import pytest
import subprocess
import sys
import os
from pathlib import Path

workspace_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(workspace_root))

from tests.true_e2e_suite import run_scenario

def test_unified_pipeline_e2e():
    """
    اختبار شامل (E2E) ينفذ دورة الحياة الكاملة للمشروع 
    بدءاً من الاستخراج وصولاً لملف out.mp4
    """
    # Ensure it works for 16:9 as a representative test to avoid burning too much CI time
    result = run_scenario("Pytest_E2E_16_9", "16:9")
    assert result == True, "Failed to complete unified pipeline E2E!"
