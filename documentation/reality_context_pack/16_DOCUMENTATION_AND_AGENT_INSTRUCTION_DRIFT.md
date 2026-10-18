# Documentation & Agent Instruction Drift Reality Report

- **Baseline Git SHA**: `90ec3de8d47494d5940d5cd1f9ed9a8e274ef6e1`
- **Branch**: `main`
- **Report Version**: 1.0.0
- **Last Updated**: 2026-10-07
- **Scope**: Comprehensive audit of contradictions, obsolete instructions, semantic divergence, and false constraints between developer/agent documentation (`.agents/AGENTS.md`, `documentation/architecture/ARCHITECTURE_TRUTH.md`, `references/ROUTER.md`, playbooks) and executable codebase reality.
- **Evidence Standard**: `CODE_PROVEN`, `TEST_PROVEN`, `CI_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`, `DOCUMENTATION_ONLY`, `INFERRED`, `UNKNOWN`

---

## 1. Executive Summary

A critical threat to agent operation and human developer onboarding in this repository is **Documentation Drift**. As the codebase underwent multiple remediation cycles (S00 through S26, followed by S27, S28, S28-M, and S28-R), agent prompt files (`.agents/AGENTS.md`) and reference manuals (`references/ROUTER.md`) retained legacy rules, outdated path assertions, and obsolete operational mandates that contradict active runtime constraints and CI gates.

This report systematically catalogs every identified drift point between documented instructions and executable code reality.

---

## 2. Detailed Drift Audit: `.agents/AGENTS.md` vs. Code Reality

`.agents/AGENTS.md` is the primary instruction file loaded into the system prompt for AI orchestrators working in this repository.

| # | Documented Rule in `AGENTS.md` | Actual Code / Runtime Reality | Drift Severity & Impact | Concrete Evidence Citations |
|---|---|---|---|---|
| **D1** | **Source of Truth Hierarchy**: Claims `ARCHITECTURE_TRUTH.md` is at Level 3 of the authority hierarchy. | File does not exist at root. It is located at `documentation/architecture/ARCHITECTURE_TRUTH.md`. Agents attempting to read `./ARCHITECTURE_TRUTH.md` encounter file not found errors. | **MEDIUM** (Operational friction) | `.agents/AGENTS.md:3`, `documentation/architecture/ARCHITECTURE_TRUTH.md:1` [`CODE_PROVEN`] |
| **D2** | **Mandatory Plan Line Count (Rule 4)**: "Plans must not exceed 490 lines or fall below 480 lines (unless structurally necessary based on references)." | `scripts/gates/plan_gate.py` contains **zero line count assertions**. It verifies markdown headers, timing markers, and scene names via regex, accepting valid plans whether they are 50 lines or 600 lines. The 480-490 rule is an artificial, ungrounded agent constraint. | **HIGH** (Brittle hallucination; forces agents into bizarre padding hacks) | `.agents/AGENTS.md:31`, `scripts/gates/plan_gate.py:50-180` [`CODE_PROVEN`] |
| **D3** | **Approved MCP Server Mandate (Rule 5 & 8)**: "Fetch media strictly through the approved MCPs (`media-sources-mcp`, `audio-tools-mcp`)... Call tools directly via the MCP Client." | Generation S28-M strictly bans internal AI code from making raw MCP JSON-RPC calls. Static AST guards (`tests/ai/audit/test_s28_m11_final_architecture_audit.py`) fail if raw MCP tools are invoked. Capabilities must route through `CapabilityRouter` and `ToolGateway` via native Python adapters. | **CRITICAL** (Architectural violation; contradicts S28-M governance) | `.agents/AGENTS.md:34,51-57`, `tests/ai/audit/test_s28_m11_final_architecture_audit.py:47-81` [`CODE_PROVEN`, `TEST_PROVEN`] |
| **D4** | **Engine Usage Mandate (Rule 7)**: "The engine is an ACTIVE production subsystem... Use the established engine integration path (`templates/effects/engine-bridge.tsx`)." | `remotion-app/tsconfig.json` explicitly excludes `src/engine/**/*` (`"exclude": ["src/engine/**/*"]`). In S28-R, rendering is managed via `RendererAdapter` and `RenderPlanner`, decoupling the engine from direct template bridge dependencies. | **HIGH** (Obsolete integration boundary; instructs agents to use excluded modules) | `.agents/AGENTS.md:43-48`, `remotion-app/tsconfig.json:16-19`, `remotion/remotion-renderer-adapter.ts:8-16` [`CODE_PROVEN`] |
| **D5** | **Banned Video Editor MCP (Rule 9)**: "Do not use the Video_Editor_MCP (quarantined)." | While `AGENTS.md` quarantines it, `references/ROUTER.md:42` explicitly recommends it: `| أمر FFmpeg حر | video-editor | execute_command |`. This creates conflicting directives between the Agent rulebook and the Router playbook. | **MEDIUM** (Conflicting directives) | `.agents/AGENTS.md:63`, `references/ROUTER.md:42` [`DOCUMENTATION_ONLY`] |
| **D6** | **Pipeline Orchestration Exclusivity (Rule 2)**: "You MUST rely entirely on the canonical orchestrator (`python scripts/pipeline.py <project_id>`) to detect changes and validate gates." | While accurate for CLI rendering, this rule ignores the entire S26/S28-R HTTP application (`api/main.py`), the asynchronous worker queue (`scripts/core/worker.py`), and the live authoring AST mutation API (`/intent`, `/mutate`), leaving agents unaware of the production API. | **MEDIUM** (Incomplete system scope) | `.agents/AGENTS.md:14-18`, `api/main.py:45-70` [`CODE_PROVEN`] |

