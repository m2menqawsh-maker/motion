# S28-H01 — AI Top-Level Package Inventory & Ownership Record

> **Milestone:** S28-H01 (AI Package Ownership, Dependency & Duplication Audit)  
> **Workspace:** `motion / clean-video-workspace`  
> **Date:** 2026-10-03  
> **Status:** AUDIT COMPLETED — ZERO EXECUTABLE CODE MODIFICATIONS  
> **Total Top-Level Packages in `ai/`:** 36

---

## 1. Executive Summary & Inventory Statistics

A full structural inspection of `ai/` identified **36 top-level packages**. Every package was systematically audited across 20 canonical architectural criteria, including responsibilities, authorities, public APIs, consumers, dependencies, state/I/O ownership, runtime reachability, and layer classifications.

### Summary Metrics

| Metric | Value |
| :--- | :--- |
| **Total Top-Level Packages** | 36 |
| **Total Python Files in `ai/`** | 291 |
| **Total Contract Models & Classes** | ~630 |
| **Inherited Verified Green Tests** | 1,366 passed in `tests/ai/` |
| **Network Calls Allowed** | Exactly 1 package (`ai/providers/openrouter.py`) |
| **Raw DB Drivers / SQL Queries in `ai/`** | Exactly 0 (Strict compliance with ADR-004 DEC-01) |
| **Filesystem Write Operations in `ai/`** | 2 packages only (Evaluation/Regression report writing) |

### Layer Distribution

| Architectural Layer | Package Count | Packages |
| :--- | :---: | :--- |
| **CREATIVE_INTELLIGENCE** | 11 | `conflict`, `directors`, `feedback`, `intent`, `knowledge`, `narrative`, `planning`, `recipes`, `skills`, `style`, `taste` |
| **AI_RUNTIME** | 5 | `batch`, `context`, `orchestration`, `prompts`, `routing` |
| **MODEL_PLATFORM** | 2 | `models`, `providers` |
| **CAPABILITY_PLATFORM** | 3 | `capabilities`, `specialized`, `tools` |
| **DOMAIN_SERVICE** | 4 | `audio`, `media`, `memory`, `speech`, `vision` *(Note: audio/vision span Domain/Creative)* |
| **GOVERNANCE** | 2 | `budget`, `candidates` |
| **OBSERVABILITY** | 2 | `cost`, `observability` |
| **EVALUATION** | 2 | `evals`, `regression` |
| **CROSS_CUTTING_PLATFORM** | 3 | `cache`, `contracts`, `security` |
| **INTEGRATION** | 1 | `mcp` |
| **LEGACY_COMPATIBILITY** | 0 | *(Retired in S28-08E)* |
| **UNCLEAR** | 0 | *(All 36 definitively mapped)* |

---

## 2. Top-Level Package Ownership Records

Below is the definitive, evidence-backed architectural record for all 36 top-level packages under `ai/`.

---

### 1. `ai/audio`
- **primary_responsibility:** Native digital signal processing (DSP), audio quality metrics (SNR, clipping), audio mode policy enforcement (`SILENT`, `MUSIC_ONLY`, `SPEECH_WITH_BGM`), and audio intelligence benchmarking.
- **architectural_layer:** `DOMAIN_SERVICE` / `CREATIVE_INTELLIGENCE`
- **canonical_authority:** `AudioModeEngine` (`ai/audio/modes.py`), `NativeAudioDSP` (`ai/audio/dsp.py`), `AudioIntelligencePipeline` (`ai/audio/pipeline.py`).
- **public_api:** `AudioModeEngine`, `AudioModePolicy`, `NativeAudioDSP`, `AudioIntelligencePipeline`, `AudioBenchmarkRunner`.
- **main_consumers[]:** `ai/recipes/`, `ai/media/`, `ai/planning/validator.py`, `scripts/run_creative_e2e.py`, `tests/ai/audio/`.
- **main_dependencies[]:** `ai/contracts/`, `ai/cache/`.
- **reverse_dependencies[]:** `ai/media/`, `ai/recipes/`.
- **owns_state?:** No (stateless DSP compute and policy validation).
- **owns_database?:** No.
- **owns_filesystem?:** Read-only inspection of audio byte buffers / fixtures.
- **owns_network_calls?:** No.
- **owns_provider_selection?:** No.
- **owns_authorization?:** No (enforces audio policy invariants, not security authorization).
- **owns_lifecycle_transition?:** No.
- **owns_evaluation?:** Yes, for native audio benchmarks (`AudioBenchmarkRunner`).
- **runtime_reachable?:** Yes.
- **test_only?:** No.
- **legacy?:** No.
- **candidate_target_layer:** `DOMAIN_SERVICE`
- **notes:** Cleanly separates native DSP and audio policy from cloud speech recognition (which lives in `ai/speech`).

---

### 2. `ai/batch`
- **primary_responsibility:** Authoritative coordinator for asynchronous batch, bulk, and background AI execution workloads. Enforces execution class boundaries (`INTERACTIVE` vs `BACKGROUND` vs `BATCH`), routes batch tasks to bulk-eligible models, coordinates durable leases, and handles batch cache re-use.
- **architectural_layer:** `AI_RUNTIME`
- **canonical_authority:** `BatchExecutionService` (`ai/batch/service.py`), `BatchPolicy` (`ai/batch/policy.py`).
- **public_api:** `BatchExecutionService`, `ForbiddenBatchRouteError`, `get_execution_policy`.
- **main_consumers[]:** Background worker pipelines, bulk generation scripts, `tests/ai/batch/`.
- **main_dependencies[]:** `ai/budget/`, `ai/cache/`, `ai/contracts/`, `ai/models/`, `ai/orchestration/`, `ai/routing/`.
- **reverse_dependencies[]:** None.
- **owns_state?:** No (delegates run and step persistence to `ai/orchestration`).
- **owns_database?:** No (uses abstract repositories).
- **owns_filesystem?:** No.
- **owns_network_calls?:** No.
- **owns_provider_selection?:** Coordinates with `ai/routing/` to enforce batch eligibility.
- **owns_authorization?:** No.
- **owns_lifecycle_transition?:** Yes, coordinates batch run status transitions via `AIRunService`.
- **owns_evaluation?:** No.
- **runtime_reachable?:** Yes.
- **test_only?:** No.
- **legacy?:** No.
- **candidate_target_layer:** `AI_RUNTIME`
- **notes:** Reuses existing platform primitives (Orchestration, Budget, Cache, Router) rather than duplicating them.

---

### 3. `ai/budget`
- **primary_responsibility:** Multi-tenant financial limit enforcement, pre-execution budget reservation, currency/credit accounting, and hard expenditure blocking.
- **architectural_layer:** `GOVERNANCE`
- **canonical_authority:** `BudgetService` (`ai/budget/service.py`), `ReservationEngine` (`ai/budget/reservation.py`), `AccountingEngine` (`ai/budget/accounting.py`).
- **public_api:** `BudgetService`, `BudgetRepository`, `InMemoryBudgetRepository`, `ReservationRequest`, `ReservationResult`, `CostProfileConfig`.
- **main_consumers[]:** `ai/batch/`, `ai/orchestration/`, `ai/specialized/`, `tests/ai/budget/`.
- **main_dependencies[]:** `ai/contracts/`, `ai/models/`, `ai/routing/`.
- **reverse_dependencies[]:** `ai/batch/`, `ai/specialized/`.
- **owns_state?:** Yes (in-memory or staged reservation balances).
- **owns_database?:** Abstract interface (`BudgetRepository`); concrete SQL repository in `scripts/core/`.
- **owns_filesystem?:** No.
- **owns_network_calls?:** No.
- **owns_provider_selection?:** No.
- **owns_authorization?:** Yes (financial gate authorization: permits or blocks AI invocation based on tenant wallet).
- **owns_lifecycle_transition?:** Yes (reservation states: `RESERVED` -> `SETTLED` / `RELEASED` / `EXPIRED`).
- **owns_evaluation?:** No.
- **runtime_reachable?:** Yes.
- **test_only?:** No.
- **legacy?:** No.
- **candidate_target_layer:** `GOVERNANCE` / `PLATFORM`
- **notes:** Distinct from `ai/cost`: `budget` enforces spend limits before execution; `cost` measures and audits actual efficiency post-execution.

