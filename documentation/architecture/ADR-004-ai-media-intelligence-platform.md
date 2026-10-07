# ADR-004: AI & Media Intelligence Platform Architecture (S27)

## Metadata
- **Status:** APPROVED (DEC-06)
- **Date:** 2026-09-30
- **Deciders:** Lead Architect / CTO & Repository Owner
- **Consulted:** S26 Governance & Core Engineering Team
- **Informed:** Video Production, Infrastructure, and Security Teams

---

## 1. Context and Problem Statement

Throughout S00–S26, `clean-video-workspace` was hardened into a deterministic, transactional video generation engine featuring:
- Server-verified identity and authorization (`ADR-002`, S02).
- Single lifecycle authority via `LifecycleService` with atomic CAS state transitions (S03, S05).
- Review bundles, human review decisions, and cryptographic render authorization (`ReviewService`, S09).
- Canonical Blueprint and Manifest V2 schemas with bi-directional TypeScript/Python parity (S11, S12).
- Ephemeral worker execution decoupled from local workspace state (S20, S24.5).
- Multi-tenant data isolation and `StorageService` abstraction (`ADR-003`, S24.5).

However, intelligent operations (script generation, template selection, audio analysis, media generation, captioning, and review interactions) remained either:
1. Delegated to external LLM agent prompts reading unstructured markdown guides (`.agents/rules/video-production-protocol.md`).
2. Executed via unmetered, fragmented CLI scripts (`image_provider.py`, `fal_seedance_video.py`, `heygen_client.py`) that read `.env` directly and write unmanaged files to root folders.
3. Mediated by local MCP servers that operate directly on raw filesystem paths without tenant awareness.

We must establish the architecture for an internal, provider-neutral **AI & Media Intelligence Platform** (S27).

---

## 2. Core Architectural Invariant

The fundamental principle governing the AI platform is:

```text
AI MAY REQUEST ACTIONS.
AI NEVER BECOMES AUTHORITY.
```

Specifically:
- **AI is NOT Source of Truth:** Core database (`database.py`), CAS state store (`StateStore`), and canonical manifests are the sole sources of truth.
- **AI is NOT Authorization Authority:** The AI cannot grant permissions, switch tenants, or forge actor identities. Identity is strictly derived from server-verified `Principal` and `TenantContext`.
- **AI is NOT Lifecycle Authority:** Project lifecycle transitions are the exclusive monopoly of `LifecycleService.transition()`. AI cannot mutate `state.lifecycle_state`.
- **AI is NOT QC Authority:** Quality control, probe validation, and render authorization belong solely to `SmartQC`, `ProbePlanner`, `FinalQC`, and `ReviewService`. AI cannot emit `.studio_approved` or declare QC passed.
- **AI is NOT Filesystem Authority:** AI cannot read, write, or delete raw project directories. All persistent assets are mediated via `StorageService` and `AssetService`.
- **AI is NOT Template Registry Authority:** AI cannot directly mutate `templates/` or `registry/`.

### Canonical Interaction Topology

```text
┌────────────────────────────────────────────────────────┐
│                   GUI / API Layer                      │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│                AI Orchestration Engine                 │
│  (ContextBuilder, MemorySystem, CapabilityRouter)      │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│               Controlled Tool Layer                    │
│   (ToolRegistry, ToolDispatcher, PolicyEnforcer)       │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│                   Domain Services                      │
│ (ProjectService, AssetService, PipelineService, etc.)  │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│             Existing Deterministic Core                │
│    (StateStore, LifecycleService, ReviewService)       │
└───────────────────────────┬────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│                 Render / Probe / QC                    │
│        (Worker, Remotion, FFmpeg, SmartQC)             │
└────────────────────────────────────────────────────────┘
```

**Forbidden Direct Access:**
```text
ai/* ──❌──> Raw Project Filesystem (e.g., projects/{id}/*)
ai/* ──❌──> Raw Database SQL (bypassing repositories)
ai/* ──❌──> Direct Lifecycle Mutation (state.lifecycle_state = ...)
ai/* ──❌──> Template Registry Mutation (templates/*, registry/*)
ai/* ──❌──> Direct Approval / QC Bypass (.studio_approved, ReviewDecision)
```

---

## 3. Binding Architectural Decisions for S27

### DEC-06.1: Python as AI Orchestration Language
- **Decision:** Python 3.12+ is the sole language for AI orchestration, capability routing, memory management, provider adapters, context construction, and media intelligence workers.
- **Rationale:** Deep native ML/AI ecosystem, native FastAPI integration, strong Pydantic contract validation, and asynchronous concurrency (`asyncio`). Native FFmpeg and C++ binaries handle heavy audio/video computation; Python orchestrates.

