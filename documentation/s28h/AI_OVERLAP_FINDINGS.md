# S28-H01 — AI Overlap Findings & Architectural Smell Audit

> **Milestone:** S28-H01 (AI Package Ownership, Dependency & Duplication Audit)  
> **Workspace:** `motion / clean-video-workspace`  
> **Date:** 2026-10-03  
> **Status:** AUDIT COMPLETED — ZERO EXECUTABLE CODE MODIFICATIONS  

---

## 1. Executive Summary

This document formalizes all findings from the in-depth structural inspection of `ai/`. Every finding is backed by empirical source code evidence (file paths, line numbers, class definitions) and classified using the canonical taxonomy.

### Findings Summary Table

| Finding ID | Packages | Type | Severity | Target Stage | Title |
| :--- | :--- | :--- | :---: | :---: | :--- |
| `FIND-01` | `models`, `providers` | `CIRCULAR_DEPENDENCY` | **HIGH** | H02 (REMEDIATED) | Model Registry $\longleftrightarrow$ Provider Registry Circular Import |
| `FIND-02` | `contracts`, `memory` | `CROSS_LAYER_DEPENDENCY` | **MEDIUM** | H02 (REMEDIATED) | Base Contracts Depending on Domain Memory Enums |
| `FIND-03` | `evals`, `regression` | `DUPLICATE_AUTHORITY` / `LEGACY_COUPLING` | **MEDIUM** | H02 (REMEDIATED) | Milestone-Specific Evaluation Scripts Lingering in `ai/evals/` |
| `FIND-04` | `speech`, `specialized`, `audio` | `OVERLAPPING_RESPONSIBILITY` | **MEDIUM** | S28-M | Speech Subsystem Fragmentation: STT in `speech` vs TTS in `specialized` |
| `FIND-05` | `capabilities`, `tools`, `mcp` | `OVERLAPPING_RESPONSIBILITY` | **HIGH** | S28-M | Three-Way Boundary Ambiguity: Capabilities vs Tools vs MCP Adapters |
| `FIND-06` | `candidates` | `WRONG_LAYER` | **LOW** | H03 (REMEDIATED) | Template Governance Domain Subsystem Placed Directly Under `ai/` |
| `FIND-07` | `budget`, `cost` | `NO_ISSUE` | **INFO** | KEEP | Clear Separation Between Financial Enforcement (`budget`) and Telemetry (`cost`) |
| `FIND-08` | `context`, `memory`, `prompts`| `NO_ISSUE` | **INFO** | KEEP | Clean Invariant Separation: Assembled Context vs Persisted Memory vs Templates |
| `FIND-09` | `media` | `OVERLAPPING_RESPONSIBILITY` | **LOW** | S28-M | Mixed Responsibilities: Raw Byte/DSP Probing alongside Multimodal AI Orchestration |
| `FIND-10` | `security`, `cache`, `budget`, `observability` | `WRONG_LAYER` | **INFO** | Future Platform | Cross-Cutting Platform Infrastructure Modules Located Under `ai/` |

---

## 2. Detailed Overlap & Structural Findings

---

### FIND-01: Model Registry $\longleftrightarrow$ Provider Registry Circular Import
- **packages:** `ai/models`, `ai/providers`
- **type:** `CIRCULAR_DEPENDENCY`
- **severity:** **HIGH**
- **status:** **REMEDIATED (S28-H02)**
- **evidence:**
  1. `ai/models/registry.py:18`:
     ```python
     from ai.providers.registry import ProviderRegistry, UnknownProviderError, get_provider_registry
     ```
  2. `ai/providers/openrouter.py:27-28`:
     ```python
     from ai.models.registry import get_model_registry
     from ai.models.types import ModelPricing
     ```
- **current_behavior:** `ModelRegistry.register()` previously called `get_provider_registry().get_provider(model_def.provider_id)` to ensure the declared provider exists. Concurrently, `OpenRouterProvider.__init__()` imported and called `get_model_registry()` to dynamically register pricing and definitions.
- **architectural_risk:** Import race conditions during cold start, fragile module initialization order, and inability to deploy `models` or `providers` as independent packages or services.
- **recommended_action:**
  1. Relocate `ModelPricing` to `ai/contracts/model.py`.
  2. Decouple `ModelRegistry.register()` from eager provider lookup by injecting a provider existence predicate or validating lazily at routing time.