---

### 4. `ai/cache`
- **primary_responsibility:** Multi-tenant, deterministic semantic and exact-match caching for AI model responses, media intelligence analyses, and execution DAG steps.
- **architectural_layer:** `CROSS_CUTTING_PLATFORM`
- **canonical_authority:** `AICacheService` (`ai/cache/service.py`), `derive_canonical_cache_key` (`ai/cache/key.py`).
- **public_api:** `AICacheService`, `AICacheRepository`, `derive_canonical_cache_key`, `SemanticCacheMatcher`.
- **main_consumers[]:** `ai/audio/`, `ai/batch/`, `ai/media/`, `ai/specialized/`, `ai/vision/`, `scripts/core/ai_cache_repository.py`.
- **main_dependencies[]:** `ai/capabilities/`, `ai/contracts/`, `ai/orchestration/`.
- **reverse_dependencies[]:** `ai/audio/`, `ai/batch/`, `ai/media/`, `ai/specialized/`, `ai/vision/`.
- **owns_state?:** Yes (cache entries and key indexes).
- **owns_database?:** Abstract repository boundary (`AICacheRepository`); concrete SQLite/PostgreSQL in `scripts/core/ai_cache_repository.py`.
- **owns_filesystem?:** No.
- **owns_network_calls?:** No.
- **owns_provider_selection?:** No.
- **owns_authorization?:** No (validates tenant isolation: Tenant A cannot read Tenant B cache).
- **owns_lifecycle_transition?:** No.
- **owns_evaluation?:** No.
- **runtime_reachable?:** Yes.
- **test_only?:** No.
- **legacy?:** No.
- **candidate_target_layer:** `PLATFORM`
- **notes:** High fan-in infrastructure component. Candidate for migration to `platform/cache` in platform reorganization.

---

### 5. `ai/candidates` (Migrated to `creative_governance/candidates` in S28-H03)
- **primary_responsibility:** Multi-stage governance, static AST security validation, hermetic Remotion runtime QC rendering, and human review/approval workflows for AI-generated template candidates.
- **architectural_layer:** `CREATIVE_GOVERNANCE` (Canonical implementation in `creative_governance/candidates/`; `ai/candidates/` retained as thin backward-compatible re-export facade).
- **canonical_authority:** `TemplateCandidateService` (`creative_governance/candidates/service.py`), `CandidateValidationService` (`creative_governance/candidates/validation_service.py`), `CandidateReviewService` (`creative_governance/candidates/review_service.py`), `PromotionService` (`creative_governance/candidates/promotion_service.py`).
- **public_api:** `TemplateCandidateService`, `CandidateValidationService`, `CandidateReviewService`, `PromotionService`, `TemplateCandidateRepository`.
- **main_consumers[]:** `api/routers/candidate_reviews.py`, `api/routers/candidate_promotions.py`, `scripts/maintenance/promote_template.py`, `scripts/core/template_candidate_repository.py`.
- **main_dependencies[]:** `ai/contracts/`.
- **reverse_dependencies[]:** None within `ai/` (strictly consumed by API routers and maintenance scripts).
- **owns_state?:** Yes (governs candidate status: `DRAFT` -> `VALIDATED` -> `UNDER_REVIEW` -> `APPROVED` -> `PROMOTED`).
- **owns_database?:** Abstract interface (`TemplateCandidateRepository`); concrete SQL in `scripts/core/template_candidate_repository.py`.
- **owns_filesystem?:** No direct raw file mutation (delegates staging and atomic publication to `scripts/core/template_registry_publisher.py`).
- **owns_network_calls?:** No.
- **owns_provider_selection?:** No.
- **owns_authorization?:** Yes (enforces separation of duties: AI cannot approve candidates; human reviewer required; creator cannot self-approve).
- **owns_lifecycle_transition?:** Yes (governs template candidate lifecycle).
- **owns_evaluation?:** Yes, static security AST and Remotion runtime QC rendering gates.
- **runtime_reachable?:** Yes (via API routes).
- **test_only?:** No.
- **legacy?:** No (`ai/candidates/` is a thin facade; canonical package is `creative_governance/candidates/`).
- **candidate_target_layer:** `CREATIVE_GOVERNANCE` (REMEDIATED in S28-H03).
- **notes:** S28-07 foundation. Functionally is Template Governance rather than AI inference. Relocated to `creative_governance/candidates` in S28-H03.

---

### 6. `ai/capabilities`
- **primary_responsibility:** Canonical registry and typed definitions for platform capabilities (e.g., `text_to_speech`, `asset_management`, `smart_qc`, `speech_to_text`), specifying privacy class, caching policy, and cost units.
- **architectural_layer:** `CAPABILITY_PLATFORM`
- **canonical_authority:** `CapabilityRegistry` (`ai/capabilities/registry.py`), `CapabilityDefinition` (`ai/capabilities/types.py`).
- **public_api:** `CapabilityRegistry`, `CapabilityDefinition`, `get_capability_registry`, `create_empty_capability_registry`.
- **main_consumers[]:** `ai/cache/`, `ai/models/`, `ai/routing/`, `ai/specialized/`, `tests/ai/capabilities/`.
- **main_dependencies[]:** `ai/contracts/`.
- **reverse_dependencies[]:** `ai/cache/`, `ai/models/`, `ai/routing/`, `ai/specialized/`.
- **owns_state?:** In-memory registry state.
- **owns_database?:** No.
- **owns_filesystem?:** No.
- **owns_network_calls?:** No.
- **owns_provider_selection?:** No.
- **owns_authorization?:** No.
- **owns_lifecycle_transition?:** No.
- **owns_evaluation?:** No.
- **runtime_reachable?:** Yes.
- **test_only?:** No.
- **legacy?:** No.
- **candidate_target_layer:** `CAPABILITY_PLATFORM`
- **notes:** Core focus of S28-M modernization.

---

### 7. `ai/conflict`
- **primary_responsibility:** Creative contradiction detection and deterministic precedence resolution across user explicit requirements, brand guidelines, creative director recommendations, and taste rules.
- **architectural_layer:** `CREATIVE_INTELLIGENCE`
- **canonical_authority:** `ConflictResolver` (`ai/conflict/resolver.py`).
- **public_api:** `ConflictResolver`.
- **main_consumers[]:** `ai/evals/creative_evals_s28_04.py`, `ai/taste/engine.py`, `tests/ai/creative/`.
- **main_dependencies[]:** `ai/contracts/`.
- **reverse_dependencies[]:** `ai/evals/`.
- **owns_state?:** No (pure deterministic resolution function).
- **owns_database?:** No.
- **owns_filesystem?:** No.
- **owns_network_calls?:** No.
- **owns_provider_selection?:** No.
- **owns_authorization?:** No.
- **owns_lifecycle_transition?:** No.
- **owns_evaluation?:** No (provides guidance, zero QC approval authority).
- **runtime_reachable?:** Yes.
- **test_only?:** No.
- **legacy?:** No.
- **candidate_target_layer:** `CREATIVE_INTELLIGENCE`
- **notes:** Small 2-file package representing a pure arbitration boundary.

---

