# S26 Required Status Checks Matrix — Clean Video Workspace

**Sprint:** S26 — Final Governance Closure  
**Date:** September 30, 2026  
**Target Branch:** `main`  
**Repository:** `m2menqawsh-maker/motion`  
**Workflow File:** `.github/workflows/remediation-ci.yml`  
**Ruleset ID:** `24256136` (`main-governance-closure`)  
**Classic Protection:** Active with `enforce_admins: true`  

---

## 1. Executive Summary

Prior to Sprint S26, the repository had continuous integration active in GitHub Actions, but lacked server-side enforcement on `main`. Branch protection contexts had drifted (`["vitest", "static-analysis", "python-tests"]`), which did not match the actual job definitions in `.github/workflows/remediation-ci.yml`.

As part of Phase S26, the CI pipeline was modernized, stabilized, and verified across all jobs. Seven production checks were determined to be essential for system integrity, contract validity, security, and hermetic rendering. All seven checks were made strictly **Required** under GitHub Repository Ruleset `24256136` and synchronized with classic branch protection.

---

## 2. Canonical Status Checks Matrix

| Check Name (GitHub Context) | Workflow Name | Job Identifier | Required? | Architectural Rationale for Requirement | Stability Assessment | CI Verification Run | Typical Runtime |
|---|---|---|:---:|---|:---:|:---:|:---:|
| **`python-quality`** | Remediation Fortress CI | `python-quality` | **YES** | Enforces static code quality, zero undefined variables, deterministic formatting via `ruff`, and prevents syntax errors in `api/` and `scripts/core/`. | **STABLE** (100%) | [Run 36739689585](https://github.com/m2menqawsh-maker/motion/actions/runs/36739689585) | ~14s |
| **`contracts-ts`** | Remediation Fortress CI | `contracts-ts` | **YES** | Verifies TypeScript compilation (`tsc --noEmit`), ESLint compliance, and Vitest suite ensuring cross-language JSON schema parity between Python and Remotion runtime. | **STABLE** (100%) | [Run 36739689585](https://github.com/m2menqawsh-maker/motion/actions/runs/36739689585) | ~44s |
| **`ground-truth`** | Remediation Fortress CI | `ground-truth` | **YES** | Validates synchronization between codebase reality and architectural ground truth metadata (`scripts/validators/check_ground_truth_sync.py`), and enforces dependency lockfile integrity (`check_dependencies_lock.py`). | **STABLE** (100%) | [Run 36739689585](https://github.com/m2menqawsh-maker/motion/actions/runs/36739689585) | ~23s |
| **`python-tests`** | Remediation Fortress CI | `python-tests` | **YES** | Runs 517 unit, gate, generator, validator, contract, architecture, and fault-injection (`FI-01` to `FI-20`) tests with coverage enforcement (`--cov-fail-under=48`, actual: 79.74%). | **STABLE** (100%) | [Run 36739689585](https://github.com/m2menqawsh-maker/motion/actions/runs/36739689585) | ~52s |
| **`strict-e2e`** | Remediation Fortress CI | `strict-e2e` | **YES** | Executes the True E2E Matrix Suite across 9:16, 16:9, and 1:1 aspect ratios, multi-template families, and real Remotion rendering without bypassing strict QC gates (`SKIP_STRICT_QC=0`). | **STABLE** (100%) | [Run 36739689585](https://github.com/m2menqawsh-maker/motion/actions/runs/36739689585) | ~1m 35s |
| **`docker-render`** | Remediation Fortress CI | `docker-render` | **YES** | Builds hermetic Docker container (`.agents/docker/Dockerfile.remotion`), executes headless Remotion within the container, and verifies subcommand security policy to prevent escapes. | **STABLE** (100%) | [Run 36739689585](https://github.com/m2menqawsh-maker/motion/actions/runs/36739689585) | ~1m 24s |
| **`security-audit`** | Remediation Fortress CI | `security-audit` | **YES** | Performs multi-layered static and dynamic security scanning: Python `pip-audit`, Node `npm audit` (high/critical), `bandit` static analysis, secret scanning, and Trivy container vulnerability scan. | **STABLE** (100%) | [Run 36739689585](https://github.com/m2menqawsh-maker/motion/actions/runs/36739689585) | ~42s |

---

## 3. Discarded / Non-Required Candidates Audit

To prevent CI deadlock and avoid enforcing development-only or non-deterministic jobs, candidate checks were evaluated against strict inclusion criteria:

1. **Ad-hoc / Scratch Workflows:** Any experimental workflows outside `remediation-ci.yml` were excluded from mandatory checks.
2. **Matrix Combinations:** Only the canonical Linux execution matrix (`ubuntu-latest`) was declared required; no unverified secondary runner OS environments are enforced.
3. **No Phantom Checks:** Every single check declared in Ruleset `24256136` matches a real, executing job in `.github/workflows/remediation-ci.yml`.

---

## 4. Enforcement Configuration

```json
{
  "ruleset_id": 24256136,
  "name": "main-governance-closure",
  "target": "refs/heads/main",
  "enforcement": "active",
  "current_user_can_bypass": "never",
  "rules": {
    "deletion": true,
    "non_fast_forward": true,
    "pull_request": {
      "required_approving_review_count": 0,
      "dismiss_stale_reviews_on_push": false,
      "require_code_owner_review": false,
      "require_last_push_approval": false,
      "required_review_thread_resolution": false
    },
    "required_status_checks": {
      "strict_required_status_checks_policy": true,
      "required_status_checks": [
        {"context": "python-quality"},
        {"context": "contracts-ts"},
        {"context": "ground-truth"},
        {"context": "python-tests"},
        {"context": "strict-e2e"},
        {"context": "docker-render"},
        {"context": "security-audit"}
      ]
    }
  }
}
```
