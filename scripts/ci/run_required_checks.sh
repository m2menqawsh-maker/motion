#!/usr/bin/env bash
# scripts/ci/run_required_checks.sh
# ==================================
# Canonical local required-check runner providing 1:1 parity with GitHub Actions (PR-A3).
# Derives gate definitions and metadata directly from scripts/ci/ci_matrix.py.
#
# Invariants:
# - Covers all 9 required verification gates matching .github/workflows/remediation-ci.yml:
#     1. python-quality
#     2. contracts-ts
#     3. ground-truth
#     4. python-tests
#     5. strict-e2e
#     6. docker-render
#     7. security-audit
#     8. remotion-verification
#     9. ai-verification
# - Strict outcome classification:
#     * PASS
#     * FAIL
#     * BLOCKED
#     * NOT RUN / ENVIRONMENT UNAVAILABLE
# - Missing Docker daemon or unavailable tools are classified as NOT RUN / UNAVAILABLE, never PASS.
# - Exit code: 0 if all runnable gates pass; 1 if any gate fails.

set -o pipefail

WORKSPACE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$WORKSPACE"

if [ -d "$WORKSPACE/.venv/bin" ]; then
  export PATH="$WORKSPACE/.venv/bin:$PATH"
fi

export PYTHONPATH="$WORKSPACE"
export TESTING=1

# Color definitions
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Default options
TARGET_GATE=""
SKIP_DOCKER=0
REPORT_JSON=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --list)
      python3 -m scripts.ci.ci_matrix --list
      exit 0
      ;;
    --gate)
      TARGET_GATE="$2"
      shift 2
      ;;
    --skip-docker)
      SKIP_DOCKER=1
      shift
      ;;
    --report-json)
      REPORT_JSON="$2"
      shift 2
      ;;
    --help|-h)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --list                List all 9 canonical CI gates"
      echo "  --gate <name>         Run a specific CI gate only"
      echo "  --skip-docker         Skip docker-render gate"
      echo "  --report-json <path>  Export machine-readable JSON summary"
      echo "  --help, -h            Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

# Gate definitions in canonical execution sequence
ALL_GATES=(
  "python-quality"
  "contracts-ts"
  "ground-truth"
  "python-tests"
  "strict-e2e"
  "docker-render"
  "security-audit"
  "remotion-verification"
  "ai-verification"
)

if [ -n "$TARGET_GATE" ]; then
  GATES_TO_RUN=("$TARGET_GATE")
else
  GATES_TO_RUN=("${ALL_GATES[@]}")
fi

declare -A GATE_STATUS
declare -A GATE_DURATION
declare -A GATE_CATEGORY

ANY_FAILURE=0

echo -e "${BOLD}${CYAN}================================================================================${NC}"
echo -e "${BOLD}${CYAN}            MOTION LOCAL VERIFICATION RUNNER — CI PARITY (PR-A3)                ${NC}"
echo -e "${BOLD}${CYAN}================================================================================${NC}"

