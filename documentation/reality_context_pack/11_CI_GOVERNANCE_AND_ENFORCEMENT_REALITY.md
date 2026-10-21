# CI Governance & Enforcement Reality Report
- **Baseline Git SHA**: `90ec3de8d47494d5940d5cd1f9ed9a8e274ef6e1`
- **Branch**: `main`
- **Report Version**: 1.0.0
- **Last Updated**: 2026-10-07
- **Scope**: Rigorous comparison between GitHub Actions CI workflows, local `run_required_checks.sh`, test coverage, generational coverage gaps (S27, S28, S28-M, S28-R), and Mandatory Checks A & B.
- **Evidence Standard**: `CODE_PROVEN`, `TEST_PROVEN`, `CI_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`, `DOCUMENTATION_ONLY`, `INFERRED`, `UNKNOWN`

---

## 1. Executive Summary

A forensic audit of CI governance across `.github/workflows/remediation-ci.yml`, `scripts/ci/run_required_checks.sh`, and root package configurations reveals a **deep governance divergence** between what developers run locally, what GitHub Actions actually enforces, and what documentation claims:

1. **Mandatory Check A is FALSE**: Required GitHub Actions CI completely excludes `tests/ai` (270 test files). Zero tests in `tests/ai` are executed in any GitHub Actions job.
2. **Mandatory Check B is FALSE**: The local runner script `scripts/ci/run_required_checks.sh` is not an authentic mirror of `.github/workflows/remediation-ci.yml`. It diverges across six major structural axes, executing test suites CI misses while omitting linters, container audits, and acceptance tests that CI enforces.
3. **The 76% Unenforced Test Suite Reality**: Out of 510 total test files in the repository, GitHub Actions CI executes only **122 test files (23.9%)**. 388 test files (76.1%) are completely omitted from automated pull-request and branch-protection gating.
4. **Remotion Test Omission**: `npm run test` executes only 13 hardcoded test files in Vitest out of 49 files in `tests/remotion/`, leaving 36 modern S28-R renderer and authoring test files unexecuted in both local and remote CI.
5. **Coverage Illusion**: Pytest coverage gating enforces `--cov=api --cov=scripts/core --cov-fail-under=48`. It does not monitor or require coverage for `ai/`, `scripts/gates/`, `authoring/`, `planner/`, or `compositor/`.

---

## 2. GitHub Actions CI Architecture (`.github/workflows/remediation-ci.yml`)

The primary CI pipeline is defined in `.github/workflows/remediation-ci.yml` (265 lines). It triggers on pushes to `main`, `remediation/*`, `feature/*`, and pull requests targeting `main` and `feature/*`.

### 2.1 Workflow Jobs Topology

```
remediation-ci.yml
├── 1. python-quality      (Ruff linter on api/ and scripts/core/)
├── 2. contracts-ts        (Node 20: npm ci, tsc --noEmit, npm run test [13 vitest files])
├── 3. ground-truth        (check_ground_truth_sync.py, check_dependencies_lock.py)
├── 4. python-tests        (Pytest on 8 selected folders, --cov-fail-under=48)
├── 5. strict-e2e          (python tests/e2e/true_e2e_suite.py)
├── 6. docker-render       (docker build clean-video-builder, test_acc_007)
└── 7. security-audit      (pip-audit, npm audit, bandit, check_secrets.py, trivy-action)
```

### 2.2 Deep Inspection of Job Configurations

1. **Job `python-quality`** (lines 14-34):
   - Command: `ruff check api/ scripts/core/` [`CI_PROVEN`].
   - Scope: Strictly limited to `api/` and `scripts/core/`. Does NOT check `ai/`, `scripts/gates/`, `scripts/generators/`, or `creative_governance/`.

2. **Job `contracts-ts`** (lines 35-62):
   - Commands:
     - `cd remotion-app && npm run lint && npx tsc --noEmit`
     - `npm run test` (executes root `package.json` script: `vitest run tests/remotion/contracts.test.ts ...` [13 files]).
   - Scope: 36 test files in `tests/remotion/` are excluded.

3. **Job `ground-truth`** (lines 63-87):
   - Commands:
     - `python scripts/validators/check_ground_truth_sync.py --check`
     - `python scripts/validators/check_dependencies_lock.py --check`
   - Scope: Verifies derivative catalogs match disk reality and `uv.lock` / `requirements.txt` consistency.