---

## 3. Detailed Drift Audit: `ARCHITECTURE_TRUTH.md` vs. Code Reality

`documentation/architecture/ARCHITECTURE_TRUTH.md` is designated as the constitutional root for system architecture.

| # | Documented Claim in `ARCHITECTURE_TRUTH.md` | Actual Code / Runtime Reality | Drift Severity & Impact | Concrete Evidence Citations |
|---|---|---|---|---|
| **A1** | **Section 3 (Official Entry Points)**: Lists API as `api/services/`. | `api/services/` contains domain service classes (`AssetService`, `RunService`, `AuthoringService`). The official API entrypoints are the FastAPI router endpoints in `api/routers/` mounted via `api/main.py`. | **LOW** (Minor terminology inaccuracy) | `documentation/architecture/ARCHITECTURE_TRUTH.md:24`, `api/main.py:57-70` [`CODE_PROVEN`] |
| **A2** | **Section 5 (State Ownership - INVARIANT-02)**: "Canonical State: `.pipeline_state.json`... This file is the sole source of truth for a project's progress through the pipeline gates. Neither the Agent nor the API may implement alternative state tracking." | In S26/S28 multi-tenant mode, state is tracked and versioned via CAS in the `project_states` table in SQLite/PostgreSQL (`scripts/core/database.py:97-106`). `api/routers/projects.py` and `CanonicalDocumentRepository` query the database first, creating competing sources of truth. | **HIGH** (Divergent state authority) | `documentation/architecture/ARCHITECTURE_TRUTH.md:33-36,80`, `scripts/core/database.py:97-106` [`CODE_PROVEN`] |
| **A3** | **Section 10 (MCP Layer)**: "MCP Servers provide local tool augmentation. Rule: Use `ffmpeg-mcp-server` over raw shell `ffmpeg` where possible." | `scripts/core/worker.py`, `scripts/render_project.py`, `compositor/master-compositor.ts`, and `probe_qc.py` invoke `ffmpeg` and `ffprobe` directly via `safe_subprocess` or Node child processes. Zero production pipeline stages use `ffmpeg-mcp-server`. | **HIGH** (Direct contradiction between documented tool choice and runtime code) | `documentation/architecture/ARCHITECTURE_TRUTH.md:60-64`, `compositor/master-compositor.ts:18-35`, `scripts/render_project.py:45` [`CODE_PROVEN`] |
| **A4** | **Absence of S27/S28 AI Subsystems**: `ARCHITECTURE_TRUTH.md` contains **zero mentions** of `ai/`, `ContextBuilder`, `CapabilityRouter`, `ToolGateway`, `CreativePlanner`, or the 32 capabilities. | The document reflects the system state at S25/S26, completely omitting the massive AI platform and creative intelligence subsystems developed in S27 and S28. | **CRITICAL** (Constitutional blindness to entire AI platform) | `documentation/architecture/ARCHITECTURE_TRUTH.md:1-108` [`CODE_PROVEN`] |

