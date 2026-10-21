# Dataflow, Persistence & Artifact Lineage Reality Report
- **Baseline Git SHA**: `90ec3de8d47494d5940d5cd1f9ed9a8e274ef6e1`
- **Branch**: `main`
- **Report Version**: 1.0.0
- **Last Updated**: 2026-10-07
- **Scope**: End-to-end dataflow, SQLite & PostgreSQL relational schemas, CAS concurrency locks, worker leases, StorageService object structure, and full artifact lineage lifecycle.
- **Evidence Standard**: `CODE_PROVEN`, `TEST_PROVEN`, `CI_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`, `DOCUMENTATION_ONLY`, `INFERRED`, `UNKNOWN`

---

## 1. Executive Summary

The persistence and dataflow architecture of the repository spans a hybrid topology combining **relational metadata stores** (SQLite/PostgreSQL), **on-disk JSON state machines** (`.pipeline_state.json`), and **pluggable object storage** (`StorageService` backed by local disk or S3/MinIO):

1. **Dual Authority State Dualism**: Projects maintain state simultaneously in `.pipeline_state.json` on disk and in the relational database table `project_states`. Synchronization is mediated by `StateStore._sync_to_db()`, with file-level cross-process locking backed by `fcntl`.
2. **Three-Tier CAS Concurrency**: Concurrency is guarded at three distinct layers:
   - **HTTP Level**: Conditional mutations enforce `If-Match` ETag headers or `base_revision` matching, rejecting stale mutations with HTTP 409 Conflict.
   - **File Level**: `StateStore.lock()` acquires an exclusive cross-process OS lock on `.pipeline_state.lock` via `fcntl.flock()`.
   - **Database Level**: `project_states` validates `expected_revision == current_revision`, raising `StateConflictError` on divergence.
3. **Worker Lease Fencing**: Asynchronous worker execution is fenced via `project_execution_leases` in SQLite/PostgreSQL, preventing concurrent duplicate pipeline runs and enforcing heartbeat TTLs.
4. **Canonical Object Storage Hierarchy**: Assets, versioned blueprints, rendered MP4s, and QC reports are structured under a strict tenant-isolated key hierarchy: `workspaces/{workspace_id}/projects/{project_id}/{category}/{item_id}/{filename}`.

---

## 2. Relational Database Architecture & Schema DDL

The database subsystem is managed by `DatabaseEngine` in `scripts/core/database.py:54-265`. It supports SQLite (default: `data/runs.db`, `data/motion.db`) and PostgreSQL via connection string URI (`DATABASE_URL`).

### 2.1 Complete Relational Table Schemas

