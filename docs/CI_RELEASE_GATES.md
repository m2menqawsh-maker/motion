# CI Release Gates & Architecture Enforcement Guide (PR-005)

## 1. Architectural Mission & Tiered CI Strategy

The PR-005 hardening initiative establishes an adversarial, continuously executable, and truth-preserving CI pipeline that guarantees the invariants established across PR-001 through PR-004 without incurring exorbitant compute costs or generating flaky failures.

### The Two CI Tiers:

```
+---------------------------------------------------------------------------------------+
|                                    TIER 1: FAST PR CHECKS                            |
| Triggers: push to remediation/*, feature/*; pull_request to main, feature/*           |
| Duration: ~1–3 minutes                                                               |
| Scope:                                                                                |
|  - Python Lint (ruff) & Ground Truth / Dependency lock sync                           |
|  - TypeScript Contracts & Vitest suite                                                |
|  - Security Regression Suite (PR-001, PR-002, PR-003, PR-004 auth/isolation/subproc)    |
|  - Architecture Guards (Layer isolation, engine neutrality, CAS, DB boundaries)      |
|  - API Router Endpoints & Permissions                                                 |
|  - POSIX Hard-Death & Post-Restart Recovery Tests (SIGKILL child processes)           |
|  - Run-to-Blueprint Provenance & Decoupling Tests                                     |
|  - Fault Injection & Deterministic Pipeline Smoke                                     |
|  - Hermetic Docker Subcommand Validation                                              |
|  - Static Security Audits (pip-audit, npm audit, Bandit, Secret Scanner, Trivy)       |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
|                                TIER 2: NIGHTLY REAL E2E RENDER                        |
| Triggers: Scheduled cron (0 2 * * * - 02:00 UTC) + workflow_dispatch (manual)         |
| Duration: ~5–10 minutes                                                               |
| Scope:                                                                                |
|  - Full AI CreativePlan/Proposal generation                                           |
|  - Canonical Blueprint persistence in SQL & StorageService                            |
|  - Explicit Human Review Bundle generation and approval gate                         |
|  - Real Worker process claiming and executing canonical pipeline                      |
|  - Remotion Chromium Headless frame rendering                                         |
|  - FFmpeg multi-stream muxing to MP4 (15-second duration, 3 scenes, 30 fps, 1080p)     |
|  - Strict QC probe inspection (black/freeze detection, audio LUFS, visual fidelity)  |
+---------------------------------------------------------------------------------------+
```

---

## 2. Release Gates Matrix (G01 – G16)