### 8. `ai/context`
- **primary_responsibility:** Bounded context assembly, multi-source retrieval (memory, project state, system policy), token budget management, ranking, deduplication, and deterministic context compression for inference requests.
- **architectural_layer:** `AI_RUNTIME`
- **canonical_authority:** `ContextBuilder` (`ai/context/builder.py`), `ContextAssembler` (`ai/context/assembly.py`), `ContextBudgetManager` (`ai/context/budgeting.py`).
- **public_api:** `ContextBuilder`, `ContextAssembler`, `ContextBudgetManager`, `ContextPackage`, `ContextRequest`.
- **main_consumers[]:** Pipeline execution runners, `tests/ai/context/`.
- **main_dependencies[]:** `ai/contracts/`, `ai/memory/`.
- **reverse_dependencies[]:** None.
- **owns_state?:** No (ephemeral request assembly).
- **owns_database?:** No.
- **owns_filesystem?:** No.
- **owns_network_calls?:** No.
- **owns_provider_selection?:** No.
- **owns_authorization?:** Validates tenant project access (`ProjectAccessDeniedError`).
- **owns_lifecycle_transition?:** No.
- **owns_evaluation?:** No.
- **runtime_reachable?:** Yes.
- **test_only?:** No.
- **legacy?:** No.
- **candidate_target_layer:** `AI_RUNTIME`
- **notes:** Rigorously enforces `Memory ≠ Context` invariant (ephemeral bounded packaging vs persisted storage).

---

### 9. `ai/contracts`
- **primary_responsibility:** Canonical typed schema definitions (Pydantic v2) for all AI and Creative Intelligence operations, ensuring JSON Schema and TypeScript parity across the workspace.
- **architectural_layer:** `CROSS_CUTTING_PLATFORM`
- **canonical_authority:** Single source of truth for contracts (`ai/contracts/`).
- **public_api:** Complete contract suite (Media, Common, Creative, Specialized, Tools, Models, Routing, Errors).
- **main_consumers[]:** 33 out of 36 `ai/` packages, API routers, scripts, tests.
- **main_dependencies[]:** `ai/memory/types.py` (anomalous inverted import in `creative/feedback.py`).
- **reverse_dependencies[]:** 33 packages.
- **owns_state?:** No (stateless schema definitions).
- **owns_database?:** No.
- **owns_filesystem?:** No.
- **owns_network_calls?:** No.
- **owns_provider_selection?:** No.
- **owns_authorization?:** No.
- **owns_lifecycle_transition?:** No.
- **owns_evaluation?:** No.
- **runtime_reachable?:** Yes.
- **test_only?:** No.
- **legacy?:** No.
- **candidate_target_layer:** `CROSS_CUTTING_PLATFORM`
- **notes:** Foundation layer. Needs removal of inverted dependency on `ai/memory/types.py` in H02.

---

### 10. `ai/cost`
- **primary_responsibility:** Multi-tenant creative cost observability, token accounting, provenance tracking (`ACTUAL` vs `ESTIMATED` vs `UNKNOWN`), format efficiency baselines, and waste detection.
- **architectural_layer:** `OBSERVABILITY`
- **canonical_authority:** `TokenAccounting` (`ai/cost/accounting.py`), `CreativeCostEstimator` (`ai/cost/accounting.py`), `CreativeEfficiencyAnalyzer` (`ai/cost/analyzer.py`).
- **public_api:** `TokenAccounting`, `CreativeCostEstimator`, `CreativeEfficiencyAnalyzer`, `FormatBaseline`, `CreativeUsageCollector`.
- **main_consumers[]:** `scripts/run_creative_cost_audit.py`, `ai/regression/runner.py`, `tests/ai/cost/`.
- **main_dependencies[]:** `ai/contracts/`, `ai/memory/`, `ai/models/`, `ai/observability/`, `ai/routing/`.
- **reverse_dependencies[]:** None.
- **owns_state?:** No (read-only observer re-using `TraceRepository`).
- **owns_database?:** No.
- **owns_filesystem?:** No.
- **owns_network_calls?:** No.
- **owns_provider_selection?:** No.
- **owns_authorization?:** Enforces multi-tenant read authorization (`TenantAuthorizationError`).
- **owns_lifecycle_transition?:** No.
- **owns_evaluation?:** Evaluates pipeline efficiency and detects waste. Zero runtime execution authority.
- **runtime_reachable?:** Yes.
- **test_only?:** No.
- **legacy?:** No.
- **candidate_target_layer:** `OBSERVABILITY`
- **notes:** S28-08C delivery. Pure observability invariant strictly upheld.

---

### 11. `ai/directors`
- **primary_responsibility:** Domain-specific creative directors providing expert advisory feedback: Rhythm & Energy, Typography & Layout, Visual Style, and Narrative.
- **architectural_layer:** `CREATIVE_INTELLIGENCE`
- **canonical_authority:** `BaseCreativeDirector` (`ai/directors/base.py`) and specialized director classes.
- **public_api:** `EnergyDirector`, `TypographyDirector`, `VisualDirector`, `NarrativeDirector`, `DirectorRecommendationBundle`.
- **main_consumers[]:** `ai/evals/creative_evals_s28_04.py`, `ai/taste/engine.py`, `tests/ai/creative/`.
- **main_dependencies[]:** `ai/contracts/`.
- **reverse_dependencies[]:** `ai/evals/`.
- **owns_state?:** No.
- **owns_database?:** No.
- **owns_filesystem?:** No.
- **owns_network_calls?:** No.
- **owns_provider_selection?:** No.
- **owns_authorization?:** No.
- **owns_lifecycle_transition?:** No.
- **owns_evaluation?:** Advisory aesthetic guidance; zero QC approval authority.
- **runtime_reachable?:** Yes.
- **test_only?:** No.
- **legacy?:** No.
- **candidate_target_layer:** `CREATIVE_INTELLIGENCE`
- **notes:** Cleanly isolated advisory intelligence agents.

---

### 12. `ai/evals`
- **primary_responsibility:** Platform-level AI evaluation infrastructure: test runner (`EvalRunner`), quality gates (`CIEvalGate`), model promotion engine (`ModelPromotionEngine`), and benchmark evaluation datasets.
- **architectural_layer:** `EVALUATION`
- **canonical_authority:** `EvalRunner` (`ai/evals/runner.py`), `CIEvalGate` (`ai/evals/gate.py`).
- **public_api:** `EvalRunner`, `CIEvalGate`, `ModelPromotionEngine`, `EvaluatorBase`, `get_dataset`.
- **main_consumers[]:** `ai/regression/`, CI gate checks, `tests/ai/evals/`.
- **main_dependencies[]:** `ai/conflict/`, `ai/contracts/`, `ai/directors/`, `ai/narrative/`, `ai/planning/`, `ai/prompts/`, `ai/taste/`.
- **reverse_dependencies[]:** `ai/regression/`.
- **owns_state?:** No.
- **owns_database?:** No.
- **owns_filesystem?:** Writes evaluation report JSON artifacts (`mkdir` / write).
- **owns_network_calls?:** No.
- **owns_provider_selection?:** No.
- **owns_authorization?:** No.
- **owns_lifecycle_transition?:** Evaluates model promotion eligibility.
- **owns_evaluation?:** Core evaluation platform.
- **runtime_reachable?:** No (CI/evaluation only).
- **test_only?:** Yes (Evaluation & benchmarking).
- **legacy?:** Contains milestone-specific legacy evaluation files (`creative_evals_s28_04.py`, etc.) that need pruning in H02.
- **candidate_target_layer:** `EVALUATION`
- **notes:** Overlaps with `ai/regression/` due to milestone eval scripts retained from S28-02..S28-06.

---

### 13. `ai/feedback`
- **primary_responsibility:** Multi-category creative feedback classification (Pacing, Color, Typography, Concept) and preference learning loop.
- **architectural_layer:** `CREATIVE_INTELLIGENCE`
- **canonical_authority:** `CreativeFeedbackClassifier` (`ai/feedback/classifier.py`), `FeedbackLearningService` (`ai/feedback/service.py`).
- **public_api:** `CreativeFeedbackClassifier`, `FeedbackLearningService`, `CreativeFeedbackAnalysis`.
- **main_consumers[]:** `ai/regression/runner.py`, `tests/ai/creative/`.
- **main_dependencies[]:** `ai/contracts/`, `ai/memory/`.
- **reverse_dependencies[]:** `ai/regression/`.
- **owns_state?:** No (persists preference updates to `ai/memory`).
- **owns_database?:** No.
- **owns_filesystem?:** No.
- **owns_network_calls?:** No.
- **owns_provider_selection?:** No.
- **owns_authorization?:** No.
- **owns_lifecycle_transition?:** No.
- **owns_evaluation?:** No.
- **runtime_reachable?:** Yes.
- **test_only?:** No.
- **legacy?:** No.
- **candidate_target_layer:** `CREATIVE_INTELLIGENCE`
- **notes:** S28-08A deliverable; manages the human-in-the-loop stylistic adjustment loop.