4. **Job `python-tests`** (lines 88-134):
   - Command (lines 125-126):
     ```bash
     pytest --cov=api --cov=scripts/core --cov-report=xml --cov-report=term --cov-fail-under=48 \
       tests/core tests/gates tests/generators tests/validators tests/architecture tests/contracts tests/fault_injection tests/e2e/test_pipeline_integration.py
     ```
   - Target folders included: `tests/core` (32), `tests/gates` (1), `tests/generators` (2), `tests/validators` (2), `tests/architecture` (47), `tests/contracts` (2), `tests/fault_injection` (20), `tests/e2e/test_pipeline_integration.py` (1) = 107 files.
   - Target folders excluded: `tests/ai/` (270 files), `tests/api/` (11 files), `tests/security/` (9 files), `tests/remediation/` (48 files), `tests/golden_scenarios/` (4 files), `tests/performance/` (2 files), `tests/metrics/` (1 file), `tests/snapshots/` (1 file), `tests/documentation/` (3 files).

5. **Job `strict-e2e`** (lines 135-181):
   - Command: `python tests/e2e/true_e2e_suite.py` [`CI_PROVEN`].
   - Installs ffmpeg, executes `npx remotion browser ensure`, runs CLI orchestrator test.

6. **Job `docker-render`** (lines 182-217):
   - Commands:
     - `docker build -t clean-video-builder -f .agents/docker/Dockerfile.remotion .`
     - `docker run --rm clean-video-builder npx remotion versions`
     - `pytest tests/remediation/s02_acceptance/test_acc_007_docker_subcommand_validation.py -v`

7. **Job `security-audit`** (lines 218-265):
   - Commands:
     - `pip-audit --desc -r requirements.txt`
     - `npm audit --audit-level=high` (root & remotion-app)
     - `bandit -r api/ scripts/core/ -lll`
     - `python scripts/validators/check_secrets.py`
     - `uses: aquasecurity/trivy-action@master` with `scan-type: 'fs'`, `severity: 'CRITICAL,HIGH'`, `exit-code: '1'`.

---

## 3. Local CI Architecture (`scripts/ci/run_required_checks.sh`)

The local test runner `scripts/ci/run_required_checks.sh` (72 lines) claims in its banner to be the "Local Mirror for S24/S26 CI Required Checks".

### 3.1 Script Stages Topology

```
run_required_checks.sh
├── 1. [ground-truth] Schema & Dependency Drift Check
│   ├── check_ground_truth_sync.py --check
│   ├── check_dependencies_lock.py --check
│   ├── generate_ai_contracts.py --check
│   └── generate_creative_contracts.py --check
├── 2. [security-audit] Security, Dependency & Secret Audits
│   ├── pip-audit --desc
│   ├── npm audit (root & remotion-app)
│   ├── bandit -r api/ scripts/ -lll
│   └── check_secrets.py
├── 3. [contracts-ts] TypeScript Contracts & Remotion Lint
│   ├── (cd remotion-app && npx tsc --noEmit)
│   ├── (cd remotion-app && npm run lint)
│   └── npm test
├── 4. [python-tests] Pytest Suite with Coverage Threshold
│   └── pytest --cov=api --cov=scripts/core --cov-fail-under=48 ... tests/ai ...
├── 5. [strict-e2e] True E2E Suite (No Bypasses)
│   └── python tests/e2e/true_e2e_suite.py
└── 6. [docker-render] Hermetic Docker Verification
    └── (optional conditional check; skips if docker absent)
```

---

## 4. Rigorous Comparison Matrix (GitHub Actions vs. Local Script)

A line-by-line comparison of `.github/workflows/remediation-ci.yml` and `scripts/ci/run_required_checks.sh` proves **six fundamental structural divergence points**:

| Axis / Verification Area | GitHub Actions CI (`remediation-ci.yml`) | Local Script (`run_required_checks.sh`) | Governance Divergence Type | Impact & Reality |
|---|---|---|---|---|
| **1. `tests/ai` vs `tests/fault_injection`** | Excludes `tests/ai`. Includes `tests/fault_injection`. (`line 126`) | Includes `tests/ai`. Excludes `tests/fault_injection`. (`line 50`) | **Direct Suite Inversion** | Local runner executes 270 AI tests that CI ignores; CI executes 20 chaos fault injection tests that local script skips. |
| **2. Contract Code Generator Verification** | Does not run contract generator drift checks. | Runs `generate_ai_contracts.py --check` and `generate_creative_contracts.py --check`. (`lines 23-24`) | **Local-Only Gate** | Code contract drift breaks local runs, but merges cleanly through GitHub CI without detection. |
| **3. Python Linting (`ruff`)** | Dedicated `python-quality` job runs `ruff check api/ scripts/core/`. (`line 33`) | Completely absent. Zero ruff invocation. | **CI-Only Gate** | Formatting/lint bugs pass locally but fail remotely in GitHub CI. |
| **4. Static Security Scanning (`bandit`)** | Restricts scanning scope to `api/ scripts/core/`. (`line 251`) | Scans all scripts: `bandit -r api/ scripts/ -lll`. (`line 35`) | **Scope Asymmetry** | Local script triggers on developer scripts in `scripts/maintenance/` or `scripts/archive/` that CI ignores. |
| **5. Container & FS Vulnerability Scan (`trivy`)** | Runs `aquasecurity/trivy-action@master` failing on CRITICAL/HIGH. (`line 257`) | Completely absent. | **CI-Only Gate** | Remote CI enforces filesystem CVE rules not audited locally. |
| **6. Hermetic Docker Build & Acceptance Test** | Always builds `clean-video-builder` and executes `test_acc_007_docker_subcommand_validation.py`. (`lines 205-217`) | Skips if Docker is absent (`lines 60-66`); never builds image and never runs `test_acc_007`. | **Conditional Bypass** | Local run passes even if Docker build or container execution is completely broken. |