```sql
-- 1. Schema Migrations Ledger
CREATE TABLE IF NOT EXISTS _schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);

-- 2. User Identity
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL
);

-- 3. Tenant Workspace
CREATE TABLE IF NOT EXISTS workspaces (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (created_by) REFERENCES users(id)
);

-- 4. Workspace Membership & RBAC
CREATE TABLE IF NOT EXISTS workspace_members (
    workspace_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL, -- 'admin', 'editor', 'reviewer', 'viewer'
    created_at TEXT NOT NULL,
    PRIMARY KEY (workspace_id, user_id),
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 5. Project Metadata
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    created_by TEXT NOT NULL,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id)
);
CREATE INDEX IF NOT EXISTS idx_projects_workspace ON projects(workspace_id);

-- 6. Project State & CAS Revision Store
CREATE TABLE IF NOT EXISTS project_states (
    project_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    lifecycle_state TEXT NOT NULL,
    state_json TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_project_states_workspace ON project_states(workspace_id);

-- 7. Artifact Version Ledger
CREATE TABLE IF NOT EXISTS project_artifact_versions (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    artifact_kind TEXT NOT NULL,
    revision INTEGER NOT NULL,
    content_hash TEXT NOT NULL,
    storage_key TEXT NOT NULL,
    created_by TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_artifact_versions_lookup ON project_artifact_versions(workspace_id, project_id, artifact_kind);

-- 8. Execution Runs Ledger
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    status TEXT NOT NULL, -- 'QUEUED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'CANCELLED'
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    attempt INTEGER NOT NULL DEFAULT 1,
    worker_id TEXT,
    lease_expires_at TEXT,
    input_revision INTEGER,
    idempotency_key TEXT,
    request_payload_hash TEXT,
    failure_code TEXT,
    failure_detail TEXT,
    result_reference TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_runs_tenant_project ON runs(workspace_id, project_id);
CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
CREATE INDEX IF NOT EXISTS idx_runs_idempotency ON runs(workspace_id, project_id, idempotency_key);

-- 9. Atomic Worker Execution Leases
CREATE TABLE IF NOT EXISTS project_execution_leases (
    project_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    worker_id TEXT NOT NULL,
    acquired_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    heartbeat_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
);

-- 10. Durable Run Events (SSE & Audit)
CREATE TABLE IF NOT EXISTS run_events (
    event_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    sequence INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    stage TEXT,
    timestamp TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    UNIQUE (run_id, sequence),
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_run_events_tenant ON run_events(workspace_id, project_id, run_id);

-- 11. Studio Review Bundles
CREATE TABLE IF NOT EXISTS review_bundles (
    bundle_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    hashes_json TEXT NOT NULL,
    status TEXT NOT NULL, -- 'PENDING', 'APPROVED', 'REJECTED'
    created_at TEXT NOT NULL,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_review_bundles_proj ON review_bundles(workspace_id, project_id);

-- 12. Review Decisions Ledger
CREATE TABLE IF NOT EXISTS review_decisions (
    decision_id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    bundle_id TEXT NOT NULL,
    actor_user_id TEXT NOT NULL,
    decision TEXT NOT NULL, -- 'APPROVED', 'REJECTED'
    revision INTEGER NOT NULL,
    decided_at TEXT NOT NULL,
    reason TEXT,
    FOREIGN KEY (bundle_id) REFERENCES review_bundles(bundle_id) ON DELETE CASCADE,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_review_decisions_proj ON review_decisions(workspace_id, project_id);

-- 13. Metering & Usage Events
CREATE TABLE IF NOT EXISTS usage_events (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    project_id TEXT,
    user_id TEXT,
    event_type TEXT NOT NULL,
    quantity REAL NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_usage_events_ws ON usage_events(workspace_id, created_at);

-- 14. Canonical Assets Ledger
CREATE TABLE IF NOT EXISTS canonical_assets (
    id TEXT PRIMARY KEY,
    asset_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    storage_key TEXT NOT NULL,
    media_type TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    provenance_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    UNIQUE (project_id, content_hash)
);
CREATE INDEX IF NOT EXISTS idx_canonical_assets_lookup ON canonical_assets(project_id, content_hash);

-- 15. Tool Idempotency Records
CREATE TABLE IF NOT EXISTS tool_idempotency_records (
    idempotency_key TEXT PRIMARY KEY,
    payload_hash TEXT NOT NULL,
    status TEXT NOT NULL,
    result_json TEXT,
    error_json TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    lease_expires_at TEXT
);

-- 16. Authoring Mutation Idempotency Records
CREATE TABLE IF NOT EXISTS authoring_idempotency_records (
    workspace_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    operation_id TEXT NOT NULL,
    operation_type TEXT NOT NULL,
    base_revision INTEGER NOT NULL,
    payload_hash TEXT NOT NULL,
    status TEXT NOT NULL,
    result_revision INTEGER,
    result_json TEXT,
    error_json TEXT,
    lease_expires_at TEXT,
    created_at TEXT NOT NULL,
    PRIMARY KEY (workspace_id, project_id, operation_id)
);
```

---

## 3. Concurrency Control, Lease Management & Compare-And-Swap (CAS) Protocols

### 3.1 Four-Tier Concurrency Architecture

```
Layer 1 (HTTP Client):       If-Match: "rev_3" (ETag) / base_revision: 3
                                 │
                                 ▼ (FastAPI Router)
Layer 2 (File Lock):         fcntl.flock(project_dir / ".pipeline_state.lock", LOCK_EX)
                                 │
                                 ▼ (StateStore.atomic_update)
Layer 3 (Relational CAS):    UPDATE project_states SET revision=4 WHERE project_id=? AND revision=3
                                 │
                                 ▼ (Worker Process)
Layer 4 (Execution Lease):   INSERT INTO project_execution_leases ... ON CONFLICT DO NOTHING
```

### 3.2 Detailed Mechanics by Layer

1. **HTTP Conditional Header CAS (`api/routers/authoring.py:65-72`)**:
   - Client sends `If-Match: "<revision>"` or payload `base_revision`.
   - `AuthoringService` fetches current revision from `CanonicalDocumentRepository`.
   - If `current_revision != base_revision`, rejects immediately with `HTTP 409 Conflict` and error code `REVISION_CONFLICT`.

2. **File-Level Cross-Process Lock (`scripts/core/state_store.py:75-80`)**:
   - `StateLock` opens `.pipeline_state.lock` in the project directory using `os.O_RDWR | os.O_CREAT`.
   - Acquires exclusive OS lock via `fcntl.flock(fd, fcntl.LOCK_EX)`.
   - While holding the lock, authoritatively re-reads `.pipeline_state.json`.
   - Asserts `actual_revision == expected_revision`. If mismatched, raises `StateConflictError` with zero disk mutations.

