# S28-R15 Evidence: Final Architecture Re-Audit

**Milestone**: S28-R15 Verification, Fault Destruction, Fencing, Load & Soak  
**Date**: October 7, 2026  

---

## 1. Authority Matrix (Section 37)

| Entity / Concern | Single Authority | Readers | Writers | Persistent Location | Transaction Boundary | Tenant Boundary | Failure Behavior |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Canonical VideoDocument** | `CanonicalDocumentRepository` | Preview, Planner, Editor | `AuthoringService` | PostgreSQL (`canonical_documents`) + StorageService | Transactional SQL (`WHERE rev = ?`) | `workspace_id`, `project_id` | `REVISION_CONFLICT` |
| **Revision / CAS** | PostgreSQL (`revision` column) | API, Workers, Editor | Repository CAS update | PostgreSQL table row | Atomic SQL UPDATE | Tenant row isolation | Fail-closed rollback |
| **Authoring Mutation** | `UnifiedAuthoringSession` | UI, Subprocess Bridge | User, AI, Template | Temporary session + DB | Atomic per request | Inherits request tenant | Rejection with `validation.ok: false` |
| **Undo / Redo History** | `UnifiedAuthoringSession` | Editor UI | Editor actions | In-memory session history | Client session | In-process session boundary | No-op on empty stack |
| **TemplateSpec** | `SemanticTemplateRegistry` | Instantiator, Planner | Template authors | Registry files (`registry/`) | Immutable catalog | Global / shared specs | `UnknownTemplateError` |
| **Preview / Proxy Cache** | `ProductionPreviewCoordinator` | Browser Live Preview | Proxy Renderer | StorageService (`previews/`) | Content hash CAS | `workspace_id`, `project_id` | Eviction / re-render on miss |
| **Renderer Registry** | `RendererRegistry` | RenderPlanner, Executor | System startup | In-memory registry | Application lifecycle | Process-wide | `RENDERER_UNAVAILABLE` |
| **RenderPlanner** | `RenderPlanner` | Production Executor | None (pure planner) | Deterministic output | Stateless function | Document tenant | `RenderPlanningError` |
| **RenderGraph Execution** | `ProductionRenderGraphExecutor`| Event listeners | Worker processes | Ephemeral sandboxes | Per-node timeout/cancel | Run workspace isolation | Fail-closed node stop |
| **MasterCompositor** | `MasterCompositor` | Executor, QC | Compositor Worker | StorageService (`renders/`) | FFmpeg execution lock | Job output prefix | `MasterCompositorError` |
| **Runs / Jobs** | `runs` table | API, Workers, UI | API (create), Worker (update)| PostgreSQL (`runs`) | Transactional SQL | `workspace_id`, `project_id` | Stale worker fenced |
| **Leases / Fencing** | `project_execution_leases` | Worker pool | Active worker heartbeats | PostgreSQL table | Atomic lease renewal | Run scope | Lease expiry & recovery |
| **Run Events** | `run_events` table | UI SSE / WebSocket | Executor / Workers | PostgreSQL (`run_events`) | Append-only sequence | `workspace_id`, `project_id` | Sequence preserved |
| **Artifact Metadata** | `project_artifact_versions` | API, Compositor | Worker | PostgreSQL table | Transactional insert | `workspace_id`, `project_id` | Discarded on failure |
| **Artifact Bytes** | `StorageService` | Workers, Compositor | Workers, Adapters | Storage Backend (S3 / Local) | Object-level atomic put | Key prefix enforcement | `StorageSecurityError` |
| **Final QC** | `runQcForCompositorResult` / `final_qc.py` | Release pipeline | QC Subsystem | QC JSON report | Gate check execution | Project scope | `VIDEO_FAILED_QC` |
| **Tenant Identity** | `TenantContext` | All API endpoints | Auth / Session Middleware | JWT / Request Context | Per HTTP request | Enforced at service entry | `401 / 403 Forbidden` |
| **Authorization / RBAC** | `Principal` & `Role` | Service methods | Security Policy | Database (`roles`, `permissions`)| Context evaluation | Workspace RBAC | `UNAUTHORIZED / FORBIDDEN` |
| **Budget Enforcement** | `BudgetService` | RenderPlanner, Executor | Billing subsystem | Database (`tenant_quotas`) | Atomic balance check | `tenant_id` quota | `BUDGET_EXCEEDED` fail-closed |
| **Usage Metering** | `usage_events` table | Billing aggregator | Worker, API | PostgreSQL (`usage_events`) | Append-only transaction | `tenant_id`, `workspace_id` | Guaranteed commit |

