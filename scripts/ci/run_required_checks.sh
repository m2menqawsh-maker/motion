#!/usr/bin/env bash
set -eo pipefail

# scripts/ci/run_required_checks.sh — Local Mirror for S24/S26 CI Required Checks
echo "========================================================"
echo "🚀 Running S24 Strict Production CI Checks (Local Mirror)"
echo "========================================================"

WORKSPACE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$WORKSPACE"

if [ -d "$WORKSPACE/.venv/bin" ]; then
  export PATH="$WORKSPACE/.venv/bin:$PATH"
fi

export PYTHONPATH="$WORKSPACE"
export TESTING=1

echo ""
echo "─── 1. [ground-truth] Schema & Dependency Drift Check ───"
python scripts/validators/check_ground_truth_sync.py --check
python scripts/validators/check_dependencies_lock.py --check
echo "✅ Ground Truth & Dependencies verified."

echo ""
echo "─── 2. [security-audit] Security, Dependency & Secret Audits ───"
echo "  • Running pip-audit..."
pip-audit --desc
echo "  • Running npm audit (root & remotion-app)..."
npm audit --audit-level=high
(cd remotion-app && npm audit --audit-level=high)
echo "  • Running bandit static code scanner..."
bandit -r api/ scripts/ -lll
echo "  • Running repository secret scanner..."
python scripts/validators/check_secrets.py
echo "✅ Security Audits passed."

echo ""
echo "─── 3. [contracts-ts] TypeScript Contracts & Remotion Lint ───"
(cd remotion-app && npx tsc --noEmit)
(cd remotion-app && npm run lint)
npm test
echo "✅ TypeScript contracts and Vitest passed."

echo ""
echo "─── 4. [python-tests] Pytest Suite with Coverage Threshold ───"
pytest --cov=api --cov=scripts/core --cov-report=xml --cov-report=term --cov-fail-under=48 \
  tests/core tests/gates tests/generators tests/validators tests/architecture tests/contracts tests/e2e/test_pipeline_integration.py
echo "✅ Python tests and coverage verified."

echo ""
echo "─── 5. [strict-e2e] True E2E Suite (No Bypasses) ───"
python tests/e2e/true_e2e_suite.py
echo "✅ True E2E suite passed."

echo ""
echo "─── 6. [docker-render] Hermetic Docker Verification ───"
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  echo "  • Docker is available. Verifying Docker container run..."
  docker run --rm clean-video-builder npx remotion versions
  echo "✅ Docker verification passed."
else
  echo "⚠️ Docker is not available locally; skipping local docker run (enforced in CI)."
fi

echo ""
echo "========================================================"
echo "🎉 ALL REQUIRED CI GATES PASSED SUCCESSFULLY!"
echo "========================================================"