3. **Database-Level Atomic CAS (`scripts/core/state_store.py:203-217`)**:
   - Within an atomic database transaction:
     `SELECT revision FROM project_states WHERE project_id = ?`
   - If `expected_revision is not None and curr_rev != expected_revision`: raises `StateConflictError`.
   - Increments revision and writes state JSON atomically.

4. **Worker Lease Fencing (`scripts/core/worker.py:180-220`)**:
   - Multiple background worker processes compete for jobs.
   - `RunRepository.claim_next_run(worker_id, lease_duration)` executes an atomic update query claiming the oldest `QUEUED` run and setting `lease_expires_at = now + 60s`.
   - Simultaneously writes to `project_execution_leases`. If another worker holds an active lease for the same `project_id`, lease acquisition fails, preventing concurrent execution on the same project workspace.
   - Active worker maintains a background heartbeat thread (`_start_heartbeat`) updating `heartbeat_at` every 15 seconds.

---

## 4. StorageService Architecture & Object Hierarchy

The object storage abstraction is implemented in `scripts/core/storage/storage_service.py:110-463`.

### 4.1 Storage Backends

1. **`LocalStorageBackend`**:
   - Filesystem-backed storage rooted at `settings.storage_local_root` (default: `data/storage/`).
   - Enforces strict path traversal prevention via `validate_storage_key()`. Rejects `..`, leading slashes, and characters outside `[a-zA-Z0-9_\-\./]`.
2. **`S3CompatibleStorageBackend`**:
   - Boto3-backed driver for AWS S3, Cloudflare R2, or MinIO.
   - Generates presigned download/upload URLs (`generate_presigned_url`).

### 4.2 Canonical Key Layout

All objects stored in `StorageService` adhere to the canonical hierarchical key schema:
```
workspaces/{workspace_id}/projects/{project_id}/{category}/{item_id}/{filename}
```

| Category | Typical Sub-Path | Contents | Producer | Consumer |
|---|---|---|---|---|
| `assets` | `assets/{asset_id}/{filename}` | Ingested images, videos, audio | `AssetService.upload_asset()` | Subprocess renderer, materializer |
| `blueprints` | `blueprints/rev_{revision}/05_blueprint.json` | Versioned canonical VideoDocument | `CanonicalDocumentRepository` | Authoring API, renderer |
| `outputs` | `outputs/{output_id}/out.mp4` | Final rendered video media | `PipelineWorker._upload_outputs` | `OutputService` streaming API |
| `qc` | `qc/probe/{filename}`, `qc/final/{filename}` | Contact sheets, QC reports | `probe_qc.py`, `final_qc.py` | `ReviewService`, Studio |
| `candidates` | `candidates/{candidate_id}/{filename}` | Promoted template packages | `CandidateService` | `TemplateRegistryPublisher` |

---

## 5. End-to-End Artifact Lineage Matrix

The end-to-end dataflow spans 10 canonical artifacts produced and consumed throughout the video lifecycle:

