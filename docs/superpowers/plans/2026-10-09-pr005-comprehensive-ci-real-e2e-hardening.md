# PR-005 Comprehensive CI & Real E2E Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Establish tiered, affordable, truthful CI pipelines and harden runtime crash recovery and Run-to-Blueprint revision domain provenance without regressions.

**Architecture:** 
1. Separate fast PR gating (lint, security, architecture, API, unit/integration, and fault-injection suites) from slow, scheduled/manual real E2E rendering (15-second multi-scene AI -> Canonical -> Worker -> QC -> MP4 pipeline).
2. Harden POSIX child-process crash recovery across state sync, blueprint review invalidation, and worker lease fencing using real `subprocess.Popen` with `SIGKILL`/`os._exit` and sentinel barriers.
3. Decouple and durably bind the immutable tuple `{workspace_id, project_id, canonical_document_revision, canonical_blueprint_sha256, immutable_storage_key, approved_review_bundle_id, lifecycle_state_revision}` in `RunRecord` with schema migrations, ensuring runs cannot be retargeted by subsequent blueprint mutations or missing/tampered storage bytes.

**Tech Stack:** Python 3.12+, FastAPI, SQLite (WAL mode) / PostgreSQL, Pydantic, pytest, Remotion, FFmpeg/ffprobe, GitHub Actions.

**Spec:** `/home/eng_Momen/Downloads/wallpapers/PR_005_COMPREHENSIVE_CI_REAL_E2E_HARDENING_AGENT_PROMPT.txt`

## Global Constraints

- Preserve working AI -> reviewed canonical Blueprint -> PipelineWorker -> real MP4 path proven in PR-003.
- Subprocesses must never receive database or auth secrets by ambient propagation; maintain strict subprocess security boundaries.
- No bypassing of human review or taste gates; `.studio_approved` and `.studio_unlocked` must not be invented or forged.
- No live external AI/cloud tokens, paid third-party APIs, or uncontrolled network access required for CI.
- No git push, remote modification, or merge to main; all work on dedicated local branch `remediation/pr-005-comprehensive-ci-real-e2e-hardening`.
- Minimal blast radius: zero unnecessary refactors or speculative abstractions.

## Review Focus

1. **Child Process Deadlock/Hang:** Child process in hard-death test fails to exit or sentinel wait blocks indefinitely; ensure strict bounded timeouts with guaranteed SIGKILL cleanup in `finally` blocks.
2. **Global Mutable State in Test Harness:** Singleton `_CONTRACT_INSTANCE` or DB engines polluted across tests; ensure `conftest.py` teardown flushes caches.
3. **Database Migration Safety:** Adding columns to `runs` table must be backward-compatible with default NULL and handle SQLite/Postgres without breaking existing rows.
4. **Idempotency vs Payload Digest:** `request_payload_hash` must remain the idempotency request payload digest while the immutable blueprint tuple is tracked in distinct fields.
5. **Worker TOCTOU / Stale Blueprint Race:** Worker materializing or rendering must verify pinned blueprint bytes against `canonical_blueprint_sha256` and reject mutated disks/stale approvals.

---

### Task 1: Fix Test Harness Singleton Isolation & Fixture Teardown

**Files:**
- Modify: `tests/conftest.py:95-105`
- Modify: `tests/api/test_candidate_promotions_router.py:280-285`
- Test: `tests/architecture/test_s15_architecture_guard.py`

**Interfaces:**
- Consumes: `scripts.core.template_contract.invalidate_template_contract_cache()`
- Produces: Clean, unpolluted template contract singleton state between test runs.

- [ ] **Step 1: Write failing verification test**
Run `pytest tests/api/test_candidate_promotions_router.py tests/architecture/test_s15_architecture_guard.py -k test_guard_template_contract_is_the_python_authority` and observe failure due to leaked singleton state (106 != 105).

- [ ] **Step 2: Add cache invalidation on fixture teardown**
Update `tests/api/test_candidate_promotions_router.py` fixture `api_promotion_env` and `tests/conftest.py` fixture `setup_test_env` to invoke `invalidate_template_contract_cache()` on teardown.

