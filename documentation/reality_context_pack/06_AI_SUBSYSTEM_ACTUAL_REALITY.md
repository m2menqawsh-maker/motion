# 06 — AI Subsystem Actual Reality Report

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
