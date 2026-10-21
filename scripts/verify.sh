#!/usr/bin/env bash
# scripts/verify.sh
# ==============================================================================
# Phase 0 Honest Baseline & Multi-Tool Verification Runner
#
# Runs all verification groups corresponding to CI (.github/workflows/remediation-ci.yml):
#   1. ruff (Python Quality)
#   2. tsc (TypeScript Type Checking - Remotion App & Root)
#   3. vitest (Contracts & Remotion Parity Suite)
#   4. ground-truth (Ground Truth & Dependency Lock Validators)
#   5. pytest python-tests (Core Platform, API, Gates, Security, Integration)
#   6. pytest strict-e2e (Product HTTP and Loopback Smoke)
#   7. pytest ai-verification (Tier 1 AI Platform & Tier 2 Candidates)
#
# Generates JUnit XML and raw logs in evidence/phase0/.
# Prints a summary table (ناجح / فاشل / متخطّى) and exits with non-zero if any tool fails.
# ==============================================================================

set -o pipefail

WORKSPACE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$WORKSPACE"

EVIDENCE_DIR="$WORKSPACE/evidence/phase0"
mkdir -p "$EVIDENCE_DIR"

# Python executable resolution
if [ -n "$VIRTUAL_ENV" ] && [ -x "$VIRTUAL_ENV/bin/python" ]; then
  PYTHON="$VIRTUAL_ENV/bin/python"
elif [ -x "$WORKSPACE/.venv/bin/python" ]; then
  PYTHON="$WORKSPACE/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON="$(command -v python3)"
else
  PYTHON="python"
fi

export PYTHONPATH="$WORKSPACE"
export TESTING=1

OVERALL_EXIT=0

declare -a TOOL_NAMES=()
declare -a TOOL_STATUSES=()
declare -a TOOL_EXITCODES=()
declare -a TOOL_DURATIONS=()
declare -a TOOL_DETAILS=()

# Helper to write basic JUnit XML for non-native tools
write_simple_junit() {
  local suite_name="$1"
  local test_name="$2"
  local exit_code="$3"
  local xml_path="$4"
  local raw_output_file="$5"
  local duration="$6"

  if [ "$exit_code" -eq 0 ]; then
    cat <<EOF > "$xml_path"
<?xml version="1.0" encoding="UTF-8"?>
<testsuites name="${suite_name}" tests="1" failures="0" errors="0" time="${duration}">
  <testsuite name="${suite_name}" tests="1" failures="0" errors="0" time="${duration}">
    <testcase name="${test_name}" classname="${suite_name}" time="${duration}"/>
  </testsuite>
</testsuites>
EOF
  elif [ "$exit_code" -eq 77 ]; then
    cat <<EOF > "$xml_path"
<?xml version="1.0" encoding="UTF-8"?>
<testsuites name="${suite_name}" tests="1" failures="0" errors="0" skipped="1" time="${duration}">
  <testsuite name="${suite_name}" tests="1" failures="0" errors="0" skipped="1" time="${duration}">
    <testcase name="${test_name}" classname="${suite_name}" time="${duration}">
      <skipped message="Prerequisite not met"/>
    </testcase>
  </testsuite>
</testsuites>
EOF
  else
    local err_msg
    err_msg=$(head -n 20 "$raw_output_file" 2>/dev/null | tr '<>&"' '    ' || echo "Execution failed")
    cat <<EOF > "$xml_path"
<?xml version="1.0" encoding="UTF-8"?>
<testsuites name="${suite_name}" tests="1" failures="1" errors="0" time="${duration}">
  <testsuite name="${suite_name}" tests="1" failures="1" errors="0" time="${duration}">
    <testcase name="${test_name}" classname="${suite_name}" time="${duration}">
      <failure message="Tool exited with code ${exit_code}">${err_msg}</failure>
    </testcase>
  </testsuite>
</testsuites>
EOF
  fi
}

