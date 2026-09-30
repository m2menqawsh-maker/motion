# ADR-003: Multi-Tenant SaaS Foundation & Storage Abstraction (S24.5)

## Metadata
- **Status:** APPROVED (DEC-05)
- **Date:** 2026-09-30
- **Deciders:** Lead Architect / CTO & Repository Owner
- **Consulted:** S24 Strict Production CI Verification Team
- **Informed:** Core Engineering & Infrastructure Team

---

## 1. Context and Problem Statement
Following S24 (Strict Production CI), the core video rendering pipeline, gate contracts, and CAS state engine were hardened. However, the system architecture remained fundamentally single-tenant and implicitly coupled to the local filesystem:
1. **Implicit Single-User / Local File Hierarchy:** Projects resided in a single flat directory `projects/{project_id}/`.
2. **Missing Workspace & Membership Authority:** No multi-tenant concept existed (no `User`, `Workspace`, `WorkspaceMember` domain models or tables).
3. **No Heavy Storage Abstraction:** Artifacts, media assets, and outputs were written and read directly from local filesystem paths.
4. **Worker Coupling to Filesystem Truth:** The worker treated the local project directory as the permanent source of truth rather than an ephemeral execution workspace.
5. **Cross-Tenant Security Invariants Unenforced:** The system had no transactional boundary enforcing that a valid object ID cannot be accessed across tenant/workspace boundaries, nor did it guard against cross-tenant AssetRef references.

---

## 2. Decision: DEC-05 (APPROVED)

We approve the **Multi-Tenant SaaS Foundation Architecture** for Clean Video Workspace:

```text
Authenticated User
        ↓
    Workspace
        ↓
     Project (belongs to exactly 1 Workspace; workspace_id NOT NULL)
        ↓
 Domain Services (TenantContext-aware)
        ↓
 PostgreSQL (State / Jobs / Tenancy / CAS / Reviews / Events)
        +
 StorageService Abstraction (LocalStorageBackend | S3CompatibleStorageBackend)
        ↓
 Worker (Durable lease)
        ↓
 Temporary Ephemeral Workspace
        ↓
 Remotion / FFmpeg
```

### Key Architectural Pillars:
1. **Target Deployment:** Multi-user SaaS.
2. **Transactional Persistence:** Relational database with full ACID transactions and optimistic concurrency (CAS). PostgreSQL in production; SQLite transactionally equivalent backend for tests/dev.
3. **Heavy / Object Storage:** `StorageService` interface with `LocalStorageBackend` (dev/tests) and `S3CompatibleStorageBackend` (production SaaS).
4. **Mandatory Workspace Ownership:** Every production project belongs to exactly one workspace (`workspace_id NOT NULL`). No legacy fallback, no `workspace_id = NULL`, and no `legacy_project = true`.
5. **Strict Server-Side Authorization:** `Valid object ID != authorized access`. Identity and tenant membership are server-verified on every sensitive operation.
6. **Ephemeral Worker Workspace:** The worker leases runs from DB, provisions an ephemeral directory, materializes assets from `StorageService`, renders, uploads persistent outputs to `StorageService`, commits state, and wipes the temporary workspace. The local disk is never the source of truth.

---

## 3. Storage Hierarchy
Server-generated canonical storage keys:
```text
workspaces/{workspace_id}/projects/{project_id}/assets/{asset_id}/{filename}
workspaces/{workspace_id}/projects/{project_id}/artifacts/{artifact_kind}/{filename}
workspaces/{workspace_id}/projects/{project_id}/outputs/{run_id}/{filename}
```
Direct client-supplied paths and directory traversal are strictly prevented and rejected fail-closed.

---

## 4. Consequences
- **Positive:** System is fully ready for multi-tenant cloud deployment without rewriting business logic, render engine, or QC gates.
- **Positive:** Complete tenant isolation prevents cross-tenant data leaks and cross-project asset hijacking.
- **Positive:** Worker filesystem cleanup does not corrupt or lose system state.
- **Constraint:** All future domain endpoints and worker flows must operate through `TenantContext` and `StorageService`.