| # | Artifact Name | Path on Disk | Canonical Storage Key | Authoritative Producer | Gate / Validator | Primary Consumers | Invalidation Rule |
|---|---|---|---|---|---|---|---|
| 1 | **Asset Manifest** | `02_asset_manifest.json` | `workspaces/{ws}/projects/{prj}/manifests/02_asset_manifest.json` | `AssetService.upload_asset()` | `scripts/gates/asset_gate.py` | `materialize_project.py`, `authoring/` | Invalided on asset deletion or re-upload. |
| 2 | **Master Plan** | `master_plan.md` | N/A (Local project disk) | Planner / Authoring | `scripts/gates/plan_gate.py`, `taste_gate.py` | `scripts/pipeline.py` | Invalidated on scene structure edit. |
| 3 | **Timings Specification**| `04_timings.json` | N/A (Local project disk) | Speech STT / Timing alignment | `scripts/gates/plan_gate.py` | `validate_blueprint.py` | Invalidated on audio replacement. |
| 4 | **Canonical VideoDocument** | `05_blueprint.json` | `workspaces/{ws}/projects/{prj}/blueprints/rev_{rev}/05_blueprint.json` | `AuthoringService` / `UnifiedAuthoringSession` | `validate_blueprint.py`, `motion_validator.py`, `code_template_gate.py` | `materialize_project.py`, `render_project.py` | Increments revision; invalidates probe QC and review bundles. |
| 5 | **Render Input Props** | `06_rendered_props.json` | N/A (Materialized scratch) | `materialize_project.py` | `scripts/core/render_input.py` | `render_project.py`, `remotion-app/src/index.ts` | Regenerated on every materialization pass. |
| 6 | **Probe QC Report** | `07_probe_qc_report.json` | `workspaces/{ws}/projects/{prj}/qc/probe/report.json` | `scripts/gates/probe_qc.py` | `probe_qc.py` | `ReviewService.create_review_bundle()` | Invalidated whenever blueprint or assets mutate. |
| 7 | **Review Bundle** | Stored in SQLite `review_bundles` | N/A (Relational DB entity) | `ReviewService.create_review_bundle()` | `ReviewService.assert_render_authorized()` | `ReviewService.approve()`, `scripts/pipeline.py` | Invalidated on state rollback. |
| 8 | **Rendered Video** | `out.mp4` | `workspaces/{ws}/projects/{prj}/outputs/{out_id}/out.mp4` | `scripts/render_project.py` | `scripts/gates/final_qc.py` | `OutputService`, `PipelineWorker` | Overwritten on re-render. |
| 9 | **Final QC Report** | `09_final_qc_report.json` | `workspaces/{ws}/projects/{prj}/qc/final/report.json` | `scripts/gates/final_qc.py` | `scripts/gates/final_qc.py` | `scripts/pipeline.py` | Generated after render completes. |
| 10 | **Pipeline State File** | `.pipeline_state.json` | Reflected in DB `project_states` | `LifecycleService`, `StateStore` | `StateStore.load()`, `RecoveryEngine` | `scripts/pipeline.py`, API | Authoritative local lifecycle truth. |

---

## 6. Invalidation Cascades, Revisions & Disaster Recovery

### 6.1 Downstream Invalidation Cascade

When an upstream artifact is modified, `LifecycleService` and `StateStore` enforce deterministic invalidation cascades:

```
[Asset Upload / Mutation]
          │
          ▼
Invalidates: 02_asset_manifest.json (Recomputes SHA-256)
          │
          ▼
Invalidates: 05_blueprint.json (Requires re-materialization)
          │
          ▼
Invalidates: 07_probe_qc_report.json (Removes .studio_unlocked)
          │
          ▼
Invalidates: ReviewBundle (Closes active review, sets status=EXPIRED)
          │
          ▼
Invalidates: out.mp4 (Deletes stale render outputs)
          │
          ▼
State Machine: Resets lifecycle_state to ASSETS_READY
```

### 6.2 Disaster Recovery & Reconciliation (`scripts/core/recovery_engine.py`)

If a pipeline run crashes mid-execution (SIGKILL, worker crash, or host reboot):
1. **Lease Expiration**: The worker heartbeat ceases. After `lease_expires_at` (TTL 60s), other workers or the API consider the lease expired.
2. **`RecoveryEngine.evaluate(project_dir)`**: When `scripts/pipeline.py` restarts:
   - Scans disk artifacts and recomputes SHA-256 hashes.
   - Compares disk hashes with `artifact_records` recorded in `.pipeline_state.json`.
   - If an artifact was partially written or corrupted during a crash, `RecoveryEngine` restores the previous consistent state or rolls back the lifecycle stage to the last validated checkpoint.
   - Deletes abandoned `.tmp` files (`out.attempt-*.tmp.mp4`, `.pipeline_state.json.tmp`).

---

## 7. Verification Methods and Reproducible Commands

To independently reproduce and verify the findings in this report:

1. **Verify Database Schema Tables**:
   ```bash
   python -c "
   from scripts.core.database import get_database_engine, SCHEMA_SQL
   import sqlite3
   conn = sqlite3.connect(':memory:')
   conn.executescript(SCHEMA_SQL)
   tables = [r[0] for r in conn.execute(\"SELECT name FROM sqlite_master WHERE type='table'\").fetchall()]
   print('Verified tables count:', len(tables))
   print('Tables:', sorted(tables))
   "
   # Verifies all 16 tables instantiate without syntax error.
   ```

2. **Verify CAS File Locking Mechanics**:
   ```bash
   # Inspect StateStore.lock and atomic_update:
   sed -n '74,80p' scripts/core/state_store.py
   sed -n '225,245p' scripts/core/state_store.py
   ```

3. **Verify StorageService Key Format**:
   ```bash
   # Inspect build_storage_key implementation:
   grep -n "def build_storage_key" scripts/core/storage/storage_service.py
   sed -n '95,110p' scripts/core/storage/storage_service.py
   ```

4. **Verify Downstream Invalidation in AssetService**:
   ```bash
   # Inspect invalidation cascade on asset upload:
   grep -n "def _invalidate_downstream" api/services/asset_service.py
   ```