- [ ] **Step 3: Run test to verify it passes**
Run: `.venv/bin/pytest tests/api/test_candidate_promotions_router.py tests/architecture/test_s15_architecture_guard.py -v`
Expected: 100% PASS with 0 failures.

---

### Task 2: Real POSIX Separate-Process Hard-Death and Durable Recovery Tests

**Files:**
- Create: `tests/integration/test_pr005_process_hard_death_recovery.py`
- Test: `tests/integration/test_pr005_process_hard_death_recovery.py`

**Interfaces:**
- Consumes: `scripts.core.state_store.StateStore`, `scripts.core.canonical_document_repository.CanonicalDocumentRepository`, `scripts.core.review_service.ReviewService`, `scripts.core.run_repository.RunRepository`, `scripts.core.worker.PipelineWorker`
- Produces: Automated verification of real OS process death (PID, SIGKILL / os._exit, post-restart recovery) across 3 critical crash windows without mocks.

- [ ] **Step 1: Write child process crash harness and tests**
Create `tests/integration/test_pr005_process_hard_death_recovery.py` with 3 test functions:
  1. `test_real_process_death_statestore_fs_vs_sql_recovery()`: StateStore writes `.pipeline_state.json`, child process terminates via `os._exit` or `SIGKILL` at a barrier before SQL sync. Fresh process reloads and asserts safe healing to authoritative SQL state.
  2. `test_real_process_death_blueprint_commit_vs_review_invalidation()`: Canonical Blueprint committed to DB, child killed before review invalidation finishes. Fresh process reloads and asserts stale approval is rejected fail-closed.
  3. `test_real_process_death_worker_lease_fencing_and_orphan_recovery()`: Worker process claims Run and receives `SIGKILL`. Fresh worker recovers orphan run and successfully processes it, while a zombie worker attempting to finish after lease expiry is fenced.

- [ ] **Step 2: Run test suite to verify execution and POSIX process isolation**
Run: `.venv/bin/pytest tests/integration/test_pr005_process_hard_death_recovery.py -v -s`
Expected: 3 passed with verified child PIDs and exit codes.

---

### Task 3: Decouple Revision Domains & Bind Immutable Blueprint Provenance to RunRecord

**Files:**
- Modify: `scripts/core/run_model.py:30-55`
- Modify: `api/schemas/run.py:20-50`
- Modify: `scripts/core/run_repository.py:80-140, 190-250`
- Modify: `scripts/core/database.py:120-150, 360-390`
- Modify: `api/services/run_service.py:70-120`
- Modify: `scripts/core/worker.py:230-310`
- Create: `tests/integration/test_pr005_run_blueprint_provenance.py`

**Interfaces:**
- Consumes: `RunRecord`, `CanonicalDocumentRepository`, `project_artifact_versions`, `StorageService`
- Produces: Persisted immutable provenance tuple on `RunRecord`:
  `{workspace_id, project_id, canonical_document_revision, canonical_blueprint_sha256, immutable_storage_key, approved_review_bundle_id, lifecycle_state_revision}`
  and fail-closed enforcement at claim/worker boundary if storage bytes are tampered/missing or if approval is stale.

- [ ] **Step 1: Write failing provenance and revision isolation tests**
Create `tests/integration/test_pr005_run_blueprint_provenance.py` testing:
  - Separate revision domains: lifecycle state revision vs blueprint revision vs run attempt.
  - RunRecord durably pins the immutable tuple.
  - New blueprint committed after Run enqueue does not silently retarget the Run (fails closed).
  - Missing/tampered storage bytes for pinned blueprint fails closed.
  - Stale/invalidated review approval fails closed.
  - Cross-tenant storage key rejected.
  - Idempotency replay returns existing run; conflicting payload returns 409.

- [ ] **Step 2: Update RunRecord, Schema, RunRepository migration v4, and database.py**
Add the new fields to `RunRecord` and `RunResponse`. Add migration v4 in `RunRepository` and safe alter table in `DatabaseEngine._init_schema`.

- [ ] **Step 3: Update RunService.create_run to pin authoritative blueprint tuple**
In `RunService.create_run`, look up canonical blueprint from `project_artifact_versions` and active review bundle from `StateStore`, pinning the immutable tuple onto `RunRecord`.

