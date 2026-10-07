# S28-H01 — AI Subsystem Authority Matrix

> **Milestone:** S28-H01 (AI Package Ownership, Dependency & Duplication Audit)  
> **Workspace:** `motion / clean-video-workspace`  
> **Date:** 2026-10-03  
> **Status:** AUDIT COMPLETED — ZERO EXECUTABLE CODE MODIFICATIONS  

---

## 1. Executive Summary

This Authority Matrix audits **31 core concepts** across the AI platform. It answers the fundamental architectural question:  
**Does each concept possess exactly ONE Canonical Authority, or do secondary/competing implementations cause authority drift?**

### Key Findings
- **27 of 31 concepts** have a single, undisputed canonical authority with zero competing duplicates.
- **4 concepts** exhibit authority tension or architectural overlaps:
  1. **Model & Provider Registries**: Bi-directional import cycle between `ModelRegistry` and `ProviderRegistry`.
  2. **Tool Registry vs MCP Catalog**: Overlap in capability declaration and tool execution boundaries.
  3. **Tool Authorization vs MCP Security Policy**: Dual authorization checkpoints.
  4. **Evaluation vs Regression**: Generic evaluation harness vs unified S28 creative regression suite and legacy milestone evaluation leftovers.

---

## 2. Canonical Authority Matrix

