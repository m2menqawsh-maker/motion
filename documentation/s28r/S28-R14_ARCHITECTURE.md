# S28-R14: Production Integration Architecture

## 1. Overview & Architectural Purpose
Milestone S28-R14 operationalizes the modular video architecture into the multi-tenant SaaS production platform. It wraps and operationalizes the renderer and authoring engines within strict production persistence, tenant isolation, durable idempotency, multi-engine execution, master composition, and storage boundaries without redefining or coupling existing subsystem contracts.

---

## 2. Production Authoring Flow

```text
                  AUTHENTICATED CLIENT
                           │
                           ▼
               Production API Router
             (/projects/{id}/mutate)
                           │
                           ▼
          TenantContext & RBAC Enforcement
         (Workspace, User, Role Validation)
                           │
                           ▼
             Authoring Domain Service
           (api/services/authoring_service.py)
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
   Durable Idempotency         Canonical Base Revision
  (Atomic Leader Claim via     (Database project_states
   authoring_idempotency)       + StorageService Check)
              │                         │
              └────────────┬────────────┘
                           ▼
               Unified Mutation Bridge
         (UnifiedAuthoringSession / Tsx Bridge)
                           │
                           ▼
             Candidate Document Validation
             (validate_blueprint_v2)
                           │
                           ▼
          Transactional CAS Commit to SQL
         (UPDATE project_states WHERE rev = ?)
                           │
                           ▼
          Immutable Artifact Versioning
          (project_artifact_versions + StorageService)
                           │
              ┌────────────┴────────────┐
              ▼                         ▼
         ChangeSet             Durable Audit Events
      Invalidation Plan        (run_events: REVISION_ADVANCED,
     (Preview Coordinator)      AUTHORING_MUTATION_COMMITTED)
```

1. **Client Request**: Client issues a mutation or intent with an `operation_id` and optional `base_revision` (or `If-Match` HTTP ETag).
2. **Tenant & RBAC Verification**: Request headers/tokens resolve into a strict `TenantContext`. Editors/Admins are authorized; cross-tenant operations fail closed with `403 Forbidden` (`TenantSecurityError`).
3. **Durable Idempotency Claim**: Atomic leader claim is executed against `authoring_idempotency_records` in PostgreSQL/SQLite. In-flight requests return `IN_PROGRESS`; completed duplicate operations return the cached result without double mutation.
4. **Optimistic Revision Check**: Canonical revision is verified. If `base_revision != current_revision`, the operation fails closed immediately with `REVISION_CONFLICT` (`409 Conflict`).
5. **Mutation Application**: The domain service invokes the canonical mutation engine (`UnifiedAuthoringSession`), executing validated operations.
6. **Transactional CAS Commit**: `CanonicalDocumentRepository` updates `project_states` using transactional SQL (`UPDATE project_states SET revision = next WHERE id = ? AND revision = expected`).
7. **Artifact Publication**: The immutable candidate document is saved to `StorageService` (`workspaces/{ws}/projects/{prj}/blueprints/rev_{n}_{hash}/blueprint.json`), and recorded in `project_artifact_versions`.
8. **Preview Invalidation & Durable Events**: The computed `ChangeSet` selectively invalidates affected proxy cache keys in `ProductionPreviewCoordinator`, and audit events are durably recorded in `run_events`.

---

## 3. Production Render Flow

```text
                  AUTHENTICATED CLIENT
                           │
                           ▼
                  Production Run API
                           │
                           ▼
                Durable PostgreSQL Run
           (runs table: status = 'QUEUED',
            bound to exact canonical_revision)
                           │
                           ▼
                   Isolated Worker
             (Lease Acquisition & Heartbeat)
                           │
                           ▼
             Exact Source Revision Fetch
           (Immutable Snapshot from StorageService)
                           │
                           ▼
              Engine-Neutral RenderPlanner
          (Capability Resolution & Graph Generation)
                           │
                           ▼
               ProductionRenderGraphExecutor
                           │
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
     Native Adapter  Remotion Adapter Mock Adapter
     (Isolated Temp  (Isolated Temp   (Isolated Temp
       Sandbox)        Sandbox)         Sandbox)
            │              │              │
            └──────────────┼──────────────┘
                           ▼
              Intermediate Node Artifacts
                           │
                           ▼
                   Master Compositor
         (Resolution, FPS, Timebase Normalization)
                           │
                           ▼
                       Final QC
           (Format & Media Probe Verification)
                           │
                           ▼
                    StorageService
        (Permanent publication: outputs/{run_id}/out.mp4)
                           │
                           ▼
              Durable Run Completion & Events
        (runs: status='SUCCESS', run_events: RENDER_SUCCEEDED)
```

1. **Pre-Execution Run Persistence**: The render job is persisted to the database with status `QUEUED` and permanently bound to `input_revision` before execution acknowledgment.
2. **Worker Lease & Sandboxing**: The worker claims the job with a leased heartbeat. A dedicated, ephemeral sandbox directory (`render_sandbox_{ws}_{prj}_{run}`) is allocated on local temporary disk with guaranteed `finally` cleanup.
3. **Immutable Revision Binding**: The worker loads the canonical document strictly at the bound revision. Concurrent edits advancing the project to newer revisions do NOT alter the running job's inputs.
4. **Pre-Execution Budget Check**: `BudgetService` evaluates workspace limits before running expensive nodes. If limits are exceeded, execution halts immediately with `BUDGET_EXCEEDED` before launching renderers.
5. **Multi-Engine Graph Execution**: Nodes are dispatched through the registered adapters (`RendererRegistry`) based on required capabilities. Nodes with missing capabilities fail closed with `RENDERER_CAPABILITY_MISMATCH`.
6. **Master Composition**: Heterogeneous scene outputs from disparate engines (e.g., SVG/shapes, canvas, Remotion) are normalized and spliced by the `MasterCompositor`.
7. **StorageService Publication**: Final output and intermediate artifacts are published through `StorageService` (`IStorageService`). Worker disk is strictly temporary.
8. **Provenance & Audit Records**: Published output records full `ArtifactProvenance` (linking project, canonical revision, run ID, node fingerprints, and engine IDs). Actual usage is recorded in `usage_events`.