run_check() {
  local name="$1"
  local desc="$2"
  local cmd="$3"
  local raw_file="$4"
  local junit_file="$5"

  echo ""
  echo "================================================================================"
  echo ">>> [RUNNING] $name: $desc"
  echo "    Command: $cmd"
  echo "================================================================================"

  local start_time
  start_time=$(date +%s)

  local exit_code=0
  eval "$cmd" > "$raw_file" 2>&1 || exit_code=$?

  local end_time
  end_time=$(date +%s)
  local duration=$((end_time - start_time))

  local status="ناجح"
  if [ "$exit_code" -eq 77 ]; then
    status="متخطّى"
  elif [ "$exit_code" -ne 0 ]; then
    status="فاشل"
    OVERALL_EXIT=1
  fi

  # Generate JUnit XML if not already written by the tool
  if [ ! -f "$junit_file" ]; then
    write_simple_junit "$name" "$desc" "$exit_code" "$junit_file" "$raw_file" "$duration"
  fi

  TOOL_NAMES+=("$name")
  TOOL_STATUSES+=("$status")
  TOOL_EXITCODES+=("$exit_code")
  TOOL_DURATIONS+=("${duration}s")
  TOOL_DETAILS+=("$desc")

  echo ">>> [RESULT] $name: $status (exit code: $exit_code, duration: ${duration}s)"
}

echo "================================================================================"
echo "          MOTION PHASE 0 BASELINE VERIFICATION & MEASUREMENT RUNNER             "
echo "================================================================================"
echo "Workspace:     $WORKSPACE"
echo "Python:        $PYTHON ($($PYTHON --version 2>&1))"
echo "Node:          $(node --version 2>/dev/null || echo 'not found')"
echo "Evidence Dir:  $EVIDENCE_DIR"
echo "Timestamp:     $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "================================================================================"

# 1. ruff (Python Linting)
run_check \
  "ruff-lint" \
  "Python lint check (api/ scripts/core/)" \
  "$PYTHON -m ruff check api/ scripts/core/ --output-format=junit --output-file=\"$EVIDENCE_DIR/ruff_junit.xml\"" \
  "$EVIDENCE_DIR/ruff_raw.txt" \
  "$EVIDENCE_DIR/ruff_junit.xml"

# 2. tsc (Remotion App TypeScript compilation & typecheck)
run_check \
  "tsc-remotion-app" \
  "TypeScript type check in remotion-app" \
  "(cd \"$WORKSPACE/remotion-app\" && npx tsc --noEmit)" \
  "$EVIDENCE_DIR/tsc_remotion_app_raw.txt" \
  "$EVIDENCE_DIR/tsc_remotion_app_junit.xml"

# 3. tsc (Root TypeScript typecheck)
run_check \
  "tsc-root" \
  "TypeScript type check in root" \
  "npx tsc --noEmit" \
  "$EVIDENCE_DIR/tsc_root_raw.txt" \
  "$EVIDENCE_DIR/tsc_root_junit.xml"

# 4. Vitest (Contracts & Parity suite - npm run test)
run_check \
  "vitest-contracts" \
  "Vitest contracts & parity suite (14 test files)" \
  "npx vitest run tests/remotion/contracts.test.ts tests/remotion/merge.test.ts tests/remotion/template_runtime_resolution.test.ts tests/remotion/datastory_contract.test.ts tests/remotion/manifest.test.ts tests/remotion/blueprint.test.ts tests/remotion/asset_resolution.test.ts tests/remotion/template_contract_parity.test.ts tests/remotion/effects.test.ts tests/remotion/s16_reproductions.test.ts tests/remotion/s16_pre_mount_gate.test.ts tests/remotion/s17_render_input_parity.test.ts tests/remotion/ai_contracts_parity.test.ts tests/remotion/zod_v3_v4_parity.test.ts --reporter=default --reporter=junit --outputFile=\"$EVIDENCE_DIR/vitest_contracts_junit.xml\"" \
  "$EVIDENCE_DIR/vitest_contracts_raw.txt" \
  "$EVIDENCE_DIR/vitest_contracts_junit.xml"

# 5. Ground Truth & Dependency Lock Validators
run_check \
  "ground-truth" \
  "Check ground truth sync & dependencies lock" \
  "$PYTHON scripts/validators/check_ground_truth_sync.py --check && $PYTHON scripts/validators/check_dependencies_lock.py --check" \
  "$EVIDENCE_DIR/ground_truth_raw.txt" \
  "$EVIDENCE_DIR/ground_truth_junit.xml"