| Concept | Current Canonical Authority | Secondary Implementations | Consumers | Conflict? | Evidence | Recommendation |
| :--- | :--- | :--- | :--- | :---: | :--- | :--- |
| **Intent** | `ai.intent.parser.IntentParser` | None (legacy direct prompt extraction retired in S28-08E) | `ai.planning.creative_planner`, `ai.recipes.selector`, `ai.regression.runner` | **NO** | Single entry point parsing raw user text into `CreativeBrief` with field-level epistemic provenance. | **KEEP** |
| **Knowledge** | `ai.knowledge.registry.KnowledgeRegistry` & `HybridKnowledgeRetriever` | None | `ai.narrative.planner`, `ai.planning.creative_planner`, `ai.regression.runner` | **NO** | Invariant enforced: *Knowledge ≠ Authority* (contextual reference only; cannot grant QC approval). | **KEEP** |
| **Skills** | `ai.skills.registry.SkillRegistry` & `SkillRouter` | None | `ai.narrative.planner`, `ai.planning.creative_planner` | **NO** | Invariant enforced: *Skill ≠ Permission* (requests tool need; server-side policy authorizes). | **DEFER_TO_S28_M** |
| **Recipe** | `ai.recipes.registry.RecipeRegistry` & `RecipeSelector` | None | `ai.planning.creative_planner`, `ai.regression.runner` | **NO** | 18/18 recipes typed; Invariant enforced: *Recipe ≠ Provider* (abstract capabilities, zero vendor names). | **KEEP** |
| **Audio Policy** | `ai.audio.modes.AudioModeEngine` | Mirrored validation in `ai.planning.validator` | `ai.recipes.selector`, `ai.planning.validator`, `scripts/run_creative_e2e.py` | **NO** | 6 canonical modes enforced (`SILENT` forbids all audio; `MUSIC_ONLY` strictly forbids TTS/VO). | **KEEP** |
| **Narrative** | `ai.narrative.planner.NarrativePlanner` | None | `ai.planning.creative_planner`, `ai.taste.engine` | **NO** | Generates typed `NarrativePlan` (arcs, pacing, beat sheets). | **KEEP** |
| **Taste** | `ai.taste.engine.TasteEngine` & `TasteEvaluator` | `ai.directors.*` provide inputs; `ai.conflict.resolver` arbitrates | `ai.planning.creative_planner`, `ai.regression.runner` | **NO** | Invariant enforced: *Taste ≠ QC* (advisory aesthetic guidance; cannot grant render approval). | **KEEP** |
| **Style** | `ai.style.resolver.EffectiveUserStyleResolver` | None | `ai.planning.creative_planner`, `ai.regression.runner` | **NO** | Invariant enforced: *Current Request Wins* across 5 strict precedence tiers. | **KEEP** |
| **CreativePlan** | `ai.planning.creative_planner.CreativePlanner` | None | `scripts.core.blueprint_compiler`, `ai.planning.tier_policy`, `ai.planning.validator` | **NO** | Invariant enforced: *CreativePlan ≠ Blueprint* (cognitive intent compiled deterministically). | **KEEP** |
| **Tier Selection** | `ai.planning.tier_policy.CreativeTierPolicy` | None (anti-bypass machine-enforced) | `ai.planning.creative_planner`, `scripts.run_creative_e2e` | **NO** | Deterministic hierarchy enforced: $\text{REUSE} \to \text{COMPOSE} \to \text{CREATE}$. | **KEEP** |
| **Blueprint Compilation** | `scripts.core.blueprint_compiler.BlueprintCompiler` | None (legacy LLM-to-blueprint retired in S28-08E) | Core render pipeline, `scripts.run_creative_e2e` | **NO** | Single deterministic translation bridge from `CreativePlan` to validated `BlueprintV2`. | **KEEP** |
| **Model Registry** | `ai.models.registry.ModelRegistry` | None | `ai.routing.router`, `ai.providers.openrouter`, `ai.cost.accounting` | **YES** *(Cycle)* | `ai.models.registry` imports `ProviderRegistry` while `ai.providers.openrouter` imports `ModelRegistry`. | **KEEP_BUT_RENAME_LATER** / Decouple in H02 |
| **Provider Registry** | `ai.providers.registry.ProviderRegistry` | None | `ai.models.registry`, `ai.routing.router`, `ai.specialized.service` | **YES** *(Cycle)* | Circular dependency with `ModelRegistry`. | **DEFER_TO_S28_M** / Decouple in H02 |
| **Model Routing** | `ai.routing.router.ModelRouter` | None | `ai.orchestration.service`, `ai.batch.service`, `ai.media.service` | **NO** | Authoritative multi-model utility ranking and fallback engine. | **DEFER_TO_S28_M** |
| **Capability Registry** | `ai.capabilities.registry.CapabilityRegistry` | None | `ai.models.registry`, `ai.cache.service`, `ai.routing.router` | **NO** | Abstract capability contract definitions. | **DEFER_TO_S28_M** |
| **Tool Registry** | `ai.tools.registry.ToolRegistry` | `ai.mcp.catalog.MCPCatalog` maintains external tools | `ai.tools.dispatcher`, `ai.skills.context` | **YES** *(Overlap)* | Canonical domain tools registered in `ToolRegistry`; MCP tools cataloged separately. | **DEFER_TO_S28_M** |
| **Tool Authorization** | `ai.tools.authorization.ToolAuthorizationPolicy` | `ai.mcp.policy.MCPSecurityPolicy` (sandboxing/SSRF) | `ai.tools.dispatcher`, `ai.skills.context` | **YES** *(Overlap)* | Dual authorization checkpoints: tenant/role policy vs MCP path/shell security guards. | **DEFER_TO_S28_M** |
| **MCP Integration** | `ai.mcp.adapters.base.BaseMCPAdapter` & `MCPCatalog` | None | Domain tool adapters (`ai.tools.domain`) | **YES** *(Overlap)* | MCP tools vs native tool adapters boundary ambiguity. | **DEFER_TO_S28_M** |
| **Memory** | `ai.memory.service.MemoryService` & `ProjectMemoryFacade` | None | `ai.context.retrieval`, `ai.style.resolver`, `ai.feedback.service` | **NO** | Invariant enforced: *Memory ≠ Context* (persisted multi-tenant storage vs ephemeral context). | **KEEP** (Fix contract import in H02) |
| **Context Assembly** | `ai.context.assembly.ContextAssembler` & `ContextBuilder` | None | AI inference execution runners | **NO** | Ephemeral, bounded token packaging; deduplication and ranking. | **KEEP** |
| **Prompt Repository** | `ai.prompts.service.PromptService` & `PromptRepository` | None | Inference execution runners, pipeline steps | **NO** | Invariant enforced: *Prompt ≠ Memory* (versioned template strings vs persisted facts). | **KEEP** |
| **Budget** | `ai.budget.service.BudgetService` | None | `ai.batch.service`, `ai.orchestration.service`, `ai.specialized.service` | **NO** | Pre-execution limit enforcement, reservation, and blocking. | **MOVE** (Platform candidate) |
| **Cost** | `ai.cost.accounting.TokenAccounting` & `CreativeCostEstimator` | `ai.routing.cost` (estimates routing cost) | `scripts.run_creative_cost_audit`, `ai.regression.runner` | **NO** | Post-execution telemetry measurement, attribution, and efficiency audit. Zero runtime authority. | **KEEP** |
| **Evaluation** | `ai.evals.runner.EvalRunner` & `CIEvalGate` | Milestone runners in `ai.evals.creative_evals_s28_*.py` | CI pipelines, gate validation | **YES** *(Duplication)* | Milestone-specific evaluation testbeds linger in `ai.evals/` alongside generic runner. | **SPLIT** / Prune legacy in H02 |
| **Regression** | `ai.regression.runner.CreativeRegressionRunner` | None | `scripts.run_creative_regression`, `tests.ai.creative` | **NO** | Unified creative intelligence regression harness (34 cases across 13 categories). | **KEEP** |
| **Candidate Lifecycle** | `creative_governance.candidates.service.TemplateCandidateService` | None (`ai.candidates` shim) | `api.routers.candidate_*`, `scripts.maintenance.promote_template` | **NO** | Invariant enforced: *Candidate ≠ Reusable Template* (isolated draft until promoted). | **MOVED (S28-H03)** |
| **Candidate Validation** | `creative_governance.candidates.validation_service.CandidateValidationService` | None (`ai.candidates` shim) | `creative_governance.candidates.service.TemplateCandidateService` | **NO** | 6 static AST security gates + headless Remotion runtime QC rendering. | **MOVED (S28-H03)** |
| **Human Review** | `creative_governance.candidates.review_service.CandidateReviewService` | None (AI self-approval strictly blocked with 403 Forbidden) | `api.routers.candidate_reviews` | **NO** | Invariant enforced: *AI ≠ Approval Authority* (human reviewer required; separation of duties). | **MOVED (S28-H03)** |
| **Promotion** | `creative_governance.candidates.promotion_service.PromotionService` | `scripts.core.template_registry_publisher.TemplateRegistryPublisher` | `api.routers.candidate_promotions`, `scripts.maintenance.promote_template` | **NO** | Sole promotion authority with atomic staging, verification, and rollback. | **MOVED (S28-H03)** |
| **Media Analysis** | `ai.media.service.MediaIntelligenceService` | `TechnicalMediaProbe` (low-level probe) | `api.services.asset_service`, core video pipelines | **NO** | Bridges deterministic technical probing, speech STT, audio DSP, and caching. | **KEEP** |
| **Observability** | `ai.observability.tracer.AITracer` & `AIMetrics` | None | Execution run steps, pipeline telemetry | **NO** | Distributed tracing, spans, metrics, and secret redaction. | **MOVE** (Platform candidate) |