---

### 14. `ai/intent`
- **primary_responsibility:** Multilingual natural language intent parsing into typed `CreativeBrief` with field-level epistemic provenance (`EXPLICIT`, `INFERRED`, `DEFAULTED`) and contradiction detection.
- **architectural_layer:** `CREATIVE_INTELLIGENCE`
- **canonical_authority:** `IntentParser` (`ai/intent/parser.py`), `BriefBuilder` (`ai/intent/brief_builder.py`).
- **public_api:** `IntentParser`, `BriefBuilder`, `ContradictionDetector`.
- **main_consumers[]:** `ai/recipes/`, `ai/regression/`, `ai/planning/creative_planner.py`.
- **main_dependencies[]:** `ai/contracts/`.
- **reverse_dependencies[]:** `ai/recipes/`, `ai/regression/`.
- **owns_state?:** No.
- **owns_database?:** No.
- **owns_filesystem?:** No.
- **owns_network_calls?:** No (LLM calls dispatched via external adapters if enabled; rule engine is local).
- **owns_provider_selection?:** No.
- **owns_authorization?:** No.
- **owns_lifecycle_transition?:** No.
- **owns_evaluation?:** No.
- **runtime_reachable?:** Yes.
- **test_only?:** No.
- **legacy?:** No.
- **candidate_target_layer:** `CREATIVE_INTELLIGENCE`
- **notes:** S28-03 foundation. Single source of truth for intent interpretation.

---

### 15. `ai/knowledge`
- **primary_responsibility:** Bounded, versioned creative knowledge packages (motion principles, typography guidelines, video formats), indexing, and hybrid (lexical + semantic) retrieval.
- **architectural_layer:** `CREATIVE_INTELLIGENCE`
- **canonical_authority:** `KnowledgeRegistry` (`ai/knowledge/registry.py`), `HybridKnowledgeRetriever` (`ai/knowledge/retriever.py`).
- **public_api:** `KnowledgeRegistry`, `HybridKnowledgeRetriever`, `KnowledgeIndexer`, `KnowledgeLoader`.
- **main_consumers[]:** `ai/narrative/`, `ai/skills/`, `ai/regression/`, `ai/planning/`.
- **main_dependencies[]:** `ai/contracts/`.
- **reverse_dependencies[]:** `ai/narrative/`, `ai/regression/`, `ai/skills/`.
- **owns_state?:** In-memory knowledge registry and vector index.
- **owns_database?:** No.
- **owns_filesystem?:** Loads static markdown/json knowledge files.
- **owns_network_calls?:** No.
- **owns_provider_selection?:** No.
- **owns_authorization?:** No.
- **owns_lifecycle_transition?:** No.
- **owns_evaluation?:** No (Knowledge ≠ Authority: contextual advice only, cannot grant QC or bypass limits).
- **runtime_reachable?:** Yes.
- **test_only?:** No.
- **legacy?:** No.
- **candidate_target_layer:** `CREATIVE_INTELLIGENCE`
- **notes:** S28-02 foundation.

---

### 16. `ai/mcp`
- **primary_responsibility:** Model Context Protocol (MCP) server catalog, security sandboxing policy (path traversal defense, shell injection defense, tool permissions), and media adapter tools (audio/video/image trimming, normalization, resizing).
- **architectural_layer:** `INTEGRATION` / `CAPABILITY_PLATFORM`
- **canonical_authority:** `MCPSecurityPolicy` (`ai/mcp/policy.py`), `MCPCatalog` (`ai/mcp/catalog.py`), `BaseMCPAdapter` (`ai/mcp/adapters/base.py`).
- **public_api:** `MCPSecurityPolicy`, `MCPCatalog`, `MCPAuditRecorder`, adapters (`AudioTrimAdapter`, `VideoTrimAdapter`, etc.).
- **main_consumers[]:** Tool integration pipelines, `tests/ai/mcp/`.
- **main_dependencies[]:** `ai/contracts/`, `ai/tools/`.
- **reverse_dependencies[]:** None.
- **owns_state?:** In-memory catalog state.
- **owns_database?:** No.
- **owns_filesystem?:** Unlinks temporary media files in adapters (`BaseMCPAdapter.unlink`).
- **owns_network_calls?:** May communicate with external MCP processes via stdio/HTTP.
- **owns_provider_selection?:** No.
- **owns_authorization?:** Yes (`MCPSecurityPolicy` validates tool invocation permissions and security rules).
- **owns_lifecycle_transition?:** No.
- **owns_evaluation?:** No.
- **runtime_reachable?:** Yes.
- **test_only?:** No.
- **legacy?:** No.
- **candidate_target_layer:** `CAPABILITY_PLATFORM` / `INTEGRATION`
- **notes:** FROZEN in H01. Modernization deferred to S28-M.

---

### 17. `ai/media`
- **primary_responsibility:** Multi-modal media intelligence service: combines deterministic technical container probing (`TechnicalMediaProbe`) with AI speech recognition and audio/vision analysis, caching reports in `AICacheService`.
- **architectural_layer:** `DOMAIN_SERVICE` / `AI_RUNTIME`
- **canonical_authority:** `MediaIntelligenceService` (`ai/media/service.py`), `TechnicalMediaProbe` (`ai/media/technical_probe.py`).
- **public_api:** `MediaIntelligenceService`, `TechnicalMediaProbe`, `MediaIntelligenceRepository`, `validate_media_intelligence`.
- **main_consumers[]:** `api/services/asset_service.py`, `tests/ai/media/`.
- **main_dependencies[]:** `ai/audio/`, `ai/cache/`, `ai/contracts/`, `ai/providers/`, `ai/routing/`, `ai/speech/`, `ai/vision/`.
- **reverse_dependencies[]:** None.
- **owns_state?:** No (delegates storage of reports to `StorageService` and indexing to `MediaIntelligenceRepository`).
- **owns_database?:** Abstract repository boundary (`MediaIntelligenceRepository`); concrete SQL in `scripts/core/`.
- **owns_filesystem?:** Reads wave headers/byte streams in memory.
- **owns_network_calls?:** No.
- **owns_provider_selection?:** Uses `ai/routing/` for AI speech/vision provider calls.
- **owns_authorization?:** Validates tenant workspace boundary.
- **owns_lifecycle_transition?:** No.
- **owns_evaluation?:** Semantic validation of media reports (`validate_media_intelligence`).
- **runtime_reachable?:** Yes.
- **test_only?:** No.
- **legacy?:** No.
- **candidate_target_layer:** `DOMAIN_SERVICE`
- **notes:** High fan-out coordinator bridging raw assets, technical DSP, and multi-modal AI intelligence.

---

### 18. `ai/memory`
- **primary_responsibility:** Long-term project and user memory store: tenant isolation, vector embeddings, deduplication, confidence decay, epistemic provenance (`FACT`, `PREFERENCE`, `FEEDBACK`), and retention policies.
- **architectural_layer:** `DOMAIN_SERVICE` / `CROSS_CUTTING_PLATFORM`
- **canonical_authority:** `MemoryService` (`ai/memory/service.py`), `ProjectMemoryFacade` (`ai/memory/facade.py`), `MemoryPolicy` (`ai/memory/policy.py`).
- **public_api:** `MemoryService`, `ProjectMemoryFacade`, `MemoryRepository`, `InMemoryMemoryRepository`, `MemoryEntry`, `TrustedTenantContext`.
- **main_consumers[]:** `ai/context/`, `ai/contracts/`, `ai/cost/`, `ai/feedback/`, `ai/planning/`, `ai/regression/`, `ai/style/`.
- **main_dependencies[]:** None (pure domain foundation).
- **reverse_dependencies[]:** 7 packages (`context`, `contracts`, `cost`, `feedback`, `planning`, `regression`, `style`).
- **owns_state?:** Yes (persisted memory entries and embeddings).
- **owns_database?:** Abstract interface (`MemoryRepository`); concrete SQLite in `scripts/core/memory/sqlite_repository.py`.
- **owns_filesystem?:** No.
- **owns_network_calls?:** No.
- **owns_provider_selection?:** No.
- **owns_authorization?:** Yes (`TenantAuthorizationError` enforces tenant boundaries).
- **owns_lifecycle_transition?:** Governs memory entry confidence and decay states.
- **owns_evaluation?:** No.
- **runtime_reachable?:** Yes.
- **test_only?:** No.
- **legacy?:** No.
- **candidate_target_layer:** `DOMAIN_SERVICE`
- **notes:** High fan-in memory domain service.