# 6. Pytest (python-tests: Core Platform & Coverage Suite)
run_check \
  "pytest-python-tests" \
  "CI python-tests suite (core, gates, generators, validators, architecture, contracts, security, api)" \
  "$PYTHON -m pytest tests/core tests/gates tests/generators tests/validators tests/architecture tests/contracts tests/fault_injection tests/security tests/api tests/integration/test_pr003_ai_runtime_vertical_slice.py tests/integration/test_pr004_state_consistency.py tests/integration/test_pr005_process_hard_death_recovery.py tests/integration/test_pr005_run_blueprint_provenance.py tests/e2e/test_pipeline_integration.py tests/integration/test_b1_context_knowledge_creative_proposal.py tests/integration/test_b2_capability_gateway_integration.py -o junit_family=xunit2 --junitxml=\"$EVIDENCE_DIR/pytest_python_tests_junit.xml\"" \
  "$EVIDENCE_DIR/pytest_python_tests_raw.txt" \
  "$EVIDENCE_DIR/pytest_python_tests_junit.xml"

# 7. Pytest (strict-e2e)
run_check \
  "pytest-strict-e2e" \
  "Strict E2E product HTTP & loopback smoke" \
  "$PYTHON -m pytest tests/e2e/test_product_http_to_mp4_e2e.py tests/e2e/test_process_loopback_smoke.py -o junit_family=xunit2 --junitxml=\"$EVIDENCE_DIR/pytest_strict_e2e_junit.xml\"" \
  "$EVIDENCE_DIR/pytest_strict_e2e_raw.txt" \
  "$EVIDENCE_DIR/pytest_strict_e2e_junit.xml"

# 8. Pytest (ai-verification Tier 1)
run_check \
  "pytest-ai-tier1" \
  "AI verification Tier 1 platform suite" \
  "$PYTHON -m pytest tests/ai/ --ignore=tests/ai/candidates -o junit_family=xunit2 --junitxml=\"$EVIDENCE_DIR/pytest_ai_tier1_junit.xml\"" \
  "$EVIDENCE_DIR/pytest_ai_tier1_raw.txt" \
  "$EVIDENCE_DIR/pytest_ai_tier1_junit.xml"

# 9. Pytest (ai-verification Tier 2)
run_check \
  "pytest-ai-tier2" \
  "AI verification Tier 2 candidates suite" \
  "$PYTHON -m pytest tests/ai/candidates/ -o junit_family=xunit2 --junitxml=\"$EVIDENCE_DIR/pytest_ai_tier2_junit.xml\"" \
  "$EVIDENCE_DIR/pytest_ai_tier2_raw.txt" \
  "$EVIDENCE_DIR/pytest_ai_tier2_junit.xml"

echo ""
echo "================================================================================"
echo "                      جدول نتائج التحقق والقياس (Summary Table)                 "
echo "================================================================================"
printf "| %-22s | %-10s | %-10s | %-10s | %-32s |\n" "الأداة / المجموعة" "الحالة" "كود الخروج" "المدة" "الوصف"
echo "|------------------------|------------|------------|------------|----------------------------------|"

PASSED_COUNT=0
FAILED_COUNT=0
SKIPPED_COUNT=0

for i in "${!TOOL_NAMES[@]}"; do
  name="${TOOL_NAMES[$i]}"
  status="${TOOL_STATUSES[$i]}"
  code="${TOOL_EXITCODES[$i]}"
  dur="${TOOL_DURATIONS[$i]}"
  det="${TOOL_DETAILS[$i]}"

  if [ "$status" == "ناجح" ]; then
    ((PASSED_COUNT++))
  elif [ "$status" == "متخطّى" ]; then
    ((SKIPPED_COUNT++))
  else
    ((FAILED_COUNT++))
  fi

  printf "| %-22s | %-10s | %-10s | %-10s | %-32s |\n" "$name" "$status" "$code" "$dur" "${det:0:32}"
done

echo "|------------------------|------------|------------|------------|----------------------------------|"
echo "الإجمالي: ${#TOOL_NAMES[@]} أدوات | ناجح: $PASSED_COUNT | فاشل: $FAILED_COUNT | متخطّى: $SKIPPED_COUNT"
echo "حالة الخروج النهائية (Overall exit): $OVERALL_EXIT"
echo "جميع ملفات الأدلة محفوظة في: $EVIDENCE_DIR"
echo "================================================================================"

exit $OVERALL_EXIT