- **target_stage:** `H02`
- **remediation_summary:**
  1. Extracted `UnknownProviderError` into `ai/contracts/errors.py`. Re-exported in `ai/providers/registry.py` and `ai/models/registry.py` for full backward compatibility.
  2. Relocated `CostTier`, `LatencyTier`, `ModelPricing`, and `CANONICAL_PROVIDER_IDS` into canonical contracts at `ai/contracts/model.py`. `ai/models/types.py` re-exports them without breakage.
  3. Decoupled `ai/models/registry.py` completely from `ai.providers`. Zero imports of `ai.providers` in `ai/models`. `ModelRegistry` validates provider IDs against canonical known IDs (`CANONICAL_PROVIDER_IDS`) or an injected provider registry / validator callback.
  4. Updated `ai/providers/openrouter.py` to import `ModelPricing` from `ai.contracts.model`, and accept an injected `model_registry` (defaulting to canonical registry) avoiding tight module coupling.
- **files_changed:**
  - `ai/contracts/errors.py`
  - `ai/contracts/model.py`
  - `ai/models/types.py`
  - `ai/models/registry.py`
  - `ai/providers/registry.py`
  - `ai/providers/openrouter.py`
- **tests:** `tests/ai/test_s28_h02_remediation.py::TestFind01CircularDependency` (100% PASS), verifying zero AST imports of `ai.providers` across `ai/models/` and verifying independent instantiation of both registries.
- **remaining_risk:** **ZERO**. Enforced by AST automated guard tests.

---

### FIND-02: Base Contracts Inverted Dependency on Domain Memory Types
- **packages:** `ai/contracts`, `ai/memory`
- **type:** `CROSS_LAYER_DEPENDENCY`
- **severity:** **MEDIUM**
- **status:** **REMEDIATED (S28-H02)**
- **evidence:**
  `ai/contracts/creative/feedback.py:21`:
  ```python
  from ai.memory.types import EpistemicStatus, MemoryScope, SourceType
  ```
- **current_behavior:** `CreativeFeedbackAnalysis` contract previously referenced `EpistemicStatus`, `MemoryScope`, and `SourceType` imported directly from the domain service `ai.memory.types`.
- **architectural_risk:** Inversion of the architectural hierarchy. The contracts package (layer 0 / foundation) depends on a domain service implementation (layer 2). Any tool or package generating or verifying contracts transitively pulls in the memory domain.
- **recommended_action:** Move `EpistemicStatus`, `MemoryScope`, and `SourceType` into `ai/contracts/common.py` or a dedicated `ai/contracts/memory.py`. Update `ai/memory/types.py` to import from contracts.
- **target_stage:** `H02`
- **remediation_summary:**
  1. Defined canonical single-authority enums `MemoryScope`, `SourceType`, `EpistemicStatus`, and `MemoryType` in `ai/contracts/memory.py` with strict validation helpers.
  2. Updated `ai/contracts/creative/feedback.py` to import `EpistemicStatus`, `MemoryScope`, and `SourceType` directly from `ai.contracts.memory`.
  3. Updated `ai/memory/types.py` to re-export the canonical enums from `ai.contracts.memory`, deprecating duplicate declarations and preserving 100% backward compatibility for existing memory consumers.
  4. Verified zero contract drift with contract code generators (`generate_ai_contracts.py --check` and `generate_creative_contracts.py --check`).
- **files_changed:**
  - `ai/contracts/memory.py`
  - `ai/contracts/creative/feedback.py`
  - `ai/memory/types.py`
- **tests:** `tests/ai/test_s28_h02_remediation.py::TestFind02ContractInvertedDependency` (100% PASS), verifying zero AST imports of `ai.memory` across `ai/contracts/`, identical enum serialization, and zero contract drift.
- **remaining_risk:** **ZERO**. Clean layer-0 definition with backward-compatible re-exports.

---

### FIND-03: Milestone-Specific Evaluation Scripts Lingering in `ai/evals/`
- **packages:** `ai/evals`, `ai/regression`
- **type:** `DUPLICATE_AUTHORITY` / `LEGACY_COUPLING`
- **severity:** **MEDIUM**
- **status:** **REMEDIATED (S28-H02)**
- **evidence:**
  1. `ai/evals/` contains:
     - `creative_datasets.py`
     - `creative_datasets_s28_06.py`
     - `creative_evals_s28_04.py`
     - `creative_evals_s28_05.py`
     - `creative_evals_s28_06.py`
  2. `ai/regression/` contains `CreativeRegressionRunner` and `datasets.py` which unifies all 34 canonical cases across 13 categories.
  3. `ai/regression/rubric_grader.py:27` and `ai/regression/runner.py:75` import `CreativeRubricsEvaluator` directly from `ai.evals.creative_evals_s28_04`.