---

### 19. `ai/models`
- **primary_responsibility:** Canonical model definitions (`ModelDefinition`), pricing metadata (`ModelPricing`), cost/latency tiers (`CostTier`, `LatencyTier`), and model catalog management (`ModelRegistry`).
- **architectural_layer:** `MODEL_PLATFORM`
- **canonical_authority:** `ModelRegistry` (`ai/models/registry.py`), `CANONICAL_MODELS_LIST` (`ai/models/definitions.py`).
- **public_api:** `ModelRegistry`, `ModelDefinition`, `ModelPricing`, `CostTier`, `LatencyTier`, `get_model_registry`.
- **main_consumers[]:** `ai/batch/`, `ai/budget/`, `ai/cost/`, `ai/providers/`, `ai/routing/`.
- **main_dependencies[]:** `ai/capabilities/`, `ai/contracts/`, `ai/providers/` *(circular cycle)*.
- **reverse_dependencies[]:** `ai/batch/`, `ai/budget/`, `ai/cost/`, `ai/providers/`, `ai/routing/`.
- **owns_state?:** In-memory catalog of models.
- **owns_database?:** No.
- **owns_filesystem?:** No.
- **owns_network_calls?:** No.
- **owns_provider_selection?:** No.
- **owns_authorization?:** No.
- **owns_lifecycle_transition?:** No.
- **owns_evaluation?:** No.
- **runtime_reachable?:** Yes.
- **test_only?:** No.
- **legacy?:** No.
- **candidate_target_layer:** `MODEL_PLATFORM`
- **notes:** Contains circular dependency with `ai/providers/` (`ai/models/registry.py` imports `ai.providers.registry`, while `ai/providers/openrouter.py` imports `ai.models.registry`). Must be decoupled in H02.

---

### 20. `ai/narrative`
- **primary_responsibility:** Story structure and narrative planning: 3-Act, Hook-Proof-CTA, and PAS arcs, pacing curves, and beat sheet generation.
- **architectural_layer:** `CREATIVE_INTELLIGENCE`
- **canonical_authority:** `NarrativePlanner` (`ai/narrative/planner.py`).
- **public_api:** `NarrativePlanner`, `NarrativeArc`, `PacingProfile`.
- **main_consumers[]:** `ai/planning/creative_planner.py`, `ai/evals/`, `ai/regression/`.
- **main_dependencies[]:** `ai/contracts/`, `ai/knowledge/`, `ai/skills/`.
- **reverse_dependencies[]:** `ai/evals/`, `ai/regression/`.
- **owns_state?:** No.
- **owns_database?:** No.
- **owns_filesystem?:** No.
- **owns_network_calls?:** No.
- **owns_provider_selection?:** No.
- **owns_authorization?:** No.
- **owns_lifecycle_transition?:** No.
- **owns_evaluation?:** Evaluates narrative pacing coherence. Zero QC authority.
- **runtime_reachable?:** Yes.
- **test_only?:** No.
- **legacy?:** No.
- **candidate_target_layer:** `CREATIVE_INTELLIGENCE`
- **notes:** S28-04 deliverable.

---

### 21. `ai/observability`
- **primary_responsibility:** Distributed tracing, OpenTelemetry-compatible spans, telemetry metrics, and PII/secret redaction for AI runs.
- **architectural_layer:** `OBSERVABILITY`
- **canonical_authority:** `AITracer` (`ai/observability/tracer.py`), `AIMetrics` (`ai/observability/metrics.py`), `TraceRepository` (`ai/observability/repository.py`).
- **public_api:** `AITracer`, `AIMetrics`, `TraceRepository`, `redact_sensitive_data`.
- **main_consumers[]:** `ai/cost/`, execution runners, `scripts/core/ai_trace_repository.py`.
- **main_dependencies[]:** `ai/contracts/`.
- **reverse_dependencies[]:** `ai/cost/`.
- **owns_state?:** In-memory active spans.
- **owns_database?:** Abstract interface (`TraceRepository`); concrete SQL in `scripts/core/ai_trace_repository.py`.
- **owns_filesystem?:** No.
- **owns_network_calls?:** OpenTelemetry collector export (if configured).
- **owns_provider_selection?:** No.
- **owns_authorization?:** No.
- **owns_lifecycle_transition?:** No.
- **owns_evaluation?:** No.
- **runtime_reachable?:** Yes.
- **test_only?:** No.
- **legacy?:** No.
- **candidate_target_layer:** `PLATFORM` / `OBSERVABILITY`
- **notes:** Cross-cutting platform telemetry. Candidate for `platform/observability`.

---

### 22. `ai/orchestration`
- **primary_responsibility:** Durable execution runtime for multi-step AI workflows (`AIRun`, `AIStep`), directed acyclic graph (DAG) scheduling, concurrency control, distributed worker leases, and crash recovery.
- **architectural_layer:** `AI_RUNTIME`
- **canonical_authority:** `AIRunService` (`ai/orchestration/service.py`), `AIRecoveryService` (`ai/orchestration/recovery.py`), `AIRunRepository` (`ai/orchestration/repository.py`).
- **public_api:** `AIRunService`, `AIRecoveryService`, `AIRunRepository`, `DAGSpecification`, `StepDefinition`, `AIRun`, `AIStep`.
- **main_consumers[]:** `ai/batch/`, `ai/cache/`, `ai/specialized/`, `scripts/core/ai_run_repository.py`.
- **main_dependencies[]:** `ai/contracts/`.
- **reverse_dependencies[]:** `ai/batch/`, `ai/cache/`, `ai/specialized/`.
- **owns_state?:** Yes (manages lifecycle state machines for `AIRun` and `AIStep`).
- **owns_database?:** Abstract repository boundary (`AIRunRepository`); concrete SQL in `scripts/core/ai_run_repository.py`.
- **owns_filesystem?:** No.
- **owns_network_calls?:** No.
- **owns_provider_selection?:** No.
- **owns_authorization?:** Validates tenant workspace boundary.
- **owns_lifecycle_transition?:** Yes (governs run states: `PENDING` -> `RUNNING` -> `COMPLETED` / `FAILED` / `CANCELLED`).
- **owns_evaluation?:** No.
- **runtime_reachable?:** Yes.
- **test_only?:** No.
- **legacy?:** No.
- **candidate_target_layer:** `AI_RUNTIME`
- **notes:** S27 durable runtime bedrock.

---