### DEC-06.2: Contract Authority Hierarchy
- **Decision:** The canonical source of truth for AI boundary contracts is Pydantic (Python).
- **Enforcement Pipeline:**
  ```text
  Pydantic Models (`ai/contracts/*.py`)
          ↓ (Export)
  JSON Schema (`schemas/ai/*.json`)
          ↓ (Code Generation)
  TypeScript Types (`remotion-app/src/types/ai/*.ts`)
  ```
- **Rule:** Hand-authoring duplicate TypeScript AI contracts is forbidden. All boundary objects entering Domain/Core must be validated Pydantic instances. Arbitrary `dict[str, Any]` is banned at boundary edges.

### DEC-06.3: Provider-Neutral Capability Abstraction
- **Decision:** The system reasons in terms of domain **Capabilities**, never vendor model names or proprietary APIs.
- **Examples:** `TEXT_TO_SPEECH`, `SPEECH_TO_TEXT`, `VIDEO_GENERATION`, `IMAGE_GENERATION`, `REASONING`, `PLANNING`, `BEAT_DETECTION`, `LIP_SYNC`.
- **Rule:** Vendor strings (e.g., `elevenlabs_tts`, `gpt-4o`, `seedance-2.5`) must NEVER appear as business capability identifiers. Providers and models are swappable adapter plugins behind capability interfaces.

### DEC-06.4: PostgreSQL & pgvector for AI State and Memory
- **Decision:** Persistent AI memory, sessions, conversation summaries, decision logs, and embeddings reside in PostgreSQL using `pgvector`.
- **Tenancy First:** Vector similarity queries MUST apply strict tenant (`workspace_id`) filtering *before* ranking.
- **Search Strategy:** Exact search is standard initially; approximate nearest neighbor (HNSW/IVFFlat) indexes will be introduced only after empirical benchmarks demonstrate latency justification.
- **Scope Isolation:** No separate external vector database is permitted in S27.

### DEC-06.5: StorageService for Heavy AI Artifacts
- **Decision:** Large AI outputs (audio transcripts, frame analyses, generated images/videos, deep multi-modal reports) are persisted exclusively through `StorageService` (`LocalStorageBackend` or `S3CompatibleStorageBackend`).
- **Rule:** Host absolute filesystem paths are NEVER exposed to AI contracts. Objects are referenced via deterministic `AssetRef` or storage keys.

### DEC-06.6: Controlled Tool Dispatcher & Security Policy
- **Decision:** AI models interact with system operations exclusively via typed, authorized tools mediated by `ToolDispatcher`.
- **Invariants:**
  - Tools declare a `SideEffectClass`: `READ_ONLY`, `PROJECT_MUTATION`, `RUN_CONTROL`, `EXTERNAL_GENERATION`, `ADMIN`.
  - Identity parameters (`workspace_id`, `actor_id`, `roles`) CANNOT be supplied or overridden by AI output. They are injected by the execution runtime from the caller's server-verified `TenantContext`.

### DEC-06.7: Durable AI Orchestration & Observability
- **Decision:** Multi-step AI workflows must be modeled as durable DAG runs (`AIRun` and `AIStep`) with step leasing, timeouts, idempotency keys, and crash recovery.
- **Budget Control:** Expensive external model calls require upfront budget estimation and reservation before dispatch, with atomic settlement upon completion.
- **Telemetry:** OpenTelemetry semantic conventions for Generative AI operations serve as the standard observability foundation.

---

## 4. S27.0 Implementation Boundaries

> [!IMPORTANT]
> **S27.0 Scope Boundary:**
> This stage encompasses **Inventory, Architecture Freeze, Boundaries, Bootstrap, and Architecture Guards only**.
> 
> The following items are explicitly DEFERRED to subsequent S27 stages and MUST NOT be implemented in S27.0:
> - No AI models or Provider SDKs (OpenAI, Anthropic, Gemini, ElevenLabs, Fal, Replicate).
> - No Model Router or Capability Router implementation.
> - No Memory System or pgvector tables/migrations.
> - No Context Builder or Prompt Engine.
> - No database schema modifications for AI state.
> - No live migration or deletion of legacy tools or MCP servers.

---

## 5. Architectural Enforcement Mechanisms

Architecture conformance is verified automatically in CI via:
- `tests/ai/test_ai_architecture_guards.py`: AST-based validation preventing raw filesystem access, direct SQL, lifecycle mutation, and QC bypass.
- `scripts/ci/run_required_checks.sh`: Integrated gate running architecture checks alongside existing test suites.
- `tests/architecture/`: Comprehensive regression coverage for core system trust boundaries.
