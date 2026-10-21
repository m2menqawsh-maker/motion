# Source of Truth and Authority Matrix Reality Report

- **Baseline Git SHA**: `90ec3de8d47494d5940d5cd1f9ed9a8e274ef6e1`
- **Branch**: `main`
- **Report Version**: 1.0.0
- **Last Updated**: 2026-10-07
- **Scope**: Comprehensive audit of canonical authorities, secondary readers, authorized writers, forbidden writers, persistence mechanisms, caches, and competing authorities across all 28 core domain entities.
- **Evidence Standard**: `CODE_PROVEN`, `TEST_PROVEN`, `CI_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`, `DOCUMENTATION_ONLY`, `INFERRED`, `UNKNOWN`

---

## 1. Principles of Authority and Persistence Architecture

The repository enforces three fundamental persistence and authority invariants:
1. **Single Source of Truth Invariant**: Every domain entity has exactly one authoritative owner. When data is replicated for performance (e.g. metadata caches or disk working copies), the canonical authority always wins in conflict resolution.
2. **Optimistic Concurrency Control (CAS Revisioning)**: High-concurrency entities (Projects, VideoDocuments, State, Leases, and Reviews) enforce monotonic integer revisions (`revision: int`). Mutations must supply an `expected_revision`; conflicts immediately raise fatal errors (`RevisionConflictError`, `StateConflictError`).
3. **Multi-Tenant Confinement**: All entity storage keys, SQL rows, and filesystem paths are scoped to `workspace_id`. Cross-tenant traversal is blocked by `validate_project_id`, `resolve_safe_path`, and `TenantSecurityError`.

---

## 2. Comprehensive Domain Entity Authority Matrix (28 Entities)

