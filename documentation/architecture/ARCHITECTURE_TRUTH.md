# Architecture Truth

This document serves as the constitutional root for the system architecture. It defines *what exists* and the rules governing it.

## Source of Truth Hierarchy

If documentation conflicts, this is the order of authority:
1. **Runtime / Executable Behavior** (The ultimate truth of what actually runs)
2. **Tests** (The automated enforcement of the runtime)
3. **ARCHITECTURE_TRUTH.md** (This document)
4. **AGENTS.md** (How the Agent must interact with the system)
5. **references/** (How-to guides)
6. **Supporting Documentation**
7. **archive/** (Historical, non-actionable)

## 1. System Purpose
The system programmatically plans, assembles, and renders cinematic videos from dynamic templates and recipes using a strict stage-gated pipeline.

## 2. Canonical Architecture
There is a single unified backend pipeline bridging Python execution with a Remotion React rendering engine.
- **Evidence:** `scripts/pipeline.py` is the single executor that sequentially delegates to validators, generators, and rendering bridges. Parallel systems do not exist in the active runtime.

## 3. Official Entry Points
- **API:** `api/services/`
- **CLI/Agent:** `scripts/pipeline.py` or specific gated scripts (e.g., `scripts/open_studio.py`).
- **Rendering:** Remotion `npm run build` triggered solely through Python orchestrators.

## 4. Pipeline
The Canonical Pipeline is implemented in `scripts/pipeline.py`.
- **Status:** ACTIVE
- **Evidence:** `pipeline.py` drives the state transitions and is the only script invoked by the orchestrator for end-to-end execution.

## 5. State Ownership
- **Canonical State:** `.pipeline_state.json`
- **Rule:** This file is the sole source of truth for a project's progress through the pipeline gates. Neither the Agent nor the API may implement alternative state tracking.
- **Evidence:** `.pipeline_state.json` is read and written exclusively by `session_manager.py` and `pipeline.py`.

## 6. Remotion Runtime
The primary rendering environment is Remotion, hosted in `remotion-app/`.
- **Contracts:** Interfaces via `contracts/blueprint.ts`.

## 7. Engine Architecture
The engine provides advanced video rendering effects and primitives.
- **Status:** ACTIVE
- **Integration Boundary:** `templates/effects/engine-bridge.tsx`
- **Evidence:** `EngineBridge` is heavily imported in `BlueprintVideo.tsx` and dynamically bridges template requests into the `remotion-app/src/engine/` layer. The subsystem compiles in TypeScript and passes regression smoke tests.

## 8. Templates / Scenes / Compositions
Templates are strictly registered structural components.
- Ad-hoc template generation that bypasses the registry is forbidden.
- **Evidence:** `scripts/maintenance/template_router.py` strictly accesses registered components.

## 9. Contracts & Schemas
- **Data Contracts:** Located in `schemas/` (Python) and `contracts/` (TypeScript).
- **Rule:** Any cross-boundary communication must adhere to these schemas.

## 10. MCP Layer
MCP Servers (`media-sources-mcp`, `audio-tools-mcp`, `ffmpeg-mcp-server`, etc.) provide local tool augmentation.
- **Rule:** Use `ffmpeg-mcp-server` over raw shell `ffmpeg` where possible.
- **Evidence:** Servers are explicitly declared in plugin configs and `.agents/`.

## 11. Agent Architecture
The Agent is a master planner and pipeline orchestrator. It does not manually build videos or bypass gates.
- **Rule:** The Agent must strictly follow `AGENTS.md`.

## 12. Security Boundaries
- Raw shell execution is restricted.
- The pipeline `mechanical_lock` cannot be bypassed. User explicit approval is strictly required.
- **Evidence:** `security.py` and `path_security.py` actively restrict directory traversals and untethered subprocess execution.

## 13. Deprecated / Quarantined Systems
- Legacy pipelines, parallel rendering systems, and disconnected ghost instructions reside in `quarantine/` or `archive/`. They hold no architectural authority.

## 14. Architectural Invariants

- **INVARIANT-01**: There MUST be exactly one canonical production pipeline.
- **INVARIANT-02**: `.pipeline_state.json` is the canonical pipeline state.
- **INVARIANT-03**: The API MUST NOT implement pipeline logic independently.
- **INVARIANT-04**: The Agent MUST NOT bypass pipeline gates.
- **INVARIANT-05**: Engine features MUST enter rendering through approved integration boundaries (`EngineBridge`).
- **INVARIANT-06**: No unrestricted shell execution may be exposed to the Agent.
- **INVARIANT-07**: The plugin MUST NOT mirror root canonical scripts, templates, recipes, references, security configuration, or system ground truth without an explicit generated contract. All tools and MCP servers must resolve canonical resources through the repository root.

## 15. Plugin Architectural Boundary & Ownership

- **Canonical Ownership**: The repository root owns all canonical application and runtime truths:
  - `templates/` (Remotion templates)
  - `scripts/` (Pipeline orchestrators, gates, and build scripts)
  - `recipes/` (Production recipes)
  - `references/` (Documentation and guides)
  - `config/` (Security policies and violations configuration)
  - `ground-truth/` (System ground-truth indexes, including `ASSET_INDEX.json`)

- **Plugin Role**: `.agents/plugins/super-video-maker-plugin` is a `REPO_COUPLED` integration subsystem responsible exclusively for:
  - Plugin discovery manifest (`plugin.json`)
  - Agent skills (`skills/remocn/`, `skills/snapcn/`)
  - MCP configuration (`mcp_config.json`)
  - MCP server implementations (`tools/mcp-servers/`)
  - External tool adapters (`tools/*.py`)
  - Agent command wrappers (`commands/*.md`)