---

## 2. Forbidden Dependency Search (Section 38)

A comprehensive codebase audit was executed to detect forbidden architectural couplings:

| Forbidden Pattern Inspected | Search Scope | Matches Found | Classification | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **Remotion imports outside allowed adapters** | `contracts/`, `api/`, `planner/`, `compositor/` | 0 | SAFE | **CLEAN** |
| **React / TSX types inside Canonical Document** | `contracts/canonical-video.ts`, `contracts/blueprint.ts` | 0 | SAFE | **CLEAN** |
| **FFmpeg commands emitted by AI** | `ai/`, `scripts/generators/` | 0 | SAFE | **CLEAN** |
| **AI selecting concrete renderer** | `api/services/authoring_service.py`, `authoring/` | 0 | SAFE | **CLEAN** |
| **CreativePlan containing renderer code** | `ai/planning/` | 0 | SAFE | **CLEAN** |
| **TemplateSpec directly requiring Remotion** | `contracts/template-spec.ts` | 0 | SAFE | **CLEAN** |
| **API router direct DB mutation** | `api/routers/authoring.py` | 0 (Delegates to `AuthoringService` CAS) | SAFE | **CLEAN** |
| **Renderer direct canonical DB mutation** | `contracts/renderer.ts`, `canvas/`, `remotion/` | 0 | SAFE | **CLEAN** |
| **Renderer arbitrary filesystem writes** | `planner/production-render-graph-executor.ts` | 0 (Strict temp sandboxing only) | SAFE | **CLEAN** |
| **StorageService bypass** | `planner/`, `compositor/`, `preview/` | 0 (All persistent outputs use StorageService) | SAFE | **CLEAN** |
| **Cross-tenant object keys** | `contracts/storage-service.ts`, `scripts/core/storage/` | 0 (Enforced by `validateStorageKey`) | SAFE | **CLEAN** |
| **Quarantined `Video_Editor_MCP` imports** | Entire repository | 0 active imports | SAFE | **CLEAN** |

---

## 3. Final Renderer-Independence Audit (Section 39)

### Proof Criteria:
1. **CreativePlan has no renderer dependency**: Validated. Schema relies strictly on semantic scene objectives.
2. **Canonical VideoDocument has no Remotion/React/TSX types**: Validated via static AST architecture guards ([`R15-AG-01`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/tests/architecture/test_s28_r15_architecture_guards.test.ts#L30)).
3. **Engine-neutral templates do not depend on Remotion**: Validated. Templates compile into abstract `CanonicalLayer[]`.
4. **AI authoring cannot emit renderer implementation code**: Validated. Mutations are constrained to declarative `AuthoringIntent` unions (`UPDATE_TEXT`, `MOVE_LAYER`, etc.).
5. **AI does not choose renderer**: Validated. Capability-based resolution is owned exclusively by `RenderPlanner`.
6. **RenderPlanner owns capability matching**: Validated across all test DAG creations.
7. **MasterCompositor is renderer-independent**: Validated. Operates purely on media files and canonical timeline math.

### Real Remotion-Disabled Verification:
- Backend starts without Remotion dependencies: **PASS**
- Canonical document opens: **PASS**
- Human and AI authoring mutations function: **PASS**
- Engine-neutral templates instantiate: **PASS**
- Undo / redo history operates: **PASS**
- Live preview core functions: **PASS**
- Non-Remotion standalone export completes (Canvas/FFmpeg): **PASS**
- Remotion-only capability requests fail explicitly (`RENDERER_CAPABILITY_MISMATCH`): **PASS**
- Whole system remains stable and never crashes: **PASS**