| # | Domain Entity | Canonical Authority (Class & Table) | Secondary Readers | Authorized Writers | Forbidden Writers | Persistence Mechanism | Caches & Competing Authorities | Evidence Citation |
|---|---|---|---|---|---|---|---|---|
| 1 | **User** | `TenantRepository` (`users` SQL table) | Auth middleware, API routers, Principal | `TenantRepository.create_user()` | AI agents, pipeline gates, CLI scripts | SQLite / PostgreSQL (`users`) | In-memory session cache | `scripts/core/database.py:61` [`CODE_PROVEN`] |
| 2 | **Workspace** | `TenantRepository` (`workspaces` SQL table) | `TenantContext`, API routers, Worker | `TenantRepository.create_workspace()` | Pipeline worker, AI agents, renderers | SQLite / PostgreSQL (`workspaces`) | In-memory context | `scripts/core/database.py:68` [`CODE_PROVEN`] |
| 3 | **Project** | `TenantRepository` (`projects` table) & disk directory | API routers, Worker, Pipeline | `ProjectService.create_project_async()` | Direct disk writes without DB record, AI agents | SQLite / PostgreSQL (`projects`) + `projects/<id>/` disk root | DB row vs local filesystem directory | `scripts/core/database.py:86`, `api/services/project_service.py:31` [`CODE_PROVEN`] |
| 4 | **Lifecycle** | `LifecycleService` & `StateStore` | API `/state`, Pipeline gates, Studio | `LifecycleService.transition()` with revision CAS | Direct file writes, AI agents, unvalidated API calls | `.pipeline_state.json` + `project_states` DB table | DB `project_states` vs disk `.pipeline_state.json` | `scripts/core/lifecycle_service.py:28-60`, `state_store.py:60` [`CODE_PROVEN`] |
| 5 | **Run** | `RunRepository` (`runs` SQL table) | `PipelineWorker`, API runs router, SSE | `RunService.create_run()`, `PipelineWorker` | Pipeline gates directly, renderers, AI agents | SQLite / PostgreSQL (`runs`, `run_events`, leases) | Ephemeral worker state | `scripts/core/run_repository.py:37-120` [`CODE_PROVEN`] |
| 6 | **Asset** | `AssetService` & `02_asset_manifest.json` | Authoring engine, Renderers, Materializer | `AssetService.upload_asset()`, `delete_asset()` | AI agents mutating asset folders directly, raw curl | `02_asset_manifest.json` + `StorageService` | Local disk vs StorageService vs manifest JSON | `api/services/asset_service.py:66-210`, `contracts/manifest.ts` [`CODE_PROVEN`] |
| 7 | **Artifact** | `DomainArtifactService` & `StateStore` | Review gates, QC gates, API `/artifacts` | Pipeline gates via `StateStore.create_artifact_record()` | Direct user upload bypassing gates, AI agents | `.pipeline_state.json` + `project_artifact_versions` | Disk files vs DB metadata records | `api/services/domain_artifact_service.py:22-80` [`CODE_PROVEN`] |
| 8 | **Storage object** | `StorageService` (`LocalStorageBackend` / `S3`) | `AssetService`, `CanonicalDocRepo`, `Worker` | `StorageService.put()` | Arbitrary path writes bypassing key traversal validator | Local root (`data/storage/`) or S3 bucket | Local disk temporary cache | `scripts/core/storage/storage_service.py:110-158` [`CODE_PROVEN`] |
| 9 | **VideoDocument** | `CanonicalDocumentRepository` & `UnifiedAuthoringSession` | Live Authoring API, Preview, RenderPlanner | `AuthoringService.execute_authoring()` via strict CAS | AI agents bypassing CAS, direct disk edits | `StorageService` (`blueprints/rev_*/`) + `project_states` | `05_blueprint.json` on disk vs StorageService | `scripts/core/canonical_document_repository.py:55-150` [`CODE_PROVEN`] |
| 10 | **Blueprint** | `contracts/blueprint.ts:BlueprintV2` (Schema) | `pipeline.py`, `validate_blueprint.py`, Studio | `AuthoringService`, `materialize_project.py` | Unvalidated TSX scripts, legacy generators | `05_blueprint.json` + `StorageService` | Blueprint V1 (`blueprint.json`) vs Blueprint V2 | `contracts/blueprint.ts:1-120` [`CODE_PROVEN`] |
| 11 | **Template identity** | `registry/template-registry-data.json` & `.tsx` | Template lint, Remotion Studio, Preview | `TemplateRegistryPublisher.publish()` | AI agents, Runtime mutation | Git-tracked JSON & TSX files in `registry/` | `ground-truth/template_catalog.json` (metadata derivative) | `scripts/core/template_registry_publisher.py:80-120` [`CODE_PROVEN`] |
| 12 | **Template metadata** | `contracts/template-runtime-contract.json` | Studio UI, Authoring picker, Preview | `TemplateRegistryPublisher`, generators | Ad-hoc agent mutations | Git-tracked JSON contracts | `ground-truth/TEMPLATE_INDEX.md` | `contracts/template-runtime-contract.json` [`CODE_PROVEN`] |
| 13 | **Recipe** | `recipes/*.json` (declarative JSON files) | `RecipeRegistry`, `RecipeSelector` (offline) | Human engineers / Git version control | Runtime API callers, autonomous AI agents | Local filesystem `recipes/*.json` | In-memory `RecipeRegistry._recipes` | `ai/recipes/registry.py:99-150` [`CODE_PROVEN`] |
| 14 | **Knowledge** | Markdown files in `references/` | `KnowledgeLoader`, `KnowledgeRouter` (offline) | Documentation authors / Git | Production API callers, runtime AI agents | Markdown files in `references/` | In-memory `KnowledgeRegistry._entries` | `ai/knowledge/registry.py:34-100` [`CODE_PROVEN`] |
| 15 | **Skill** | Code definitions & `.agents/skills/*/SKILL.md`| `SkillLoader`, `SkillRegistry` (offline) | Skill authors / Git | Runtime API callers | In-code definitions and markdown files | In-memory `SkillRegistry._entries` | `ai/skills/loader.py:62-240` [`CODE_PROVEN`] |
| 16 | **Memory** | `MemoryRepository` (`ai/memory/service.py`) | `ContextBuilder` (tests only) | `MemoryService.store_memory()` | Cross-tenant actors, direct SQL writes | SQL database or in-memory repository | In-memory vs SQL store | `ai/memory/service.py:49-115` [`CODE_PROVEN`] |
| 17 | **Provider** | `CANONICAL_PROVIDERS` & `ProviderRegistry` | `ModelRouter`, capability dispatchers | Static code definitions (frozen at boot) | Dynamic runtime callers | In-memory frozen singleton | None | `ai/providers/registry.py:32-94` [`CODE_PROVEN`] |
| 18 | **Model** | `CANONICAL_MODELS` & `ModelRegistry` | `ModelRouter` | Static code definitions (frozen at boot) | Dynamic runtime callers | In-memory frozen singleton | None | `ai/models/registry.py:30-80` [`CODE_PROVEN`] |
| 19 | **Capability** | `CapabilityCatalog` (`ai/capabilities/catalog.py`) | `CapabilityRouter`, `ToolGateway` | Static code catalog definitions | Unregistered runtime executions | In-memory catalog (32 capabilities) | None | `ai/capabilities/catalog.py:1-60` [`CODE_PROVEN`] |
| 20 | **Tool** | `ToolRegistry` (`ai/tools/registry.py`) | `ToolGateway` | `ToolRegistry.register()` | Direct unmanaged script execution | In-memory thread-safe dictionary | None | `ai/tools/registry.py:44-110` [`CODE_PROVEN`] |
| 21 | **CreativePlan** | `CreativePlanner` (`ai/planning/creative_planner.py`)| `CreativePlanValidator`, eval runners | `CreativePlanner.plan()` | Production pipeline (not connected) | Ephemeral Pydantic instance (status: PROPOSED) | None (disconnected from VideoDocument) | `ai/planning/creative_planner.py:58-115` [`CODE_PROVEN`] |
| 22 | **Candidate** | `TemplateCandidateService` & `CandidateRepository`| Candidate Review / Promotion API | `TemplateCandidateService` (server-controlled) | Direct registry mutation, AI agents | SQLite / PostgreSQL + `StorageService` | Candidate quarantine vs registered templates | `creative_governance/candidates/service.py:1-60` [`CODE_PROVEN`] |
| 23 | **RenderPlan** | `RenderPlanner` (`planner/render-planner.ts`)| `ProductionRenderGraphExecutor` | `RenderPlanner.plan()` | Remotion CLI directly | Ephemeral in-memory TypeScript object | None | `planner/render-planner.ts:1-50` [`CODE_PROVEN`] |
| 24 | **RenderGraph** | `ProductionRenderGraphExecutor` | Master Compositor, renderer node dispatchers | `RenderPlanner.buildGraph()` | Raw shell scripts | Directed Acyclic Graph (DAG) in memory | None | `planner/production-render-graph-executor.ts:1-60` [`CODE_PROVEN`] |
| 25 | **Review** | `ReviewService` & `review_bundles` / `decisions`| Pipeline (`AWAITING_REVIEW`), API artifacts | `ReviewService.approve()`, `ReviewService.reject()` | Direct `.studio_approved` marker creation | SQLite / PostgreSQL tables + `.pipeline_state.json` | Legacy `.studio_approved` vs DB decisions | `scripts/core/review_service.py:1-70`, `database.py:178` [`CODE_PROVEN`] |
| 26 | **QC** | `probe_qc.py` & `final_qc.py` | Pipeline orchestrator, ReviewService | Gate scripts writing JSON reports | Arbitrary manual report overrides | `probe_qc_report.json`, `final_qc_report.json` | None | `scripts/gates/probe_qc.py:1-50`, `final_qc.py:1-50` [`CODE_PROVEN`] |
| 27 | **Usage** | `TenantRepository` (`usage_events` table) | Billing / Metering auditors | `TenantRepository.record_usage()`, `PipelineWorker` | Direct SQL bypass | SQLite / PostgreSQL (`usage_events`) | None | `scripts/core/database.py:207-217` [`CODE_PROVEN`] |
| 28 | **Output** | `OutputService` (`api/services/output_service.py`)| API `/projects/{id}/outputs/{output_id}`, clients | `render_project.py`, `PipelineWorker` | Premature unverified output copy before QC | `projects/{id}/out.mp4` + `StorageService` | Local file vs signed URL in StorageService | `api/services/output_service.py:19-70` [`CODE_PROVEN`] |

