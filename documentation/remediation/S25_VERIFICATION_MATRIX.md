# S25 Verification Matrix — Fault Injection & Architecture Re-Audit

**Sprint:** S25 — Fault Injection + Final Architecture Re-Audit  
**Baseline Commit SHA:** `0d4550c76a649317a6376485fc1c8a18d9443608`  
**Target Branch:** `remediation/s24.5-multi-tenant-saas`  
**Execution Standard:** Live Behavior & Executable Evidence (Zero Mocks for Critical Paths)  
**Status:** Completed & Verified (56/56 FI Tests Passed, 517/517 Total Tests Passed, Coverage: 79.74%)

---

## 1. Complete Scenario Verification Matrix

| Scenario ID | Domain | Historical Finding IDs Affected | Preconditions | Injection | Expected Invariant | Actual Result | Evidence | Classification | Fix Required? | Regression Test | CI Result | Status | Ledger Rows Updated |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **FI-01** | State / Concurrency | STATE-001, CONC-001, STATE-002, LED-006, LED-013 | Project at revision R; DatabaseEngine active | DB outage simulated during atomic_update / transition transaction | No partial state; revision strictly monotonic; no lost updates; retry safe; machine-readable failure | PASSED | `tests/fault_injection/test_fi_01_db_outage_transition.py` | RESOLVED | None | 3 tests passing | PASSED | GREEN | Rows 1, 3, 7 |
| **FI-02** | Worker / Fencing | LED-059, LED-061, REC-001, LED-012 | Run claimed by Worker 1; active lease | DB outage drops heartbeat; lease expires; Worker 2 claims run; Worker 1 attempts to publish/finish | Mutual exclusion; stale Worker 1 fenced from publishing or finishing run after lease loss | PASSED (After S25-NEW-003 fix) | `tests/fault_injection/test_fi_02_lease_fencing.py` | RESOLVED | Yes (`run_repository.py` & `worker.py`) | 2 tests passing | PASSED | GREEN | Rows 4, 12, 59, 61 |
| **FI-03** | Worker / Lifecycle | REC-001, LED-012, LED-059, LED-061, LED-091 | Worker process executing pipeline | `SIGKILL` sent to worker at claim, execution, upload, and pre-commit | Ephemeral workspace cleaned/abandoned; lease expires; orphan recovery kicks in; no false SUCCEEDED; artifacts matched to DB | PASSED | `tests/fault_injection/test_fi_03_worker_hard_death.py` | RESOLVED | None | 3 tests passing | PASSED | GREEN | Rows 4, 12, 59, 91 |
| **FI-04** | API / Durability | LED-059, LED-061, LED-070 | Run initiated via API; worker executing | Process termination / restart sent to API server process mid-job | Worker continues unaffected; API restarts cleanly; run state & events fully readable; zero state corruption | PASSED | `tests/fault_injection/test_fi_04_api_hard_death.py` | RESOLVED | None | 1 test passing | PASSED | GREEN | Rows 59, 61, 70 |
| **FI-05** | Storage / Persistence | ASSET-003, ASSET-010, LED-063, LED-065, LED-091 | StorageService active (Local & S3) | Storage backend raises StorageError on put, get, metadata, delete | DB does not mark output usable before storage success; readiness fails-closed (503); retry idempotent | PASSED | `tests/fault_injection/test_fi_05_storage_outage.py` | RESOLVED | None | 3 tests passing | PASSED | GREEN | Rows 28, 29, 63, 65, 91 |
| **FI-06** | Storage / Upload | LED-065, LED-068, LED-091 | Output render complete; upload initiated | Upload fails mid-stream (partial bytes or network reset) | Partial object rejected; run does not reach SUCCEEDED; size/hash mismatch detected; retry clean | PASSED | `tests/fault_injection/test_fi_06_partial_upload.py` | RESOLVED | None | 2 tests passing | PASSED | GREEN | Rows 65, 68, 91 |
| **FI-07** | State / Storage Recon | REC-001, LED-005, LED-088, LED-091 | Disagreement injected between DB & Storage | Case A: DB has record, Storage missing; Case B: Storage has file, DB missing; Case C: Hash mismatch; Case D: Run COMPLETE, artifact missing | Delivery rejects missing/corrupted objects; DB is metadata authority, Storage is payload authority; reconciliation recovers state | PASSED | `tests/fault_injection/test_fi_07_db_storage_disagreement.py` | RESOLVED | None | 4 tests passing | PASSED | GREEN | Rows 4, 5, 88, 91 |
| **FI-08** | CAS / Concurrency | CONC-001, STATE-002, LED-068 | Multi-process writers starting at revision R | 2 distinct OS processes simultaneously execute `update_state_cas(R)` | Exactly 1 process succeeds (R -> R+1); second receives 409 conflict; 0 lost updates; monotonic revision | PASSED | `tests/fault_injection/test_fi_08_multiprocess_cas.py` | RESOLVED | None | 1 test passing | PASSED | GREEN | Rows 3, 7, 68 |
| **FI-09** | Idempotency | LED-059, LED-061 | Run submitted with idempotency_key | Duplicate requests sent concurrently and sequentially after crash | Same run returned; no duplicate execution; no extra worker spawned; conflicting payload returns 409 | PASSED (After S25-NEW-004 fix) | `tests/fault_injection/test_fi_09_idempotency.py` | RESOLVED | Yes (`RunCreateRequest` extra allow) | 4 tests passing | PASSED | GREEN | Rows 59, 61 |
| **FI-10** | Tenant Isolation | LED-016, LED-018, ASSET-009, LED-063, LED-064, LED-065 | Workspace A & Workspace B provisioned | User B attempts direct access to Project A, Assets, Runs, Outputs, Artifacts, Events | Fail-closed HTTP 403/404; zero metadata or byte leakage across workspaces | PASSED (After S25-NEW-001 fix) | `tests/fault_injection/test_fi_10_cross_tenant_access.py` | RESOLVED | Yes (`permissions.py`) | 6 tests passing | PASSED | GREEN | Rows 2, 16, 18, 63, 64, 65 |
| **FI-11** | Indirect Reference | ASSET-009, ASSET-001, ASSET-005, LED-024 | Project A in Workspace A | Manifest/Blueprint references AssetRef from Workspace B | Domain layer & AssetResolver reject reference; worker halts before execution; fail-closed | PASSED | `tests/fault_injection/test_fi_11_cross_tenant_indirect_ref.py` | RESOLVED | None | 4 tests passing | PASSED | GREEN | Rows 2, 23, 24, 31 |
| **FI-12** | RBAC Matrix | LED-016, LED-017, LED-018, LED-020 | Roles: Viewer, Editor, Reviewer, Admin | Sensitive ops: read, edit, upload, run, cancel, approve, reject, download | Server-side enforcement matches matrix; client claims ignored; reviewers cannot edit, viewers cannot trigger | PASSED | `tests/fault_injection/test_fi_12_rbac_matrix.py` | RESOLVED | None | 4 tests passing | PASSED | GREEN | Rows 16, 17, 18, 20 |
| **FI-13** | Context Spoofing | LED-016, LED-017 | Authenticated session | Client sends spoofed X-Workspace-ID, X-User-ID, X-Role, or body overrides | Server derives context strictly from validated DB membership; spoofed claims rejected with 403 | PASSED (After S25-NEW-002 fix) | `tests/fault_injection/test_fi_13_tenant_spoofing.py` | RESOLVED | Yes (`auth.py`) | 4 tests passing | PASSED | GREEN | Rows 16, 17 |
| **FI-14** | Workspace Cleanup | LED-091, LED-059 | Completed successful run | Ephemeral workspace directory completely deleted from host disk | Output & artifacts streamable from StorageService; DB state intact; host disk not source of truth | PASSED | `tests/fault_injection/test_fi_14_ephemeral_cleanup.py` | RESOLVED | None | 2 tests passing | PASSED | GREEN | Rows 59, 91 |
| **FI-15** | Ephemeral Loss Mid-Job | REC-001, LED-012, LED-091 | Pipeline actively executing | Ephemeral directory deleted or corrupted mid-pipeline | Pipeline fails cleanly; run marked FAILED; no partial output published; recovery engine resets safely | PASSED | `tests/fault_injection/test_fi_15_ephemeral_loss.py` | RESOLVED | None | 2 tests passing | PASSED | GREEN | Rows 4, 12, 91 |
| **FI-16** | Zero Migration Rebuild | LED-088, LED-089 | Empty database instance | Execute schema migrations from scratch on fresh DB | Tables, FKs, CASCADE, unique constraints created cleanly; idempotent rerun; FK enforces workspace_id | PASSED | `tests/fault_injection/test_fi_16_migration_rebuild.py` | RESOLVED | None | 2 tests passing | PASSED | GREEN | Rows 88, 89 |
| **FI-17** | Readiness Truthfulness | LED-073 | API running with dependencies | Simulate outage in DB, StorageService, or Worker | `/health/ready` returns 503; `/health/live` returns 200; readiness never masks critical dependency failure | PASSED | `tests/fault_injection/test_fi_17_readiness_truthfulness.py` | RESOLVED | None | 4 tests passing | PASSED | GREEN | Row 73 |
| **FI-18** | Event Stream Reconnect | LED-060 | Active run emitting events | Client disconnects; API restarts; reconnect with cursor `after_sequence=N` | No lost events; no duplicate replay beyond cursor; strictly monotonic sequence ordering | PASSED | `tests/fault_injection/test_fi_18_event_stream_reconnect.py` | RESOLVED | None | 2 tests passing | PASSED | GREEN | Row 60 |
| **FI-19** | Cancellation Subprocess | LED-062 | Worker executing long render/probe | `POST /runs/{id}/cancel` sent; worker handles cancellation | Process group killed cleanly (SIGTERM -> SIGKILL); no orphan background processes; final status CANCELLED | PASSED | `tests/fault_injection/test_fi_19_cancellation_execution.py` | RESOLVED | None | 2 tests passing | PASSED | GREEN | Row 62 |
| **FI-20** | E2E Destructive SaaS | LED-088, LED-089, LED-091, LED-092 | SaaS tenancy setup | Complete lifecycle journey with destructive failure injected mid-way, recovery, and completion | System recovers from mid-flight crash; completes review approval, render, QC; outputs verified in Storage | PASSED | `tests/fault_injection/test_fi_20_e2e_destructive.py` | RESOLVED | None | 1 test passing | PASSED | GREEN | Rows 88, 89, 91, 92 |