- [ ] **Step 4: Update PipelineWorker to verify pinned provenance fail-closed**
In `PipelineWorker.process_one`, before invoking rendering, verify:
  - If `run.canonical_blueprint_sha256` is set, verify tenant storage key, retrieve bytes from `StorageService`, assert SHA-256 match.
  - Assert project review approval matches `run.canonical_blueprint_sha256`.
  - Assert disk `05_blueprint.json` matches pinned SHA-256 (fail closed if disk was mutated).

- [ ] **Step 5: Run tests to verify they pass**
Run: `.venv/bin/pytest tests/integration/test_pr005_run_blueprint_provenance.py -v`
Expected: 100% PASS.

---

### Task 4: Upgrade GitHub Actions Workflows (Tiered CI: Fast PR vs Real E2E)

**Files:**
- Modify: `.github/workflows/remediation-ci.yml`
- Create: `.github/workflows/real-e2e-nightly.yml`
- Validate: actionlint or YAML syntax / security checks

**Interfaces:**
- Consumes: GitHub Actions runner, ubuntu-latest, Node 20, Python 3.12, FFmpeg
- Produces: 
  - `remediation-ci.yml`: Fast required PR checks (python lint, contracts-ts, ground-truth, security-and-contracts, python-fast-tests, security-audit, docker-render). Concurrency cancel-in-progress on PR only; permissions contents: read; no `@master` unpinned actions; scoped artifact uploads.
  - `real-e2e-nightly.yml`: Scheduled (cron) and manual (`workflow_dispatch`) real 15-second E2E video rendering with deterministic fixtures, ffprobe inspection, and full multi-scene verification.

- [ ] **Step 1: Upgrade `.github/workflows/remediation-ci.yml`**
Refactor `remediation-ci.yml`:
  - Add top-level `permissions: contents: read`.
  - Set `cancel-in-progress: ${{ github.event_name == 'pull_request' }}`.
  - Expand test matrix in fast CI to include `tests/security/`, `tests/architecture/`, `tests/contracts/`, `tests/gates/`, `tests/generators/`, `tests/validators/`, `tests/api/`, `tests/fault_injection/`, `tests/core/`, and new PR-004/PR-005 integration suites.
  - Pin `aquasecurity/trivy-action` to a released stable version (e.g. `v0.28.0`).
  - Scope failure artifact uploads to exclude sensitive files or arbitrary project directories.

- [ ] **Step 2: Create `.github/workflows/real-e2e-nightly.yml`**
Create companion workflow for nightly and manual E2E execution:
  - Triggers: `workflow_dispatch`, `schedule: [{cron: "0 2 * * *"}]`.
  - Runs full 15-second AI -> review -> worker -> Multi-Engine planner -> QC -> MP4 pipeline.
  - Enforces strict ffprobe duration, resolution, audio channels, and active render path.

- [ ] **Step 3: Validate workflow YAML syntax and structure**
Verify workflow file structure and syntax using python yaml parser.

---

### Task 5: Execute Local Real E2E and Capture Machine-Auditable Verification Evidence

**Files:**
- Execute: `tests/integration/test_pr003_provenance_verification.py`
- Create: `docs/CI_RELEASE_GATES.md`
- Record: Full test run outputs, ffprobe measurements, active render path receipt, git status/diff.

- [ ] **Step 1: Execute Real E2E test locally**
Run: `.venv/bin/pytest tests/integration/test_pr003_provenance_verification.py -v -s`
Record MP4 duration, stream specs, review bundle hash, and active render path receipt.

- [ ] **Step 2: Run complete fast PR suite locally**
Run the fast suite covering security, architecture, core, API, fault injection, and new integration tests. Record pass counts and execution time.

- [ ] **Step 3: Author `docs/CI_RELEASE_GATES.md`**
Document local execution commands, fast vs nightly tiers, secrets policy, troubleshooting, and residual risks.

- [ ] **Step 4: Check git status and diff**
Run `git diff --check` and `git status --short`. Ensure no stray files or untracked changes other than the planned additions.

- [ ] **Step 5: Local git commit**
Create a clean local commit on `remediation/pr-005-comprehensive-ci-real-e2e-hardening`. Do not push or merge.