### 23. `ai/planning`
- **primary_responsibility:** 3-Tier Creative Planning engine: deterministic tier selection (`CreativeTierPolicy`: REUSE -> COMPOSE -> CREATE), candidate reuse matching (`ReuseEngine`), multi-scene composition assembly (`ComposeEngine`), and semantic plan validation (`CreativePlanValidator`).
- **architectural_layer:** `CREATIVE_INTELLIGENCE`
- **canonical_authority:** `CreativePlanner` (`ai/planning/creative_planner.py`), `CreativeTierPolicy` (`ai/planning/tier_policy.py`), `CreativePlanValidator` (`ai/planning/validator.py`).
- **public_api:** `CreativePlanner`, `CreativeTierPolicy`, `ReuseEngine`, `ComposeEngine`, `CreativePlanValidator`.
- **main_consumers[]:** `ai/evals/`, `ai/regression/`, `scripts/run_creative_e2e.py`.
- **main_dependencies[]:** `ai/contracts/`, `ai/memory/`, `ai/style/`.
- **reverse_dependencies[]:** `ai/evals/`, `ai/regression/`.
- **owns_state?:** No (produces immutable `CreativePlan` proposals).
- **owns_database?:** No.
- **owns_filesystem?:** No.
- **owns_network_calls?:** No direct network calls; calls internal router for LLM calls if needed.
- **owns_provider_selection?:** No (delegates to `ai/routing`).
- **owns_authorization?:** No.
- **owns_lifecycle_transition?:** Yes, controls tier escalation decisions (`REUSE` vs `COMPOSE` vs `CREATE`).
- **owns_evaluation?:** Validates creative plan semantic coherence (`CreativePlanValidator`).
- **runtime_reachable?:** Yes.
- **test_only?:** No.
- **legacy?:** No.
- **candidate_target_layer:** `CREATIVE_INTELLIGENCE`
- **notes:** Invariant `CreativePlan ≠ Blueprint` rigorously enforced; plan output is compiled by `scripts/core/blueprint_compiler.py`.

---

### 24. `ai/prompts`
- **primary_responsibility:** Versioned prompt template repository, variable interpolation, formatting, and prompt retrieval.
- **architectural_layer:** `AI_RUNTIME` / `CROSS_CUTTING_PLATFORM`
- **canonical_authority:** `PromptService` (`ai/prompts/service.py`), `PromptRepository` (`ai/prompts/repository.py`).
- **public_api:** `PromptService`, `PromptRepository`, `InMemoryPromptRepository`.
- **main_consumers[]:** `ai/evals/`, `scripts/core/ai_prompt_repository.py`.
- **main_dependencies[]:** `ai/contracts/`.
- **reverse_dependencies[]:** `ai/evals/`.
- **owns_state?:** In-memory prompt template store.
- **owns_database?:** Abstract interface (`PromptRepository`); concrete SQL in `scripts/core/ai_prompt_repository.py`.
- **owns_filesystem?:** No.
- **owns_network_calls?:** No.
- **owns_provider_selection?:** No.
- **owns_authorization?:** No.
- **owns_lifecycle_transition?:** No.
- **owns_evaluation?:** No.
- **runtime_reachable?:** Yes.
- **test_only?:** No.
- **legacy?:** No.
- **candidate_target_layer:** `AI_RUNTIME`
- **notes:** Small 3-file package (`VALID_SMALL_DOMAIN`). Invariant `Prompt ≠ Memory` strictly upheld.

---

### 25. `ai/providers`
- **primary_responsibility:** Vendor model provider integration layer: base provider interface (`AIProvider`), provider catalog (`ProviderRegistry`), OpenRouter implementation (`OpenRouterProvider`), and test fake (`FakeProvider`).
- **architectural_layer:** `MODEL_PLATFORM`
- **canonical_authority:** `ProviderRegistry` (`ai/providers/registry.py`), `AIProvider` (`ai/providers/base.py`), `OpenRouterProvider` (`ai/providers/openrouter.py`).
- **public_api:** `ProviderRegistry`, `AIProvider`, `ProviderDefinition`, `OpenRouterProvider`, `FakeProvider`, `get_provider_registry`.
- **main_consumers[]:** `ai/media/`, `ai/models/`, `ai/routing/`, `ai/specialized/`, `ai/speech/`.
- **main_dependencies[]:** `ai/contracts/`, `ai/models/` *(circular cycle)*.
- **reverse_dependencies[]:** 5 packages.
- **owns_state?:** In-memory provider catalog.
- **owns_database?:** No.
- **owns_filesystem?:** No.
- **owns_network_calls?:** **YES** (`OpenRouterProvider` executes HTTP POST via `httpx`).
- **owns_provider_selection?:** No (executes requested provider; selection owned by `ai/routing`).
- **owns_authorization?:** Manages provider API keys via secure environment injection.
- **owns_lifecycle_transition?:** No.
- **owns_evaluation?:** No.
- **runtime_reachable?:** Yes.
- **test_only?:** No.
- **legacy?:** No.
- **candidate_target_layer:** `MODEL_PLATFORM`
- **notes:** The ONLY package in `ai/` that makes outbound network requests. Contains circular dependency with `ai/models/` to be resolved in H02. Modernization deferred to S28-M.

---

### 26. `ai/recipes`
- **primary_responsibility:** 18 provider-neutral, machine-readable creative video recipes (TalkingHead, KineticTypography, ProductShowcase, etc.), recipe schema contracts, and rule-based recipe selection.
- **architectural_layer:** `CREATIVE_INTELLIGENCE`
- **canonical_authority:** `RecipeRegistry` (`ai/recipes/registry.py`), `RecipeSelector` (`ai/recipes/selector.py`).
- **public_api:** `RecipeRegistry`, `RecipeSelector`, `RecipeDefinition`.
- **main_consumers[]:** `ai/regression/`, `ai/planning/creative_planner.py`.
- **main_dependencies[]:** `ai/audio/`, `ai/contracts/`, `ai/intent/`.
- **reverse_dependencies[]:** `ai/regression/`.
- **owns_state?:** In-memory recipe catalog.
- **owns_database?:** No.
- **owns_filesystem?:** No.
- **owns_network_calls?:** No.
- **owns_provider_selection?:** No (Recipe ≠ Provider: recipes demand abstract capabilities, zero vendor names).
- **owns_authorization?:** No.
- **owns_lifecycle_transition?:** No.
- **owns_evaluation?:** No.
- **runtime_reachable?:** Yes.
- **test_only?:** No.
- **legacy?:** No.
- **candidate_target_layer:** `CREATIVE_INTELLIGENCE`
- **notes:** S28-03 deliverable. 100% provider-neutral recipes.

---

### 27. `ai/regression`
- **primary_responsibility:** Centralized creative intelligence regression suite: 34 canonical test cases across 13 creative categories, rubric evaluation (`RubricGrader`), retrieval precision/recall metrics (`RetrievalGrader`), and telemetry span grading (`CreativeTraceGrader`).
- **architectural_layer:** `EVALUATION`
- **canonical_authority:** `CreativeRegressionRunner` (`ai/regression/runner.py`), `CreativeTraceGrader` (`ai/regression/trace_grader.py`), `RubricGrader` (`ai/regression/rubric_grader.py`).
- **public_api:** `CreativeRegressionRunner`, `CreativeTraceGrader`, `RubricGrader`, `RetrievalGrader`, `get_all_creative_eval_cases`.
- **main_consumers[]:** `scripts/run_creative_regression.py`, `tests/ai/creative/`.
- **main_dependencies[]:** 12 `ai/` packages (broad evaluation fan-out).
- **reverse_dependencies[]:** None.
- **owns_state?:** No (stateless regression harness).
- **owns_database?:** No.
- **owns_filesystem?:** Writes regression report JSON to disk.
- **owns_network_calls?:** No.
- **owns_provider_selection?:** No.
- **owns_authorization?:** No.
- **owns_lifecycle_transition?:** No.
- **owns_evaluation?:** Yes, authoritative evaluator for Creative Intelligence regression.
- **runtime_reachable?:** No (CLI/regression test runner only).
- **test_only?:** Yes.
- **legacy?:** No.
- **candidate_target_layer:** `EVALUATION`
- **notes:** S28-08B deliverable. Reuses `CreativeRubricsEvaluator` from `ai.evals.creative_evals_s28_04`.

---