---

## 4. Detailed Drift Audit: `references/ROUTER.md` vs. Code Reality

`references/ROUTER.md` is described in its header as "العقل الموجّه" (the directing mind).

| # | Documented Claim in `ROUTER.md` | Actual Code / Runtime Reality | Drift Severity & Impact | Concrete Evidence Citations |
|---|---|---|---|---|
| **R1** | **Section 1 (Pipeline Reference)**: Claims the global pipeline is inspired by `patterns/index.ts`. | No file named `patterns/index.ts` exists anywhere in the repository. | **MEDIUM** (Phantom code reference) | `references/ROUTER.md:11` [`DOCUMENTATION_ONLY`] |
| **R2** | **Section 1 (Recipe Match Mandate)**: "Recipe Match: `python .agents/plugins/super-video-maker-plugin/tools/video_recipes.py match --goal '<الهدف>'` is mandatory before any build." | The modern recipe matching and registration platform resides in `ai/recipes/registry.py` (`RecipeRegistry`) and `ai/planning/recipe_selector.py` (`RecipeSelector`). The legacy script `video_recipes.py` is not even present in `tools/` (it was superseded or moved). | **HIGH** (Broken tool path) | `references/ROUTER.md:14`, `ai/recipes/registry.py:99-150` [`CODE_PROVEN`] |
| **R3** | **Section 2 (MCP Decision Matrix)**: Lists 7 MCP servers with mandatory execution for audio, video, image, and cache tasks. | Modern capability dispatch routes all of these tasks through Python native classes in `ai/capabilities/` and `ai/tools/adapters/native_tool.py`. Raw MCP calls are blocked by AST guards. | **HIGH** (Instructs agents to use superseded transport) | `references/ROUTER.md:21-44`, `ai/capabilities/catalog.py:1-120` [`CODE_PROVEN`] |
| **R4** | **Section 3 (Python Tools Table)**: Cites `ground-truth/TOOLS_INDEX.md` as the detail source. | `ground-truth/TOOLS_INDEX.md` is an auto-generated static list with zero runtime authority. | **LOW** (Derivative citation) | `references/ROUTER.md:45` [`DOCUMENTATION_ONLY`] |

---

## 5. Architectural Recommendations & Harmonization Plan (DO NOT FIX YET)

To eliminate documentation drift and establish a single coherent operating manual:

1. **Update `.agents/AGENTS.md`**:
   - Fix path to `documentation/architecture/ARCHITECTURE_TRUTH.md`.
   - Remove the ungrounded 480-490 plan line count rule; replace with structural section validation.
   - Clarify that AI agents must use `CapabilityRouter` / native Python tools rather than raw MCP servers.
   - Remove reference to excluded `templates/effects/engine-bridge.tsx`.
   - Add awareness of FastAPI REST entrypoints and the S28-R Live Authoring mutation API.
2. **Revise `ARCHITECTURE_TRUTH.md`**:
   - Expand Section 2 & 10 to document the S27/S28 AI platform (`ai/`) and its current isolation boundary from the production HTTP run pipeline.
   - Document the S28-R renderer-neutral contracts (`contracts/blueprint.ts`) and RenderPlanner architecture.
   - Reconcile the state ownership model (clarifying relationship between `.pipeline_state.json` and SQL `project_states`).
3. **Deprecate or Modernize `references/ROUTER.md`**:
   - Remove phantom paths (`patterns/index.ts`, `video_recipes.py`).
   - Align tool recommendations with S28-M Capability Catalog IDs (`AUDIO_VO_ANALYZE`, `IMAGE_UPSCALE`, etc.).