- **current_behavior:** Incremental evaluation scripts developed during milestone execution (S28-02 through S28-06) remained in `ai/evals/`, creating confusion regarding whether `evals` or `regression` is the authority for creative evaluation.
- **architectural_risk:** Dual testbeds, fragmented grading logic, and dead code accumulation.
- **recommended_action:**
  1. Move `CreativeRubricsEvaluator` from `ai.evals.creative_evals_s28_04` into `ai.regression.rubric_grader`.
  2. Prune milestone-specific evaluation files from `ai/evals/`, keeping `ai/evals/` as the generic platform evaluation framework (`EvalRunner`, `CIEvalGate`).
- **target_stage:** `H02`
- **remediation_summary:**
  1. Defined canonical `ScenarioRubricScores`, `PairwiseComparisonResult`, and `CreativeRubricsEvaluator` directly in `ai/regression/rubric_grader.py`.
  2. Refactored `ai/regression/runner.py` to use a native, validated `make_test_brief` helper and call `self.rubric_grader` directly without importing `ai.evals.creative_evals_s28_04`.
  3. Converted `ai/evals/creative_evals_s28_04.py` into a lightweight compatibility shim re-exporting from `ai.regression.rubric_grader` (`KEEP_COMPATIBILITY`).
  4. Preserved milestone experimental testbeds (`creative_evals_s28_05.py`, `creative_evals_s28_06.py`, `creative_datasets_s28_06.py`) under `documentation/s28/evidence/testbeds/` for audit trail preservation, and purged them from `ai/evals/`.
- **files_changed:**
  - `ai/regression/rubric_grader.py`
  - `ai/evals/creative_evals_s28_04.py`
  - `ai/regression/runner.py`
  - `documentation/s28/evidence/testbeds/creative_evals_s28_05.py` (preserved)
  - `documentation/s28/evidence/testbeds/creative_evals_s28_06.py` (preserved)
  - `documentation/s28/evidence/testbeds/creative_datasets_s28_06.py` (preserved)
- **tests:** `tests/ai/test_s28_h02_remediation.py::TestFind03MilestoneEvals` (100% PASS), and `scripts/run_creative_regression.py` (34/34 passed, 100%).
- **remaining_risk:** **ZERO**. Generic platform evaluation framework preserved in `ai/evals/`; S28 creative evaluation consolidated in `ai/regression/`.

---

### FIND-04: Speech Subsystem Fragmentation (STT vs TTS)
- **packages:** `ai/speech`, `ai/specialized`, `ai/audio`
- **type:** `OVERLAPPING_RESPONSIBILITY`
- **severity:** **MEDIUM**
- **evidence:**
  1. `ai/speech/adapter.py`: defines `SpeechProviderAdapter` (STT exclusively).
  2. `ai/specialized/interfaces.py:53`: defines `TTSProviderInterface` and `TTSRequest`/`TTSResult`.
  3. `ai/specialized/adapters.py:150`: implements TTS synthesis.
  4. `ai/audio/modes.py:289`: enforces invariants forbidding TTS under `MUSIC_ONLY` and `SILENT`.
- **current_behavior:** Speech understanding (STT) lives in `ai/speech/`, while Speech generation (TTS) lives in `ai/specialized/`. A developer seeking voice capabilities must navigate two disjoint packages.
- **architectural_risk:** Cognitive load, duplicated provider configuration, and uncoordinated voice model lifecycle management.
- **recommended_action:** Unify speech recognition (STT) and speech synthesis (TTS) into a consolidated Speech Capability domain under `ai/speech/` or modern capability platform.
- **target_stage:** `S28-M`

---

