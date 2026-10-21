# PILLAR 2: Runtime Reachability, Dependency Injection & Authority Matrix

> **Consolidated Master Pillar** — Comprehensive integration of Reports 03, 04, 05, and 13

> **Baseline SHA**: `90ec3de8d47494d5940d5cd1f9ed9a8e274ef6e1` | **Branch**: `main`

> **Evidence Standard**: Strictly Preserved (`CODE_PROVEN`, `TEST_PROVEN`, `CI_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`, `DOCUMENTATION_ONLY`, `INFERRED`, `UNKNOWN`)


---

## Table of Contents

1. [Part 1: Runtime Reachability Matrix (53 Components)](#part-1-runtime-reachability-matrix-53-components) *(Source: `03_RUNTIME_REACHABILITY_MATRIX.md`)*
2. [Part 2: Bootstrap Dependency Injection & Registry Reality](#part-2-bootstrap-dependency-injection--registry-reality) *(Source: `04_BOOTSTRAP_DEPENDENCY_INJECTION_AND_REGISTRY_REALITY.md`)*
3. [Part 3: Source of Truth & Canonical Authority Matrix](#part-3-source-of-truth--canonical-authority-matrix) *(Source: `05_SOURCE_OF_TRUTH_AND_AUTHORITY_MATRIX.md`)*
4. [Part 4: Dataflow, Persistence & Artifact Lineage](#part-4-dataflow-persistence--artifact-lineage) *(Source: `13_DATAFLOW_PERSISTENCE_AND_ARTIFACT_LINEAGE.md`)*

---


<a name='part-1-runtime-reachability-matrix-53-components'></a>

## Part 1: Runtime Reachability Matrix (53 Components)


> *Original Source: `documentation/reality_context_pack/03_RUNTIME_REACHABILITY_MATRIX.md`*


### Sub-Report Title: Runtime Reachability Matrix Reality Report


- **Baseline Git SHA**: `90ec3de8d47494d5940d5cd1f9ed9a8e274ef6e1`
- **Branch**: `main`
- **Report Version**: 1.0.0
- **Last Updated**: 2026-10-07
- **Scope**: Comprehensive reachability audit of all 28 core subsystems across Product, Development, Compatibility, and Test execution paths with evidence classifications.
- **Evidence Standard**: `CODE_PROVEN`, `TEST_PROVEN`, `CI_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`, `DOCUMENTATION_ONLY`, `INFERRED`, `UNKNOWN`

---

## 1. Subsystem Reachability Classification Taxonomy

Every subsystem is evaluated against real production entrypoints (FastAPI routes in `api/main.py`, background worker in `scripts/worker.py`, and CLI orchestrator in `scripts/pipeline.py`) and assigned exactly one classification:

- **`PRODUCTION_REACHABLE`**: Invoked directly along active production runtime paths triggered by authentic user HTTP requests or background worker tasks.
- **`INDIRECTLY_REACHABLE`**: Invoked by a production-reachable component via dynamic delegation, inter-process bridges, or event-driven state triggers.
- **`DEV_ONLY`**: Invoked exclusively by interactive local developer tooling (e.g., Remotion Studio UI, local diagnostic scripts).
- **`COMPATIBILITY_ONLY`**: Maintained strictly for legacy backwards compatibility; invoked only when explicitly toggled or when modern paths fail.
- **`TEST_ONLY`**: Invoked exclusively within unit tests, component integration tests, synthetic benchmarks, or offline evaluation harnesses.
- **`UNREACHABLE_FROM_PRODUCT`**: Implemented in codebase but has zero incoming call sites or imports from any production entrypoint or worker.
- **`UNKNOWN`**: Ambiguous wiring or unproven execution path.

---

## 2. Core Subsystems Reachability Matrix (28 Subsystems)

| # | Subsystem | Code Paths / Core Files | Reachability Status | Production Entrypoints / Triggers | Direct Callers | Direct Callees | Evidence Citation |
|---|---|---|---|---|---|---|---|
| 1 | **Context Subsystem** | `ai/context/builder.py`, `ai/context/retrieval.py` | `UNREACHABLE_FROM_PRODUCT` | None | None (`tests/ai/context/*` only) | Retrievers, MemoryService, TokenEstimator | `ai/context/builder.py:47-91` [`CODE_PROVEN`] |
| 2 | **Memory Subsystem** | `ai/memory/service.py`, `ai/memory/repository.py` | `UNREACHABLE_FROM_PRODUCT` | None | None (`tests/ai/memory/*` only) | MemoryRepository, EmbeddingProvider | `ai/memory/service.py:49-115` [`CODE_PROVEN`] |
| 3 | **Knowledge Subsystem** | `ai/knowledge/router.py`, `ai/knowledge/registry.py` | `UNREACHABLE_FROM_PRODUCT` | None | None (`tests/ai/knowledge/*`, eval runner) | KnowledgeLoader, KnowledgeIndexer | `ai/knowledge/router.py:34-68` [`CODE_PROVEN`] |
| 4 | **Skills Subsystem** | `ai/skills/registry.py`, `ai/skills/loader.py` | `UNREACHABLE_FROM_PRODUCT` | None | None (`tests/ai/skills/*` only) | SkillLoader, Markdown parser | `ai/skills/registry.py:34-100` [`CODE_PROVEN`] |
| 5 | **Recipes Subsystem** | `ai/recipes/registry.py`, `recipes/*.json` | `UNREACHABLE_FROM_PRODUCT` | None | None (`tests/ai/recipes/*`, offline eval) | JSON disk loader, RecipeDefinition | `ai/recipes/registry.py:99-150` [`CODE_PROVEN`] |
| 6 | **Intent Subsystem** | `authoring/intent-planner.ts`, `contracts/authoring.ts` | `INDIRECTLY_REACHABLE` | `POST /projects/{id}/intent` | `execute_authoring_mutation.ts:206` | UnifiedAuthoringSession, AST Mutators | `contracts/authoring.ts:273-304`, `authoring/intent-planner.ts:5-14` [`CODE_PROVEN`] |
| 7 | **Narrative Subsystem** | `ai/narrative/planner.py`, `ai/narrative/models.py` | `UNREACHABLE_FROM_PRODUCT` | None | None (`tests/ai/narrative/*`, eval runner) | Archetype matchers, Beat generators | `ai/narrative/planner.py:35-80` [`CODE_PROVEN`] |
| 8 | **Taste Subsystem (AI)** | `ai/taste/engine.py`, `ai/taste/rules.py` | `UNREACHABLE_FROM_PRODUCT` | None | None (`tests/ai/taste/*`, eval runner) | TasteRuleRegistry, TasteEvaluator | `ai/taste/engine.py:26-85` [`CODE_PROVEN`] |
| 9 | **Taste Gate (Pipeline)** | `scripts/gates/taste_gate.py` | `PRODUCTION_REACHABLE` | `POST /projects/{id}/runs` | `scripts/pipeline.py:372` | Regex heuristics on `master_plan.md` | `scripts/gates/taste_gate.py:1-60` [`CODE_PROVEN`] |
| 10 | **Creative Planning Subsystem** | `ai/planning/creative_planner.py`, `ai/planning/compiler.py` | `UNREACHABLE_FROM_PRODUCT` | None | None (`tests/ai/planning/*`, eval runner) | BlueprintCompiler, ConflictResolver | `ai/planning/creative_planner.py:58-115` [`CODE_PROVEN`] |
| 11 | **Model & Capability Routing** | `ai/routing/router.py`, `ai/routing/capability_router.py` | `UNREACHABLE_FROM_PRODUCT` | None | None (`tests/ai/routing/*` only) | ModelRegistry, ToolGateway, Providers | `ai/routing/router.py:67-130`, `ai/routing/capability_router.py:69-120` [`CODE_PROVEN`] |
| 12 | **Provider Subsystem** | `ai/providers/registry.py`, `ai/providers/adapters/*` | `UNREACHABLE_FROM_PRODUCT` | None | None (`tests/ai/providers/*` only) | Provider APIs (OpenAI, Fal, Groq) | `ai/providers/registry.py:32-94` [`CODE_PROVEN`] |
| 13 | **Tool Subsystem** | `ai/tools/gateway.py`, `ai/tools/registry.py` | `UNREACHABLE_FROM_PRODUCT` | None | None (`tests/ai/tools/*` only) | NativeToolAdapter, DomainServiceAdapter | `ai/tools/gateway.py:231-310` [`CODE_PROVEN`] |
| 14 | **MCP FastMCP Compatibility** | `ai/mcp/compatibility/server.py` | `COMPATIBILITY_ONLY` | Standalone CLI (`python -m ai.mcp`) | External MCP clients | ToolGateway, FastMCP | `ai/mcp/compatibility/server.py:1-40` [`CODE_PROVEN`] |
| 15 | **MCP Plugin Servers** | `.agents/plugins/.../mcp-servers/*` | `DEV_ONLY` | IDE / Developer MCP Client | Claude / Antigravity Agent | Local Python scripts, FFmpeg | `.agents/plugins/super-video-maker-plugin/mcp_config.json` [`CODE_PROVEN`] |
| 16 | **Pipeline Orchestration** | `scripts/pipeline.py`, `scripts/core/worker.py` | `PRODUCTION_REACHABLE` | `POST /projects/{id}/runs`, `scripts/worker.py` | `PipelineWorker.process_one:289` | Gate scripts, Materializer, RenderProject | `scripts/pipeline.py:221-520`, `scripts/core/worker.py:176-350` [`RUNTIME_REACHABILITY_PROVEN`] |
| 17 | **Creative Governance** | `creative_governance/candidates/service.py` | `PRODUCTION_REACHABLE` | `POST /candidates/{id}/reviews/*`, `promote` | `candidate_reviews.py`, `candidate_promotions.py` | TemplateCandidateRepository, Publisher | `creative_governance/candidates/service.py:1-60` [`CODE_PROVEN`] |
| 18 | **Live Authoring Engine** | `authoring/unified-authoring-session.ts` | `INDIRECTLY_REACHABLE` | `POST /projects/{id}/mutate`, `batch`, `intent` | `AuthoringService.execute_authoring:170` | IntentPlanner, CanonicalMutations | `authoring/unified-authoring-session.ts:1-50` [`CODE_PROVEN`] |
| 19 | **VideoDocument / BlueprintV2** | `contracts/blueprint.ts`, `scripts/core/canonical_document_repository.py` | `PRODUCTION_REACHABLE` | `GET /projects/{id}/document`, authoring, render | `AuthoringService`, `RenderPlanner` | DatabaseEngine, StorageService, JSON schema | `scripts/core/canonical_document_repository.py:55-150` [`CODE_PROVEN`] |
| 20 | **Preview Subsystem** | `preview/preview-runtime.ts`, `scripts/open_studio.py` | `DEV_ONLY` | `python scripts/open_studio.py` | Developer CLI | Remotion Studio on port 3000 | `scripts/open_studio.py:1-60`, `preview/preview-runtime.ts:1-50` [`CODE_PROVEN`] |
| 21 | **Render Planning Subsystem** | `planner/render-planner.ts` | `INDIRECTLY_REACHABLE` | `scripts/render_project.py:140` | `scripts/render_via_planner.ts:124` | ProductionRenderGraphExecutor | `planner/render-planner.ts:1-50` [`CODE_PROVEN`] |
| 22 | **Render Graph Subsystem** | `planner/production-render-graph-executor.ts` | `INDIRECTLY_REACHABLE` | `scripts/render_project.py:140` | `scripts/render_via_planner.ts:150` | Renderer Adapters, MasterCompositor | `planner/production-render-graph-executor.ts:1-60` [`CODE_PROVEN`] |
| 23 | **Renderer Adapters** | `remotion/remotion-renderer-adapter.ts`, `canvas/canvas-renderer-adapter.ts` | `INDIRECTLY_REACHABLE` | `scripts/render_via_planner.ts`, `scripts/render_via_adapter.ts` | `ProductionRenderGraphExecutor` | Remotion CLI, Canvas renderer | `remotion/remotion-renderer-adapter.ts:8-50`, `canvas/canvas-renderer-adapter.ts:1-40` [`CODE_PROVEN`] |
| 24 | **Master Compositor** | `compositor/master-compositor.ts` | `INDIRECTLY_REACHABLE` | `scripts/render_via_planner.ts:160` | `ProductionRenderGraphExecutor` | FFmpeg subprocess muxing/normalization | `compositor/master-compositor.ts:1-60` [`CODE_PROVEN`] |
| 25 | **Quality Control (QC)** | `scripts/gates/probe_qc.py`, `final_qc.py`, `motion_validator.py` | `PRODUCTION_REACHABLE` | `POST /projects/{id}/runs` | `scripts/pipeline.py:413,497` | Remotion still, FFprobe, Audio LUFS | `scripts/gates/probe_qc.py:1-50`, `scripts/gates/final_qc.py:1-50` [`CODE_PROVEN`] |
| 26 | **StorageService** | `scripts/core/storage/storage_service.py` | `PRODUCTION_REACHABLE` | All asset, document, run, and output routes | `AssetService`, `CanonicalDocRepo`, `Worker` | Local disk (`LocalStorageBackend`) or S3 | `scripts/core/storage/storage_service.py:110-158` [`CODE_PROVEN`] |
| 27 | **AssetService** | `api/services/asset_service.py` | `PRODUCTION_REACHABLE` | `POST /projects/{id}/assets` | `api/routers/assets.py:50` | StorageService, `02_asset_manifest.json` | `api/services/asset_service.py:66-210` [`CODE_PROVEN`] |
| 28 | **RunService & Lifecycle** | `api/services/run_service.py`, `scripts/core/lifecycle_service.py`, `state_store.py` | `PRODUCTION_REACHABLE` | `POST /projects/{id}/runs`, `GET /state` | `api/routers/runs.py`, `pipeline.py` | `RunRepository`, `StateStore`, `DatabaseEngine` | `api/services/run_service.py:34-114`, `scripts/core/lifecycle_service.py:1-50` [`CODE_PROVEN`] |
| 29 | **Usage & Metering** | `scripts/core/database.py:TenantRepository.record_usage()` | `PRODUCTION_REACHABLE` | Background worker output upload | `PipelineWorker._upload_outputs_and_meter:100` | SQLite/PostgreSQL `usage_events` table | `scripts/core/worker.py:100-110`, `scripts/core/database.py:207-217` [`CODE_PROVEN`] |

---

## 3. Deep Dive: The Architectural Boundary Islands

Our analysis identifies three distinct, isolated runtime islands within the codebase:

### Island 1: The Production-Reachable Core Runtime
- **Components**: FastAPI (`api/`), Domain Core (`scripts/core/`), State Machine & Gates (`scripts/pipeline.py`, `scripts/gates/`), Asset Management (`api/services/asset_service.py`), Live Authoring Bridge (`authoring/`, `scripts/execute_authoring_mutation.ts`), Candidate Governance (`creative_governance/`), and Multi-Engine Renderer (`planner/`, `remotion/`, `canvas/`, `compositor/`).
- **Characteristics**:
  - Deterministic, robust, multi-tenant, and transactional.
  - Reaches 100% of the 53 production API routes.
  - Backed by SQLite/PostgreSQL CAS locking and `StorageService` persistence.
  - Zero dependencies on external AI vendors during rendering.

### Island 2: The Unreachable AI Platform (S27/S28)
- **Components**: `ai/context`, `ai/memory`, `ai/knowledge`, `ai/skills`, `ai/recipes`, `ai/planning`, `ai/narrative`, `ai/taste`, `ai/routing`, `ai/capabilities`, `ai/providers`, `ai/tools`.
- **Characteristics**:
  - High internal elegance and modular abstraction (clean protocols, deterministic fallbacks, Pydantic DTOs).
  - High unit test density (270 test files in `tests/ai/`).
  - **Zero production incoming callers**: Completely unimported and uncalled by any production HTTP route or pipeline worker script.
  - Excluded from required GitHub Actions CI (`remediation-ci.yml:125-126`).
  - Disconnected from the production document authority (`VideoDocument` / `BlueprintV2`).

### Island 3: Compatibility & Migration Layer
- **Components**: FastMCP compatibility server (`ai/mcp/compatibility/server.py`), legacy plugin MCP servers (`.agents/plugins/...`), template catalog publisher (`scripts/core/template_registry_publisher.py`), and legacy Remotion CLI render fallback (`scripts/render_project.py:177`).
- **Characteristics**:
  - Activated conditionally as fallbacks or offline utilities.
  - Never act as primary authoritative execution paths in SaaS production mode.

---

## 4. AST & Grep Verification of Reachability Isolation

The complete isolation between Island 1 (Production) and Island 2 (AI Platform) is proven by direct static analysis of production code:

1. **Production API Imports Sweep**:
   - Query: `grep -rn "from ai" api/`
   - Result: `0 matches` [`CODE_PROVEN`]
   - Query: `grep -rn "import ai" api/`
   - Result: `0 matches` [`CODE_PROVEN`]

2. **Pipeline Orchestrator Imports Sweep**:
   - Query: `grep -rn "from ai" scripts/pipeline.py scripts/core/worker.py scripts/render_project.py`
   - Result: `0 matches` [`CODE_PROVEN`]

3. **Production Authoring Bridge Imports Sweep**:
   - Query: `grep -rn "ai/" scripts/execute_authoring_mutation.ts authoring/`
   - Result: `0 matches` (enforced by AST invariant comments in `scripts/execute_authoring_mutation.ts:8` and `authoring/intent-planner.ts:5`) [`CODE_PROVEN`]

4. **CreativePlan to VideoDocument Bridge Sweep**:
   - Query: `grep -rn "BlueprintCompiler" api/ scripts/core/worker.py scripts/pipeline.py`
   - Result: `0 matches` [`CODE_PROVEN`]

---

## 5. Conclusion & Architectural Summary

The reachability audit definitively demonstrates that:
1. All core video production, asset management, document mutation, candidate governance, and rendering subsystems are **`PRODUCTION_REACHABLE`** or **`INDIRECTLY_REACHABLE`** via deterministic TypeScript/Python execution paths.
2. The entire AI intelligence and creative planning platform is **`UNREACHABLE_FROM_PRODUCT`**. It exists as an offline library that is neither triggered by HTTP API calls nor invoked by background worker daemons.


---


<a name='part-2-bootstrap-dependency-injection--registry-reality'></a>

## Part 2: Bootstrap Dependency Injection & Registry Reality


> *Original Source: `documentation/reality_context_pack/04_BOOTSTRAP_DEPENDENCY_INJECTION_AND_REGISTRY_REALITY.md`*


### Sub-Report Title: Bootstrap, Dependency Injection and Registry Reality Report


- **Baseline Git SHA**: `90ec3de8d47494d5940d5cd1f9ed9a8e274ef6e1`
- **Branch**: `main`
- **Report Version**: 1.0.0
- **Last Updated**: 2026-10-07
- **Scope**: Rigorous audit of object construction, dependency injection, registry population, default behaviors, fallbacks, and test vs. production wiring for 14 core subsystems with explicit answers to Mandatory Checks G, H, I, P, and Q.
- **Evidence Standard**: `CODE_PROVEN`, `TEST_PROVEN`, `CI_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`, `DOCUMENTATION_ONLY`, `INFERRED`, `UNKNOWN`

---

## 1. Executive Summary: The Dual-Reality Dependency Architecture

The repository exhibits two completely disconnected dependency injection ecosystems:
1. **The Production Deterministic Container**: In `api/` and `scripts/core/`, services are constructed either via class-level lazy singletons (`get_database_engine()`, `get_storage_service()`, `AuthoringService._doc_repo`) or instantiated per-request with explicit parameters (`RunService(repo=RunRepository())`, `ProjectService(repo=TenantRepository())`). This ecosystem is 100% active, hardened, and proven reachable.
2. **The AI Platform Modular DI Framework**: In `ai/`, an elaborate protocol-driven dependency injection architecture is implemented across 14 subsystems (`ContextBuilder`, `KnowledgeRouter`, `ModelRouter`, `CapabilityRouter`, `ToolGateway`, `CreativePlanner`, etc.) featuring optional constructor parameters, automatic fallback to deterministic defaults, and frozen singleton registries. **However, zero components of this framework are wired into the production FastAPI application or pipeline worker.** It exists as a dormant library instantiated exclusively within unit tests, architecture guardrails, and offline regression harnesses.

---

## 2. In-Depth Subsystem DI & Registry Audit (14 Subsystems)

### 2.1 Subsystem 1: `ContextBuilder`
- **File**: `ai/context/builder.py:47-91`
- **Constructor Signature**:
  ```python
  def __init__(
      self,
      project_service: Optional[object] = None,
      asset_service: Optional[object] = None,
      review_service: Optional[object] = None,
      memory_service: Optional[MemoryService] = None,
      knowledge_retriever: Optional[KnowledgeRetriever] = None,
      ranking_policy: Optional[ContextRankingPolicy] = None,
      budget_policy: Optional[ContextBudgetPolicy] = None,
      compressor: Optional[DeterministicContextCompressor] = None,
      token_estimator: Optional[TokenEstimator] = None,
  ):
  ```
- **Defaults & Fallbacks**:
  - `self.knowledge_retriever = knowledge_retriever or DeterministicKnowledgeRetriever()` (`ai/context/builder.py:77`)
  - `self.token_estimator = token_estimator or DeterministicTokenEstimator()` (`ai/context/builder.py:84`)
  - `self.compressor = compressor or DeterministicContextCompressor()` (`ai/context/builder.py:85`)
  - `self.budget_manager = ContextBudgetManager(policy=budget_policy, ...)` (`ai/context/builder.py:86-90`)
- **Population Protocol**: Dynamic assembly upon calling `build(request: ContextRequest)` across sub-retrievers (`SystemPolicyRetriever`, `SharedConfigRetriever`, `ProjectFactRetriever`, `MemoryRetriever`, `DeterministicKnowledgeRetriever`, `RequestRetriever`).
- **Production Wiring**: **NONE** (`CODE_PROVEN`). Zero references across `api/` and `scripts/`.
- **Test Wiring**: Instantiated with mocks/fakes in `tests/ai/context/test_builder.py:64,141`, `tests/ai/context/test_architecture_guards.py:159,205,252`, `tests/ai/context/test_determinism.py:82`, `tests/ai/context/test_tenant_isolation.py:89`.

---

### 2.2 Subsystem 2: `KnowledgeRouter`
- **File**: `ai/knowledge/router.py:34-68`
- **Constructor Signature**:
  ```python
  def __init__(
      self,
      registry: Optional[KnowledgeRegistry] = None,
      indexer: Optional[KnowledgeIndexer] = None,
      loader: Optional[KnowledgeLoader] = None,
      semantic_scorer: Optional[BaseSemanticScorer] = None,
      workspace_root: Optional[Path] = None,
  ) -> None:
  ```
- **Defaults & Fallbacks**:
  - `self.workspace_root = workspace_root or Path.cwd()`
  - `self.registry = registry or KnowledgeRegistry()`
  - `self.indexer = indexer or KnowledgeIndexer()`
  - `self.loader = loader or KnowledgeLoader(workspace_root=self.workspace_root)`
  - `self.retriever = KnowledgeRetriever(indexer=self.indexer, registry=self.registry, semantic_scorer=semantic_scorer)`
- **Population Protocol**: Explicit initialization via `initialize_canonical_catalog(verify_hash=True)` (`ai/knowledge/router.py:58-68`), which calls `loader.load_canonical_catalog(registry=self.registry)` and `indexer.index_many(loaded_docs)`.
- **Production Wiring**: **NONE** (`CODE_PROVEN`).
- **Test / Eval Wiring**: Invoked in eval runner `ai/regression/runner.py:161-162` with `verify_hash=False`, and tests `tests/ai/evals/test_knowledge_and_skill_evals.py:51`, `tests/ai/knowledge/test_knowledge_platform.py:69`.

---

### 2.3 Subsystem 3: `KnowledgeRegistry`
- **File**: `ai/knowledge/registry.py:34-100`
- **Constructor Signature**: `def __init__(self) -> None`
- **Defaults & Fallbacks**: In-memory dictionaries `_entries: Dict[Tuple[str, str], KnowledgeDescriptor]` and `_latest: Dict[str, KnowledgeDescriptor]`. Missing key lookups return `None`.
- **Population Protocol**: Populated via `register()` / `register_many()` invoked by `KnowledgeLoader.load_canonical_catalog()`.
- **Production Wiring**: **NONE** (`CODE_PROVEN`).
- **Test Wiring**: Tested in `tests/ai/knowledge/test_knowledge_platform.py`.

---

### 2.4 Subsystem 4: `SkillRegistry`
- **File**: `ai/skills/registry.py:34-100`
- **Constructor Signature**: `def __init__(self) -> None`
- **Defaults & Fallbacks**: In-memory dictionaries `_entries` and `_latest`. `get_active(skill_id)` strictly returns skills where `status == SkillStatus.ACTIVE`.
- **Population Protocol**: Populated via `register()` / `register_many()` called by `SkillLoader`.
- **Production Wiring**: **NONE** (`CODE_PROVEN`).
- **Test Wiring**: Tested in `tests/ai/skills/test_skill_platform.py`.

---

### 2.5 Subsystem 5: `RecipeRegistry`
- **File**: `ai/recipes/registry.py:99-150`
- **Constructor Signature**:
  ```python
  def __init__(self, recipe_dir: Optional[Path] = None, auto_load: bool = True) -> None:
  ```
- **Defaults & Fallbacks**:
  - `self.recipe_dir = recipe_dir or (Path(__file__).resolve().parent.parent.parent / "recipes")` (`ai/recipes/registry.py:106`)
  - If `auto_load=True` and directory exists, automatically runs `load_from_directory()`.
- **Population Protocol**: Scans all `*.json` in `recipes/` (skipping `schema.json`), audits legacy provider bindings via `_audit_legacy_providers()`, migrates to `RecipeDefinition`, and registers into `_recipes` (`ai/recipes/registry.py:113-145`).
- **Production Wiring**: **NONE** (`CODE_PROVEN`).
- **Test Wiring**: Tested in `tests/ai/recipes/test_recipe_platform.py`, `tests/ai/planning/test_recipe_selector.py`.

---

### 2.6 Subsystem 6: `ModelRouter`
- **File**: `ai/routing/router.py:67-130`
- **Constructor Signature**:
  ```python
  def __init__(
      self,
      model_registry: Optional[ModelRegistry] = None,
      provider_registry: Optional[ProviderRegistry] = None,
      capability_registry: Optional[CapabilityRegistry] = None,
      default_policy: Optional[RoutingPolicy] = None,
  ) -> None:
  ```
- **Defaults & Fallbacks**:
  - `self._model_registry = model_registry or get_model_registry()` (`ai/routing/router.py:80`)
  - `self._provider_registry = provider_registry or get_provider_registry()` (`ai/routing/router.py:81`)
  - `self._capability_registry = capability_registry or get_capability_registry()` (`ai/routing/router.py:82`)
  - Deterministically ranks eligible models by quality, latency, error rate, and cost, returning a primary model and ordered fallbacks (`ai/routing/router.py:120-130`).
- **Production Wiring**: **NONE** (`CODE_PROVEN`).
- **Test Wiring**: Tested in `tests/ai/routing/test_router.py`, `tests/ai/routing/test_capability_router.py`.

---

### 2.7 Subsystem 7: `ProviderRegistry`
- **File**: `ai/providers/registry.py:32-94`
- **Constructor Signature**: `def __init__(self) -> None`
- **Defaults & Fallbacks**: In-memory `_providers: Dict[str, ProviderDefinition]`, `_frozen: bool = False`. Singleton accessor `get_provider_registry()` registers `CANONICAL_PROVIDERS` from `ai/providers/definitions.py` and freezes registry.
- **Production Wiring**: **NONE** (`CODE_PROVEN`).
- **Test Wiring**: Tested in `tests/ai/providers/test_registry.py`.

---

### 2.8 Subsystem 8: `CapabilityRouter`
- **File**: `ai/routing/capability_router.py:69-120`
- **Constructor Signature**:
  ```python
  def __init__(
      self,
      catalog: Optional[CapabilityCatalog] = None,
      tool_gateway: Optional[ToolGateway] = None,
      model_seam: Optional[ModelRouterSeam] = None,
      model_router: Optional[ModelRouter] = None,
  ) -> None:
  ```
- **Defaults & Fallbacks**:
  - `self.catalog = catalog or get_capability_catalog()` (`ai/routing/capability_router.py:83`)
  - `self.tool_gateway = tool_gateway or ToolGateway(catalog=self.catalog)` (`ai/routing/capability_router.py:84`)
  - `self.model_router = model_router or ModelRouter()` (`ai/routing/capability_router.py:85`)
  - `self.model_seam = model_seam or ModelRouterSeam(self.model_router)` (`ai/routing/capability_router.py:86`)
  - Dispatches `CapabilityCategory.MODEL` $\to$ `model_seam.execute_model_capability()`; dispatches `TOOL` & `DOMAIN_SERVICE` $\to$ `tool_gateway.execute()`.
- **Production Wiring**: **NONE** (`CODE_PROVEN`).
- **Test Wiring**: Tested in `tests/ai/routing/test_capability_router.py`, `tests/ai/e2e/test_s28_m11_product_e2e_matrix.py`.

---

### 2.9 Subsystem 9: `ToolGateway`
- **File**: `ai/tools/gateway.py:231-310`
- **Constructor Signature**:
  ```python
  def __init__(
      self,
      catalog: Optional[CapabilityCatalog] = None,
      adapter_registry: Optional[AdapterRegistry] = None,
      idempotency_store: Optional[IdempotencyStore] = None,
  ) -> None:
  ```
- **Defaults & Fallbacks**:
  - `self.catalog = catalog or get_capability_catalog()` (`ai/tools/gateway.py:254`)
  - `self.adapter_registry = adapter_registry or get_adapter_registry()` (`ai/tools/gateway.py:255`)
  - `self.idempotency_store = idempotency_store or _default_idempotency_store` (`ai/tools/gateway.py:256`)
  - Enforces 15-stage execution pipeline (lookup, idempotency, leasing, authorization, output validation).
- **Production Wiring**: **NONE** (`CODE_PROVEN`).
- **Test Wiring**: Tested in `tests/ai/tools/test_tool_gateway.py`.

---

### 2.10 Subsystem 10: `ToolRegistry`
- **File**: `ai/tools/registry.py:44-110`
- **Constructor Signature**: `def __init__(self)`
- **Defaults & Fallbacks**: Thread-safe dictionary `_tools: Dict[str, ToolRegistration] = {}`, `_lock = threading.Lock()`.
- **Population Protocol**: Populated via `register(definition, adapter)`.
- **Production Wiring**: **NONE** (`CODE_PROVEN`).
- **Test Wiring**: Tested in `tests/ai/tools/test_registry.py`.

---

### 2.11 Subsystem 11: `CreativePlanner`
- **File**: `ai/planning/creative_planner.py:58-115`
- **Constructor Signature**: `def __init__(self, planner_version: str = "1.0.0") -> None`
- **Defaults & Fallbacks**: Invariant: `CreativePlan` is strictly advisory (`status=PROPOSED`). Fails closed on unresolved conflicts with `UnresolvedCreativeConflictError`.
- **Production Wiring**: **NONE** (`CODE_PROVEN`).
- **Test Wiring**: Tested in `tests/ai/planning/test_creative_planner.py`, `ai/regression/runner.py:155`.

---

### 2.12 Subsystem 12: `NarrativePlanner`
- **File**: `ai/narrative/planner.py:35-80`
- **Constructor Signature**:
  ```python
  def __init__(
      self,
      knowledge_router: Optional[KnowledgeRouter] = None,
      skill_router: Optional[SkillRouter] = None,
  ) -> None:
  ```
- **Defaults & Fallbacks**: `self.knowledge_router = None`, `self.skill_router = None`. Synthesizes `NarrativePlan` from `CreativeBrief` archetypes, beats, and audio mode.
- **Production Wiring**: **NONE** (`CODE_PROVEN`).
- **Test Wiring**: Tested in `tests/ai/narrative/test_narrative_planner.py`, `ai/regression/runner.py:171`.

---

### 2.13 Subsystem 13: `TasteEngine`
- **File**: `ai/taste/engine.py:26-85`
- **Constructor Signature**:
  ```python
  def __init__(
      self,
      registry: Optional[TasteRuleRegistry] = None,
      evaluator: Optional[TasteEvaluator] = None,
  ) -> None:
  ```
- **Defaults & Fallbacks**: `self.registry = registry or TasteRuleRegistry()`, `self.evaluator = evaluator or TasteEvaluator()`. Evaluates `CANONICAL_TASTE_RULES` against `TasteContext`.
- **Production Wiring**: **NONE** (`CODE_PROVEN`). Note: Pipeline executes `scripts/gates/taste_gate.py` (regex heuristics), NOT `ai/taste/engine.py`.
- **Test Wiring**: Tested in `tests/ai/taste/test_taste_engine.py`, `ai/regression/runner.py:156`.

---

### 2.14 Subsystem 14: `MemoryService`
- **File**: `ai/memory/service.py:49-115`
- **Constructor Signature**:
  ```python
  def __init__(
      self,
      repository: MemoryRepository,
      embedding_provider: EmbeddingProvider,
      clock: Optional[Clock] = None,
      policy: Optional[MemoryPolicy] = None,
  ):
  ```
- **Defaults & Fallbacks**: Requires explicit `repository` and `embedding_provider`. `clock = clock or SystemClock()`.
- **Production Wiring**: **NONE** (`CODE_PROVEN`).
- **Test Wiring**: Tested in `tests/ai/memory/test_memory_service.py` (with `InMemoryMemoryRepository` and fake embeddings).

---

## 3. Explicit Verification of Mandatory Checks (G, H, I, P, Q)

### Check G: Who instantiates `ContextBuilder` in Production?
- **Reality Finding**: **NO ONE** (`Production caller: NONE`).
- **Evidence Citation**: `ai/context/builder.py:47`.
- **Proof**: A comprehensive search across the entire repository reveals that every single instantiation of `ContextBuilder(` resides strictly within test files (`tests/ai/context/test_builder.py:64,141`, `tests/ai/context/test_architecture_guards.py:159,205,252`, `tests/ai/context/test_determinism.py:82,138,152`, `tests/ai/context/test_irrelevant_memory.py:85`, `tests/ai/context/test_tenant_isolation.py:89,133,150`, `tests/ai/context/test_token_safety.py:232`). Zero production modules in `api/` or `scripts/` instantiate or import `ContextBuilder`.
- **Evidence Standard**: `CODE_PROVEN`.

### Check H: Who injects `KnowledgeRouter` into `ContextBuilder`?
- **Reality Finding**: **NO ONE**.
- **Evidence Citation**: `ai/context/builder.py:59-77`, `ai/context/retrieval.py:61-71`, `ai/knowledge/router.py:34-56`.
- **Proof**:
  1. `ContextBuilder.__init__` accepts `knowledge_retriever: Optional[KnowledgeRetriever] = None`.
  2. `KnowledgeRetriever` is an abstract Protocol defined in `ai/context/retrieval.py:61-71` requiring `retrieve(context_request: ContextRequest) -> List[ContextItem]`.
  3. When omitted, `ContextBuilder` defaults to `DeterministicKnowledgeRetriever()` (`ai/context/builder.py:77`).
  4. `KnowledgeRouter` (`ai/knowledge/router.py:34`) does NOT implement the `KnowledgeRetriever` protocol; it is a higher-level facade wrapping `KnowledgeIndexer`, `KnowledgeLoader`, and `KnowledgeRegistry`.
  5. Nowhere in the repository (neither production nor test suites) is a `KnowledgeRouter` instance ever passed or injected into `ContextBuilder`.
- **Evidence Standard**: `CODE_PROVEN`.

### Check I: Does `initialize_canonical_catalog()` execute in Production?
- **Reality Finding**: **NO**.
- **Evidence Citation**: `ai/knowledge/router.py:58-68`, `ai/regression/runner.py:162`, `api/main.py:28-40`.
- **Proof**:
  1. `initialize_canonical_catalog()` is a method on `KnowledgeRouter` that loads and indexes markdown documents from `references/`.
  2. It is called in exactly two evaluation scripts: `ai/regression/runner.py:162` and `scripts/run_creative_regression.py:90`.
  3. It is called in 4 unit/integration tests: `tests/ai/evals/test_knowledge_and_skill_evals.py:51`, `tests/ai/integration/test_knowledge_skill_integration.py:72`, `tests/ai/knowledge/test_knowledge_platform.py:69`, `tests/ai/skills/test_skill_platform.py:209`.
  4. It is never invoked during FastAPI startup lifespan (`api/main.py:28-40`), worker initialization (`scripts/core/worker.py`), or pipeline execution (`scripts/pipeline.py`).
- **Evidence Standard**: `CODE_PROVEN`.

### Check P: Do `CapabilityRouter` and `ToolGateway` receive real product requests?
- **Reality Finding**: **NO**.
- **Evidence Citation**: `api/main.py:57-69`, `ai/routing/capability_router.py:88-120`, `ai/tools/gateway.py:258-310`.
- **Proof**:
  1. All 53 production API endpoints in `api/main.py` route directly to deterministic domain services (`RunService`, `AuthoringService`, `AssetService`, `ProjectService`, `OutputService`, `ReviewService`).
  2. None of these services dispatch requests to `CapabilityRouter` or `ToolGateway`.
  3. Invocations of `CapabilityRouter.dispatch()` and `ToolGateway.execute()` are confined strictly to unit and integration test suites (`tests/ai/routing/test_capability_router.py`, `tests/ai/tools/test_tool_gateway.py`, `tests/ai/e2e/test_s28_m11_product_e2e_matrix.py`).
- **Evidence Standard**: `CODE_PROVEN`.

### Check Q: Does `ModelRouter` receive real product requests?
- **Reality Finding**: **NO**.
- **Evidence Citation**: `api/main.py:57-69`, `ai/routing/router.py:67-130`, `.agents/plugins/super-video-maker-plugin/tools/elevenlabs_voice.py:60-85`.
- **Proof**:
  1. Neither the HTTP API nor the pipeline worker routes any request to `ModelRouter`.
  2. Legacy tool scripts in `.agents/plugins/.../tools/` have runtime blockers that raise `RuntimeError("DIRECT PROVIDER EXECUTION BLOCKED... Use canonical S27 speech capability adapters and ModelRouter")`.
  3. However, no production path dispatches to `ModelRouter` to execute models in production.
- **Evidence Standard**: `CODE_PROVEN`.

---

## 4. Summary Matrix of Bootstrap & Wiring Truth

| Subsystem | Constructor Injected Parameters | In-Code Defaults / Fallbacks | Production Instantiation Reality | Test Wiring Reality |
|---|---|---|---|---|
| **`ContextBuilder`** | 9 optional parameters (retrievers, policies, estimators) | `DeterministicKnowledgeRetriever`, `DeterministicTokenEstimator`, `DeterministicContextCompressor` | **None** (`UNREACHABLE_FROM_PRODUCT`) | In-memory mocks / fakes |
| **`KnowledgeRouter`** | 5 optional parameters (registry, indexer, loader, scorer, root) | `KnowledgeRegistry()`, `KnowledgeIndexer()`, `KnowledgeLoader(Path.cwd())` | **None** (`UNREACHABLE_FROM_PRODUCT`) | Eval runner & unit tests |
| **`KnowledgeRegistry`** | 0 parameters | Empty dictionaries | **None** (`UNREACHABLE_FROM_PRODUCT`) | In-memory instances |
| **`SkillRegistry`** | 0 parameters | Empty dictionaries | **None** (`UNREACHABLE_FROM_PRODUCT`) | In-memory instances |
| **`RecipeRegistry`** | `recipe_dir`, `auto_load=True` | `Path("recipes")`, scans `*.json` | **None** (`UNREACHABLE_FROM_PRODUCT`) | In-memory instances |
| **`ModelRouter`** | 4 optional parameters (registries, policy) | `get_model_registry()`, `get_provider_registry()`, `get_capability_registry()` | **None** (`UNREACHABLE_FROM_PRODUCT`) | In-memory instances |
| **`ProviderRegistry`** | 0 parameters | `CANONICAL_PROVIDERS` (frozen) | **None** (`UNREACHABLE_FROM_PRODUCT`) | Singleton frozen registry |
| **`CapabilityRouter`** | 4 optional parameters (catalog, gateway, seam, router) | `get_capability_catalog()`, `ToolGateway()`, `ModelRouter()`, `ModelRouterSeam()` | **None** (`UNREACHABLE_FROM_PRODUCT`) | In-memory instances |
| **`ToolGateway`** | 3 optional parameters (catalog, registry, store) | `get_capability_catalog()`, `get_adapter_registry()`, `_default_idempotency_store` | **None** (`UNREACHABLE_FROM_PRODUCT`) | In-memory instances |
| **`ToolRegistry`** | 0 parameters | Empty thread-safe dictionary | **None** (`UNREACHABLE_FROM_PRODUCT`) | In-memory instances |
| **`CreativePlanner`** | `planner_version="1.0.0"` | Fails closed on unresolved conflicts | **None** (`UNREACHABLE_FROM_PRODUCT`) | In-memory instances |
| **`NarrativePlanner`**| `knowledge_router=None`, `skill_router=None` | Static rule heuristics | **None** (`UNREACHABLE_FROM_PRODUCT`) | In-memory instances |
| **`TasteEngine`** | 2 optional parameters (registry, evaluator) | `TasteRuleRegistry()`, `TasteEvaluator()` | **None** (`UNREACHABLE_FROM_PRODUCT`) | In-memory instances |
| **`MemoryService`** | 4 parameters (repo, provider, clock, policy) | `SystemClock()` | **None** (`UNREACHABLE_FROM_PRODUCT`) | In-memory fakes |


---


<a name='part-3-source-of-truth--canonical-authority-matrix'></a>

## Part 3: Source of Truth & Canonical Authority Matrix


> *Original Source: `documentation/reality_context_pack/05_SOURCE_OF_TRUTH_AND_AUTHORITY_MATRIX.md`*


### Sub-Report Title: Source of Truth and Authority Matrix Reality Report


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


---


<a name='part-4-dataflow-persistence--artifact-lineage'></a>

## Part 4: Dataflow, Persistence & Artifact Lineage


> *Original Source: `documentation/reality_context_pack/13_DATAFLOW_PERSISTENCE_AND_ARTIFACT_LINEAGE.md`*


### Sub-Report Title: Dataflow, Persistence & Artifact Lineage Reality Report

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


---