---

## 2. New Vulnerabilities Discovered & Remediated in S25

1. **`S25-NEW-001` (P0 - Security Isolation Bypass):**
   - *Description:* In `scripts/core/security/permissions.py:AuthorizationPolicy.is_authorized`, `if principal.is_admin: return True` evaluated prior to project-to-workspace scope checks. This allowed an admin in Workspace B to access projects in Workspace A.
   - *Fix:* Reordered check so project workspace membership is strictly enforced before granting administrative privileges.
   - *Regression Test:* `tests/fault_injection/test_fi_10_cross_tenant_access.py`

2. **`S25-NEW-002` (P0 - Identity Context Spoofing):**
   - *Description:* In `api/core/auth.py:require_tenant_context`, when an unauthorized workspace header was sent and no membership existed, the function defaulted to `effective_role = Role.VIEWER` and permitted access.
   - *Fix:* Added strict fail-closed check raising `AccessDeniedError` if `membership is None`.
   - *Regression Test:* `tests/fault_injection/test_fi_13_tenant_spoofing.py`

3. **`S25-NEW-003` (P0 - Worker Fencing / Split-Brain Overwrite):**
   - *Description:* In `scripts/core/run_repository.py:finish_run`, SQL UPDATE did not verify that caller worker matched current `worker_id` or that status was still active. A stale worker waking up after lease expiration could overwrite a newly reclaimed run.
   - *Fix:* Enforced worker ID fencing in `finish_run`, added `is_lease_active()` method, and verified active lease before storage upload in `worker.py`.
   - *Regression Test:* `tests/fault_injection/test_fi_02_lease_fencing.py`

4. **`S25-NEW-004` (P1 - Idempotency Payload Hash Bypass):**
   - *Description:* In `api/schemas/run.py:RunCreateRequest`, extra request fields (such as `parameters` or `config`) were discarded by default Pydantic `extra='ignore'`, resulting in identical empty hashes for different payloads with the same idempotency key.
   - *Fix:* Added `model_config = {"extra": "allow"}` to `RunCreateRequest`.
   - *Regression Test:* `tests/fault_injection/test_fi_09_idempotency.py`