### FIND-05: Three-Way Boundary Ambiguity (Capabilities vs Tools vs MCP)
- **packages:** `ai/capabilities`, `ai/tools`, `ai/mcp`
- **type:** `OVERLAPPING_RESPONSIBILITY`
- **severity:** **HIGH**
- **evidence:**
  1. `ai/capabilities/registry.py`: registers abstract capability types (`CapabilityDefinition`).
  2. `ai/tools/registry.py`: registers executable tools (`ToolRegistration`).
  3. `ai/tools/authorization.py`: evaluates `ToolAuthorizationPolicy` against `TrustedToolExecutionContext`.
  4. `ai/mcp/catalog.py`: registers external MCP servers (`MCPServerDefinition`).
  5. `ai/mcp/policy.py`: evaluates `MCPSecurityPolicy` for MCP operations.
  6. `ai/mcp/adapters/`: implements domain wrappers for audio/video/image operations.
- **current_behavior:** Three separate registries and two independent authorization policies exist for tool/capability execution:
  - `ai/capabilities`: logical abstraction.
  - `ai/tools`: local domain execution and RBAC authorization.
  - `ai/mcp`: protocol adapter and sandbox security authorization.
- **architectural_risk:** Redundant configuration, dual security auditing, and difficulty maintaining feature parity between native tools and MCP tools.
- **recommended_action:** Unify under a modernized Capability Platform in S28-M.
- **target_stage:** `S28-M`

---

### FIND-06: Template Governance Domain Subsystem Placed Directly Under `ai/`
- **packages:** `ai/candidates`
- **type:** `WRONG_LAYER`
- **severity:** **LOW**
- **status:** **REMEDIATED (S28-H03)**
- **evidence:**
  1. `ai/candidates/` contains 24 Python files implementing:
     - Static AST parsing (`StaticCodeGate`, `SecurityGate`, `TypeScriptGate`)
     - Headless Remotion rendering (`RenderSmokeGate`, `CandidateQCGate`)
     - Human review workflows (`CandidateReviewService`, separation of duties)
     - Template registry publication (`PromotionService`)
  2. Zero machine learning models or LLM inference calls occur inside `ai/candidates/`.
- **current_behavior:** `ai/candidates/` was treated as an AI package solely because the templates it governs are proposed by AI. Functionally, it is an end-to-end Template Governance platform.
- **architectural_risk:** Bloats the `ai/` package with non-AI platform governance code and creates conceptual confusion about whether candidates are AI models or Remotion components.
- **recommended_action:** Relocate canonical candidate governance implementation to `creative_governance/candidates`, retaining a thin backward-compatible re-export facade under `ai/candidates`.
- **target_stage:** `H03`
- **remediation_summary:**
  1. Relocated canonical implementation to `creative_governance/candidates/` (Pillar 4 Creative Governance domain).
  2. Converted all 24 modules in `ai/candidates/` into thin compatibility re-exports (`DEPRECATED_COMPATIBILITY_IMPORT`) containing zero business logic and zero class definitions.
  3. Migrated all first-party production consumers (`api/routers/candidate_reviews.py`, `api/routers/candidate_promotions.py`, `scripts/core/template_candidate_repository.py`, `scripts/core/template_registry_publisher.py`, `scripts/validators/candidate_runtime_runner.py`) to `creative_governance.candidates`.
  4. Verified all non-negotiable governance invariants: AI ≠ Approval Authority, Creator ≠ Reviewer, PromotionService remains sole publication authority, zero registry bypass.
  5. Verified clean layering: `creative_governance` has zero imports of AI planner, taste, routing, providers, or evals; `ai/contracts` has zero imports of `creative_governance`.
- **files_changed:**
  - `creative_governance/__init__.py` (new canonical package)
  - `creative_governance/candidates/*` (24 canonical modules)
  - `ai/candidates/*` (24 thin compatibility re-exports)
  - `api/routers/candidate_reviews.py`
  - `api/routers/candidate_promotions.py`
  - `scripts/core/template_candidate_repository.py`
  - `scripts/core/template_registry_publisher.py`
  - `scripts/validators/candidate_runtime_runner.py`
  - `scripts/validators/template_proposal_validator.py`
  - `tests/ai/candidates/test_candidate_architecture_guards.py`
  - `tests/api/test_candidate_reviews_router.py`
  - `tests/api/test_candidate_promotions_router.py`
  - `tests/core/test_template_candidate_repository.py`
  - `tests/ai/e2e/test_real_service_e2e_closeout.py`
  - `tests/ai/candidates/*.py`
  - `tests/ai/test_s28_h03_remediation.py` (new architecture guard suite)