| Gate ID | Gate Name | Scope & Requirement | Verification Command / Target | Status |
|---|---|---|---|---|
| **G01** | Ancestry & Tree Integrity | Strict base on PR-004 `2950ba8ade704d6b05f60963a250ce524ea4178a`. Clean branch, zero user work lost. | `git merge-base --is-ancestor 2950ba8 HEAD` | **PASS** |
| **G02** | Workflow Inventory | Existing `.github/workflows/remediation-ci.yml` retained, audited, and enhanced without dropping guards. | `diff` inspection against baseline | **PASS** |
| **G03** | Fast PR Scope | Comprehensive coverage of security, architecture, contracts, API, and core suites. | `pytest tests/core tests/gates tests/generators tests/validators tests/architecture tests/contracts tests/fault_injection tests/security tests/api tests/integration` | **PASS** |
| **G04** | Workflow Security | Top-level `permissions: contents: read`, PR-only cancellation, pinned actions (`trivy-action@v0.28.0`). | Inspect `.github/workflows/*.yml` | **PASS** |
| **G05** | Deterministic Tooling | Python 3.12/3.14, Node 20+, FFmpeg 8+ compatibility, lockfile conformance. | `scripts/validators/check_dependencies_lock.py --check` | **PASS** |
| **G06** | Ephemeral State Hygiene | Isolated temp directories per test run; no shared tmp state or cache collisions. | `tests/conftest.py`, `tests/integration/` fixtures | **PASS** |
| **G07** | POSIX Hard-Death Recovery | Real OS child-process kill (`subprocess.Popen` + `SIGKILL`) across 3 crash windows. | `pytest tests/integration/test_pr005_process_hard_death_recovery.py -v` | **PASS** |
| **G08** | Revision Domain Decoupling | Decouple lifecycle revision, document revision, run attempt, and idempotency request hash. | `scripts/core/run_model.py`, `api/schemas/run.py` | **PASS** |
| **G09** | Run-to-Blueprint Pinning | Immutable binding tuple persisted in `RunRecord` with schema migrations. | `scripts/core/run_repository.py` (v4 migration) | **PASS** |
| **G10** | Retarget & Tamper Prevention | Worker materializes pinned storage bytes, rejects tampered bytes, foreign tenants, and stale approvals. | `pytest tests/integration/test_pr005_run_blueprint_provenance.py -v` | **PASS** |
| **G11** | Lease Fencing & Idempotency | Stale workers cannot publish outputs; duplicate idempotent requests yield 1 run and 1 event. | `tests/core/test_worker_ephemeral_workspace.py`, `tests/integration/test_pr005_run_blueprint_provenance.py` | **PASS** |
| **G12** | Real E2E Render Path | AI -> Canonical -> Review -> Worker -> Remotion/FFmpeg -> MP4 (15s, 3-scene, 1080p, 30fps). | `pytest tests/integration/test_pr003_provenance_verification.py -v -s` | **PASS** |
| **G13** | Regression Guard Integrity | No skipped assertions, silenced exceptions, or weakened thresholds (coverage >= 48%). | Terminal execution with real stdout | **PASS** |
| **G14** | Artifact & Secret Sanitization | Scoped failure artifact uploads (`projects/**/final_qc_report.json`), zero ambient secret leakage. | `scripts/validators/check_secrets.py`, CI upload configs | **PASS** |
| **G15** | Red -> Green Evidence | Concrete before/after regression proof on template cache pollution, hard-death split-brain, and provenance retargeting. | Documented test execution traces | **PASS** |
| **G16** | Local Commit & Safety | Verified with `git diff --check` and `git status --short`; clean local commit; NO remote push/merge. | Local commit on branch | **PASS** |

---

## 3. Provenance Architecture: Decoupling Revision Domains

A critical flaw in legacy video pipelines is overloading a single revision counter or assuming that a mutable disk file (`projects/{id}/05_blueprint.json`) represents the authoritative state for a queued run.

### Revision Domain Decoupling:

1. **Lifecycle State Revision (`ProjectState.revision`):**
   - Counter tracking transitions through the production lifecycle (`DRAFT -> PLAN_READY -> BLUEPRINT_READY -> AWAITING_REVIEW -> REVIEW_APPROVED -> COMPLETE`).
   - Guarded by atomic Check-and-Swap (CAS) in SQL and disk `StateStore`.

2. **Canonical Document Revision (`project_artifact_versions.revision`):**
   - Monotonically increasing revision of the authoritative `BlueprintV2` document.
   - Pinned immutable storage object in `StorageService` referenced by SHA-256 content hash.

3. **Run Execution Attempt (`RunRecord.attempt`):**
   - Execution counter incremented by worker lease recovery when a worker dies.
   - Independent of document revision or lifecycle state.

4. **Idempotency Request Payload Hash (`RunRecord.request_payload_hash`):**
   - SHA-256 digest of the client's HTTP request body for API idempotency.

### Pinned Run Provenance Tuple:

Every `RunRecord` in `runs` (SQL Schema v4) durably binds:
```json
{
  "workspace_id": "ws_12345678",
  "project_id": "proj_abcdefgh",
  "canonical_document_revision": 3,
  "canonical_blueprint_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "immutable_storage_key": "workspaces/ws_12345678/projects/proj_abcdefgh/blueprints/rev_3_e3b0c442.json",
  "approved_review_bundle_id": "rbd_fedcba98",
  "lifecycle_state_revision": 5
}
```