### 28. `ai/routing`
- **primary_responsibility:** Multi-model routing engine: utility score ranking, fallback chains, cost estimation, quality target policies, and escalation management.
- **architectural_layer:** `MODEL_PLATFORM` / `AI_RUNTIME`
- **canonical_authority:** `ModelRouter` (`ai/routing/router.py`), `RoutingPolicy` (`ai/routing/policy.py`).
- **public_api:** `ModelRouter`, `RoutingDecision`, `RoutingPolicy`, `build_fallback_chain`, `calculate_utility_score`.
- **main_consumers[]:** `ai/batch/`, `ai/budget/`, `ai/cost/`, `ai/media/`, `ai/specialized/`.
- **main_dependencies[]:** `ai/capabilities/`, `ai/contracts/`, `ai/models/`, `ai/providers/`.
- **reverse_dependencies[]:** 5 packages.
- **owns_state?:** In-memory router configuration and health stats.
- **owns_database?:** No.
- **owns_filesystem?:** No.
- **owns_network_calls?:** No.
- **owns_provider_selection?:** **YES** (Authoritative engine for model/provider selection and fallback).
- **owns_authorization?:** No.
- **owns_lifecycle_transition?:** No.
- **owns_evaluation?:** Evaluates model capability match and quality score.
- **runtime_reachable?:** Yes.
- **test_only?:** No.
- **legacy?:** No.
- **candidate_target_layer:** `MODEL_PLATFORM` / `AI_RUNTIME`
- **notes:** Core routing authority. Modernization deferred to S28-M.

---

### 29. `ai/security`
- **primary_responsibility:** Platform input bounds checking, prompt injection detection, server-side request forgery (SSRF) validation, and PII/secret scrubbing.
- **architectural_layer:** `CROSS_CUTTING_PLATFORM` / `GOVERNANCE`
- **canonical_authority:** `SecurityBounds` (`ai/security/bounds.py`), `SSRFValidator` (`ai/security/ssrf.py`), `SecretScrubber` (`ai/security/scrubber.py`).
- **public_api:** `SecurityBounds`, `SSRFValidator`, `SecretScrubber`, `SecurityPolicyConfig`.
- **main_consumers[]:** Dispatchers, prompt handlers, API gateways.
- **main_dependencies[]:** None.
- **reverse_dependencies[]:** None direct within `ai/` (used across system boundaries).
- **owns_state?:** No (stateless security filters).
- **owns_database?:** No.
- **owns_filesystem?:** No.
- **owns_network_calls?:** DNS resolution for SSRF checks (no outbound HTTP).
- **owns_provider_selection?:** No.
- **owns_authorization?:** Input sanitation security gate.
- **owns_lifecycle_transition?:** No.
- **owns_evaluation?:** No.
- **runtime_reachable?:** Yes.
- **test_only?:** No.
- **legacy?:** No.
- **candidate_target_layer:** `PLATFORM`
- **notes:** General platform security functions placed under `ai/security`. Candidate for `platform/security`.

---

### 30. `ai/skills`
- **primary_responsibility:** Operational creative skills definitions, skill-to-task routing, and operational context assembly. Enforces invariant: `Skill ≠ Permission`.
- **architectural_layer:** `CREATIVE_INTELLIGENCE`
- **canonical_authority:** `SkillRegistry` (`ai/skills/registry.py`), `SkillRouter` (`ai/skills/router.py`), `SkillContextAssembler` (`ai/skills/context.py`).
- **public_api:** `SkillRegistry`, `SkillRouter`, `SkillDefinition`, `SkillContextAssembler`.
- **main_consumers[]:** `ai/narrative/`, `ai/regression/`, `ai/planning/creative_planner.py`.
- **main_dependencies[]:** `ai/contracts/`, `ai/knowledge/`, `ai/tools/`.
- **reverse_dependencies[]:** `ai/narrative/`, `ai/regression/`.
- **owns_state?:** In-memory skill catalog.
- **owns_database?:** No.
- **owns_filesystem?:** Loads skill definitions from disk.
- **owns_network_calls?:** No.
- **owns_provider_selection?:** No.
- **owns_authorization?:** No (Skill ≠ Permission: requests tools, but relies on `ai/tools/authorization.py`).
- **owns_lifecycle_transition?:** No.
- **owns_evaluation?:** No.
- **runtime_reachable?:** Yes.
- **test_only?:** No.
- **legacy?:** No.
- **candidate_target_layer:** `CREATIVE_INTELLIGENCE`
- **notes:** S28-02 deliverable. Tool modernizations deferred to S28-M.

---

### 31. `ai/specialized`
- **primary_responsibility:** Provider-neutral execution service for multimodal AI operations: Text-to-Speech (TTS), image generation, video generation, and headless Remotion video rendering.
- **architectural_layer:** `CAPABILITY_PLATFORM` / `INTEGRATION`
- **canonical_authority:** `SpecializedCapabilityService` (`ai/specialized/service.py`), `TTSProviderInterface`, `ImageGenProviderInterface`, `VideoGenProviderInterface`, `RemotionExecutionInterface`.
- **public_api:** `SpecializedCapabilityService`, `TTSProviderInterface`, `ImageGenProviderInterface`, `VideoGenProviderInterface`, `RemotionExecutionInterface`.
- **main_consumers[]:** Execution pipelines, `tests/ai/specialized/`.
- **main_dependencies[]:** `ai/budget/`, `ai/cache/`, `ai/capabilities/`, `ai/contracts/`, `ai/orchestration/`, `ai/providers/`, `ai/routing/`.
- **reverse_dependencies[]:** None.
- **owns_state?:** No (delegates to orchestration/cache/budget).
- **owns_database?:** No.
- **owns_filesystem?:** No.
- **owns_network_calls?:** Dispatches to multimodal provider adapters.
- **owns_provider_selection?:** Dispatches via `ai/routing/`.
- **owns_authorization?:** Enforces budget reservation before invoking costly multimodal generation.
- **owns_lifecycle_transition?:** No.
- **owns_evaluation?:** No.
- **runtime_reachable?:** Yes.
- **test_only?:** No.
- **legacy?:** No.
- **candidate_target_layer:** `CAPABILITY_PLATFORM`
- **notes:** Contains TTS implementation (while STT is in `ai/speech`). Modernization deferred to S28-M.

---

### 32. `ai/speech`
- **primary_responsibility:** Speech-to-Text (STT) provider adapters (Whisper, Google STT), long-form audio chunking and multi-chunk transcript reconciliation, and speech recognition benchmarking.
- **architectural_layer:** `DOMAIN_SERVICE` / `CAPABILITY_PLATFORM`
- **canonical_authority:** `SpeechProviderAdapter` (`ai/speech/adapter.py`), `reconcile_chunk_transcripts` (`ai/speech/reconciliation.py`), `SpeechBenchmarkRunner` (`ai/speech/benchmark/runner.py`).
- **public_api:** `SpeechProviderAdapter`, `WhisperStyleAdapter`, `GoogleStyleAdapter`, `reconcile_chunk_transcripts`, `reconcile_speaker_catalog`, `SpeechBenchmarkRunner`.
- **main_consumers[]:** `ai/media/`, `tests/ai/speech/`.
- **main_dependencies[]:** `ai/contracts/`, `ai/providers/`.
- **reverse_dependencies[]:** `ai/media/`.
- **owns_state?:** No.
- **owns_database?:** No.
- **owns_filesystem?:** No.
- **owns_network_calls?:** No direct network calls (delegates to `ai/providers`).
- **owns_provider_selection?:** No.
- **owns_authorization?:** No.
- **owns_lifecycle_transition?:** No.
- **owns_evaluation?:** Authoritative runner for STT word error rate (WER) and diarization benchmarks.
- **runtime_reachable?:** Yes.
- **test_only?:** No.
- **legacy?:** No.
- **candidate_target_layer:** `DOMAIN_SERVICE`
- **notes:** Exclusively handles STT; does NOT contain TTS (which is located in `ai/specialized`). Modernization deferred to S28-M.

---