---

## 4. Persistence Ownership Table

| Entity | Canonical Persistent Owner | Secondary / Ephemeral Store | Authority Invariants |
| :--- | :--- | :--- | :--- |
| **VideoDocument (Current)** | PostgreSQL `project_states` | StorageService (canonical JSON) | Single truth; updated strictly via SQL CAS (`WHERE revision = ?`). |
| **VideoDocument (Revisions)** | PostgreSQL `project_artifact_versions` | StorageService (`blueprints/rev_{n}/...`) | Immutable historical revisions; write-once, never updated in place. |
| **Authoring Idempotency** | PostgreSQL `authoring_idempotency_records` | Process memory during lease | Atomic leader claim; payload hash verification; survives API restart. |
| **Runs & Jobs** | PostgreSQL `runs` & `project_execution_leases` | Worker process memory | Leased with heartbeats; orphan recovery reconciles dead workers. |
| **Audit Events** | PostgreSQL `run_events` | In-memory log stream / MetricsCollector | Chronological, append-only; replayable progression after client reconnect. |
| **Artifact Metadata** | PostgreSQL `project_artifact_versions` | In-memory `ArtifactProvenance` | Tracks source revision, engine IDs, input fingerprints, and creation time. |
| **Artifact Bytes (Persistent)** | `StorageService` (Local / S3) | N/A | Server-generated tenant-scoped keys; path traversal strictly rejected. |
| **Preview Proxies** | `StorageService` (`proxies/{hash}/...`) | In-memory LRU cache | Stale proxy for older revision cannot overwrite newer revision proxy. |
| **Final Outputs** | `StorageService` (`outputs/{run_id}/out.mp4`) | N/A | Bound to exact source revision; verified via media probe prior to release. |
| **Usage Metering** | PostgreSQL `usage_events` | MetricsCollector snapshot | Tracks resource units (`render_seconds`, `ai_tokens`); used for budget checks. |

---

## 5. Tenant Boundary & Isolation Model

1. **API Perimeter**: Every incoming request must provide authenticated identity mapped to a workspace membership (`TenantContext`). Role-based access control enforces `EDITOR` / `ADMIN` permissions for mutations and renders.
2. **Database Queries**: All SQL operations mandate `workspace_id` in `WHERE` clauses and compound primary keys (`workspace_id`, `project_id`). Cross-tenant lookups return `TenantSecurityError` / `403 Forbidden`.
3. **StorageService Keys**: All storage paths are server-constructed via `buildStorageKey(workspace_id, project_id, category, ...)`. User-controlled path segments with `..`, leading slashes, or cross-tenant workspace prefixes throw `StorageSecurityError`.
4. **Asset References**: Any asset referenced in a document or render graph must be owned by the caller's workspace. Cross-workspace asset resolution fails closed.

---

## 6. Failure Model & Resiliency

| Failure Mode | Failure Code | Retry Disposition | Recovery Responsibility |
| :--- | :--- | :--- | :--- |
| **Revision CAS Conflict** | `REVISION_CONFLICT` | NEVER | Caller receives `409 Conflict`; must fetch latest revision and rebase changes. |
| **Idempotency Hash Conflict** | `IDEMPOTENCY_CONFLICT` | NEVER | Caller reused `operation_id` with different payload; fails closed immediately. |
| **Budget Limit Reached** | `BUDGET_EXCEEDED` | NEVER | Pre-execution check fails closed before expensive compute; caller must adjust quota. |
| **Renderer Timeout** | `RENDERER_TIMEOUT` | CONDITIONALLY_RETRYABLE | Node execution aborted via AbortSignal; sandbox cleaned up; retry with backoff. |
| **Renderer Engine Outage** | `RENDERER_UNAVAILABLE` | NEVER (without fallback) | Isolated from API/editor; returns structured failure without crashing host. |
| **Capability Mismatch** | `RENDERER_CAPABILITY_MISMATCH`| NEVER | Deterministic failure; prevents silent degradation when feature is unsupported. |
| **Storage Service Failure** | `STORAGE_UNAVAILABLE` | CONDITIONALLY_RETRYABLE | Upload/download error wrapped in typed error; temporary artifacts preserved for retry. |
| **User Cancellation** | `RENDERER_CANCELLED` / `RUN_CANCELLED` | NEVER | Cancellation propagates through AbortSignal; halts child processes; frees disk. |
| **Worker Crash / Orphan** | `WORKER_LEASE_LOST` | RETRYABLE | Lease expires in `runs`; recovery worker claims job and resumes execution. |

---

## 7. Remotion Independence Verification
Remotion is strictly an optional rendering adapter within `RendererRegistry`.
- When Remotion is absent, unconfigured, or unavailable:
  - Backend starts and serves documents normally.
  - Human and AI authoring execute without impairment.
  - Template instantiation proceeds identically.
  - Non-Remotion rendering pipelines (e.g. native canvas, mock engines) compile and composite via `MasterCompositor`.
  - Only nodes explicitly requiring Remotion-specific capabilities yield `RENDERER_UNAVAILABLE` or `RENDERER_CAPABILITY_MISMATCH`.
  - The system kernel, authoring core, and API never depend on Remotion.