### Worker Enforcement Protocol:
When a worker claims a run:
1. **Tenant Confinement:** Verifies that `immutable_storage_key` has prefix `workspaces/{run.workspace_id}/`.
2. **Byte Integrity:** Reads `immutable_storage_key` from `StorageService`, hashes bytes with SHA-256, and verifies exact match with `canonical_blueprint_sha256`. Fails closed if missing (`STORAGE_OBJECT_MISSING`) or tampered (`STORAGE_OBJECT_CORRUPTED`).
3. **Anti-Retargeting Materialization:** Overwrites disk `projects/{project_id}/05_blueprint.json` with the pinned bytes. If a concurrent actor or later request created revision 4, this run executes revision 3 without silent retargeting.
4. **Active Review Verification:** Verifies `approved_review_bundle_id` exists in project state, has `status == "ACTIVE"`, references the matching blueprint SHA-256, and is accompanied by an `APPROVED` decision. Fails closed with `RENDER_NOT_AUTHORIZED` or `STALE_REVIEW_APPROVAL` otherwise.

---

## 4. POSIX Hard-Death & Post-Restart Recovery Testing

Implemented in `tests/integration/test_pr005_process_hard_death_recovery.py`:
- **Unmocked OS Process Isolation:** Uses `subprocess.Popen(start_new_session=True)` to execute distinct child Python processes.
- **Deterministic Signal Barriers:** Child synchronization via file barriers followed by immediate `os.kill(child.pid, signal.SIGKILL)`.
- **Three Critical Crash Windows:**
  1. `StateStore` disk write succeeds, child killed before SQL commit -> fresh process resolves split-brain to SQL authoritative truth (rev 2) and heals disk.
  2. Blueprint revision 3 committed, child killed before review invalidation -> fresh process fails closed with `RenderNotAuthorizedError` and invalidates stale review bundle.
  3. Worker holding lease killed with SIGKILL -> stale worker resurrection fails lease check; fresh worker orphan recovery transitions run to attempt 2 and finishes cleanly.

---

## 5. Local Execution Commands

### Fast PR Suite:
```bash
.venv/bin/pytest --cov=api --cov=scripts/core --cov-report=term --cov-fail-under=48 \
  tests/core tests/gates tests/generators tests/validators tests/architecture \
  tests/contracts tests/fault_injection tests/security tests/api \
  tests/integration/test_pr003_ai_runtime_vertical_slice.py \
  tests/integration/test_pr004_state_consistency.py \
  tests/integration/test_pr005_process_hard_death_recovery.py \
  tests/integration/test_pr005_run_blueprint_provenance.py \
  tests/e2e/test_pipeline_integration.py
```

### Process Hard-Death Recovery:
```bash
.venv/bin/pytest tests/integration/test_pr005_process_hard_death_recovery.py -v
```

### Run-to-Blueprint Provenance & Decoupling:
```bash
.venv/bin/pytest tests/integration/test_pr005_run_blueprint_provenance.py -v
```

### Nightly Real E2E Render Suite:
```bash
.venv/bin/pytest tests/integration/test_pr003_provenance_verification.py -v -s
python tests/e2e/true_e2e_suite.py
```

---

## 6. Residual Risk Assessment

| Risk ID | Severity | Category | Description | Mitigation / Residual Boundary |
|---|---|---|---|---|
| **R01** | **P1** | Concurrency / Storage | S3/MinIO eventual consistency latency during immediate read-after-write on very high-throughput clusters. | Mitigation: `StorageService` supports read-after-write verification; SQLite/local storage driver is strongly consistent. |
| **R02** | **P2** | Rendering / Host | Remotion Chromium GPU acceleration variations across headless Linux cloud runners. | Mitigation: Chromium software GL fallback (`--use-gl=angle --use-angle=swiftshader`) configured in `.agents/docker/Dockerfile.remotion`. |
| **R03** | **P2** | Worker / Distributed | Worker lease expiration clock drift across multi-node Kubernetes clusters. | Mitigation: Monotonic epoch UTC timestamps used in leases; database engine serves as central time authority. |
