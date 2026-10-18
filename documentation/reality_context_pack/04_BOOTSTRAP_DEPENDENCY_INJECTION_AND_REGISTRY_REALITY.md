# Bootstrap, Dependency Injection and Registry Reality Report

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
