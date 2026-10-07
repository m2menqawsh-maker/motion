# S28-R: Renderer Independence & Live Editor Core — Final Architecture

**Milestone Series**: S28-R (R01 through R15)  
**Status**: COMPLETE  
**Canonical Authority**: `BlueprintV2` (`contracts/blueprint.ts`, `contracts/canonical-video.ts`)  

---

## 1. End-to-End System Topology

```text
                 Creative Intelligence
                         │
                         ▼
                    CreativePlan
                         │
                         ▼
             Canonical VideoDocument
                 persistent truth
                         │
             ┌───────────┴───────────┐
             │                       │
             ▼                       ▼
      Unified Authoring         Live Preview
      Human / AI / Template     + Proxy System
             │
        CanonicalMutation
             │
      revision/CAS/history
             │
             └────────────┐
                          ▼
                    RenderPlanner
                          │
                      RenderGraph
               ┌──────────┼──────────┐
               ▼          ▼          ▼
             Native    Remotion     Other
             Adapter    Adapter     Adapter
               └──────────┼──────────┘
                          ▼
                  MasterCompositor
                          │
                          ▼
                       Final QC
                          │
                          ▼
                    StorageService
```

---

## 2. Distributed Production Subsystems

Across the entire lifecycle, seven strict systemic disciplines are enforced:

### 1. Persistence & Concurrency
- **Single Source of Truth**: `BlueprintV2` stored in PostgreSQL `canonical_documents` table.
- **Transactional CAS**: All document updates execute atomic SQL (`WHERE project_id = ? AND revision = ?`).
- **Durable Idempotency**: Atomic leader claim stored in `authoring_idempotency_records` table, surviving process crashes.

### 2. Tenant Isolation & Security
- **RBAC & TenantContext**: Every API router and domain service requires explicit `TenantContext` verification.
- **Storage Boundary**: All persistent artifact writes pass through `StorageService` with strict key validation (`validateStorageKey`) preventing path traversal (`../`, null bytes).

### 3. Execution Sandboxing & Fencing
- **Sandboxed Workspaces**: Every render node executes in an isolated temporary directory with guaranteed `finally` cleanup.
- **Generational Fencing**: Expired worker leases can never commit authoritative run results or artifacts; recovered workers advance the attempt epoch and fence stale workers.

### 4. Engine-Neutral Planning
- **Zero Renderer Branching**: Neither AI nor authors choose renderers. `RenderPlanner` derives required capabilities and queries `RendererRegistry`.
- **Topological DAG**: `RenderPlanner` builds dependency edges and calculates parallelizable `RenderExecutionGroup[]`.

### 5. Multi-Engine Normalization
- **MasterCompositor**: Decouples scene rendering from final assembly. Automatically normalizes resolution, framerate, pixel format, and resamples all audio tracks to 48kHz.
- **Provenance Tracking**: Every output artifact carries complete `ArtifactProvenance` tracing back to run, project, revision, and node fingerprints.

### 6. Failure Semantics & Resilience
- **Structured Error Taxonomy**: Failures map to canonical codes: `RENDERER_TIMEOUT`, `RENDERER_UNAVAILABLE`, `RENDERER_EXECUTION_FAILED`, `RENDERER_OUTPUT_INVALID`, `RENDERER_CANCELLED`, `RENDERER_CAPABILITY_MISMATCH`, `STORAGE_UNAVAILABLE`.
- **Immediate Cancellation**: `AbortSignal` propagates instantly across execution groups and halts worker subprocesses.

### 7. Governance, Metering & Quality
- **Budget Gating**: `BudgetService` evaluates quota limits pre-execution and fails closed with `BUDGET_EXCEEDED` before incurring compute costs.
- **Quality Control Gate**: `runQcForCompositorResult` inspects output with ffprobe, enforcing duration parity (< 150ms drift), video compliance, and audio compliance.