---

## 5. Mandatory Check A — Formal Architectural Answer

### Question:
> **Does required GitHub CI run `tests/ai` in its entirety?**

### Reality Finding:
**NO (`CI_PROVEN`, `CODE_PROVEN`). Required GitHub Actions CI completely omits `tests/ai`.**

### Verbatim Evidence:
In `.github/workflows/remediation-ci.yml`, the only step executing pytest is lines 124-127:
```yaml
      - name: Run Pytest with Coverage Threshold
        env:
          PYTHONPATH: .
          TESTING: '1'
        run: |
          pytest --cov=api --cov=scripts/core --cov-report=xml --cov-report=term --cov-fail-under=48 \
            tests/core tests/gates tests/generators tests/validators tests/architecture tests/contracts tests/fault_injection tests/e2e/test_pipeline_integration.py
```
- Total test files in `tests/ai/`: **270 files** (`find tests/ai -name "test_*.py" | wc -l` yields 270).
- Search for `tests/ai` across the entire `.github/` folder: **0 occurrences** (`grep -rn "tests/ai" .github/` returns 0).
- No other job in `.github/workflows/remediation-ci.yml` invokes pytest or Python test runners against `tests/ai`.

### Architectural Conclusion:
The entire S27 and S28 AI platform (routing, capabilities, planning, context, memory, audio/vision intelligence, speech) is completely **ungated by remote GitHub Actions CI**. Code breaking `tests/ai` can be committed, pushed to `main`, and pass all required branch protection checks without failure.

---

## 6. Mandatory Check B — Formal Architectural Answer

### Question:
> **Does local `run_required_checks.sh` match actual GitHub required checks?**

### Reality Finding:
**NO (`CI_PROVEN`, `CODE_PROVEN`). The local runner script `scripts/ci/run_required_checks.sh` substantially diverges from `.github/workflows/remediation-ci.yml`.**

### Comparative Verbatim Evidence:
1. **Pytest Invocations Side-by-Side**:
   - `remediation-ci.yml:125-126`:
     ```bash
     pytest ... tests/core tests/gates tests/generators tests/validators tests/architecture tests/contracts tests/fault_injection tests/e2e/test_pipeline_integration.py
     ```
   - `run_required_checks.sh:49-50`:
     ```bash
     pytest ... tests/core tests/gates tests/generators tests/validators tests/architecture tests/ai tests/contracts tests/e2e/test_pipeline_integration.py
     ```
   *Difference*: CI runs `tests/fault_injection` and excludes `tests/ai`. Local runs `tests/ai` and excludes `tests/fault_injection`.

2. **Contract Generator Drift Checks**:
   - `run_required_checks.sh:23-24`:
     ```bash
     python scripts/generate_ai_contracts.py --check
     python scripts/generate_creative_contracts.py --check
     ```
   - `remediation-ci.yml`: Omitted.

3. **Linter Enforcement**:
   - `remediation-ci.yml:33`: Runs `ruff check api/ scripts/core/`.
   - `run_required_checks.sh`: Omitted.

4. **Security Audit Scope**:
   - `remediation-ci.yml:251`: `bandit -r api/ scripts/core/ -lll`.
   - `run_required_checks.sh:35`: `bandit -r api/ scripts/ -lll`.

5. **Docker Acceptance Test**:
   - `remediation-ci.yml:216`: Executes `pytest tests/remediation/s02_acceptance/test_acc_007_docker_subcommand_validation.py -v`.
   - `run_required_checks.sh`: Skips if Docker is absent, never builds image, never runs `test_acc_007`.

### Architectural Conclusion:
`scripts/ci/run_required_checks.sh` gives developers a false sense of parity. Passing checks locally does not guarantee passing GitHub CI, and passing GitHub CI does not guarantee local checks would pass.

---

## 7. Cross-Generational CI Coverage Gap Analysis