for gate in "${GATES_TO_RUN[@]}"; do
  if [ "$gate" == "docker-render" ] && [ "$SKIP_DOCKER" -eq 1 ]; then
    GATE_STATUS["$gate"]="SKIPPED"
    GATE_DURATION["$gate"]="0.0s"
    GATE_CATEGORY["$gate"]="container"
    continue
  fi

  # Query gate metadata from canonical matrix
  GATE_INFO=$(python3 -m scripts.ci.ci_matrix --get-gate "$gate" 2>/dev/null)
  if [ -z "$GATE_INFO" ]; then
    echo -e "${RED}Error: Gate '$gate' not found in canonical CI matrix.${NC}" >&2
    exit 1
  fi

  CATEGORY=$(python3 -c "import json, sys; print(json.loads('''$GATE_INFO''')['category'])")
  GATE_CATEGORY["$gate"]="$CATEGORY"

  echo ""
  echo -e "${BOLD}>>> [GATE] ${CYAN}${gate}${NC} (${CATEGORY}) — Executing...${NC}"

  # Evaluate prerequisites
  PREREQ_MET=1
  PREREQ_REASON=""

  if [ "$gate" == "docker-render" ]; then
    if ! command -v docker >/dev/null 2>&1; then
      PREREQ_MET=0
      PREREQ_REASON="Docker CLI binary not found in PATH"
    elif ! docker info >/dev/null 2>&1; then
      PREREQ_MET=0
      PREREQ_REASON="Docker daemon is not running or socket is inaccessible"
    fi
  fi

  if [ "$PREREQ_MET" -eq 0 ]; then
    echo -e "    ${YELLOW}⚠️  PREREQUISITE NOT MET: ${PREREQ_REASON}${NC}"
    echo -e "    ${YELLOW}Status: NOT RUN / ENVIRONMENT UNAVAILABLE (not marked as PASS)${NC}"
    GATE_STATUS["$gate"]="NOT RUN / ENVIRONMENT UNAVAILABLE"
    GATE_DURATION["$gate"]="0.0s"
    continue
  fi

  START_TIME=$(python3 -c "import time; print(time.time())")
  GATE_FAILED=0

  # Extract commands and run
  NUM_CMDS=$(python3 -c "import json; print(len(json.loads('''$GATE_INFO''')['commands']))")

  for ((i=0; i<NUM_CMDS; i++)); do
    CMD=$(python3 -c "import json; print(json.loads('''$GATE_INFO''')['commands'][$i])")
    echo -e "    ${CYAN}\$ ${CMD}${NC}"
    
    if ! eval "$CMD"; then
      GATE_FAILED=1
      echo -e "    ${RED}❌ Command failed with non-zero exit code.${NC}"
      break
    fi
  done

  END_TIME=$(python3 -c "import time; print(time.time())")
  DURATION=$(python3 -c "print(f'{$END_TIME - $START_TIME:.1f}s')")
  GATE_DURATION["$gate"]="$DURATION"

  if [ "$GATE_FAILED" -eq 0 ]; then
    echo -e "    ${GREEN}✅ GATE '${gate}' PASSED (${DURATION})${NC}"
    GATE_STATUS["$gate"]="PASS"
  else
    echo -e "    ${RED}❌ GATE '${gate}' FAILED (${DURATION})${NC}"
    GATE_STATUS["$gate"]="FAIL"
    ANY_FAILURE=1
  fi
done

# Render Summary Table
echo ""
echo -e "${BOLD}${CYAN}================================================================================${NC}"
echo -e "${BOLD}${CYAN}                       VERIFICATION & PARITY SUMMARY TABLE                      ${NC}"
echo -e "${BOLD}${CYAN}================================================================================${NC}"
printf "%-26s %-14s %-32s %-10s\n" "GATE" "CATEGORY" "STATUS" "DURATION"
echo "--------------------------------------------------------------------------------"

for gate in "${GATES_TO_RUN[@]}"; do
  status="${GATE_STATUS[$gate]}"
  cat="${GATE_CATEGORY[$gate]}"
  dur="${GATE_DURATION[$gate]}"

  if [ "$status" == "PASS" ]; then
    status_fmt="${GREEN}${status}${NC}"
  elif [ "$status" == "FAIL" ]; then
    status_fmt="${RED}${status}${NC}"
  elif [[ "$status" == *"NOT RUN"* ]]; then
    status_fmt="${YELLOW}${status}${NC}"
  else
    status_fmt="${CYAN}${status}${NC}"
  fi

  printf "%-26s %-14s " "$gate" "$cat"
  echo -ne "$status_fmt"
  # padding for status
  pad=$((32 - ${#status}))
  if [ $pad -gt 0 ]; then
    printf "%*s" $pad ""
  fi
  printf " %-10s\n" "$dur"
done

echo -e "${BOLD}${CYAN}================================================================================${NC}"

# Optional JSON report export
if [ -n "$REPORT_JSON" ]; then
  mkdir -p "$(dirname "$REPORT_JSON")"
  python3 -c "
import json
results = []
for g in '''${GATES_TO_RUN[*]}'''.split():
    results.append({
        'gate': g,
        'category': '''${GATE_CATEGORY[\$g]}''',
        'status': '''${GATE_STATUS[\$g]}''',
        'duration': '''${GATE_DURATION[\$g]}''',
    })
with open('''$REPORT_JSON''', 'w') as f:
    json.dump({'gates': results, 'any_failure': bool($ANY_FAILURE)}, f, indent=2)
"
  echo "Machine-readable summary exported to: $REPORT_JSON"
fi

if [ "$ANY_FAILURE" -eq 1 ]; then
  echo -e "${RED}${BOLD}❌ LOCAL VERIFICATION FAILED — One or more required gates failed.${NC}"
  exit 1
else
  echo -e "${GREEN}${BOLD}✅ LOCAL VERIFICATION COMPLETE — All executed gates passed.${NC}"
  exit 0
fi