---

## 3. Subsystem Separation Summaries

### A. Budget vs Cost
- **`Budget` owns:** Financial pre-execution reservations, tenant spend limits, credit balance enforcement, and hard execution blocking.
- **`Cost` owns:** Post-execution telemetry accounting, token auditing, efficiency baselines, waste detection, and cost provenance (`ACTUAL` vs `ESTIMATED` vs `UNKNOWN`).
- **Conclusion:** There is **zero duplicate authority**. Budget enforces; Cost observes.

### B. Evals vs Regression
- **`evals` owns:** Generic evaluation platform primitives (`EvalRunner`, `CIEvalGate`, `ModelPromotionEngine`, `EvaluatorBase`).
- **`regression` owns:** S28-specific unified creative regression testbed (34 canonical test cases, `CreativeTraceGrader`, `RubricGrader`, `RetrievalGrader`).
- **Conclusion:** Architectural roles are distinct, but `ai/evals/` contains lingering milestone eval scripts (`creative_evals_s28_04/05/06.py`) that should be consolidated or deprecated in H02.

### C. Audio vs Speech vs Specialized
- **`audio` owns:** Native DSP (SNR, clipping, RMS), audio intelligence pipeline, and `AudioMode` policy enforcement (`SILENT`, `MUSIC_ONLY`, etc.).
- **`speech` owns:** Speech-to-Text (STT) provider adapters (Whisper, Google), long-media chunk reconciliation, and STT benchmarks.
- **`specialized` owns:** Text-to-Speech (TTS), image generation, video generation, and Remotion execution adapters.
- **Conclusion:** STT and TTS are currently fragmented across two different packages (`speech` and `specialized`). Consolidation is scheduled for **S28-M**.

### D. Capabilities vs Tools vs MCP
- **`capabilities` owns:** Abstract capability contract declarations (privacy class, cost unit, cache policy).
- **`tools` owns:** Canonical domain tool registry, tool dispatcher, and tenant/role authorization policy.
- **`mcp` owns:** External MCP server catalog, process sandboxing, and media adapter tools.
- **Conclusion:** Three-way conceptual overlap. Consolidation into a unified Capability Platform is the explicit charter of **S28-M**.
