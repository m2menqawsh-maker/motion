# PILLAR 3: AI Subsystem Reality, Creative Authoring & Execution Pipeline

> **Consolidated Master Pillar** — Comprehensive integration of Reports 06, 07, 08, and 09

> **Baseline SHA**: `90ec3de8d47494d5940d5cd1f9ed9a8e274ef6e1` | **Branch**: `main`

> **Evidence Standard**: Strictly Preserved (`CODE_PROVEN`, `TEST_PROVEN`, `CI_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`, `DOCUMENTATION_ONLY`, `INFERRED`, `UNKNOWN`)


---

## Table of Contents

1. [Part 1: AI Platform & Context Construction Reality](#part-1-ai-platform--context-construction-reality) *(Source: `06_AI_SUBSYSTEM_ACTUAL_REALITY.md`)*
2. [Part 2: Ground Truth, References, Knowledge, Skills & Recipes](#part-2-ground-truth-references-knowledge-skills--recipes) *(Source: `07_GROUND_TRUTH_REFERENCES_KNOWLEDGE_SKILLS_RECIPES_REALITY.md`)*
3. [Part 3: Creative Authoring, Editor & Render Pipeline](#part-3-creative-authoring-editor--render-pipeline) *(Source: `08_CREATIVE_AUTHORING_EDITOR_RENDER_REALITY.md`)*
4. [Part 4: Capability, Model, Provider & Tool Execution](#part-4-capability-model-provider--tool-execution) *(Source: `09_CAPABILITY_MODEL_PROVIDER_TOOL_EXECUTION_REALITY.md`)*

---


<a name='part-1-ai-platform--context-construction-reality'></a>

## Part 1: AI Platform & Context Construction Reality


> *Original Source: `documentation/reality_context_pack/06_AI_SUBSYSTEM_ACTUAL_REALITY.md`*


### Sub-Report Title: 06 — AI Subsystem Actual Reality Report


- **Baseline Git SHA**: `90ec3de8d47494d5940d5cd1f9ed9a8e274ef6e1`
- **Branch**: `main`
- **Report Version**: 1.0.0
- **Last Updated**: 2026-10-07
- **Scope**: AI Subsystem Architecture, Prompt Intake, Context Building, Planning, Routing, Model Providers, and Production Reachability
- **Evidence Standards**: `CODE_PROVEN`, `TEST_PROVEN`, `CI_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`, `DOCUMENTATION_ONLY`, `INFERRED`, `UNKNOWN`

---

## 1. Executive Summary & Reality Verdict

The AI Subsystem in this repository represents an extensive, sophisticated architectural design developed across two major generations (S27 AI Infrastructure and S28 Creative Intelligence / Modernization). It comprises over 15 distinct subpackages in the `ai/` root directory (`ai/contracts`, `ai/capabilities`, `ai/routing`, `ai/providers`, `ai/tools`, `ai/planning`, `ai/intent`, `ai/narrative`, `ai/taste`, `ai/directors`, `ai/conflict`, `ai/recipes`, `ai/skills`, `ai/knowledge`, `ai/memory`, `ai/context`, `ai/speech`, `ai/vision`, `ai/audio`, `ai/mcp`).

However, rigorous static AST analysis and production call graph verification prove a fundamental architectural reality:

1. **Total Production Disconnection**: The entire modern AI subsystem (`ai/`) is **completely disconnected** from the production runtime HTTP API (`api/`) and the production pipeline worker (`scripts/pipeline.py`, `scripts/core/worker.py`).
2. **Zero Natural-Language Intake in Production**: The production REST API contains **zero** endpoints capable of accepting a natural-language prompt or creative brief to generate or modify a video project (`CODE_PROVEN`).
3. **Purely Deterministic Production Runtime**: The production pipeline (`scripts/pipeline.py`) operates as a strictly deterministic state machine validating pre-existing files on disk (`01_manifest.json`, `master_plan.md`, `05_blueprint.json`). It does not invoke any LLM, prompt compiler, or creative planner.
4. **Ad-hoc Bypasses in Legacy Gates**: The only LLM call within the entire `scripts/` runtime is an optional, ad-hoc `ask_llm_judge` routine inside `scripts/gates/plan_gate.py:16-64`, which directly instantiates `OpenAI(api_key=...)` and silently falls back (skips) if `OPENAI_API_KEY` is missing or fails, bypassing the entire `ai/` platform subsystem.
5. **Development & Benchmark Gateway Only**: Upstream provider integration within `ai/` is limited to `OpenRouterProvider` (`ai/providers/openrouter.py`), which is explicitly flagged in code as a temporary development gateway (`production_default=False`), and `LocalSTTProvider` (`ai/speech/local_provider.py`) using local `faster-whisper`. All other canonical provider definitions (OpenAI, Anthropic, Gemini, ElevenLabs, Fal.ai) lack production execution adapters in `ai/providers/` and exist only as metadata descriptors or test fakes (`FakeProvider`).

---

## 2. Intended vs. Actual AI Flow

### 2.1 The Documented / Intended Flow (S28 Platform Vision)

The documented architecture (in `documentation/s28/`, `documentation/s28m/`, and `ARCHITECTURE_TRUTH.md`) describes an end-to-end multi-agent creative video generation engine:

```
[User Natural-Language Prompt]
              │
              ▼
   [IntentParser / BriefBuilder] ──────────► [Epistemic CreativeBrief]
              │                                      │
              ▼                                      ▼
     [ContextBuilder] ◄──── [Memory / Knowledge / Skills / Recipes]
              │
              ▼
     [NarrativePlanner] ───► [Beat Sheet & Narrative Arc]
              │
              ▼
     [RecipeSelector]  ────► [Canonical Recipe Binding]
              │
              ▼
     [CreativePlanner] ────► [Advisory CreativePlan (Scenes/Intents)]
              │
              ▼
    [CreativeTierPolicy] ──► [REUSE / COMPOSE / CREATE Decisions]
              │
              ▼
     [BlueprintCompiler] ──► [Authoritative BlueprintV2 / VideoDocument]
              │
              ▼
     [CapabilityRouter] ───► [ModelRouter / ToolGateway / Providers]
              │
              ▼
     [Render & Delivery]
```

### 2.2 The Actual Proven Flow

In the actual code repository, the flow bifurcates into two completely decoupled realities:

```
REALITY A: Active Product API & Worker Pipeline (PRODUCTION REACHABLE)
===================================================================================
[Client HTTP Request]
        │
        ├─► POST /projects/ (creates blank project on disk)
        ├─► POST /projects/{id}/intent (accepts strictly typed discriminated union AuthoringIntent)
        │         └─► scripts/execute_authoring_mutation.ts ──► UnifiedAuthoringSession
        │
        └─► POST /projects/{id}/runs (enqueues RunRecord in SQLite data/runs.db)
                  │
                  ▼
          [PipelineWorker] (scripts/core/worker.py)
                  │
                  ▼
          [scripts/pipeline.py] (State Machine advancing through 10 stages)
                  ├── Stage 1: asset_gate.py (validates files on disk)
                  ├── Stage 2: plan_gate.py (validates master_plan.md on disk; ad-hoc OpenAI fallback)
                  ├── Stage 3: taste_gate.py (deterministic regex on master_plan.md)
                  ├── Stage 4: validate_blueprint.py (checks 05_blueprint.json schema)
                  ├── Stage 5: motion_validator.py (checks timing & transforms)
                  ├── Stage 6: code_template_gate.py (verifies template imports)
                  ├── Stage 7: materialize_project.py (copies media to public/)
                  ├── Stage 8: probe_qc.py (runs npx remotion still)
                  ├── Stage 9: render_project.py (invokes RenderPlanner / Remotion CLI)
                  └── Stage 10: final_qc.py (FFprobe verification of out.mp4)

REALITY B: AI Intelligence Platform (TEST & DEV HARNESS ONLY)
===================================================================================
[Direct Python Invocation in scripts/run_creative_e2e.py or tests/ai/]
        │
        ├── CreativeBriefBuilder.build_brief() [ai/intent/brief_builder.py]
        ├── RecipeSelector.select_recipe() [ai/recipes/selector.py]
        ├── NarrativePlanner.plan() [ai/narrative/planner.py]
        ├── CreativePlanner.plan() [ai/planning/creative_planner.py]
        ├── CreativeTierPolicy.decide() [ai/planning/tier_policy.py]
        ├── BlueprintCompiler.compile() [ai/planning/compiler.py]
        ├── CapabilityRouter.route_and_execute() [ai/routing/capability_router.py]
        └── ModelRouter / OpenRouterProvider [ai/providers/openrouter.py]
```

**Evidence Citation**:
- `api/main.py:57-70`: Router registration contains zero creative or generation endpoints [`CODE_PROVEN`].
- `scripts/pipeline.py:221-520`: Pipeline main loop never calls or imports `ai.*` [`CODE_PROVEN`].
- `scripts/run_creative_e2e.py:99-310`: Test harness constructs the AI intelligence pipeline in-memory [`CODE_PROVEN`, `TEST_PROVEN`].

---

## 3. Mandatory Check E: Natural-Language Production Entrypoint Audit

### 3.1 Question Statement
> **Check E**: Does the Production API have a natural-language AI generation entrypoint?

### 3.2 Verbatim Audit of All HTTP Routers
A comprehensive inspection of all 34 endpoints registered across the 12 router modules in `api/` (`api/main.py:57-70`) yields:

| HTTP Method & Path | Router Module | Request Payload / Input Model | Accepts Freeform Natural Language? | Verdict |
|---|---|---|---|---|
| `POST /projects/` | `api/routers/projects.py:24` | `ProjectCreateRequest` (`workspace_id`, `project_name`, `template_id`) | No (Typed metadata strings only) | `NOT_NL` |
| `GET /projects/` | `api/routers/projects.py:46` | Query parameters (`workspace_id`, pagination) | No | `NOT_NL` |
| `GET /projects/{id}` | `api/routers/projects.py:58` | Path parameter | No | `NOT_NL` |
| `GET /projects/{id}/state` | `api/routers/projects.py:70` | Path parameter | No | `NOT_NL` |
| `POST /projects/{id}/runs` | `api/routers/runs.py:23` | `RunCreateRequest` (`idempotency_key`, optional configuration dict) | No (Execution trigger) | `NOT_NL` |
| `GET /projects/{id}/runs` | `api/routers/runs.py:59` | Query parameters | No | `NOT_NL` |
| `GET /projects/{id}/runs/{rid}` | `api/routers/runs.py:72` | Path parameter | No | `NOT_NL` |
| `POST /projects/{id}/runs/{rid}/cancel` | `api/routers/runs.py:84` | Path parameter | No | `NOT_NL` |
| `GET /projects/{id}/runs/{rid}/events` | `api/routers/runs.py:96` | Path parameter | No | `NOT_NL` |
| `GET /projects/{id}/document` | `api/routers/authoring.py:35` | Path parameter | No | `NOT_NL` |
| `POST /projects/{id}/mutate` | `api/routers/authoring.py:57` | `CanonicalMutationSchema` (typed AST operation) | No (Strict AST schema) | `NOT_NL` |
| `POST /projects/{id}/batch` | `api/routers/authoring.py:80` | `MutationBatchSchema` (list of typed AST operations) | No (Strict AST schema) | `NOT_NL` |
| `POST /projects/{id}/intent` | `api/routers/authoring.py:104` | `AuthoringRequestSchema` (`AuthoringIntentSchema`) | **No (Discriminated union of 14 typed AST intents)** | `NOT_NL` |
| `POST /projects/{id}/template` | `api/routers/authoring.py:135` | `TemplateInstantiationRequest` (`template_id`, `props`) | No (Typed template parameters) | `NOT_NL` |
| `POST /projects/{id}/undo` | `api/routers/authoring.py:165` | Path parameter | No | `NOT_NL` |
| `POST /projects/{id}/redo` | `api/routers/authoring.py:187` | Path parameter | No | `NOT_NL` |
| `POST /projects/{id}/assets` | `api/routers/assets.py:30` | Multipart file upload | No | `NOT_NL` |
| `GET /projects/{id}/assets` | `api/routers/assets.py:55` | Query parameters | No | `NOT_NL` |
| `DELETE /projects/{id}/assets/{aid}` | `api/routers/assets.py:70` | Path parameter | No | `NOT_NL` |
| `GET /projects/{id}/artifacts` | `api/routers/artifacts.py:25` | Query parameters | No | `NOT_NL` |
| `GET /projects/{id}/review` | `api/routers/artifacts.py:50` | Path parameter | No | `NOT_NL` |
| `POST /projects/{id}/review/approve` | `api/routers/artifacts.py:65` | `ReviewDecisionRequest` | No | `NOT_NL` |
| `POST /projects/{id}/review/reject` | `api/routers/artifacts.py:80` | `ReviewDecisionRequest` | No | `NOT_NL` |
| `GET /projects/{id}/outputs/{oid}` | `api/routers/outputs.py:25` | Path parameter | No | `NOT_NL` |
| `GET /gates/{id}/status` | `api/routers/gates.py:30` | Path parameter | No | `NOT_NL` |
| `POST /gates/{id}/start/{stg}` | `api/routers/gates.py:45` | Path parameter | No | `NOT_NL` |
| `POST /gates/{id}/finish/{stg}` | `api/routers/gates.py:60` | Path parameter | No | `NOT_NL` |
| `POST /gates/{id}/approve/{gt}` | `api/routers/gates.py:75` | Path parameter | No | `NOT_NL` |
| `POST /gates/{id}/reject/{gt}` | `api/routers/gates.py:90` | Path parameter | No | `NOT_NL` |
| `POST /render/{id}` | `api/routers/render.py:25` | Path parameter (deprecated adapter) | No | `NOT_NL` |
| `GET /blueprint/{id}` | `api/routers/blueprint.py:20`| Path parameter | No | `NOT_NL` |
| `POST /blueprint/{id}/blueprint` | `api/routers/blueprint.py:35`| Raw `BlueprintV2` JSON document | No | `NOT_NL` |
| `GET /brand/{id}`, `POST /brand/{id}` | `api/routers/brand.py:20` | Brand token configuration dict | No | `NOT_NL` |
| `GET /health/*` | `api/routers/health.py:15` | None | No | `NOT_NL` |

### 3.3 Answer to Check E
**NO** (`CODE_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`).
The production API has **zero** natural-language AI generation entrypoints. Every endpoint exposed by `api/main.py` requires pre-existing stable IDs, uploaded files, or strongly typed AST schemas. There is no route that takes a prompt such as `"Create a video about coffee"` and triggers video generation or plan formulation.

---

## 4. Prompt Intake, Input Handling & Epistemic Boundaries

### 4.1 `IntentParser` (`ai/intent/parser.py`)
`IntentParser` is designed to translate raw user prompts into structured `IntentParseResult` contracts.
- **Implementation Reality**: It is implemented as a pure, deterministic keyword and regex scanner (`ai/intent/parser.py:30-518`).
- **Zero LLM Invocation**: It does not make any API or model calls. It parses keywords like `"vertical"`, `"9:16"`, `"reels"`, `"tiktok"`, `"voiceover"`, `"music"`, and Arabic equivalents (`"فيديو عمودي"`, `"ريلز"`, `"تعليق صوتي"`).
- **Epistemic Tracking**: Assigns explicit `FieldProvenance` (`EXPLICIT`, `INFERRED`, `DEFAULTED`, `UNKNOWN`) to every parsed property (`ai/intent/parser.py:9-16`).
- **Contradiction Detection**: Detects direct conflicts (e.g., `SILENT` + `VOICEOVER`) and flags them in `detected_contradictions` without silent resolution (`ai/intent/parser.py:51`).

### 4.2 `CreativeBriefBuilder` (`ai/intent/brief_builder.py`)
Wraps `IntentParser.parse()` to produce a canonical `CreativeBrief`:
- Assembles `CreativeIntent` (`ai/intent/brief_builder.py:59-71`).
- Assembles `CreativeConstraints` (`ai/intent/brief_builder.py:74-84`).
- Packages provenance record with `model_id="deterministic_intent_pipeline_v1"` (`ai/intent/brief_builder.py:89`).
- **Production Caller**: `UNKNOWN` / None (`CODE_PROVEN`). Only called within test files (`tests/ai/intent/test_intent_parser.py`, `tests/ai/e2e/test_full_creative_e2e_matrix.py`) and offline evaluation runners (`scripts/run_creative_e2e.py:72`, `ai/regression/runner.py:53`).

---

## 5. Audit of What AI Actually Reads

When the AI Subsystem is exercised via test harnesses or benchmark scripts, its knowledge and context retrieval mechanisms function as follows:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             ContextBuilder                                  │
│                          (ai/context/builder.py)                            │
├─────────────────────────────────────────────────────────────────────────────┤
│  Sub-Retriever                 Target Source               Production Caller │
├─────────────────────────────────────────────────────────────────────────────┤
│  SystemPolicyRetriever       Static configuration files    NONE (Tests only) │
│  SharedConfigRetriever       violations_config.json        NONE (Tests only) │
│  ProjectFactRetriever        StateStore / 01_manifest.json NONE (Tests only) │
│  MemoryRetriever             PostgreSQL / In-memory memory NONE (Tests only) │
│  KnowledgeRetriever          KnowledgeRegistry (in-memory) NONE (Tests only) │
│  RequestRetriever            User prompt payload           NONE (Tests only) │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.1 Memory Selection Mechanisms (`ai/memory/`)
- **Architecture**: `MemoryService` (`ai/memory/facade.py:34-110`) manages semantic, episodic, and procedural memory.
- **Persistence**: Employs `PostgresMemoryRepository` (`scripts/core/memory/postgres_memory_repository.py`) in production-target designs and `InMemoryMemoryRepository` in tests.
- **Tenant Isolation**: Strictly enforces `TrustedTenantContext(workspace_id, project_id)`. Cross-workspace queries raise `TenantIsolationViolationError`.
- **Production Status**: `UNREACHABLE_FROM_PRODUCT`. No production HTTP route or background pipeline task initializes `MemoryService`.

### 5.2 Knowledge Selection Mechanisms (`ai/knowledge/`)
- **Architecture**: `KnowledgeRouter` (`ai/knowledge/router.py`) coordinates indexing and retrieval over domain knowledge descriptors.
- **Indexing**: `KnowledgeIndexer` indexes markdown and structured documents.
- **Scoring**: Uses `BaseSemanticScorer` or deterministic token overlap.
- **Production Status**: `UNREACHABLE_FROM_PRODUCT`. Zero production callers exist.

### 5.3 Skill Selection Mechanisms (`ai/skills/`)
- **Architecture**: `SkillRouter` (`ai/skills/router.py`) resolves active skills from `SkillRegistry` (`ai/skills/registry.py`).
- **Skill Definitions**: Loaded via `SkillLoader` (`ai/skills/loader.py`) from both canonical typed Python objects (`get_canonical_skills()`) and `SKILL.md` markdown files with YAML frontmatter.
- **Production Status**: `UNREACHABLE_FROM_PRODUCT`. Zero production callers exist.

### 5.4 Recipe Selection Mechanisms (`ai/recipes/`)
- **Architecture**: `RecipeSelector` (`ai/recipes/selector.py:35-150`) scores candidate recipes against a `CreativeBrief`.
- **Catalog**: Loaded by `RecipeRegistry` (`ai/recipes/registry.py`) from all 18 JSON files in `recipes/*.json`.
- **Scoring Logic**: Evaluates hard constraints (aspect ratio, duration, audio mode) then applies weighted scoring on video type matching, style matching, and tone matching.
- **Production Status**: `UNREACHABLE_FROM_PRODUCT`. Zero production callers exist.

---

## 6. Deterministic vs. LLM Boundaries

The codebase exhibits a strict, intentional separation between deterministic logic and LLM reasoning:

| Subsystem / Component | Boundary Nature | Logic Implementation | LLM Role |
|---|---|---|---|
| **Intent Parsing** | Deterministic | Regex, token scanning, keyword matching (`ai/intent/parser.py`) | None |
| **Recipe Selection** | Deterministic | Hard constraint elimination + weighted scoring (`ai/recipes/selector.py`) | None |
| **Taste Engine** | Deterministic | AST pattern linting, layout symmetry, rule evaluation (`ai/taste/engine.py`) | None |
| **Creative Tier Policy** | Deterministic | Rules engine selecting `REUSE`, `COMPOSE`, or `CREATE` (`ai/planning/tier_policy.py`) | None |
| **Blueprint Compilation** | Deterministic | AST generation compiling `CreativePlan` $\to$ `BlueprintV2` (`ai/planning/compiler.py`) | None |
| **Pipeline Gates** | Deterministic | File validation, schema checking, FFmpeg probe (`scripts/gates/`) | Ad-hoc LLM judge in `plan_gate.py` (optional, skipped if key absent) |
| **Narrative Planning** | Hybrid / LLM-ready | Template beat layout with LLM prompt generator (`ai/narrative/planner.py`) | LLM completion when provider wired; deterministic fallbacks in tests |
| **Creative Planning** | Hybrid / LLM-ready | Advisory plan synthesis (`ai/planning/creative_planner.py`) | LLM completion when provider wired; deterministic fallbacks in tests |
| **Candidate QC Gate** | Deterministic | Subprocess rendering + AST validation (`ai/candidates/gates/`) | None |
| **Capability Execution** | Hybrid | `ToolGateway` is 100% deterministic code; `ModelRouter` delegates to LLM/STT | STT via local Whisper; completions via OpenRouter |

---

## 7. Routing & Provider Execution Reality

### 7.1 `ModelRouter` (`ai/routing/router.py`)
- **Purpose**: Central routing engine that ranks models based on hard constraints, latency tiers, quality targets, and cost estimates.
- **Routing Decision**: Returns a `ModelSelection` containing primary model and ordered fallbacks.
- **Execution Reality**: In `execute_model_capability()` (`ai/routing/router.py:672-708`), the **ONLY** capability currently dispatched to an execution engine is `CapabilityType.SPEECH_TO_TEXT`. Any other model capability returns:
  ```python
  AIError(code=AIErrorCode.CAPABILITY_UNAVAILABLE, message=f"Model capability '{cap_id}' is not yet supported in ModelRouter.")
  ```
- **Production Reachability**: `UNREACHABLE_FROM_PRODUCT` [`CODE_PROVEN`].

### 7.2 Upstream Provider Implementations (`ai/providers/`)
A survey of `ai/providers/` reveals:
1. `OpenRouterProvider` (`ai/providers/openrouter.py`):
   - Only live LLM provider adapter in `ai/providers/`.
   - Wired to OpenRouter API (`https://openrouter.ai/api/v1`) using `httpx.AsyncClient`.
   - Explicitly configured with `environment="development"` and `production_default=False` (`ai/providers/openrouter.py:66-67`).
   - Defaults to `google/gemini-2.5-flash`.
   - Enforces pre-flight spend caps (`DEFAULT_MAX_SPEND_PER_CALL = Decimal("0.50")`) and concurrency limits (`DEFAULT_MAX_CONCURRENCY = 3`).
2. `FakeProvider` (`ai/providers/fake.py`):
   - In-memory mock returning synthetic responses for test fixtures.
3. Native Providers (OpenAI, Anthropic, Gemini, ElevenLabs, Fal.ai):
   - **Zero** execution adapters exist in `ai/providers/` [`CODE_PROVEN`].
   - They exist solely as data entries in `CANONICAL_PROVIDERS` (`ai/providers/definitions.py:23-95`).

---

## 8. Tenant Scoping and Isolation in the AI Subsystem

The AI Subsystem implements comprehensive multi-tenant isolation mechanisms, although they are currently exercised only within test suites:

1. **`TrustedTenantContext`** (`ai/memory/models.py:28-55`, `ai/tools/types.py:35-85`):
   - Requires immutable `workspace_id`, `actor_id`, and `role`.
   - Server-side derived; client claims in HTTP headers or payloads are strictly rejected.
2. **Gateway Tenant Enforcement** (`ai/tools/gateway.py:320-352`):
   - Stage 4 validates request `workspace_id` against `ctx.workspace_id`.
   - Fails closed with `TenantScopeViolationError` if cross-tenant data access is detected.
   - For `PROJECT`-scoped capabilities, verifies `ctx.can_access_project(project_id)`.
   - For `SYSTEM`-scoped capabilities, requires `ctx.is_admin`.
3. **Storage Boundary Confinement** (`ai/tools/gateway.py:380-383`, `ai/tools/adapters/mcp.py:105-125`):
   - Path resolution validates `validate_project_id()`.
   - Confines all writes to `projects/{project_id}/` or `data/storage/{workspace_id}/`.
   - Detects and rejects directory traversal attacks (`..`).
4. **SSRF and Network Egress Guardrails** (`ai/tools/gateway.py:79-115`):
   - Blocks private RFC1918 addresses (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), loopback (`127.0.0.1`), link-local, cloud metadata endpoints (`169.254.169.254`), and forbidden URI schemes (`file://`, `ftp://`, `gopher://`).

---

## 9. File & Symbol Evidence Index

| File Path | Symbol / Function / Class | Line Range | Architectural Function | Classification |
|---|---|---|---|---|
| `api/main.py` | `FastAPI(lifespan=...)` | 45-70 | Mounts all 12 routers; zero AI routes | `CODE_PROVEN` |
| `api/routers/runs.py` | `create_run` | 23-56 | Enqueues run; zero AI interaction | `CODE_PROVEN` |
| `api/routers/authoring.py` | `apply_intent` | 104-132 | Accepts typed AuthoringIntent; no NL | `CODE_PROVEN` |
| `contracts/authoring.ts` | `AuthoringIntentSchema` | 273-288 | Discriminated union of 14 typed AST intents | `CODE_PROVEN` |
| `authoring/intent-planner.ts` | `IntentPlanner` | 1-50 | Pure deterministic intent translator | `CODE_PROVEN` |
| `scripts/pipeline.py` | `main` | 221-520 | Pipeline orchestrator; zero AI imports | `CODE_PROVEN` |
| `scripts/gates/plan_gate.py` | `ask_llm_judge` | 16-64 | Ad-hoc OpenAI call; silent fallback | `CODE_PROVEN` |
| `ai/intent/parser.py` | `IntentParser` | 30-80 | Deterministic regex/token intent parser | `CODE_PROVEN` |
| `ai/intent/brief_builder.py` | `CreativeBriefBuilder` | 25-105 | Builds CreativeBrief; 0 prod callers | `CODE_PROVEN` |
| `ai/planning/creative_planner.py`| `CreativePlanner` | 58-115 | Advisory plan generator; 0 prod callers | `CODE_PROVEN` |
| `ai/planning/compiler.py` | `BlueprintCompiler` | 62-443 | Translates CreativePlan $\to$ BlueprintV2 | `CODE_PROVEN` |
| `ai/routing/router.py` | `ModelRouter` | 67-140 | Model ranking & routing engine | `CODE_PROVEN` |
| `ai/routing/router.py` | `execute_model_capability` | 672-708 | STT only; completions unhandled | `CODE_PROVEN` |
| `ai/routing/capability_router.py`| `CapabilityRouter` | 69-140 | Top-level capability dispatcher | `CODE_PROVEN` |
| `ai/tools/gateway.py` | `ToolGateway.execute` | 258-525 | 15-stage capability execution pipeline | `CODE_PROVEN` |
| `ai/providers/openrouter.py` | `OpenRouterProvider` | 40-70 | Development-only OpenRouter gateway | `CODE_PROVEN` |
| `ai/providers/definitions.py` | `CANONICAL_PROVIDERS` | 23-95 | Provider metadata list; 0 native adapters | `CODE_PROVEN` |
| `ai/speech/local_provider.py` | `LocalSTTProvider` | 40-120 | Native faster-whisper STT provider | `CODE_PROVEN` |
| `scripts/run_creative_e2e.py` | `FullCreativeE2ERunner` | 99-310 | In-memory test harness wiring AI stack | `TEST_PROVEN` |
| `.github/workflows/remediation-ci.yml`| `python-tests` job | 125-127 | Pytest command completely omits `tests/ai` | `CI_PROVEN` |

---

## 10. Conclusion & Strategic Assessment

1. **Architectural Status**: The AI Subsystem in `ai/` is an advanced, high-fidelity **dormant platform layer** (Active Development). It possesses robust contract modeling, epistemic tracking, and capability definitions, but it has not been wired into the live customer-facing API or worker execution loops.
2. **Product Journey Gap**: A customer submitting requests through the REST API cannot experience AI-driven video creation today. All pipeline execution relies on pre-rendered or pre-authored blueprints and manifests created on disk.
3. **Remediation Direction**: To bridge the AI Subsystem into production without destabilizing the frozen baseline, a dedicated asynchronous ingestion endpoint (e.g. `POST /projects/generate`) must be constructed that invokes `CreativeBriefBuilder` $\to$ `NarrativePlanner` $\to$ `CreativePlanner` $\to$ `BlueprintCompiler` within a managed background task before initiating pipeline rendering.


---


<a name='part-2-ground-truth-references-knowledge-skills--recipes'></a>

## Part 2: Ground Truth, References, Knowledge, Skills & Recipes


> *Original Source: `documentation/reality_context_pack/07_GROUND_TRUTH_REFERENCES_KNOWLEDGE_SKILLS_RECIPES_REALITY.md`*


### Sub-Report Title: 07 — Ground Truth, References, Knowledge, Skills & Recipes Reality Report


- **Baseline Git SHA**: `90ec3de8d47494d5940d5cd1f9ed9a8e274ef6e1`
- **Branch**: `main`
- **Report Version**: 1.0.0
- **Last Updated**: 2026-10-07
- **Scope**: Rigorous Demarcation of Root `/ground-truth/`, ML Evaluation Ground Truth, `references/`, Knowledge Platform, Skills Platform, Recipes Platform, and Template Registry
- **Evidence Standards**: `CODE_PROVEN`, `TEST_PROVEN`, `CI_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`, `DOCUMENTATION_ONLY`, `INFERRED`, `UNKNOWN`

---

## 1. Executive Summary & Architectural Verdict

A critical source of confusion in this codebase is the overloaded terminology surrounding "ground truth", "references", "knowledge", "skills", and "recipes". Previous documentation and agent prompt files frequently conflate root filesystem indexes with machine learning evaluation ground truths, or treat human playbooks as runtime configuration authorities.

Rigorous static code analysis, execution tracing, and CI verification establish a clear taxonomy and architectural truth across seven distinct concepts:

1. **Root `/ground-truth/` is NOT an ML Dataset**: Root `/ground-truth/` is an **auto-generated derivative documentation and index folder** created by `scripts/generators/build_ground_truth.py`. It serves as a human/agent navigation index for templates, assets, and tools.
2. **ML Evaluation Ground Truth is Strictly Isolated**: ML evaluation datasets reside inside `ai/evals/datasets.py` and `ai/regression/datasets.py`, using immutable `EvalExample` pairs with SHA-256 hashes for model benchmarking. They share zero code or storage with `/ground-truth/`.
3. **`references/` Represents Static Playbooks**: Located at Level 5 of the architectural hierarchy, `references/` contains human and agent playbooks, SOPs, and taste matrices. It is read-only reference documentation.
4. **Knowledge Platform Reads from `references/`**: The modern Knowledge Platform (`ai/knowledge/`) maps typed `KnowledgeDescriptor` objects with cryptographic hashes to files in `references/`, treating knowledge purely as informational context rather than runtime authority.
5. **Skills Support Both Typed & Markdown Definitions**: The Skills Platform (`ai/skills/`) supports loading from both statically typed Python `SkillDefinition` objects and `.agents/skills/**/SKILL.md` markdown files with YAML frontmatter.
6. **`RecipeRegistry` Actively Consumes `recipes/*.json`**: Upon initialization, `RecipeRegistry` auto-discovers and migrates all 18 JSON recipe files in `recipes/` into typed `RecipeDefinition` objects.
7. **`template_catalog.json` is a Metadata Derivative, NOT an Authority**: The canonical machine-readable authority for templates is `registry/template-registry-data.json` (105 templates), while `ground-truth/template_catalog.json` (289 entries) is a downstream compatibility catalog.

---

## 2. Strict Demarcation of the Seven Core Concepts

```
┌───────────────────────────────────────────────────────────────────────────────────────────────┐
│                               SEVEN-WAY ARCHITECTURAL DEMARCATION                             │
├─────────────────────────┬──────────────────────────┬──────────────────────┬───────────────────┤
│ Concept / Subsystem     │ Location & Files         │ Primary Function     │ Authority Level   │
├─────────────────────────┼──────────────────────────┼──────────────────────┼───────────────────┤
│ 1. Root /ground-truth/  │ ground-truth/*.json, .md │ Auto-generated index │ Derivative / Read │
│ 2. ML / Eval GT         │ ai/evals/, regression/   │ Benchmark test pairs │ Test Fixture      │
│ 3. References           │ references/**/*.md       │ Human/Agent SOPs     │ Ref Doc (L5)      │
│ 4. Knowledge Platform   │ ai/knowledge/            │ Context retrieval    │ Advisory (L4)     │
│ 5. Skills Platform      │ ai/skills/, .agents/     │ Operational runbooks │ Advisory (L4)     │
│ 6. Recipes Platform     │ ai/recipes/, recipes/    │ Video archetypes     │ Canonical Catalog │
│ 7. Template Registry    │ registry/, templates/    │ Component contracts  │ AUTHORITATIVE (L1)│
└─────────────────────────┴──────────────────────────┴──────────────────────┴───────────────────┘
```

### Concept 1: Root `/ground-truth/` Directory
- **Path**: `/home/eng_Momen/Projects/المشروع الحالي/Video maker/ground-truth/`
- **Files**: 14 files (`template_catalog.json`, `ASSET_INDEX.json`, `TEMPLATE_INDEX.md`, `CINEMATIC_INDEX.md`, `MCP_INDEX.md`, `PLAYBOOKS_INDEX.md`, `RECIPES_INDEX.md`, `TOOLS_INDEX.md`, `VOCAB_REMAP.md`, `CANONICAL_PATHS.json`, `TEMPLATE_DUPLICATES.md`, `adapter_family_candidates.json`, `orchestration_resolved_spec.json`, `collections/`).
- **Nature**: Derivative cache and navigation index generated by scanning the workspace.
- **Producer**: `scripts/generators/build_ground_truth.py`.
- **Enforcement**: Validated in CI via `scripts/validators/check_ground_truth_sync.py --check`. Fails CI if uncommitted diffs exist after running generator.

### Concept 2: ML / Evaluation Ground Truth
- **Path**: `ai/evals/datasets.py`, `ai/regression/datasets.py`, `ai/contracts/evals.py`
- **Nature**: Immutable benchmark datasets for algorithmic evaluation (model routing, DAG planning, tool selection, STT transcription, vision extraction).
- **Structure**: Strongly-typed `EvalDatasetContract` wrapping collections of `EvalExample(input_payload=..., expected_output=..., min_quality_score=...)`.
- **Integrity**: Every dataset is stamped with a deterministic SHA-256 content hash (`EvalDatasetContract.compute_content_hash()`).
- **Isolation**: Does not touch or read `/ground-truth/`. Completely separate runtime domain.

### Concept 3: `references/` Directory
- **Path**: `/home/eng_Momen/Projects/المشروع الحالي/Video maker/references/`
- **Subdirectories**: `1_playbooks/`, `2_sops/`, `3_engineering/`, `4_taste_engine/`, plus `README.md` and `ROUTER.md`.
- **Nature**: Static developer and AI agent documentation (Level 5 in Source of Truth Hierarchy).
- **Producers**: Human engineers.
- **Consumers**: Human developers, prompt engineering context, and `KnowledgeLoader`.

### Concept 4: Knowledge Platform (`ai/knowledge/`)
- **Path**: `ai/knowledge/` (`router.py`, `loader.py`, `registry.py`, `indexer.py`, `contracts.py`)
- **Nature**: Programmatic retrieval subsystem for the S28 AI platform.
- **Mechanism**: `KnowledgeLoader` maps canonical seed descriptors (`get_canonical_descriptors()`) to files in `references/` (e.g. `references/1_playbooks/ffmpeg_recipes.md`), verifying exact SHA-256 hashes (`KnowledgeHashMismatchError`).
- **Authority**: Explicit invariant in `ai/knowledge/loader.py:7`: *"Knowledge = Information & Experience (Knowledge ≠ Runtime Authority)"*.

### Concept 5: Skills Platform (`ai/skills/`)
- **Path**: `ai/skills/` (`router.py`, `loader.py`, `registry.py`, `context.py`, `contracts.py`) and `.agents/skills/`
- **Nature**: Behavioral guidelines and tool orchestration protocols.
- **Mechanism**: Loaded by `SkillLoader` through two paths:
  1. Statically typed Python instances (`SkillLoader.get_canonical_skills()`).
  2. YAML frontmatter parsing from markdown (`SkillLoader.load_from_markdown()`).
- **Authority**: Advisory operational context; skills cannot bypass gateway security or database authority.

### Concept 6: Recipes Platform (`ai/recipes/` & `recipes/`)
- **Path**: `recipes/*.json` (18 files) and `ai/recipes/` (`registry.py`, `selector.py`, `evaluator.py`, `contracts.py`)
- **Nature**: Declarative templates defining video structures, scene sequences, timing constraints, platforms, and audio modes.
- **Mechanism**: `RecipeRegistry` auto-loads all 18 files from disk, migrates legacy provider strings to provider-neutral capability IDs, and registers them into memory.

### Concept 7: Template Registry
- **Path**: `registry/` (`template-registry-data.json`, `template-registry.tsx`, `template-aliases.ts`), `contracts/template-runtime-contract.json`, and `templates/`
- **Nature**: **The sole authoritative component registry for video rendering**.
- **Canonical Authority**: `registry/template-registry-data.json` defines all 105 valid templates, categories, and props.
- **Implementation Authority**: `registry/template-registry.tsx` binds template IDs to React/Remotion component exports.
- **Mutation Authority**: Governed strictly by `PromotionService` (`ai/candidates/promotion_service.py`) and `TemplateRegistryPublisher` (`scripts/core/template_registry_publisher.py`).

---

## 3. Mandatory Check J: Exact Function of Root `/ground-truth/`

### 3.1 Question Statement
> **Check J**: What is the exact function of root `/ground-truth/`?

### 3.2 Code Evidence & Execution Tracing
In `scripts/generators/build_ground_truth.py:2-4`:
```python
"""build_ground_truth.py — Generates ground-truth indices from actual disk scan.
Zero-hardcode: every line is from a real scan. Exit 1 on failure."""
```
`build_ground_truth.py` executes disk discovery over the repository:
1. Regex parses `registry/template-registry.tsx` to discover registered templates and writes `ground-truth/template_catalog.json`, `ground-truth/TEMPLATE_INDEX.md`, and categorized sub-indexes in `ground-truth/collections/`.
2. Inspects `assets/` to construct `ground-truth/ASSET_INDEX.json`.
3. Scans MCP servers to produce `ground-truth/MCP_INDEX.md` and `ground-truth/TOOLS_INDEX.md`.
4. Indexes `references/1_playbooks/` to produce `ground-truth/PLAYBOOKS_INDEX.md`.
5. Indexes `recipes/` to produce `ground-truth/RECIPES_INDEX.md`.

In `scripts/validators/check_ground_truth_sync.py:24-49`:
- `--check` executes `build_ground_truth.py` and inspects `git status --porcelain ground-truth/`. If any file in `ground-truth/` has changed or drifted, it fails closed with exit code 1.
- This is executed in required CI via `.github/workflows/remediation-ci.yml:82` and `scripts/ci/run_required_checks.sh:21`.

### 3.3 Answer to Check J
Root `/ground-truth/` is an **auto-generated derivative documentation and index folder** [`CODE_PROVEN`, `CI_PROVEN`]. Its exact function is to provide human developers and AI coding agents with pre-indexed, synchronized markdown and JSON summaries of templates, assets, MCP tools, and playbooks. It is **NOT** a machine learning training dataset, **NOT** an evaluation ground truth, and **NOT** a production runtime authority.

---

## 4. Mandatory Check K: Active Production Consumers of `/ground-truth/`

### 4.1 Question Statement
> **Check K**: Which files in `/ground-truth/` have active Production consumers?

### 4.2 Comprehensive Audit of All 14 Files

| File in `ground-truth/` | Callers / References Found | Runtime Classification | Active Production Consumer? |
|---|---|---|---|
| `template_catalog.json` | `ai/planning/reuse_engine.py:49`, `scripts/core/template_registry_publisher.py:94`, `scripts/maintenance/template_router.py:15` | `TEST_ONLY` / Compatibility Publisher | **NO** (Production API & pipeline bypass this file) |
| `ASSET_INDEX.json` | `scripts/gates/asset_gate.py:44`, `scripts/core/authority_matrix.py:35` | `COMPATIBILITY_ONLY` (Only checked if asset has `mcp_fetch` provenance) | **YES (CONDITIONAL COMPATIBILITY GATE)** |
| `TEMPLATE_INDEX.md` | `scripts/validators/template_lint.py:126`, `scripts/gates/motion_validator.py:191` | Diagnostic & Lint Only | **NO** (Only cited in Arabic error message string) |
| `CINEMATIC_INDEX.md` | `scripts/validators/template_lint.py:140` | Validation Tool | **NO** |
| `CANONICAL_PATHS.json` | Zero callers | `DEPRECATED_UNCONSUMED` | **NO** |
| `MCP_INDEX.md` | Zero runtime callers | `DOCUMENTATION_ONLY` | **NO** |
| `PLAYBOOKS_INDEX.md` | `scripts/archive/stitch_skill.py:20` | `ARCHIVE_ONLY` | **NO** |
| `RECIPES_INDEX.md` | Zero runtime callers | `DOCUMENTATION_ONLY` | **NO** |
| `TEMPLATE_DUPLICATES.md` | Zero runtime callers | `DOCUMENTATION_ONLY` | **NO** |
| `TOOLS_INDEX.md` | Zero runtime callers | `DOCUMENTATION_ONLY` | **NO** |
| `VOCAB_REMAP.md` | Zero runtime callers | `DOCUMENTATION_ONLY` | **NO** |
| `adapter_family_candidates.json` | `scripts/archive/phase13/*`, `scripts/remotion_interop/*` | `HISTORICAL_EVIDENCE` | **NO** |
| `orchestration_resolved_spec.json` | Zero runtime callers | `DOCUMENTATION_ONLY` | **NO** |
| `collections/*.md` | Zero runtime callers | `DOCUMENTATION_ONLY` | **NO** |

### 4.3 Deep Audit of `ASSET_INDEX.json` in `asset_gate.py`
In `scripts/gates/asset_gate.py:44-60`:
```python
index_path = repo_root / "ground-truth" / "ASSET_INDEX.json"
...
if item.provenance == Provenance.MCP_FETCH:
    # 1. Check cache_checked
    # 2. Check if ASSET_INDEX has a match
```
If a project's `01_manifest.json` contains assets fetched via legacy MCP (`Provenance.MCP_FETCH`), `asset_gate.py` reads `ground-truth/ASSET_INDEX.json` to verify that the asset metadata matches the index. However, user-uploaded assets (`Provenance.USER_UPLOAD`) bypass this check entirely (`asset_gate.py:51-52`).

### 4.4 Answer to Check K
Exactly **one** file in `/ground-truth/` has a conditional runtime gate consumer: **`ASSET_INDEX.json`** is read by `scripts/gates/asset_gate.py:44` during Stage 1 of the pipeline strictly when processing assets with `MCP_FETCH` provenance [`CODE_PROVEN`]. All other 13 files in `/ground-truth/` have **zero active production consumers** on the runtime execution path.

---

## 5. Mandatory Check L: Authority vs. Metadata Role of `template_catalog.json`

### 5.1 Question Statement
> **Check L**: Is `template_catalog.json` an authority or metadata input?

### 5.2 Architectural Proof & Citation
In `scripts/core/template_registry_publisher.py:6-11`, the Single Source of Truth hierarchy is explicitly codified:
```python
"""
Single Source of Truth:
- registry/template-registry-data.json is the CANONICAL machine-readable authority.
- contracts/template-runtime-contract.json and registry/template-aliases.ts are GENERATED derivatives.
- registry/template-registry.tsx is the concrete Remotion component binding authority.
- ground-truth/template_catalog.json is the compatibility catalog.
- templates/<category>/<ComponentName>.tsx is the production component package.
"""
```

Furthermore:
1. `registry/template-registry-data.json` contains exactly **105 validated canonical templates** governed by strict Zod/Pydantic schemas [`CODE_PROVEN`].
2. `ground-truth/template_catalog.json` contains **289 entries**, generated by regex pattern matching across `registry/template-registry.tsx` (`scripts/generators/build_ground_truth.py:46-60`).
3. When a new candidate template is promoted via `CandidatePromotionService.promote()`, `TemplateRegistryPublisher` mutates `template-registry-data.json` first, regenerates TypeScript bindings, and then updates `ground-truth/template_catalog.json` purely as a downstream compatibility metadata catalog (`template_registry_publisher.py:94`).

### 5.3 Answer to Check L
`template_catalog.json` is strictly a **metadata input / compatibility derivative**, **NOT** an authority [`CODE_PROVEN`]. The canonical authority for template definitions is `registry/template-registry-data.json`.

---

## 6. Mandatory Check M: Consumption of `recipes/*.json` by `RecipeRegistry`

### 6.1 Question Statement
> **Check M**: Does `RecipeRegistry` consume `recipes/*.json` in practice?

### 6.2 Code Evidence
In `ai/recipes/registry.py:105-125`:
```python
class RecipeRegistry:
    def __init__(self, recipe_dir: Optional[Path] = None, auto_load: bool = True) -> None:
        self.recipe_dir = recipe_dir or (Path(__file__).resolve().parent.parent.parent / "recipes")
        self._recipes: Dict[str, RecipeDefinition] = {}
        self._legacy_provider_audit: Dict[str, List[str]] = {}

        if auto_load and self.recipe_dir.exists():
            self.load_from_directory(self.recipe_dir)

    def load_from_directory(self, dir_path: Path) -> None:
        json_files = sorted(dir_path.glob("*.json"))
        for json_path in json_files:
            if json_path.name == "schema.json":
                continue  # Skip legacy draft schema
            recipe = self._migrate_recipe_file(json_path)
            self.register(recipe)
```

The repository root contains exactly 18 production recipe JSON files in `recipes/`:
- `agent-browser-proof.json`, `avatar-explainer.json`, `avatar-hook-broll.json`, `avatar-insta-split.json`, `avatar-product-walkthrough.json`, `avatar-vo-broll.json`, `captioned-talking-head.json`, `dynamic-montage-ad.json`, `faceless-broll-ad.json`, `living-canvas-explainer.json`, `longform-repurpose.json`, `misotts-article-sprint.json`, `motion-collage-explainer.json`, `motion-graphics.json`, `review-conquest-compilation.json`, `screencast-demo.json`, `tabletop-levels-explainer.json`, `ugc-ai-ad.json`.

Upon instantiation, `RecipeRegistry` loads all 18 files, audits any legacy hardcoded providers (e.g. OpenAI, HeyGen) via `_audit_legacy_providers()`, cleans them, normalizes platforms and aspect ratios, and registers them into memory as validated `RecipeDefinition` objects.

### 6.3 Answer to Check M
**YES** (`CODE_PROVEN`, `TEST_PROVEN`).
`RecipeRegistry` actively consumes and parses all 18 JSON files in `recipes/*.json` in practice.

---

## 7. Mandatory Check N: Skills Runtime Loading Mechanism

### 7.1 Question Statement
> **Check N**: Does Skills runtime load from typed definitions, markdown, or both?

### 7.2 Code Evidence
In `ai/skills/loader.py`:
1. **Markdown Loading with YAML Frontmatter**:
   `SkillLoader.load_from_markdown(markdown_path)` (`ai/skills/loader.py:62-112`) reads markdown files from disk (e.g. `.agents/skills/**/SKILL.md`), extracts YAML frontmatter via regex `r"^---\s*\n(.*?)\n---\s*\n(.*)$"`, parses metadata, and validates the dictionary against `SkillDefinition.model_validate(raw_dict)`.
2. **Statically Typed Definitions**:
   `SkillLoader.get_canonical_skills()` (`ai/skills/loader.py:115-302`) programmatically returns a list of pre-constructed Python `SkillDefinition` objects (`skill_motion_typography`, `skill_speech_alignment`, `skill_broll_composition`, `skill_talking_head_framing`, `skill_continuous_canvas`, `skill_sound_design`, `skill_taste_enforcement`).
3. **Registry Loading**:
   `SkillLoader.load_canonical_catalog(registry)` (`ai/skills/loader.py:304-309`) registers the canonical typed skills directly into `SkillRegistry`.

### 7.3 Answer to Check N
The Skills runtime loads from **BOTH** typed Python definitions and markdown files with YAML frontmatter [`CODE_PROVEN`].

---

## 8. Cross-Subsystem Governance & Authority Matrix

| Subsystem | Primary Artifact | Producer | Mutation Rights | Verification in CI | Authority Level |
|---|---|---|---|---|---|
| **Template Authority** | `registry/template-registry-data.json` | PromotionService | Automated via publisher | `npm run test:contracts` | **Canonical Authority** |
| **Component Binding** | `registry/template-registry.tsx` | PromotionService | Automated via publisher | `npx tsc --noEmit` | **Implementation Authority** |
| **Compatibility Catalog**| `ground-truth/template_catalog.json` | `build_ground_truth.py` | Auto-generated | `check_ground_truth_sync.py` | **Derivative Metadata** |
| **Asset Index** | `ground-truth/ASSET_INDEX.json` | `build_ground_truth.py` | Auto-generated | `check_ground_truth_sync.py` | **Derivative Metadata** |
| **Recipes** | `recipes/*.json` | Domain Engineers | Manual authoring | `RecipeRegistry` validation | **Domain Catalog** |
| **Skills** | `.agents/skills/` & `ai/skills/` | Engineers / Prompts | Manual / Promotion | `SkillLoader` validation | **Advisory Context** |
| **Knowledge** | `references/` & `ai/knowledge/` | Technical Writers | Manual authoring | SHA-256 hash checks | **Advisory Context** |
| **ML Evaluation** | `ai/evals/datasets.py` | ML / QA Engineers | Manual / Versioned | `pytest tests/ai/evals` | **Evaluation Standard** |

---

## 9. Desynchronization & Drift Risks

1. **Dual Template Registry Drift**:
   - `registry/template-registry-data.json` (105 templates) and `ground-truth/template_catalog.json` (289 templates) have diverged numerically. While `check_ground_truth_sync.py` verifies that `template_catalog.json` matches what `build_ground_truth.py` generates, `build_ground_truth.py` uses raw regex on `template-registry.tsx` rather than reading canonical `template-registry-data.json`. This creates phantom template entries in `template_catalog.json` that do not exist in the canonical contract.
2. **CI Exclusion of Knowledge & Skill Evals**:
   - Because required GitHub Actions CI omits `tests/ai` (Check A), regressions in `KnowledgeLoader` SHA-256 hash checking or `SkillLoader` schema validation are **not caught** during pull request validation in GitHub CI.
3. **Hardcoded Windows Paths in Legacy Plugins**:
   - Plugin MCP configurations in `.agents/plugins/super-video-maker-plugin/mcp_config.json` contain hardcoded `C:/video/clean-video-workspace/...` filepaths, causing legacy plugin tools to fail on Linux systems unless modernized through `ai/mcp/compatibility/`.

---

## 10. File & Symbol Evidence Index

| File Path | Symbol / Function | Line Range | Architectural Function | Classification |
|---|---|---|---|---|
| `scripts/generators/build_ground_truth.py` | `main` / script body | 1-299 | Generates all files in root `ground-truth/` | `CODE_PROVEN` |
| `scripts/validators/check_ground_truth_sync.py` | `run_ground_truth_check` | 24-55 | Enforces zero git diff on `ground-truth/` | `CI_PROVEN` |
| `scripts/core/template_registry_publisher.py` | Docstring / `Single Source of Truth` | 6-18 | Declares canonical hierarchy of registries | `CODE_PROVEN` |
| `scripts/core/template_registry_publisher.py` | `TemplateRegistryPublisher` | 65-200 | Updates canonical and compatibility registries | `CODE_PROVEN` |
| `registry/template-registry-data.json` | Root object (`templates`) | 1-105 | Authoritative canonical template catalog (105 items) | `CODE_PROVEN` |
| `ground-truth/template_catalog.json` | Array of template objects | 1-289 | Compatibility derivative catalog (289 items) | `CODE_PROVEN` |
| `scripts/gates/asset_gate.py` | `validate_assets` | 44-75 | Reads `ground-truth/ASSET_INDEX.json` for MCP | `CODE_PROVEN` |
| `ai/recipes/registry.py` | `RecipeRegistry.__init__` | 105-125 | Auto-loads all 18 JSON recipes from `recipes/` | `CODE_PROVEN` |
| `ai/skills/loader.py` | `load_from_markdown` | 62-112 | Loads skills from markdown + YAML frontmatter | `CODE_PROVEN` |
| `ai/skills/loader.py` | `get_canonical_skills` | 115-302 | Returns canonical typed Python SkillDefinitions | `CODE_PROVEN` |
| `ai/knowledge/loader.py` | `KnowledgeLoader` | 53-114 | Loads references with SHA-256 validation | `CODE_PROVEN` |
| `ai/evals/datasets.py` | `build_routing_dataset` | 19-43 | ML evaluation ground truth dataset | `CODE_PROVEN` |
| `.github/workflows/remediation-ci.yml` | `ground-truth` job | 63-87 | Executes `check_ground_truth_sync.py --check` | `CI_PROVEN` |

---

## 11. Conclusion & Recommendations

- **Terminology Freeze**: Cease using the term "ground truth" to describe root `/ground-truth/`. Rename documentation references to "Repository Navigation Index".
- **Generator Alignment**: Update `scripts/generators/build_ground_truth.py` to source template entries directly from canonical `registry/template-registry-data.json` instead of regex parsing TypeScript, eliminating the 105 vs. 289 discrepancy.
- **CI Re-inclusion**: Ensure `tests/ai/evals` and `tests/ai/knowledge` are added to the CI matrix so cryptographic hash verification remains enforced on all commits.


---


<a name='part-3-creative-authoring-editor--render-pipeline'></a>

## Part 3: Creative Authoring, Editor & Render Pipeline


> *Original Source: `documentation/reality_context_pack/08_CREATIVE_AUTHORING_EDITOR_RENDER_REALITY.md`*


### Sub-Report Title: 08 — Creative Authoring, Editor & Render Reality Report


- **Baseline Git SHA**: `90ec3de8d47494d5940d5cd1f9ed9a8e274ef6e1`
- **Branch**: `main`
- **Report Version**: 1.0.0
- **Last Updated**: 2026-10-07
- **Scope**: Creative Authoring Pipeline, VideoDocument Mutations, Intent Planning, Remotion Renderer Role, Render Graph Execution, and Quality Control
- **Evidence Standards**: `CODE_PROVEN`, `TEST_PROVEN`, `CI_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`, `DOCUMENTATION_ONLY`, `INFERRED`, `UNKNOWN`

---

## 1. Executive Summary & Reality Verdict

The creative authoring and rendering architecture in this repository is divided into two distinct domains:

1. **A Highly Structured, Deterministic Production Runtime**: The active production path comprises FastAPI authoring services (`api/services/authoring_service.py`), a TypeScript AST mutation engine (`authoring/`, `contracts/`), a background pipeline orchestrator (`scripts/pipeline.py`), and a multi-engine render pipeline (`planner/`, `remotion/`, `compositor/`). This runtime enforces strict transactional CAS (Compare-And-Swap) revisioning, immutable review bundles, and mechanical locks.
2. **An Isolated Creative Planning Platform**: The algorithmic Creative Intelligence pipeline (Brief $\to$ Narrative $\to$ CreativePlan $\to$ Tier Selection $\to$ BlueprintCompiler) exists entirely in Python (`ai/planning/`, `ai/intent/`, `ai/narrative/`, `ai/recipes/`), but is **completely bypassed** by the production HTTP run and render execution paths.

Crucially:
- `POST /projects/{id}/runs` **never reaches Creative Intelligence**; it validates and renders pre-authored blueprints already on disk.
- `POST /projects/{id}/intent` **does not accept natural language**; it strictly requires typed discriminated-union AST intent schemas.
- `CreativePlan` is **never compiled into `VideoDocument` on the production path**; `BlueprintCompiler` is only called in test harnesses.
- Remotion is **contractually declared as a swappable adapter**, but **retains substantial operational authority and lock-in** across template code, CLI fallbacks, and visual QC probes.

---

## 2. Creative Pipeline Trace: Intended vs. Actual Production Flow

```
INTENDED ARCHITECTURE (S28 Vision):
[Raw User Prompt] ──► [CreativeBrief] ──► [NarrativePlan] ──► [CreativePlan]
                                                                     │
                                                                     ▼
[Canonical VideoDocument] ◄── [BlueprintCompiler] ◄── [REUSE/COMPOSE/CREATE]
           │
           ├─► [AuthoringIntents] ──► [CanonicalMutations] (Live Editor)
           │
           ▼
[RenderPlanner] ──► [RenderGraph DAG] ──► [Renderer Adapters (Remotion/Canvas)]
                                                         │
                                                         ▼
[Final MP4 Output] ◄── [Final QC] ◄── [MasterCompositor] ◄── [Render Chunks]


ACTUAL PROVEN PRODUCTION RUNTIME:
[Pre-Existing Disk Files] (master_plan.md, 01_manifest.json, 05_blueprint.json)
           │
           ▼
[POST /projects/{id}/runs] (api/routers/runs.py)
           │
           ▼ Enqueues RunRecord in SQLite (data/runs.db)
[PipelineWorker] (scripts/core/worker.py)
           │
           ▼ Launches Subprocess: python scripts/pipeline.py <project_id>
[scripts/pipeline.py]
   ├── 1. asset_gate.py (Validates files on disk against manifest)
   ├── 2. plan_gate.py (Checks master_plan.md structure; ad-hoc OpenAI fallback)
   ├── 3. taste_gate.py (Deterministic layout/symmetry regex lint)
   ├── 4. validate_blueprint.py (Validates 05_blueprint.json schema)
   ├── 5. motion_validator.py (Validates timing, frame counts, typography)
   ├── 6. code_template_gate.py (Verifies template imports in source code)
   ├── 7. materialize_project.py (Copies media to remotion-app/public/)
   ├── 8. probe_qc.py (npx remotion still -> Generates ReviewBundle & .studio_unlocked)
   ├── 9. [GATE: AWAITING_REVIEW] (Requires user approval -> .studio_approved)
   ├── 10. render_project.py:
   │         ├─ Priority 1: scripts/render_via_planner.ts (RenderPlanner DAG)
   │         ├─ Priority 2: scripts/render_via_adapter.ts (RemotionRendererAdapter)
   │         └─ Priority 3: npx remotion render src/index.ts (Legacy CLI)
   └── 11. final_qc.py (FFprobe verification: aspect ratio, audio/video duration, sync)
           │
           ▼
[out.mp4 Saved & Metered]
```

---

## 3. Mandatory Check C: Exact Runtime Path for `POST /projects/{id}/runs`

### 3.1 Question Statement
> **Check C**: What is the exact runtime path for `POST /projects/{id}/runs`?

### 3.2 Step-by-Step Production Call Graph
Tracing execution from incoming HTTP socket to final output:

1. **HTTP Routing & Ingestion**:
   - `api/routers/runs.py:23-56` (`create_run`):
   - Validates caller authentication and checks permission `Action.RUN_EXECUTE`.
   - Calls `RunService.create_run(project_id, idempotency_key, payload, workspace_id)`.
2. **Domain Service & Idempotency**:
   - `api/services/run_service.py:34-114`:
   - Validates `project_id` format via `validate_project_id()`.
   - Verifies project directory exists on disk (`projects/{project_id}`). If absent, raises `ProjectNotFoundError`.
   - Queries `RunRepository.find_by_idempotency(project_id, idempotency_key)` to prevent duplicate execution or payload mismatch (`IdempotencyConflictError`).
   - Reads current lifecycle state from disk via `StateStore.load(proj_dir)` to snapshot `input_revision`.
   - Instantiates `RunRecord(run_id=f"run_{uuid.uuid4().hex}", workspace_id=ws, project_id=pid, status=RunStatus.QUEUED, input_revision=input_revision)`.
   - Persists record into SQLite database (`data/runs.db`) via `RunRepository.create_run()`.
   - Emits durable event `RUN_QUEUED` via `RunRepository.record_event()`.
   - Returns HTTP `202 Accepted` with `RunResponse`.
3. **Background Worker Claim & Ephemeral Preparation**:
   - `scripts/core/worker.py:180-360` (`PipelineWorker.process_one()`):
   - Background daemon (`scripts/worker.py`) executes polling loop `run_loop()`.
   - Claims queued run using atomic CAS query `RunRepository.claim_next_run(worker_id, lease_duration=300)`. Status becomes `RUN_STARTED`.
   - Spawns background lease heartbeat thread (`_start_heartbeat`).
   - Validates tenant asset isolation against `01_manifest.json` (`ManifestValidator.validate_tenant_assets`).
   - Creates isolated ephemeral workspace (`tempfile.mkdtemp(prefix=f"ephemeral_{project_id}_")`).
   - Spawns child process (`scripts/core/worker.py:289`):
     ```bash
     python scripts/pipeline.py <project_id>
     ```
     with environment variables `AGY_RUN_ID`, `AGY_WORKER_ID`, `AGY_WORKSPACE_ID`, `AGY_INPUT_REVISION`.
4. **Pipeline Orchestrator State Machine**:
   - `scripts/pipeline.py:221-520` (`main()`):
   - Loads project state and verifies recovery engine (`RecoveryEngine.evaluate()`).
   - Sequentially advances state machine:
     - `DRAFT` $\to$ `ASSETS_READY`: runs `scripts/gates/asset_gate.py`.
     - `ASSETS_READY` $\to$ `PLAN_READY`: runs `scripts/gates/plan_gate.py` and `scripts/gates/taste_gate.py`.
     - `PLAN_READY` $\to$ `BLUEPRINT_READY`: runs `scripts/gates/validate_blueprint.py`, `scripts/gates/motion_validator.py`, `scripts/gates/code_template_gate.py`.
     - `BLUEPRINT_READY` $\to$ `MATERIALIZED`: runs `scripts/generators/materialize_project.py` (materializes media to `remotion-app/public/`).
     - `MATERIALIZED` $\to$ `PROBE_PASSED`: runs `scripts/gates/probe_qc.py` (generates contact sheets, creates HMAC-sealed `ReviewBundle`, creates `.studio_unlocked`).
     - `PROBE_PASSED` $\to$ `AWAITING_REVIEW`: pauses for human/client review decision.
     - `AWAITING_REVIEW` $\to$ `REVIEW_APPROVED`: checks for approved `ReviewDecision` in database or `.studio_approved` marker file on disk.
     - `REVIEW_APPROVED` $\to$ `RENDERED`: verifies authorization (`assert_render_authorized()`) and runs `scripts/render_project.py`.
     - `RENDERED` $\to$ `FINAL_QC_PASSED`: runs `scripts/gates/final_qc.py`.
     - `FINAL_QC_PASSED` $\to$ `COMPLETE`.
5. **Render Sub-Path Execution**:
   - `scripts/render_project.py:100-200`:
   - Builds render props (`build_render_input()` writing `.render_props.json`).
   - Executes render through prioritized ladder:
     - Priority 1: `npx tsx scripts/render_via_planner.ts <project_id> --out <tmp_out_file>`
     - Priority 2: `npx tsx scripts/render_via_adapter.ts <project_id> --out <tmp_out_file>`
     - Priority 3 (fallback): `npx remotion render src/index.ts BlueprintVideo <tmp_out_file> --props <props_file>`
   - Moves `tmp_out_file` to `out.mp4`.
6. **Worker Completion & Metering**:
   - `scripts/core/worker.py:306-350`:
   - `PipelineWorker` captures subprocess exit code 0.
   - Invokes `_upload_outputs_and_meter()` to store `out.mp4` into `StorageService` and record usage telemetry.
   - Calls `RunRepository.finish_run(run_id, status=RunStatus.SUCCEEDED)`.
   - Emits terminal event `RUN_SUCCEEDED`.

---

## 4. Mandatory Check D: Creative Intelligence Reachability from `POST /projects/{id}/runs`

### 4.1 Question Statement
> **Check D**: Does `POST /projects/{id}/runs` reach Creative Intelligence?

### 4.2 Code Audit
A line-by-line inspection of the entire execution chain for `POST /projects/{id}/runs` (`api/routers/runs.py`, `api/services/run_service.py`, `scripts/core/worker.py`, `scripts/pipeline.py`, and all 8 gate scripts):
1. **Zero AI Platform Imports**: None of the files in the execution chain import `CreativePlanner`, `NarrativePlanner`, `RecipeSelector`, `TasteEngine`, `BlueprintCompiler`, `ModelRouter`, or `ai.*` (`CODE_PROVEN`).
2. **Pre-Existing File Mandate**:
   - `scripts/pipeline.py:371` asserts: `plan_file = proj_dir / "master_plan.md"`. If absent, pipeline fails closed.
   - `scripts/pipeline.py:381` asserts: `blueprint_file = proj_dir / "05_blueprint.json"`. If absent, pipeline fails closed.
3. **Purely Validating & Rendering**: The run pipeline does not create, generate, or ideate video content. It solely validates, materializes, probes, and renders files that already exist in `projects/{id}/`.

### 4.3 Answer to Check D
**NO** (`CODE_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`).
`POST /projects/{id}/runs` does not reach Creative Intelligence at any point in its execution path.

---

## 5. Mandatory Check F: Nature of `/intent` Endpoint

### 5.1 Question Statement
> **Check F**: Does `/intent` accept natural language or only pre-structured typed intents?

### 5.2 Schema & Handler Inspection
In `api/routers/authoring.py:104-132`:
```python
@router.post("/{project_id}/intent", response_model=AuthoringResultDTO)
async def apply_intent(
    project_id: str,
    payload: Dict[str, Any] = Body(...),
    ...
):
    return AuthoringService.execute_authoring(
        project_id=project_id,
        tenant_context=tenant_ctx,
        action="apply_intent",
        payload=payload,
        actor_id=principal.actor_id,
    )
```

In `api/services/authoring_service.py:150-176`, the payload is piped directly via JSON IPC to `scripts/execute_authoring_mutation.ts`.

In `contracts/authoring.ts:273-288`, `AuthoringIntentSchema` is defined as a discriminated union over literal field `type`:
```typescript
export const AuthoringIntentSchema = z.discriminatedUnion("type", [
  UpdateTextIntentSchema,           // type: "UPDATE_TEXT", target: { scene_id, layer_id }, text: string
  UpdateTransformIntentSchema,      // type: "UPDATE_TRANSFORM", target: ..., transform: ...
  UpdateStyleIntentSchema,          // type: "UPDATE_STYLE", target: ..., style: ...
  ReplaceMediaIntentSchema,         // type: "REPLACE_MEDIA", target: ..., asset_id: string
  ChangeTimingIntentSchema,         // type: "CHANGE_TIMING", target: ..., in_frame, out_frame
  ApplyTemplateParamIntentSchema,   // type: "APPLY_TEMPLATE_PARAM", param_name, param_value
  CompoundCommandIntentSchema,      // type: "COMPOUND_COMMAND", commands: [...]
  AddLayerIntentSchema,             // type: "ADD_LAYER", layer: CanonicalLayer
  RemoveLayerIntentSchema,          // type: "REMOVE_LAYER", target: ...
  ReorderLayerIntentSchema,         // type: "REORDER_LAYER", target: ..., new_index: number
  AddSceneIntentSchema,             // type: "ADD_SCENE", scene: BlueprintScene
  RemoveSceneIntentSchema,          // type: "REMOVE_SCENE", scene_id: string
  ReorderSceneIntentSchema,         // type: "REORDER_SCENE", scene_id: string, new_index: number
  UnsupportedIntentSchema,          // type: "UNSUPPORTED"
]);
```

In `authoring/intent-planner.ts:5-14`:
```typescript
/**
 * Invariants:
 * - Pure, deterministic, zero-AI-SDK, zero-renderer, zero-side-effects.
 * - Strict Stable-ID entity targeting (scene_id, layer_id, clip_id, keyframe_id).
 * - Fail-closed error handling with structured diagnostics.
 */
```

Passing a raw natural-language string such as `{"prompt": "Make the title bigger and red"}` results in immediate schema validation failure (`ZodError` / HTTP 422 / `AUTHORING_VALIDATION_FAILED`).

### 5.3 Answer to Check F
`/intent` accepts **ONLY pre-structured typed intents** [`CODE_PROVEN`]. It rejects arbitrary natural-language text.

---

## 6. Mandatory Check R: Compilation of `CreativePlan` to Canonical `VideoDocument`

### 6.1 Question Statement
> **Check R**: Is `CreativePlan` compiled into canonical `VideoDocument` on the production path?

### 6.2 Code Evidence
The compilation logic is housed in `BlueprintCompiler` (`ai/planning/compiler.py:62-443`). It takes a `CreativePlan`, `ResolvedTemplateDecision` mappings, a `ManifestV2`, and a `TemplateRegistryContract`, and outputs a canonical `BlueprintV2` / `VideoDocument`.

A comprehensive codebase search for callers of `BlueprintCompiler`:
- `scripts/run_creative_e2e.py:116`: Offline benchmark runner [`TEST_PROVEN`].
- `tests/ai/planning/test_compiler.py`: Unit test suite [`TEST_PROVEN`].
- `tests/ai/e2e/test_full_creative_e2e_matrix.py`: Test harness [`TEST_PROVEN`].
- `scripts/core/blueprint_compiler.py`: Re-export module with zero production callers.
- **Production API (`api/`)**: Exactly 0 callers [`CODE_PROVEN`].
- **Pipeline Worker (`scripts/core/worker.py`, `scripts/pipeline.py`)**: Exactly 0 callers [`CODE_PROVEN`].
- **Authoring Engine (`authoring/`, `api/services/authoring_service.py`)**: Exactly 0 callers [`CODE_PROVEN`].

On the production path, `VideoDocument` is generated in one of three ways:
1. Created from scratch by disk fixtures or seed generators.
2. Created via template instantiation: `POST /projects/{id}/template` $\to$ `AuthoringService.instantiate_template()` $\to$ `contracts/templates.ts:instantiateTemplateToCanonicalDocument()`.
3. Mutated incrementally via `POST /projects/{id}/mutate` or `POST /projects/{id}/batch` $\to$ `UnifiedAuthoringSession`.

### 6.3 Answer to Check R
**NO** (`CODE_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`).
`CreativePlan` is **never** compiled into a canonical `VideoDocument` on the production path.

---

## 7. Mandatory Check S: Runtime Role of Remotion (Adapter vs. Lingering Authority)

### 7.1 Question Statement
> **Check S**: Is Remotion strictly an adapter at runtime or does it retain authority?

### 7.2 The Dual Reality: Adapter Intent vs. Runtime Lock-In

#### Architectural / Contractual Intent (Adapter Role)
- In `remotion/remotion-renderer-adapter.ts:8-16`:
  ```typescript
  // Enforces:
  // - Remotion is strictly a rendering engine; canonical document is the sole authority
  // - Zero mutation of canonical video document
  ```
- `RemotionRendererAdapter` implements `RendererAdapter` (`contracts/renderer.ts`). It declares capabilities, bundles Remotion compositions in temporary staging directories, renders frame chunks, and returns structured `RenderResult` objects.
- In `planner/render-planner.ts`, `RemotionRendererAdapter` is registered alongside `CanvasRendererAdapter` in `CANONICAL_RENDERER_REGISTRY`. The planner decides renderer assignments dynamically based on declared node capabilities.

#### Concrete Runtime Reality (Lingering Structural Authority)
Despite the contractual adapter abstraction, Remotion retains deep operational authority and lock-in across the codebase:
1. **Component Coupling**: All 105 production video templates in `remotion-app/src/templates/` and `templates/` directly import and execute Remotion runtime primitives (`useCurrentFrame`, `useVideoConfig`, `AbsoluteFill`, `spring`, `interpolate`). They cannot render on Canvas or HTML5 without Remotion.
2. **CLI Fallback Authority**: In `scripts/render_project.py:177-185`, the final fallback executes `npx remotion render src/index.ts BlueprintVideo ...` directly in `remotion-app/`.
3. **Probe QC Dependency**: `scripts/gates/probe_qc.py:180` derives contact sheets and review stills by directly invoking `npx remotion still src/index.ts BlueprintVideo ...`.
4. **Studio UI Authority**: `scripts/open_studio.py:75` launches `npx remotion studio` on port 3000 as the sole live visual inspection interface.
5. **Governance Harness**: `creative_governance/candidates/candidate_runtime_runner.py` compiles candidate templates into a Remotion `CandidateHarness.tsx` importing `registerRoot` from `remotion`.

### 7.3 Answer to Check S
Remotion is an **adapter in contract design**, but **retains substantial lingering operational authority and lock-in at runtime** (`CODE_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`). The system cannot execute visual preview, probe QC, or render any of the 105 production templates without Remotion.

---

## 8. VideoDocument & BlueprintV2 Authority, AST Mutations, and CAS Locking

### 8.1 Document Authority & Invariant Governance
The authoritative video representation is `BlueprintV2` / `VideoDocument` (`contracts/blueprint.ts` and `schemas/blueprint.schema.json`). It enforces:
- Strict Stable-ID targeting for every scene (`scene_id`), layer (`layer_id`), clip (`clip_id`), and keyframe (`keyframe_id`).
- Strict FPS authority (no silent defaults).
- Strict dimensions and aspect ratios (`16:9`, `9:16`, `1:1`).
- Bounded timing: every scene defines non-overlapping `start_frame` and `duration_frames`.

### 8.2 AST Mutations & Session Bridge
When an authoring request arrives at `AuthoringService`:
1. `AuthoringService` acquires a transactional CAS lock via `CanonicalDocumentRepository` (`api/services/authoring_service.py:115-147`).
2. If client `base_revision != curr_rev`, fails closed with `RevisionConflictError`.
3. Passes `(document, request)` to `scripts/execute_authoring_mutation.ts` via Node.js IPC subprocess.
4. `execute_authoring_mutation.ts` calls `UnifiedAuthoringSession` in `authoring/unified-authoring-session.ts`.
5. `IntentPlanner` translates intents into typed `CanonicalMutation` objects (`contracts/mutations.ts`).
6. Mutations are applied immutably, generating a new `BlueprintV2` and a `ChangeSet`.
7. `AuthoringService` validates the new document against `CanonicalDocumentRepository`, increments `revision = curr_rev + 1`, commits to SQL, persists to `StorageService`, and emits invalidation events.

### 8.3 Cache & Artifact Invalidation
Committing an authoring mutation automatically invalidates:
- Any pre-rendered video chunks (`out.mp4`, `.render_props.json`).
- Any active review bundle (`ReviewBundle` state reset).
- Removes `.studio_approved` and `.studio_unlocked` markers from disk, locking Remotion Studio until `probe_qc.py` is re-run.

---

## 9. RenderPlanner, MasterCompositor & Multi-Engine Graph Architecture

### 9.1 Multi-Engine RenderGraph (`planner/render-planner.ts`)
- **Role**: Compiles `BlueprintV2` into an execution DAG (`RenderGraph`) composed of `RenderNode` and `RenderEdge`.
- **Node Classification**: Nodes represent distinct timeline segments, background tracks, overlay tracks, or audio stems.
- **Renderer Assignment**: Resolves compatible renderers from `CANONICAL_RENDERER_REGISTRY` based on required capabilities (e.g., WebGL, Canvas, Remotion).

### 9.2 MasterCompositor (`compositor/master-compositor.ts`)
- **Role**: Timeline stitcher and audio normalizer.
- **Function**: Takes individual scene or layer render chunks produced by the render graph, executes FFmpeg audio mixing with ducking (-16 LUFS voiceover, -24 LUFS music), applies GL transitions, and outputs the final master MP4.

---

## 10. Quality Control Gates, Review Bundles & Mechanical Locks

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          GATE & LOCK PROTOCOL                               │
├───────────────────┬──────────────────────────┬──────────────────────────────┤
│ Gate / Mechanism  │ Script Location          │ Security / Enforcement Rule  │
├───────────────────┼──────────────────────────┼──────────────────────────────┤
│ Taste Gate        │ scripts/gates/taste_gate │ Layout symmetry, contrast,   │
│                   │                          │ typography overlap checks    │
│ Probe QC          │ scripts/gates/probe_qc   │ npx remotion still probes;   │
│                   │                          │ creates sealed ReviewBundle; │
│                   │                          │ unlocks .studio_unlocked     │
│ Mechanical Lock   │ scripts/open_studio.py   │ Studio UI blocked unless     │
│                   │                          │ .studio_unlocked exists      │
│ Human Review Gate │ scripts/core/review_svc  │ Rendering blocked unless     │
│                   │                          │ approved (.studio_approved)  │
│ Render Auth Gate  │ scripts/render_project   │ assert_render_authorized()   │
│                   │                          │ fails closed if unapproved   │
│ Final QC          │ scripts/gates/final_qc   │ FFprobe stream analysis;     │
│                   │                          │ AV-sync error < 200ms        │
└───────────────────┴──────────────────────────┴──────────────────────────────┘
```

1. **Probe QC (`scripts/gates/probe_qc.py`)**:
   - Computes deterministic frame probe plan (`derive_probe_frame_plan()`).
   - Renders still frames and contact sheets.
   - Seals report with HMAC-SHA256 using `.agents/secrets/.qc_salt`.
   - Touches `.studio_unlocked` on disk.
2. **Review Approval Protocol**:
   - Pipeline transitions to `AWAITING_REVIEW`.
   - Rendering is strictly forbidden until the user reviews contact sheets and approves via `POST /projects/{id}/review/approve` or manual touch of `.studio_approved`.
3. **Final QC (`scripts/gates/final_qc.py`)**:
   - Analyzes `out.mp4` streams using `ffprobe`.
   - Validates aspect ratio against `CANONICAL_ASPECT_MAP`.
   - Validates AV-sync error does not exceed `MAX_AV_SYNC_ERROR_MS = 200.0`.
   - Rejects corrupted or misaligned output files.

---

## 11. File & Symbol Evidence Index

| File Path | Symbol / Function | Line Range | Architectural Function | Classification |
|---|---|---|---|---|
| `api/routers/runs.py` | `create_run` | 23-56 | Enqueues run; zero AI reachability | `CODE_PROVEN` |
| `api/services/run_service.py` | `RunService.create_run` | 34-114 | Validates project & persists RunRecord | `CODE_PROVEN` |
| `scripts/core/worker.py` | `PipelineWorker.process_one` | 180-360 | Claims run and executes pipeline.py | `CODE_PROVEN` |
| `scripts/pipeline.py` | `main` | 221-520 | 10-stage sequential pipeline orchestrator | `CODE_PROVEN` |
| `api/routers/authoring.py` | `apply_intent` | 104-132 | Accepts typed AuthoringIntentSchema | `CODE_PROVEN` |
| `contracts/authoring.ts` | `AuthoringIntentSchema` | 273-288 | Discriminated union of 14 typed AST intents | `CODE_PROVEN` |
| `authoring/intent-planner.ts` | `IntentPlanner` | 1-60 | Deterministic intent-to-mutation translator | `CODE_PROVEN` |
| `api/services/authoring_service.py` | `execute_authoring` | 81-195 | CAS revision control and Node.js bridge | `CODE_PROVEN` |
| `scripts/execute_authoring_mutation.ts`| `main` | 1-220 | IPC bridge invoking UnifiedAuthoringSession | `CODE_PROVEN` |
| `ai/planning/compiler.py` | `BlueprintCompiler` | 62-443 | Compiles CreativePlan $\to$ BlueprintV2 (0 prod callers)| `CODE_PROVEN` |
| `remotion/remotion-renderer-adapter.ts`| `RemotionRendererAdapter` | 8-50 | Implements RendererAdapter contract | `CODE_PROVEN` |
| `planner/render-planner.ts` | `RenderPlanner` | 1-60 | Multi-engine RenderGraph DAG compiler | `CODE_PROVEN` |
| `scripts/render_project.py` | `main` / render ladder | 100-200 | Executes render priority 1, 2, or 3 | `CODE_PROVEN` |
| `scripts/gates/probe_qc.py` | `main` / seal logic | 1-60 | Renders stills, seals ReviewBundle, unlocks studio | `CODE_PROVEN` |
| `scripts/open_studio.py` | `main` / mechanical lock | 49-65 | Asserts .studio_unlocked before opening studio | `CODE_PROVEN` |
| `scripts/gates/final_qc.py` | `main` / ffprobe analysis | 1-60 | Verifies aspect ratio, duration, AV-sync | `CODE_PROVEN` |

---

## 12. Strategic Recommendations

1. **Wire Creative Planning to Authoring Service**: To allow AI-generated video projects, introduce an asynchronous `POST /projects/{id}/generate` endpoint in FastAPI that calls `CreativeBriefBuilder` $\to$ `CreativePlanner` $\to$ `BlueprintCompiler` $\to$ `AuthoringService.save_document()`.
2. **Standardize on RenderPlanner**: Remove legacy Remotion CLI fallback in `scripts/render_project.py` once `scripts/render_via_planner.ts` achieves 100% soak stability in CI.
3. **Decouple Templates from Remotion**: For true renderer independence, extract template visual markup into framework-agnostic AST declarations, allowing `CanvasRendererAdapter` to render templates without the Remotion React runtime.


---


<a name='part-4-capability-model-provider--tool-execution'></a>

## Part 4: Capability, Model, Provider & Tool Execution


> *Original Source: `documentation/reality_context_pack/09_CAPABILITY_MODEL_PROVIDER_TOOL_EXECUTION_REALITY.md`*


### Sub-Report Title: 09 — Capability, Model, Provider & Tool Execution Reality Report


- **Baseline Git SHA**: `90ec3de8d47494d5940d5cd1f9ed9a8e274ef6e1`
- **Branch**: `main`
- **Report Version**: 1.0.0
- **Last Updated**: 2026-10-07
- **Scope**: Capability Catalog Architecture, Tool Gateway Pipeline, MCP Isolation, Model/Provider Routing, and Repository-Wide Bypass Sweep
- **Evidence Standards**: `CODE_PROVEN`, `TEST_PROVEN`, `CI_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`, `DOCUMENTATION_ONLY`, `INFERRED`, `UNKNOWN`

---

## 1. Executive Summary & Architectural Verdict

The Capability and Tool Execution subsystem in this repository represents a mature, hardened abstraction designed during the S28-M modernization initiative. It introduces a unified catalog of 43 canonical capabilities (`documentation/s28m/CAPABILITY_CATALOG.json`), an authoritative 15-stage execution pipeline in `ToolGateway` (`ai/tools/gateway.py`), and a strict isolation layer that severs internal AI from raw MCP protocols.

Key architectural realities proven from the codebase:

1. **Internal Product AI Does NOT Require Raw MCP (Check O)**: Internal AI platforms (planning, narrative, intent, recipes, skills) have zero dependency on raw MCP transports. AST architecture guards enforce zero MCP calls in creative planning, recipes, and domain services (`CODE_PROVEN`, `TEST_PROVEN`). MCP servers are relegated to legacy external compatibility facades.
2. **Hardened 15-Stage Tool Gateway**: `ToolGateway` enforces complete tenant isolation, server-side RBAC, SSRF egress validation, storage path confinement, CAS idempotency leasing, and compound `side_effects[]` evaluation before invoking any tool adapter.
3. **Blocked Security Implementations**: `CONCATENATE_VIDEOS` is explicitly hard-blocked inside `MCPToolAdapter` (`ai/tools/adapters/mcp.py:83`) due to a verified shell injection finding in legacy scripts, failing closed with `ImplementationSecurityBlockedError`.
4. **Clean Shell Security Invariant**: A repository-wide audit reveals **zero** instances of `shell=True` in production code. All subprocess invocations use explicit argument vectors via `safe_subprocess` or `asyncio.create_subprocess_exec`.
5. **Provider Execution Boundary**: Production LLM routing remains unwired; the only active LLM provider adapter in `ai/providers/` is `OpenRouterProvider` (flagged `environment="development"`, `production_default=False`). Native provider adapters (OpenAI, Anthropic, Gemini, ElevenLabs, Fal.ai) exist only as metadata descriptors or test fakes.

---

## 2. Capability Catalog & Execution Matrix (All 43 Capabilities)

The authoritative runtime repository is `documentation/s28m/CAPABILITY_CATALOG.json`, loaded by `CapabilityCatalog` (`ai/capabilities/catalog.py`).

| # | Capability ID | Category | Family | Execution Mode | Tenant Scope | Required Perms | Side Effects | Target Storage Boundary | Primary Implementation | Reachability |
|---|---|---|---|---|---|---|---|---|---|---|
| 01 | `SPEECH_TO_TEXT` | `MODEL` | `SPEECH_INTELLIGENCE` | `MODEL` | `PROJECT` | `viewer`, `editor` | `LOCAL_TEMP_WRITE` | Transient Analysis Cache | `local_stt_provider` (faster-whisper) | `DEV_ONLY` |
| 02 | `SEGMENT_SPEECH_AUDIO` | `TOOL` | `SPEECH_INTELLIGENCE` | `LOCAL` | `PROJECT` | `editor` | `PERSISTENT_WRITE`, `SUBPROCESS` | StorageService / Audio Slices | `canonical_speech_preparation_service` | `DEV_ONLY` |
| 03 | `GENERATE_SPEECH_MANIFEST` | `DOMAIN_SERVICE` | `SPEECH_INTELLIGENCE` | `LOCAL` | `PROJECT` | `viewer`, `editor` | `PERSISTENT_WRITE`, `DOMAIN_MUTATION` | ArtifactService / Speech Manifest | `canonical_speech_manifest_builder` | `DEV_ONLY` |
| 04 | `BUILD_SPEECH_TIMELINE` | `DOMAIN_SERVICE` | `SPEECH_INTELLIGENCE` | `LOCAL` | `PROJECT` | `viewer`, `editor` | `PERSISTENT_WRITE`, `DOMAIN_MUTATION` | ArtifactService / Speech Timeline | `canonical_speech_timeline_builder` | `DEV_ONLY` |
| 05 | `TRIM_AUDIO` | `TOOL` | `AUDIO_PROCESSING` | `LOCAL` | `PROJECT` | `editor` | `PERSISTENT_WRITE`, `SUBPROCESS` | StorageService / Project Audio | `canonical_media_processing_service` | `DEV_ONLY` |
| 06 | `EXTEND_AUDIO` | `TOOL` | `AUDIO_PROCESSING` | `LOCAL` | `PROJECT` | `editor` | `PERSISTENT_WRITE`, `SUBPROCESS` | StorageService / Project Audio | `canonical_media_processing_service` | `DEV_ONLY` |
| 07 | `NORMALIZE_AUDIO_LOUDNESS` | `TOOL` | `AUDIO_PROCESSING` | `LOCAL` | `PROJECT` | `editor` | `PERSISTENT_WRITE`, `SUBPROCESS` | StorageService / Project Audio | `canonical_media_processing_service` | `DEV_ONLY` |
| 08 | `TRIM_AUDIO_SILENCE` | `TOOL` | `AUDIO_PROCESSING` | `LOCAL` | `PROJECT` | `editor` | `PERSISTENT_WRITE`, `SUBPROCESS` | StorageService / Project Audio | `canonical_media_processing_service` | `DEV_ONLY` |
| 09 | `TRIM_VIDEO` | `TOOL` | `VIDEO_PROCESSING` | `LOCAL` | `PROJECT` | `editor` | `PERSISTENT_WRITE`, `SUBPROCESS` | StorageService / Project Video | `canonical_media_processing_service` | `DEV_ONLY` |
| 10 | `EXTEND_VIDEO` | `TOOL` | `VIDEO_PROCESSING` | `LOCAL` | `PROJECT` | `editor` | `PERSISTENT_WRITE`, `SUBPROCESS` | StorageService / Project Video | `canonical_media_processing_service` | `DEV_ONLY` |
| 11 | `RESIZE_VIDEO` | `TOOL` | `VIDEO_PROCESSING` | `LOCAL` | `PROJECT` | `editor` | `PERSISTENT_WRITE`, `SUBPROCESS` | StorageService / Project Video | `canonical_media_processing_service` | `DEV_ONLY` |
| 12 | `TRIM_BLACK_FRAMES` | `TOOL` | `VIDEO_PROCESSING` | `LOCAL` | `PROJECT` | `editor` | `PERSISTENT_WRITE`, `SUBPROCESS` | StorageService / Project Video | `canonical_media_processing_service` | `DEV_ONLY` |
| 13 | `CHANGE_VIDEO_SPEED` | `TOOL` | `VIDEO_PROCESSING` | `WORKER` | `PROJECT` | `editor` | `PERSISTENT_WRITE`, `SUBPROCESS`, `BACKGROUND_JOB`| StorageService / Project Video | `canonical_media_processing_service` | `DEV_ONLY` |
| 14 | `ENFORCE_KEYFRAME_INTERVAL`| `TOOL` | `VIDEO_PROCESSING` | `WORKER` | `PROJECT` | `editor` | `PERSISTENT_WRITE`, `SUBPROCESS` | StorageService / Project Video | `canonical_media_processing_service` | `DEV_ONLY` |
| 15 | `CONCATENATE_VIDEOS` | `TOOL` | `VIDEO_PROCESSING` | `LOCAL` | `PROJECT` | `editor` | `PERSISTENT_WRITE`, `SUBPROCESS` | StorageService / Project Video | `canonical_media_processing_service` | `SECURITY_BLOCKED` |
| 16 | `RESIZE_IMAGE` | `TOOL` | `IMAGE_PROCESSING` | `LOCAL` | `PROJECT` | `editor` | `PERSISTENT_WRITE` | StorageService / Project Images | `canonical_image_processing_service_resize_image` | `DEV_ONLY` |
| 17 | `CROP_IMAGE_TO_RATIO` | `TOOL` | `IMAGE_PROCESSING` | `LOCAL` | `PROJECT` | `editor` | `PERSISTENT_WRITE` | StorageService / Project Images | `canonical_image_processing_service_crop_image_ratio` | `DEV_ONLY` |
| 18 | `AUTO_CROP_IMAGE` | `TOOL` | `IMAGE_PROCESSING` | `LOCAL` | `PROJECT` | `editor` | `PERSISTENT_WRITE` | StorageService / Project Images | `canonical_image_processing_service_auto_crop_image` | `DEV_ONLY` |
| 19 | `DOWNLOAD_REMOTE_MEDIA` | `TOOL` | `MEDIA_ACQUISITION` | `LOCAL` | `PROJECT` | `editor` | `PERSISTENT_WRITE`, `EXTERNAL_NETWORK` | StorageService / Ingestion Hierarchy | `canonical_acquisition_download_remote_media` | `DEV_ONLY` |
| 20 | `EXTRACT_MEDIA_PAGE` | `TOOL` | `MEDIA_ACQUISITION` | `LOCAL` | `PROJECT` | `editor` | `PERSISTENT_WRITE`, `EXTERNAL_NETWORK` | StorageService / Ingestion Hierarchy | `canonical_acquisition_extract_media_page` | `DEV_ONLY` |
| 21 | `SEARCH_ICONS` | `TOOL` | `MEDIA_ACQUISITION` | `EXTERNAL_API` | `WORKSPACE` | `viewer`, `editor` | `EXTERNAL_NETWORK`, `READ_ONLY` | Stateless In-Memory API | `canonical_acquisition_search_icons` | `DEV_ONLY` |
| 22 | `DOWNLOAD_ICON` | `TOOL` | `MEDIA_ACQUISITION` | `EXTERNAL_API` | `PROJECT` | `editor` | `PERSISTENT_WRITE`, `EXTERNAL_NETWORK` | StorageService / Project Icons | `canonical_acquisition_download_icon` | `DEV_ONLY` |
| 23 | `SEARCH_STOCK_IMAGES` | `TOOL` | `MEDIA_ACQUISITION` | `EXTERNAL_API` | `WORKSPACE` | `viewer`, `editor` | `EXTERNAL_NETWORK`, `READ_ONLY` | Stateless In-Memory API | `canonical_acquisition_search_stock_images` | `DEV_ONLY` |
| 24 | `SEARCH_STOCK_VIDEOS` | `TOOL` | `MEDIA_ACQUISITION` | `EXTERNAL_API` | `WORKSPACE` | `viewer`, `editor` | `EXTERNAL_NETWORK`, `READ_ONLY` | Stateless In-Memory API | `canonical_acquisition_search_stock_videos` | `DEV_ONLY` |
| 25 | `SEARCH_STOCK_AUDIO` | `TOOL` | `MEDIA_ACQUISITION` | `EXTERNAL_API` | `WORKSPACE` | `viewer`, `editor` | `EXTERNAL_NETWORK`, `READ_ONLY` | Stateless In-Memory API | `canonical_acquisition_search_stock_audio` | `DEV_ONLY` |
| 26 | `SEARCH_SOUND_EFFECTS` | `TOOL` | `MEDIA_ACQUISITION` | `EXTERNAL_API` | `WORKSPACE` | `viewer`, `editor` | `EXTERNAL_NETWORK`, `READ_ONLY` | Stateless In-Memory API | `canonical_acquisition_search_sound_effects` | `DEV_ONLY` |
| 27 | `INSPECT_MEDIA` | `TOOL` | `MEDIA_INSPECTION` | `LOCAL` | `PROJECT` | `viewer`, `editor` | `READ_ONLY`, `SUBPROCESS` | StorageService / Read-Only Probe | `canonical_media_processing_service` | `DEV_ONLY` |
| 28 | `MUTATE_ASSET_STATUS` | `DOMAIN_SERVICE`| `ASSET_DOMAIN_OPERATIONS`| `LOCAL` | `PROJECT` | `editor`, `admin` | `DOMAIN_MUTATION`, `PERSISTENT_WRITE` | AssetService / ManifestV2 Authority | `legacy_media_sources_mcp_change_asset_status` | `COMPATIBILITY_ONLY` |
| 29 | `CHECK_MEDIA_CACHE` | `DOMAIN_SERVICE`| `CACHE_MANAGEMENT` | `LOCAL` | `PROJECT` | `viewer`, `editor` | `READ_ONLY` | AssetService / Managed Cache | `legacy_common_tools_mcp_check_cache` | `COMPATIBILITY_ONLY` |
| 30 | `STORE_MEDIA_CACHE` | `DOMAIN_SERVICE`| `CACHE_MANAGEMENT` | `LOCAL` | `PROJECT` | `editor` | `PERSISTENT_WRITE`, `DOMAIN_MUTATION` | AssetService / Managed Cache | `legacy_common_tools_mcp_save_to_cache` | `COMPATIBILITY_ONLY` |
| 31 | `GET_JOB_STATUS` | `DOMAIN_SERVICE`| `JOB_MANAGEMENT` | `LOCAL` | `PROJECT` | `viewer`, `editor` | `READ_ONLY` | RunService / Durable Job Record | `legacy_ffmpeg_mcp_server_check_processing_status`| `COMPATIBILITY_ONLY` |
| 32 | `CANCEL_PROCESSING_JOB` | `DOMAIN_SERVICE`| `JOB_MANAGEMENT` | `LOCAL` | `PROJECT` | `editor`, `admin` | `DOMAIN_MUTATION`, `SUBPROCESS` | RunService / Durable Job Record | `legacy_ffmpeg_mcp_server_cancel_video_processing`| `COMPATIBILITY_ONLY` |
| 33 | `NORMALIZE_AUDIO` | `TOOL` | `AUDIO_PROCESSING` | `LOCAL` | `PROJECT` | `editor` | `PERSISTENT_WRITE`, `SUBPROCESS` | StorageService / Project Audio | `canonical_media_processing_service` | `DEV_ONLY` |
| 34 | `ANALYZE_LOUDNESS` | `TOOL` | `AUDIO_PROCESSING` | `LOCAL` | `PROJECT` | `viewer`, `editor` | `READ_ONLY`, `SUBPROCESS` | In-Memory (Read-Only Analysis) | `canonical_media_processing_service` | `DEV_ONLY` |
| 35 | `DETECT_SILENCE` | `TOOL` | `AUDIO_PROCESSING` | `LOCAL` | `PROJECT` | `viewer`, `editor` | `READ_ONLY`, `SUBPROCESS` | In-Memory (Read-Only Analysis) | `canonical_media_processing_service` | `DEV_ONLY` |
| 36 | `SPLIT_SPEECH_TEXT` | `TOOL` | `SPEECH_INTELLIGENCE` | `LOCAL` | `PROJECT` | `viewer`, `editor` | `READ_ONLY` | None (In-Memory Computation) | `canonical_speech_preparation_service` | `DEV_ONLY` |
| 37 | `PREPARE_VO_SEGMENTS` | `TOOL` | `SPEECH_INTELLIGENCE` | `LOCAL` | `PROJECT` | `viewer`, `editor` | `READ_ONLY` | None (In-Memory Computation) | `canonical_speech_preparation_service` | `DEV_ONLY` |
| 38 | `ALIGN_AUDIO_METADATA` | `TOOL` | `SPEECH_INTELLIGENCE` | `LOCAL` | `PROJECT` | `viewer`, `editor` | `READ_ONLY` | None (In-Memory Computation) | `canonical_speech_preparation_service` | `DEV_ONLY` |
| 39 | `PROBE_IMAGE` | `TOOL` | `IMAGE_PROCESSING` | `LOCAL` | `PROJECT` | `editor` | `READ_ONLY` | StorageService / Read Only | `canonical_image_processing_service_probe_image` | `DEV_ONLY` |
| 40 | `CONVERT_IMAGE` | `TOOL` | `IMAGE_PROCESSING` | `LOCAL` | `PROJECT` | `editor` | `PERSISTENT_WRITE` | StorageService / Project Images | `canonical_image_processing_service_convert_image` | `DEV_ONLY` |
| 41 | `OPTIMIZE_IMAGE` | `TOOL` | `IMAGE_PROCESSING` | `LOCAL` | `PROJECT` | `editor` | `PERSISTENT_WRITE` | StorageService / Project Images | `canonical_image_processing_service_optimize_image` | `DEV_ONLY` |
| 42 | `PREPARE_IMAGE_ASSET` | `TOOL` | `IMAGE_PROCESSING` | `LOCAL` | `PROJECT` | `editor` | `PERSISTENT_WRITE`, `DOMAIN_MUTATION` | StorageService / AssetService Manifest | `canonical_image_processing_service_prepare_image_asset`| `DEV_ONLY` |
| 43 | `THUMBNAIL` | `TOOL` | `IMAGE_PROCESSING` | `LOCAL` | `PROJECT` | `editor` | `PERSISTENT_WRITE` | StorageService / Project Cache | `canonical_image_processing_service_generate_thumbnail`| `DEV_ONLY` |

---

## 3. Mandatory Check O: Raw MCP Requirement for Internal Product AI

### 3.1 Question Statement
> **Check O**: Is raw MCP required for Internal Product AI?

### 3.2 Architectural Proof & AST Guard Enforcement
In `tests/ai/audit/test_s28_m11_final_architecture_audit.py:46-81`:
- **Guard 1 (`test_guard_01_no_raw_mcp_in_creative_planner`)**:
  ```python
  def test_guard_01_no_raw_mcp_in_creative_planner(self):
      """CreativePlanner and planning modules must have zero imports or calls to raw MCP servers."""
      for py_file in (AI_ROOT / "planning").rglob("*.py"):
          content = py_file.read_text(encoding="utf-8")
          assert "ai.mcp" not in content and "mcp_servers" not in content
  ```
- **Guard 3 (`test_guard_03_no_raw_mcp_transport_in_skills`)**:
  ```python
  def test_guard_03_no_raw_mcp_transport_in_skills(self):
      """Skills must resolve through CapabilityRouter or SkillRegistry, never direct raw MCP."""
      for py_file in (AI_ROOT / "skills").rglob("*.py"):
          content = py_file.read_text(encoding="utf-8")
          assert "ai.mcp" not in content and "mcp-servers" not in content
  ```
- **Guard 9 (`test_guard_09_domain_services_do_not_depend_on_compatibility_mcp`)**:
  Verifies that `scripts/core/`, `api/services/`, `ai/media_processing/`, `ai/image_processing/`, `ai/speech/`, and `ai/acquisition/` have zero import dependencies on `ai.mcp.compatibility`.

Furthermore:
- In `ai/tools/adapters/domain_service.py:8`:
  ```
  "ZERO raw MCP invocations for state mutations. Every domain operation routes through the authoritative 15-stage ToolGateway pipeline into DomainServiceAdapter."
  ```
- All internal tool invocations dispatch via `CapabilityRouter` $\to$ `ToolGateway` $\to$ Python domain adapters (`LocalMediaProcessingService`, `LocalSpeechPreparationService`, `DomainServiceAdapter`).
- Raw MCP servers (`.agents/plugins/.../tools/mcp-servers/`) are wrapped behind `FastMCP` compatibility facades (`ai/mcp/compatibility/server.py`) for external developer/agent tools only.

### 3.3 Answer to Check O
**NO** (`CODE_PROVEN`, `TEST_PROVEN`).
Raw MCP is **not required** and is **strictly forbidden** for Internal Product AI. All internal operations execute via strongly typed in-process Python services and `ToolGateway`.

---

## 4. The 15-Stage Tool Gateway Pipeline (`ai/tools/gateway.py`)

`ToolGateway.execute()` (`ai/tools/gateway.py:258-525`) is the single authoritative gateway for capability execution:

```
[Incoming CapabilityRequest]
              │
              ▼
    Stage 1: Capability Lookup (Resolves CapabilityDefinition from CapabilityCatalog)
              │
    Stage 2: Input Contract Resolution (Resolves canonical Pydantic model)
              │
    Stage 3: Input Contract Validation (Strict Pydantic model_validate)
              │
    Stage 4: TenantContext Validation (Enforces workspace_id match; validates PROJECT/SYSTEM scope)
              │
    Stage 5: Authorization Enforcement (Verifies required_permissions against actor roles)
              │
    Stage 6: Resource Ownership / Confinement (Prevents directory traversal outside projects/)
              │
    Stage 7: Side-Effects Policy Enforcement (Evaluates full side_effects[] array: SSRF, storage, subprocess)
              │
    Stage 8: Budget & Spending Ceiling Policy (Enforces max cost & quota limits)
              │
    Stage 9: Idempotency Enforcement (CAS leadership claim & in-flight replay)
              │
    Stage 10: Timeout & Deadline Policy (Sets asyncio.wait_for bounded deadline)
              │
    Stage 11: Adapter Selection (Resolves adapter from AdapterRegistry; checks security blocks)
              │
    Stage 12: Adapter Execution (Async execution within isolated process/thread)
              │
    Stage 13: Output Contract Validation (Validates raw output against output_contract Pydantic schema)
              │
    Stage 14: Storage & Integrity Verification (Validates output storage keys against path traversal)
              │
    Stage 15: Telemetry & Structured Result (Emits CapabilityResult with latency, cost, and metadata)
              │
              ▼
[Outgoing CapabilityResult]
```

### 4.1 Security Invariants Enforced by the Gateway
1. **SSRF Guardrail (`FORBIDDEN_SCHEMES`)**:
   - Blocks non-HTTP/HTTPS schemes (`file://`, `ftp://`, `gopher://`, `data://`).
   - Resolves DNS and blocks loopback (`127.0.0.1`), private RFC1918 subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`), link-local (`169.254.0.0/16`), and AWS/GCP cloud metadata endpoints (`169.254.169.254`).
2. **Security-Blocked Implementations**:
   - `CONCATENATE_VIDEOS` is explicitly hard-blocked (`MCPToolAdapter.STATIC_CAPABILITY_BINDINGS:83`) due to a verified shell injection finding in the legacy implementation. Attempts to invoke it fail closed with `ImplementationSecurityBlockedError`.
3. **Compound `side_effects[]` Processing**:
   - The gateway parses the full `side_effects` array (not just the scalar fallback), simultaneously applying network egress guards, storage confinement, and subprocess constraints for compound capabilities.

---

## 5. Comprehensive Repository-Wide Bypass Sweep

An exhaustive static sweep across the entire repository evaluates five common architectural bypass vectors:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           BYPASS AUDIT SUMMARY                              │
├──────────────────────────┬──────────────┬───────────────────────────────────┤
│ Bypass Vector            │ Status       │ Findings & Evidence               │
├──────────────────────────┼──────────────┼───────────────────────────────────┤
│ 1. AI Directly to Model  │ BYPASS FOUND │ plan_gate.py:26 calls OpenAI()    │
│                          │ (Legacy Gate)│ directly, bypassing ModelRouter.  │
│ 2. Raw MCP Bypass        │ CLEAN        │ Zero raw MCP calls in ai/. AST    │
│                          │              │ guards prevent regressions.       │
│ 3. Arbitrary Shell Exec  │ CLEAN        │ Zero shell=True in production.    │
│                          │              │ All subprocesses use argv lists.  │
│ 4. Filesystem Direct CAS │ PARTIAL      │ Core and authoring enforce CAS.   │
│                          │ BYPASS       │ Maintenance scripts write direct. │
│ 5. Domain Service Bypass │ BYPASS FOUND │ pipeline.py advances state via    │
│                          │ (Pipeline)   │ save_state() instead of service.  │
└──────────────────────────┴──────────────┴───────────────────────────────────┘
```

### 5.1 Bypass Vector 1: AI Directly to Upstream Provider (Bypass Found)
- **Violation**: `scripts/gates/plan_gate.py:26-53` imports `from openai import OpenAI` and calls `client.chat.completions.create(model="gpt-4o", ...)` directly.
- **Architectural Impact**: Bypasses `ModelRouter`, `ProviderRegistry`, `CapabilityRouter`, `AITracer`, and OpenRouter development gateway. Furthermore, if `OPENAI_API_KEY` is absent or the API fails, it silently returns `True, []`, skipping the check.

### 5.2 Bypass Vector 2: Raw MCP Protocol Bypass (Clean)
- **Status**: **CLEAN** in modern architecture (`CODE_PROVEN`, `TEST_PROVEN`).
- **Evidence**: `tests/ai/audit/test_s28_m11_final_architecture_audit.py` (Guards 1, 3, 9) rigorously scan the codebase and verify that no creative planning, narrative, skill, recipe, or domain service imports or calls raw MCP servers.

### 5.3 Bypass Vector 3: Arbitrary Shell Execution (`shell=True`) (Clean)
- **Status**: **CLEAN** across the entire repository (`CODE_PROVEN`).
- **Evidence**: Repository-wide AST search confirms zero instances of `shell=True` in production code. All calls execute via `safe_subprocess` (`scripts/security/security.py`) or `asyncio.create_subprocess_exec` using explicit argument lists.

### 5.4 Bypass Vector 4: Direct Filesystem Writes Bypassing Storage CAS (Partial Bypass)
- **Status**: Enforced in product authoring; bypassed in maintenance/legacy scripts.
- **Evidence**: `AuthoringService` and `CanonicalDocumentRepository` strictly enforce CAS locks on video documents. However, legacy scripts (`scripts/maintenance/sync_templates.py`, `scripts/archive/migrate_state.py`) write files directly to disk without revision checking or CAS.

### 5.5 Bypass Vector 5: State Machine Domain Service Bypass (Bypass Found)
- **Violation**: `scripts/pipeline.py:427` directly writes lifecycle state via local `save_state(LifecycleState.AWAITING_REVIEW, [])` rather than invoking `LifecycleService` (`scripts/core/lifecycle_service.py`).
- **Architectural Impact**: Circumvents lifecycle precondition checks and transition validation guards codified in `LifecycleService`.

---

## 6. Production vs. Dev/Test Reachability Analysis

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       SUBSYSTEM REACHABILITY SUMMARY                        │
├───────────────────────────────┬──────────────────────────┬──────────────────┤
│ Subsystem                     │ Production Reachability  │ Status           │
├───────────────────────────────┼──────────────────────────┼──────────────────┤
│ FastAPI REST Routes (api/)    │ PRODUCTION_REACHABLE     │ Active HTTP      │
│ Pipeline Worker (worker.py)   │ PRODUCTION_REACHABLE     │ Active Daemon    │
│ State Machine (pipeline.py)   │ PRODUCTION_REACHABLE     │ Subprocess       │
│ Authoring Engine (authoring/) │ PRODUCTION_REACHABLE     │ Subprocess IPC   │
│ Remotion Adapter (remotion/)  │ PRODUCTION_REACHABLE     │ Primary Render   │
│ Master Compositor             │ PRODUCTION_REACHABLE     │ Primary Render   │
│ CapabilityRouter              │ UNREACHABLE_FROM_PRODUCT │ Dev / Test Only  │
│ ToolGateway                   │ UNREACHABLE_FROM_PRODUCT │ Dev / Test Only  │
│ ModelRouter                   │ UNREACHABLE_FROM_PRODUCT │ Dev / Test Only  │
│ OpenRouterProvider           │ DEV_ONLY                 │ Benchmark Only   │
│ LocalSTTProvider              │ DEV_ONLY                 │ Benchmark Only   │
│ FastMCP Compatibility Server  │ COMPATIBILITY_ONLY       │ External Tools   │
└───────────────────────────────┴──────────────────────────┴──────────────────┤
```

Neither `CapabilityRouter`, `ToolGateway`, nor `ModelRouter` receive real customer traffic from `api/` or `scripts/pipeline.py`. They operate as an active development platform exercised by unit, integration, and evaluation suites (`tests/ai/`).

---

## 7. File & Symbol Evidence Index

| File Path | Symbol / Function | Line Range | Architectural Function | Classification |
|---|---|---|---|---|
| `documentation/s28m/CAPABILITY_CATALOG.json` | `capabilities` array | 1-43 | Authoritative 43 capability definitions | `CODE_PROVEN` |
| `ai/capabilities/catalog.py` | `CapabilityCatalog` | 34-110 | In-memory catalog loader and lookup | `CODE_PROVEN` |
| `ai/routing/capability_router.py` | `CapabilityRouter` | 69-140 | Routes MODEL $\to$ ModelRouter, TOOL $\to$ Gateway | `CODE_PROVEN` |
| `ai/tools/gateway.py` | `ToolGateway.execute` | 258-525 | Authoritative 15-stage execution pipeline | `CODE_PROVEN` |
| `ai/tools/gateway.py` | `validate_safe_url` | 79-115 | SSRF and network egress validation | `CODE_PROVEN` |
| `ai/tools/adapters/mcp.py` | `STATIC_CAPABILITY_BINDINGS` | 70-91 | Hardened static MCP bindings map | `CODE_PROVEN` |
| `ai/tools/adapters/mcp.py` | Blocked `CONCATENATE_VIDEOS`| 83 | Explicit security block for shell injection | `CODE_PROVEN` |
| `ai/mcp/compatibility/server.py` | `CompatibilityMCPServer` | 35-110 | FastMCP wrapper delegating to ToolGateway | `CODE_PROVEN` |
| `tests/ai/audit/test_s28_m11_final_architecture_audit.py`| `TestS28M11ArchitectureAudit` | 43-180 | AST architecture guard test suite | `TEST_PROVEN` |
| `scripts/gates/plan_gate.py` | `ask_llm_judge` | 16-64 | Ad-hoc OpenAI client bypass | `CODE_PROVEN` |
| `ai/providers/openrouter.py` | `OpenRouterProvider` | 57-70 | Development-only OpenRouter provider | `CODE_PROVEN` |
| `scripts/security/security.py` | `safe_subprocess` | 15-50 | Hermetic subprocess runner (zero shell=True) | `CODE_PROVEN` |

---

## 8. Strategic Remediation Direction

1. **Eliminate `plan_gate.py` Direct Provider Bypass**: Refactor `ask_llm_judge` in `scripts/gates/plan_gate.py` to route through `CapabilityRouter` using a typed `CRITIQUE_PLAN` capability, removing direct `OpenAI` client instantiation and unifying telemetry with `AITracer`.
2. **Expose Capability Gateway to API**: Wire `ToolGateway` directly into FastAPI under a managed administrative router (e.g. `POST /api/v1/capabilities/execute`), allowing authenticated clients to invoke media tools securely.
3. **Graduate Modern Concatenation**: Replace the blocked legacy `CONCATENATE_VIDEOS` MCP tool with the hardened, memory-safe `LocalMediaProcessingService.concatenate()` in `ai/media_processing/`.


---