| Architectural Generation | Subsystem Scope | Total Test Files | Tests Run in GitHub CI | Tests Run in Local Script | CI Enforcement Status |
|---|---|---|---|---|---|
| **Pre-S25 (Legacy / Pipeline)** | `tests/core/`, `tests/gates/`, `tests/generators/`, `tests/validators/`, `tests/e2e/` | 41 | 39 | 38 | ✅ **ENFORCED** (95%) |
| **S26 (Governance & Architecture)**| `tests/architecture/`, `tests/fault_injection/`, `tests/contracts/` | 69 | 69 | 49 | ⚠️ **PARTIAL** (Fault injection dropped locally) |
| **S27 (AI Infrastructure)** | `tests/ai/routing/`, `tests/ai/providers/`, `tests/ai/context/`, `tests/ai/memory/` | 84 | 0 | 84 | ❌ **UNENFORCED IN CI** (0%) |
| **S28 (Creative Intelligence)** | `tests/ai/planning/`, `tests/ai/narrative/`, `tests/ai/taste/`, `tests/ai/recipes/`, `tests/ai/skills/` | 96 | 0 | 96 | ❌ **UNENFORCED IN CI** (0%) |
| **S28-M (Capability / MCP Platform)**| `tests/ai/capabilities/`, `tests/ai/tools/`, `tests/ai/acquisition/`, `tests/ai/media_processing/` | 90 | 0 | 90 | ❌ **UNENFORCED IN CI** (0%) |
| **S28-R (Renderer Independence & Authoring)**| `tests/remotion/s28_r*` (Mutations, Preview, Canvas, Compositor, RenderPlanner) | 36 | 0 | 0 | ❌ **UNENFORCED ANYWHERE** (0%) |
| **SaaS API Subsystem** | `tests/api/`, `tests/security/` | 20 | 0 | 0 | ❌ **UNENFORCED ANYWHERE** (0%) |

### Key Takeaway on S28-R & Remotion Tests:
The 36 test files under `tests/remotion/` created during the S28-R milestone (Renderer Independence, Unified Authoring, Preview Engine, Master Compositor, and Render Planner) are **unwired from root `package.json`** (`package.json:8` lists only 13 test files). As a consequence, neither GitHub Actions CI nor the local CI runner ever executes the modern S28-R test suite!

---

## 8. Python Quality & Coverage Gate Reality

In `pyproject.toml:47-57` and `.github/workflows/remediation-ci.yml:125`:
```toml
[tool.pytest.ini_options]
addopts = "--import-mode=importlib --cov=api --cov=scripts/core --cov-report=term-missing --cov-fail-under=48"
```
The test coverage gate enforces:
1. **Low Baseline**: Fail under threshold is set to **48%**.
2. **Narrow Scope**: Coverage measures strictly `api/` and `scripts/core/`.
3. **Excluded Subsystems**:
   - `ai/` is excluded from coverage accounting.
   - `scripts/gates/` is excluded from coverage accounting.
   - `scripts/generators/` is excluded from coverage accounting.
   - `authoring/`, `planner/`, `compositor/`, `preview/` are TypeScript and excluded from Python coverage.
4. **False Security**: Because `tests/api/` (11 test files) is excluded from the CI pytest command, coverage of `api/` relies primarily on indirect calls from `tests/core/` and `tests/fault_injection/`.

---

## 9. Verification Methods and Reproducible Commands

To independently reproduce and verify the findings in this report:

1. **Verify Check A (`tests/ai` Exclusion in CI)**:
   ```bash
   # Check if tests/ai is referenced anywhere in .github/workflows/remediation-ci.yml:
   grep -n "tests/ai" .github/workflows/remediation-ci.yml
   # Returns 0 lines (exit code 1)
   ```

2. **Verify Check B (Divergence between Workflow and Local Script)**:
   ```bash
   # Compare pytest testpaths:
   echo "--- GitHub CI pytest command ---"
   grep -n "pytest " .github/workflows/remediation-ci.yml
   echo "--- Local script pytest command ---"
   grep -n "pytest " scripts/ci/run_required_checks.sh
   # Observe: CI includes tests/fault_injection; script includes tests/ai
   ```

3. **Verify Remotion Unrun Tests in `package.json`**:
   ```bash
   # Inspect package.json test script:
   grep '"test":' package.json
   # Note: Exactly 13 files specified.
   # Count total remotion test files:
   find tests/remotion -name "*.test.ts" | wc -l
   # Note: Exactly 49 files on disk. (36 files unrun).
   ```

4. **Verify Total Test File Counts**:
   ```bash
   find tests -type f \( -name "test_*.py" -o -name "*_test.py" -o -name "*.test.ts" -o -name "true_e2e_suite.py" \) | wc -l
   # Returns: 510
   ```