---

## 3. Critical Authority Competing Paths & Conflict Analysis

### 3.1 Lifecycle & State: SQLite `project_states` vs Disk `.pipeline_state.json`
- **Mechanism**: In `scripts/core/state_store.py`, states are saved to disk `.pipeline_state.json` using atomic CAS file writes with `.lock` files. Concurrently, in multi-tenant SaaS environments, `DatabaseEngine` maintains the `project_states` table.
- **Conflict Risk**: If a local script (such as a developer test or direct CLI command) writes to `.pipeline_state.json` without notifying `DatabaseEngine`, state revision numbers diverge.
- **Resolution**: `StateStore.load()` verifies file hashes, and `PipelineWorker` enforces `AGY_INPUT_REVISION` matching the database record.

### 3.2 Canonical Document vs Local Disk: `StorageService` vs `05_blueprint.json`
- **Mechanism**: `CanonicalDocumentRepository` treats `StorageService` (under key `workspaces/{ws}/projects/{id}/blueprints/rev_{rev}_{hash}/blueprint.json`) as the authoritative immutable byte store.
- **Sync Protocol**: When an authoring mutation is committed, the repository updates `project_states` revision in SQL, stores the object in `StorageService`, and synchronizes the local disk file `projects/{id}/05_blueprint.json` if the project directory is present locally (`scripts/core/canonical_document_repository.py:130-145`).
- **Forbidden Action**: Directly editing `05_blueprint.json` on disk without invoking `AuthoringService` bypasses revision CAS and is overwritten on the next mutation commit.

### 3.3 Template Registry vs Compatibility Catalog: Dual Catalog Reality
- **Canonical Authority**: `registry/template-registry-data.json` is the sole machine-readable authority, and `registry/template-registry.tsx` is the Remotion component binding authority.
- **Derivative Derivative**: `ground-truth/template_catalog.json` is generated downstream by `scripts/core/template_registry_publisher.py:94` and `build_ground_truth.py`.
- **Finding**: While legacy agent instructions often cite `ground-truth/template_catalog.json`, runtime components treat it strictly as a read-only compatibility derivative.

### 3.4 Review Authorization: Database Review Decision vs `.studio_approved`
- **Mechanism**: Modern SaaS reviews are recorded via `ReviewService.approve()` in `review_decisions` SQL table. However, in `scripts/pipeline.py:449-465`, a compatibility path checks `approved_marker = proj_dir / ".studio_approved"`.
- **Bridge Behavior**: If `.studio_approved` exists on disk, `scripts/pipeline.py` automatically synthesizes a local trusted review approval (`create_local_trusted_principal("local_studio_reviewer")`) and invokes `ReviewService.approve()` to ensure transactional record creation in the database before proceeding to the render stage.

---

## 4. Conclusion

All 28 domain entities have clearly delineated canonical authorities, authorized mutating interfaces, and strict isolation policies. The deterministic production pipeline prevents unauthorized mutations via CAS revision checks, tenant validation, and gate state machines.