### 33. `ai/style`
- **primary_responsibility:** User personalization and style resolution: enforces the strict architectural invariant that **Current Explicit User Requests Strictly Override Remembered Preferences**. Resolves across 5 precedence tiers.
- **architectural_layer:** `CREATIVE_INTELLIGENCE`
- **canonical_authority:** `EffectiveUserStyleResolver` / `UserStyleResolver` (`ai/style/resolver.py`).
- **public_api:** `UserStyleResolver`, `EffectiveUserStyleResolver`.
- **main_consumers[]:** `ai/planning/creative_planner.py`, `ai/regression/runner.py`, `tests/ai/creative/`.
- **main_dependencies[]:** `ai/contracts/`, `ai/memory/`.
- **reverse_dependencies[]:** `ai/planning/`, `ai/regression/`.
- **owns_state?:** No (reads from `ai/memory`, returns resolved style trace).
- **owns_database?:** No.
- **owns_filesystem?:** No.
- **owns_network_calls?:** No.
- **owns_provider_selection?:** No.
- **owns_authorization?:** No.
- **owns_lifecycle_transition?:** No.
- **owns_evaluation?:** No.
- **runtime_reachable?:** Yes.
- **test_only?:** No.
- **legacy?:** No.
- **candidate_target_layer:** `CREATIVE_INTELLIGENCE`
- **notes:** S28-08A deliverable. Small 2-file package representing a pure, independent precedence resolution authority (`VALID_SMALL_DOMAIN`).

---

### 34. `ai/taste`
- **primary_responsibility:** Aesthetic evaluation and taste rule engine: enforces design rules (contrast, safe zones, pacing, typography harmony) and aggregates creative director recommendations. Invariant: `Taste ≠ QC`.
- **architectural_layer:** `CREATIVE_INTELLIGENCE`
- **canonical_authority:** `TasteEngine` (`ai/taste/engine.py`), `TasteEvaluator` (`ai/taste/evaluator.py`), `TasteRuleRegistry` (`ai/taste/registry.py`).
- **public_api:** `TasteEngine`, `TasteEvaluator`, `TasteRuleRegistry`, `TasteContext`, `TasteDecision`.
- **main_consumers[]:** `ai/evals/creative_evals_s28_04.py`, `ai/planning/creative_planner.py`, `ai/regression/runner.py`.
- **main_dependencies[]:** `ai/contracts/`.
- **reverse_dependencies[]:** `ai/evals/`, `ai/regression/`.
- **owns_state?:** In-memory taste rule registry.
- **owns_database?:** No.
- **owns_filesystem?:** No.
- **owns_network_calls?:** No.
- **owns_provider_selection?:** No.
- **owns_authorization?:** No.
- **owns_lifecycle_transition?:** No.
- **owns_evaluation?:** Advisory aesthetic grading; zero QC render approval authority.
- **runtime_reachable?:** Yes.
- **test_only?:** No.
- **legacy?:** No.
- **candidate_target_layer:** `CREATIVE_INTELLIGENCE`
- **notes:** S28-04 deliverable.

---

### 35. `ai/tools`
- **primary_responsibility:** Authoritative tool registry (`ToolRegistry`), tool execution dispatcher (`ToolDispatcher`), tenant boundary authorization (`ToolAuthorizationPolicy`), and domain tool adapters (projects, assets, blueprints, runs, qc).
- **architectural_layer:** `CAPABILITY_PLATFORM`
- **canonical_authority:** `ToolRegistry` (`ai/tools/registry.py`), `ToolDispatcher` (`ai/tools/dispatcher.py`), `ToolAuthorizationPolicy` (`ai/tools/authorization.py`).
- **public_api:** `ToolRegistry`, `ToolDispatcher`, `ToolAuthorizationPolicy`, `create_canonical_tool_registry`, `register_canonical_tools`.
- **main_consumers[]:** `ai/mcp/`, `ai/skills/`, API execution layer.
- **main_dependencies[]:** `ai/contracts/`.
- **reverse_dependencies[]:** `ai/mcp/`, `ai/skills/`.
- **owns_state?:** In-memory tool registry.
- **owns_database?:** No.
- **owns_filesystem?:** No.
- **owns_network_calls?:** No.
- **owns_provider_selection?:** No.
- **owns_authorization?:** **YES** (`ToolAuthorizationPolicy` validates tenant workspace boundaries, user roles, and side-effect classes).
- **owns_lifecycle_transition?:** No.
- **owns_evaluation?:** No.
- **runtime_reachable?:** Yes.
- **test_only?:** No.
- **legacy?:** No.
- **candidate_target_layer:** `CAPABILITY_PLATFORM`
- **notes:** S27.9 foundation. Modernization deferred to S28-M.

---

### 36. `ai/vision`
- **primary_responsibility:** Multi-modal visual intelligence: scene composition analysis, facial detection, visual quality assessment, on-screen text/OCR detection, and content safety.
- **architectural_layer:** `DOMAIN_SERVICE` / `CREATIVE_INTELLIGENCE`
- **canonical_authority:** `VisionPipeline` (`ai/vision/pipeline.py`), `VisionAnalyzer` (`ai/vision/analyzer.py`), `CompositionEngine` (`ai/vision/composition.py`).
- **public_api:** `VisionPipeline`, `VisionAnalyzer`, `CompositionEngine`, `SceneComposition`, `FaceDetectionResult`.
- **main_consumers[]:** `ai/media/`, `tests/ai/vision/`.
- **main_dependencies[]:** `ai/cache/`, `ai/contracts/`.
- **reverse_dependencies[]:** `ai/media/`.
- **owns_state?:** No (caches results via `ai/cache`).
- **owns_database?:** No.
- **owns_filesystem?:** No.
- **owns_network_calls?:** No (dispatches to vision models via routing).
- **owns_provider_selection?:** No.
- **owns_authorization?:** No.
- **owns_lifecycle_transition?:** No.
- **owns_evaluation?:** Visual composition and quality scoring. Zero QC authority.
- **runtime_reachable?:** Yes.
- **test_only?:** No.
- **legacy?:** No.
- **candidate_target_layer:** `DOMAIN_SERVICE`
- **notes:** S27.15 foundation. Modernization deferred to S28-M.

---

## 3. Small Package Audit & Architectural Justification

In accordance with Section 11, small packages (<= 4 files) were evaluated based on **conceptual independence, authority boundary, and invariant isolation**, rather than arbitrary file or line counts.

| Package | Files | Classification | Architectural Justification & Invariant Boundary |
| :--- | :---: | :---: | :--- |
| `ai/style` | 2 | **VALID_SMALL_DOMAIN** | Represents the single canonical authority for **User Style Resolution** and enforces the critical invariant: *Current Explicit Request Strictly Overrides Remembered Preferences* across 5 precedence tiers. Isolating this prevents memory or planner pollution. |
| `ai/conflict` | 2 | **VALID_SMALL_DOMAIN** | Represents a pure arbitration boundary (`ConflictResolver`) resolving contradictions across Brief, Recipe, Directors, and Taste. Keeping it isolated prevents circular dependencies between Directors and Taste. |
| `ai/prompts` | 3 | **VALID_SMALL_DOMAIN** | Manages prompt template versioning, retrieval, and interpolation. Independent lifecycle boundary ensuring *Prompt ≠ Memory* invariant is upheld. |
| `ai/batch` | 3 | **VALID_SMALL_DOMAIN** | Enforces `ExecutionClass` scheduling boundaries (`INTERACTIVE` vs `BATCH`) across the durable runtime. Cleanly reuses existing engines without duplication. |
| `ai/feedback` | 3 | **VALID_SMALL_DOMAIN** | Dedicated domain for classifying post-render human feedback into structured design modifications (Pacing, Colors, Typography) and updating style memory. |
| `ai/narrative` | 4 | **VALID_SMALL_DOMAIN** | Dedicated cognitive authority for narrative arc design, beat sheets, and pacing curves. |
| `ai/models` | 4 | **VALID_SMALL_DOMAIN** | Canonical registry for model metadata, pricing, and latency tiers. (Note: Circular dependency with `providers` is an import smell, not an over-fragmentation issue). |
| `ai/capabilities`| 4 | **VALID_SMALL_DOMAIN** | Canonical capability contract definitions and registry. Slated for expansion in S28-M. |

**Conclusion:** Zero packages are deemed invalidly small due to cosmetic directory depth. Every small package encapsulates a distinct architectural authority or invariant boundary.
