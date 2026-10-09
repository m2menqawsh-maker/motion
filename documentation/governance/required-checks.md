# CI Required Checks Specification (S24 / S26)

This document establishes the canonical and stable check names enforced in CI to protect the `main` branch.
In S26, these exact job identifiers will be configured as GitHub Required Status Checks.

## 1. Summary of Required Checks

| Check Name (Job ID) | Category | Failure Semantics | Description |
|----------------------|----------|-------------------|-------------|
| `python-quality`     | Static Quality | Fail-Closed | Enforces code formatting, ruff/flake8 lint, and AST subprocess confinement. |
| `contracts-ts`       | Typecheck & Contracts | Fail-Closed | Enforces TypeScript compilation (`tsc --noEmit`), Remotion lint, and Vitest suite. |
| `ground-truth`       | Drift Detection | Fail-Closed | Verifies zero drift between schemas, TypeScript types, and JSON schemas (`check_ground_truth_sync.py --check`). Also checks dependency locks (`check_dependencies_lock.py --check`). |
| `python-tests`       | Unit & Integration | Fail-Closed | Executes Python test suites with coverage measurement enforcing `--cov-fail-under=48`. Uploads `coverage.xml`. |
| `strict-e2e`         | True End-to-End | Fail-Closed | Executes `tests/e2e/true_e2e_suite.py` across multi-template and aspect ratio matrix with 0 bypasses (`SKIP_STRICT_QC` strictly banned). Verifies positive rendering and negative defect rejection. |
| `docker-render`      | Hermetic Container | Fail-Closed | Builds clean Docker image (`clean-video-builder`) without host `node_modules`, executes representative containerized render, and validates strict Final QC parity. |
| `security-audit`     | Security & Supply Chain | Fail-Closed | Executes `pip-audit`, `npm audit --audit-level=high`, `bandit -r api/ scripts/ -lll`, repository secret scanning (`check_secrets.py`), and container scanning. High and Critical severity findings trigger exit code 1. |

## 2. Policy Enforcements

1. **No Silent Bypasses**:
   - `SKIP_STRICT_QC` is completely banned from all production, CI, and test execution paths.
   - `continue-on-error: true` is strictly prohibited on all critical gates.
   - Shell pipeline swallows (`|| true`) are forbidden on quality, test, and security steps.

2. **Coverage Guard**:
   - Baseline coverage is locked at >= 48% across `api` and `scripts/core`.
   - Any regression below this threshold immediately fails the `python-tests` check.

3. **Hermetic Docker Guarantees**:
   - The Docker build context respects `.dockerignore`, excluding host `node_modules` and local artifacts.
   - Package installations run deterministically via `npm ci` inside the container.
   - Non-root user (`renderer`: UID 1000) executes the Remotion rendering process.

4. **Security Severity Policy**:
   - `CRITICAL` and `HIGH` severity vulnerabilities or findings fail the build immediately (`exit 1`).
   - Audit and scan reports are archived as job artifacts for inspection.