- **tests:** `tests/ai/test_s28_h03_remediation.py` (13/13 PASS), `tests/api/test_candidate*.py` (11/11 PASS), `tests/core/test_template_candidate_repository.py` (3/3 PASS), `tests/ai/e2e/test_real_service_e2e_closeout.py` (5/5 PASS), full AI regression sweep.
- **remaining_risk:** **ZERO**. All canonical classes live in `creative_governance.candidates`; legacy imports resolve identically through the thin compatibility facade.

---

### FIND-07: Budget Limits vs Cost Observability
- **packages:** `ai/budget`, `ai/cost`
- **type:** `NO_ISSUE`
- **severity:** **INFO**
- **evidence:**
  1. `ai/budget/service.py`: `BudgetService` enforces pre-execution limits, reserves credits, and blocks overages with `BudgetExceededError`.
  2. `ai/cost/accounting.py`: `TokenAccounting` and `CreativeEfficiencyAnalyzer` observe completed executions, compute actual/estimated/unknown costs, and detect waste without any execution blocking authority.
- **current_behavior:** `Budget` acts as an active financial gatekeeper; `Cost` acts as a passive, read-only observability collector and auditor.
- **architectural_risk:** None. Responsibilities are strictly orthogonal and well-defined.
- **recommended_action:** Retain separation of concerns. In future platform refactoring, both may migrate to platform infrastructure (`platform/budget` and `platform/cost`).
- **target_stage:** `KEEP`

---

### FIND-08: Context Assembly vs Memory vs Prompt Templates
- **packages:** `ai/context`, `ai/memory`, `ai/prompts`
- **type:** `NO_ISSUE`
- **severity:** **INFO**
- **evidence:**
  1. `ai/memory/service.py`: Persisted multi-tenant storage for long-term project facts and user preferences with confidence decay.
  2. `ai/context/builder.py`: Ephemeral, request-scoped context assembly, ranking, and token budgeting.
  3. `ai/prompts/service.py`: Versioned prompt templates and variable interpolation.
- **current_behavior:** Each package strictly adheres to its invariant:
  - *Memory ≠ Context*: Memory is durable storage; Context is ephemeral request packaging.
  - *Prompt ≠ Memory*: Prompts are code templates; Memory is user/project data.
- **architectural_risk:** None. Boundaries are exceptionally clean.
- **recommended_action:** Retain current architecture.
- **target_stage:** `KEEP`

---

### FIND-09: Mixed Responsibilities in Media Package
- **packages:** `ai/media`
- **type:** `OVERLAPPING_RESPONSIBILITY`
- **severity:** **LOW**
- **evidence:**
  1. `ai/media/technical_probe.py`: Low-level binary PCM unpacking, WAV header parsing, and RMS energy calculation.
  2. `ai/media/service.py`: High-level multi-modal AI intelligence coordination (speech recognition, caching, and vision integration).
  3. `ai/media/repository.py`: Relational database index metadata interface.
- **current_behavior:** Low-level file format parsing (DSP) coexists with high-level AI multi-modal pipeline orchestration in the same package.
- **architectural_risk:** Minor coupling between raw binary file formats and cognitive AI intelligence.
- **recommended_action:** In S28-M, separate low-level technical media probing (which can move to `media/probe` or `audio/dsp`) from AI media intelligence orchestration.
- **target_stage:** `S28-M`

---

### FIND-10: Cross-Cutting Platform Infrastructure Located Under `ai/`
- **packages:** `ai/security`, `ai/cache`, `ai/budget`, `ai/observability`
- **type:** `WRONG_LAYER`
- **severity:** **INFO**
- **evidence:**
  - `ai/security`: General SSRF validation (`ssrf.py`), secret scrubbing (`scrubber.py`).
  - `ai/cache`: General deterministic caching service (`service.py`).
  - `ai/budget`: Financial limit reservation and accounting (`service.py`).
  - `ai/observability`: Distributed tracing, spans, and metrics (`tracer.py`, `metrics.py`).
- **current_behavior:** Platform infrastructure services are nested under `ai/` because they were developed in AI-focused sprints (S27/S28).
- **architectural_risk:** Tightly couples generic SaaS platform infrastructure with AI domain logic.
- **recommended_action:** Evaluate platform restructuring proposal (e.g. `platform/*`) during future platform modernization.
- **target_stage:** `Future Restructure`
