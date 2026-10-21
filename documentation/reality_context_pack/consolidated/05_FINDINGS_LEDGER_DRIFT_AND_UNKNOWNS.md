# PILLAR 5: Architectural Drift, Product Journey Gap, Unified Findings Ledger & Unknowns

> **Consolidated Master Pillar** — Comprehensive integration of Reports 14, 15, 16, 18, 19, and 20

> **Baseline SHA**: `90ec3de8d47494d5940d5cd1f9ed9a8e274ef6e1` | **Branch**: `main`

> **Evidence Standard**: Strictly Preserved (`CODE_PROVEN`, `TEST_PROVEN`, `CI_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`, `DOCUMENTATION_ONLY`, `INFERRED`, `UNKNOWN`)


---

## Table of Contents

1. [Part 1: Legacy Code, Historical Compatibility & Deletion Candidates](#part-1-legacy-code-historical-compatibility--deletion-candidates) *(Source: `14_LEGACY_HISTORICAL_COMPATIBILITY_AND_DELETION_CANDIDATES.md`)*
2. [Part 2: Cross-Generation Architecture Drift Analysis](#part-2-cross-generation-architecture-drift-analysis) *(Source: `15_CROSS_GENERATION_ARCHITECTURE_DRIFT.md`)*
3. [Part 3: Documentation & Agent Directive Instruction Drift](#part-3-documentation--agent-directive-instruction-drift) *(Source: `16_DOCUMENTATION_AND_AGENT_INSTRUCTION_DRIFT.md`)*
4. [Part 4: True Product Journey Edge-by-Edge Gap Analysis](#part-4-true-product-journey-edge-by-edge-gap-analysis) *(Source: `18_TRUE_PRODUCT_JOURNEY_GAP_ANALYSIS.md`)*
5. [Part 5: Unified Findings Ledger (REALITY-001 through REALITY-024+)](#part-5-unified-findings-ledger-reality-001-through-reality-024+) *(Source: `19_FINDINGS_LEDGER.md`)*
6. [Part 6: Catalog of Critical Unknowns & Required Follow-Up Probes](#part-6-catalog-of-critical-unknowns--required-follow-up-probes) *(Source: `20_UNKNOWNS_AND_UNPROVEN_CLAIMS.md`)*

---


<a name='part-1-legacy-code-historical-compatibility--deletion-candidates'></a>

## Part 1: Legacy Code, Historical Compatibility & Deletion Candidates


> *Original Source: `documentation/reality_context_pack/14_LEGACY_HISTORICAL_COMPATIBILITY_AND_DELETION_CANDIDATES.md`*


### Sub-Report Title: Legacy, Historical Compatibility & Deletion Candidates Reality Report


- **Baseline Git SHA**: `90ec3de8d47494d5940d5cd1f9ed9a8e274ef6e1`
- **Branch**: `main`
- **Report Version**: 1.0.0
- **Last Updated**: 2026-10-07
- **Scope**: Comprehensive repository-wide audit of legacy directories, compatibility layers, historical migration artifacts, deprecated API routes, MCP server boundaries, and candidate evaluation for safe deletion vs preservation.
- **Evidence Standard**: `CODE_PROVEN`, `TEST_PROVEN`, `CI_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`, `DOCUMENTATION_ONLY`, `INFERRED`, `UNKNOWN`

---

## 1. Executive Summary & Audit Methodology

Across the evolution of the video creation engine (spanning historical generations from Pre-S25 through S28-R), numerous subsystems, tools, migration scripts, and documentation files were introduced, modified, or superseded.

This audit evaluates every suspect legacy artifact across the repository using a strict **Zero-Presumption Consumer Analysis**:
1. An artifact is classified as a **`DELETE_CANDIDATE`** **ONLY IF** it has **exactly 0 active consumers** across:
   - Production API runtime (`api/`)
   - Production pipeline & worker runtime (`scripts/core/`, `scripts/pipeline.py`, `scripts/gates/`, `scripts/generators/`, `scripts/render_project.py`)
   - Active TypeScript runtime & contracts (`authoring/`, `contracts/`, `planner/`, `preview/`, `compositor/`, `registry/`, `remotion/`, `canvas/`, `remotion-app/`)
   - Active AI & capability subsystems (`ai/`)
   - Active development tooling & maintenance utilities (`scripts/maintenance/`, `scripts/validators/`)
   - Active automated test suites (`tests/`)
   - Required CI workflows (`.github/workflows/remediation-ci.yml`, `scripts/ci/run_required_checks.sh`)
   - Active normative documentation (`documentation/architecture/`, `schemas/`)
2. If an artifact has even a single consumer in any category—including negative regression tests, CI hash/drift validators, or backwards-compatible API adapters—it is strictly classified as **`NOT SAFE TO DELETE YET`**, documenting the exact consumer, failure mode, and prerequisites for future retirement.

---

## 2. Directory & Component Legacy Audit

### 2.1 Audit of `scripts/archive/` (Historical Migration Scripts & Phases)

The `scripts/archive/` directory contains 8 Python files and 4 subdirectories (`phase13/`, `phase14/`, `phase15/`, `phase16/`) totaling 23 scripts.

| Path | Purpose / Description | Consumers Identified | Classification | Deletion Safety Rationale |
|---|---|---|---|---|
| `scripts/archive/migrate_legacy_projects.py` | Legacy project manifest migration utility. | `tests/archive/test_migrate_legacy.py:4` imports `migrate_project`. | `NOT SAFE TO DELETE YET` | Actively imported by automated test suite. Deletion breaks `pytest tests/archive/test_migrate_legacy.py`. Requires deprecating the test first. [`TEST_PROVEN`] |
| `scripts/archive/migrate_state.py` | State format migration script from early milestones. | `tests/golden_scenarios/test_migration_from_legacy.py:4,15` imports `migrate_project` and `ms`. | `NOT SAFE TO DELETE YET` | Actively imported by golden scenario test suite. Deletion causes test failure. [`TEST_PROVEN`] |
| `scripts/archive/stitch_skill.py` | Idempotent file stitching tool for early skills. | Reads `ground-truth/PLAYBOOKS_INDEX.md:20`. Referenced in `documentation/archive/WORKSPACE_COMPREHENSIVE_GUIDE.md:520`. | `NOT SAFE TO DELETE YET` | Historical script reading ground-truth. While uncalled by production, removing it leaves dead documentation references. Safe only after doc cleanup. [`DOCUMENTATION_ONLY`] |
| `scripts/archive/classify_templates.py` | Early template classifier. | Zero imports in `api/`, `scripts/`, `tests/`, or `.github/`. | **`DELETE_CANDIDATE`** | Proven 0 consumers across production, tests, and CI. [`CODE_PROVEN`] |
| `scripts/archive/migrate_assets.py` | Legacy asset folder migrator. | Zero imports in `api/`, `scripts/`, `tests/`, or `.github/`. | **`DELETE_CANDIDATE`** | Proven 0 consumers across production, tests, and CI. [`CODE_PROVEN`] |
| `scripts/archive/smoke_crd019_templates.py` | Render smoke test for CRD-019. | Zero imports or executions in CI or `tests/`. | **`DELETE_CANDIDATE`** | Superseded by modern test suites (`tests/gates/`, `tests/core/`). Zero consumers. [`CODE_PROVEN`] |
| `scripts/archive/smoke_crd020_temporal.py` | Temporal verification smoke test for CRD-020. | Zero imports or executions in CI or `tests/`. | **`DELETE_CANDIDATE`** | Superseded by modern test suites. Zero consumers. [`CODE_PROVEN`] |
| `scripts/archive/phase13/` (3 files: `baseline.ts`, `coverage.ts`, `prioritize.ts`) | Phase 13 remediation analysis scripts. | Zero imports in root or `remotion-app/` package manifests, tests, or CI. | **`DELETE_CANDIDATE`** | Historical milestone scrap scripts with zero consumers. [`CODE_PROVEN`] |
| `scripts/archive/phase14/` (4 files: `baseline.ts`, `execution_bridge_audit.ts`, `patch_candidates.ts`, `prioritize.ts`) | Phase 14 execution bridge audit scripts. | Zero imports in production, tests, or CI. | **`DELETE_CANDIDATE`** | Historical milestone scrap scripts with zero consumers. [`CODE_PROVEN`] |
| `scripts/archive/phase15/` (4 files: `build_execution_cohorts.ts`, `generate_sample_batch.ts`, `validate_execution_contracts.ts`, `validate_verification_integrity.ts`) | Phase 15 cohort execution scripts. | Zero imports in production, tests, or CI. | **`DELETE_CANDIDATE`** | Historical milestone scrap scripts with zero consumers. [`CODE_PROVEN`] |
| `scripts/archive/phase16/` (12 files: `build_16_3_coverage_report.ts`, `mine_adapter_families.ts`, `validate_phase_16_3.ts`, etc.) | Phase 16 adapter family mining and analysis scripts. | Zero imports in production, tests, or CI. | **`DELETE_CANDIDATE`** | Historical milestone scrap scripts with zero consumers. [`CODE_PROVEN`] |

---

### 2.2 Audit of Root `ground-truth/` (13 Derivative Artifacts)

The root `ground-truth/` directory contains 13 files and a `collections/` subdirectory generated by `scripts/generators/build_ground_truth.py`.

| File | Purpose | Consumer & Verification Reality | Classification | Deletion Safety Rationale |
|---|---|---|---|---|
| `ground-truth/template_catalog.json` | JSON catalog of registered templates parsed from `registry/template-registry.tsx`. | Gated by `scripts/validators/check_ground_truth_sync.py:20`. Read by `ai/planning/reuse_engine.py:49` in test beds. Written by `scripts/core/template_registry_publisher.py:94`. | `NOT SAFE TO DELETE YET` | **CRITICAL CI FAILURE**: `.github/workflows/remediation-ci.yml:82` and `scripts/ci/run_required_checks.sh:21` run `check_ground_truth_sync.py --check`. Deleting this file causes CI to fail immediately with exit code 1. [`CI_PROVEN`] |
| `ground-truth/TEMPLATE_INDEX.md` | Markdown index of template props and schemas. | Gated by `check_ground_truth_sync.py`. Referenced by `.agents/AGENTS.md` and `references/ROUTER.md`. | `NOT SAFE TO DELETE YET` | Gated by CI hash verification. Deletion causes CI failure. [`CI_PROVEN`] |
| `ground-truth/ASSET_INDEX.json` | Generated index of static media assets. | Gated by `check_ground_truth_sync.py`. Read by legacy plugin tool `.agents/.../common-tools-mcp/utils/cache_ops.py:26`. | `NOT SAFE TO DELETE YET` | Gated by CI hash verification. Deletion causes CI failure. [`CI_PROVEN`] |
| `ground-truth/CINEMATIC_INDEX.md` | Index of cinematic zoom/motion presets. | Gated by `check_ground_truth_sync.py`. | `NOT SAFE TO DELETE YET` | Gated by CI hash verification. Deletion causes CI failure. [`CI_PROVEN`] |
| `ground-truth/MCP_INDEX.md` | Index of legacy MCP servers and tools. | Gated by `check_ground_truth_sync.py`. Referenced in `references/ROUTER.md:21`. | `NOT SAFE TO DELETE YET` | Gated by CI hash verification. Deletion causes CI failure. [`CI_PROVEN`] |
| `ground-truth/TOOLS_INDEX.md` | Index of Python scripts and gates. | Gated by `check_ground_truth_sync.py`. Referenced in `references/ROUTER.md:45`. | `NOT SAFE TO DELETE YET` | Gated by CI hash verification. Deletion causes CI failure. [`CI_PROVEN`] |
| `ground-truth/PLAYBOOKS_INDEX.md` | Index of playbooks and recipes. | Gated by `check_ground_truth_sync.py`. Read by `scripts/archive/stitch_skill.py:20`. | `NOT SAFE TO DELETE YET` | Gated by CI hash verification. Deletion causes CI failure. [`CI_PROVEN`] |
| `ground-truth/RECIPES_INDEX.md` | Index of recipe JSON files. | Gated by `check_ground_truth_sync.py`. | `NOT SAFE TO DELETE YET` | Gated by CI hash verification. Deletion causes CI failure. [`CI_PROVEN`] |
| `ground-truth/TEMPLATE_DUPLICATES.md` | Audit of duplicate template identifiers. | Gated by `check_ground_truth_sync.py`. | `NOT SAFE TO DELETE YET` | Gated by CI hash verification. Deletion causes CI failure. [`CI_PROVEN`] |
| `ground-truth/VOCAB_REMAP.md` | Vocabulary remapping index. | Gated by `check_ground_truth_sync.py`. | `NOT SAFE TO DELETE YET` | Gated by CI hash verification. Deletion causes CI failure. [`CI_PROVEN`] |
| `ground-truth/CANONICAL_PATHS.json` | Path indexing dictionary. | Gated by `check_ground_truth_sync.py`. | `NOT SAFE TO DELETE YET` | Gated by CI hash verification. Deletion causes CI failure. [`CI_PROVEN`] |
| `ground-truth/adapter_family_candidates.json` | Candidate adapter groupings. | Gated by `check_ground_truth_sync.py`. | `NOT SAFE TO DELETE YET` | Gated by CI hash verification. Deletion causes CI failure. [`CI_PROVEN`] |
| `ground-truth/orchestration_resolved_spec.json` | Orchestration specification snapshot. | Gated by `check_ground_truth_sync.py`. | `NOT SAFE TO DELETE YET` | Gated by CI hash verification. Deletion causes CI failure. [`CI_PROVEN`] |

**Crucial Architectural Note**:
Even though **0 production callers** exist on the live API or worker pipeline path for any file in `ground-truth/` (Mandatory Check K = 0), **NONE** of these files can be deleted without first removing `scripts/validators/check_ground_truth_sync.py` from CI! Because `check_ground_truth_sync.py` executes `git status --porcelain ground-truth/` and rejects any missing files, the entire directory is frozen under active CI governance.

---

### 2.3 Audit of `.agents/` Ecosystem & Plugins

The `.agents/` directory holds agent prompts, Docker files, skills, and the `super-video-maker-plugin`.

| Path / Component | Purpose | Consumer Analysis | Classification | Deletion Safety Rationale |
|---|---|---|---|---|
| `.agents/AGENTS.md` | Agent master rules and directives. | Loaded automatically into agent context. Constitution for orchestrator agents. | `NOT SAFE TO DELETE YET` | Active agent rule file. Deletion removes core behavioral constraints. [`CODE_PROVEN`] |
| `.agents/docker/Dockerfile.remotion` | Hermetic rendering container definition. | Built and tested in CI job `docker-render` (`.github/workflows/remediation-ci.yml:197,203-217`). | `NOT SAFE TO DELETE YET` | Actively built and gated in GitHub Actions CI. Deletion breaks the `docker-render` CI pipeline. [`CI_PROVEN`] |
| `.agents/skills/` (`prompt-engineering-expert/`, etc.) | Markdown skill definitions with YAML frontmatter. | Loaded dynamically by `SkillLoader.load_from_markdown()` and `load_skills_directory()` (`ai/skills/loader.py:62,160`). | `NOT SAFE TO DELETE YET` | Actively parsed by the skills subsystem. Deletion breaks dynamic skill registration. [`CODE_PROVEN`] |
| `.agents/plugins/super-video-maker-plugin/mcp_config.json` | MCP client server launch definitions. | Configures MCP clients. Contains legacy Windows absolute paths (`C:/video/...`). | `NOT SAFE TO DELETE YET` | Referenced by agent plugins and wrapped by FastMCP compatibility server. [`DOCUMENTATION_ONLY`] |
| `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/` (6 servers: `audio-tools-mcp`, `media-sources-mcp`, `video-tools-mcp`, `image-tools-mcp`, `common-tools-mcp`, `ffmpeg-mcp-server`) | Local MCP server implementations in Python and JS. | Wrapped by `ai/mcp/compatibility/server.py` (`CompatibilityMCPServer`). Tested in `tests/ai/mcp/test_development_agent_preservation.py`. | `NOT SAFE TO DELETE YET` | Actively verified by MCP preservation tests. Deleting servers causes test regressions. [`TEST_PROVEN`] |
| `.agents/plugins/super-video-maker-plugin/tools/elevenlabs_voice.py`, `replicate_video.py` | Legacy provider CLI scripts with active security blockers. | `tests/ai/contracts/test_provider_bypass_guards.py:12,36,102` explicitly tests that these tools raise `PermissionError` on direct invocation. | `NOT SAFE TO DELETE YET` | **Negative Enforcement Test Requirement**: Deleting these files causes `test_provider_bypass_guards.py` to fail with `FileNotFoundError` or module import error. [`TEST_PROVEN`] |
| `.agents/plugins/super-video-maker-plugin/tools/agent_browser_recorder.py` | Browser-based UI recording tool. | Referenced by recipe `agent-browser-proof.json:4`. | `NOT SAFE TO DELETE YET` | Bound to active video recipe. [`CODE_PROVEN`] |
| `.agents/guardian/` | Agent boundary monitoring runtime. | Local development guardrail runtime. | `NOT SAFE TO DELETE YET` | Active development guardrail. [`CODE_PROVEN`] |

---

### 2.4 Audit of `references/ROUTER.md` & Historical References

The `references/` directory contains developer documentation and standard operating procedures (SOPs).

| Path | Purpose | Consumer Analysis | Classification | Deletion Safety Rationale |
|---|---|---|---|---|
| `references/ROUTER.md` | Decision matrix and tool selection guide. | Referenced in `.agents/AGENTS.md` and developer playbooks. Cites `ground-truth/MCP_INDEX.md` and `TOOLS_INDEX.md`. | `NOT SAFE TO DELETE YET` | Level 5 reference document. While out of sync with S28-M native capabilities, it provides essential context for agent prompt routing. Requires documentation update before retirement. [`DOCUMENTATION_ONLY`] |
| `references/1_playbooks/` (10 playbooks) | Video production playbooks (`living_canvas.md`, `tabletop_explainer.md`, etc.). | Cited by recipes in `recipes/*.json` and `ai/recipes/definitions.py`. | `NOT SAFE TO DELETE YET` | Domain reference files tied to production recipe definitions. [`CODE_PROVEN`] |
| `references/2_sops/` (7 SOPs) | Operational SOPs (`audio_qc.md`, `font_pairing.md`, `hyperrealistic_image.md`). | Cited by taste gate policies and narrative planning archetypes. | `NOT SAFE TO DELETE YET` | Active domain documentation. [`DOCUMENTATION_ONLY`] |
| `references/SFX_BINDING_MATRIX.md` | Matrix mapping video genres to sound effects. | Cited in `.agents/AGENTS.md:11` as mandatory reading before scene planning. | `NOT SAFE TO DELETE YET` | Referenced in agent directives. [`DOCUMENTATION_ONLY`] |

---

### 2.5 Audit of Deprecated API Endpoints & Adapters

| Endpoint | File & Lines | Implementation Nature | Consumers & Tests | Classification | Deletion Safety Rationale |
|---|---|---|---|---|---|
| `POST /render/{project_id}` | `api/routers/render.py:32-56` | Deprecated adapter delegating to `RunService.create_run()`. Returns header `Deprecation: @deprecated: Use POST /projects/{project_id}/runs`. | Tested in `tests/api/test_render.py:18,40`, `tests/remediation/reproductions/test_s21_remediation_proof.py:106`, `tests/security/test_s02_negative_enforcement.py:116`. | `NOT SAFE TO DELETE YET` | Active compatibility adapter with 3 dedicated test suites. Removing it requires formal API deprecation window and test suite updates. [`CODE_PROVEN`, `TEST_PROVEN`] |
| `GET /render/{project_id}/ws` | `api/routers/render.py:21-30` | WebSocket endpoint for render status. | Tested in `tests/api/test_render.py:23,45`. | `NOT SAFE TO DELETE YET` | Actively tested WebSocket endpoint. [`TEST_PROVEN`] |
| `GET /health` | `api/routers/health.py:46-63` | Legacy health adapter returning `{"status": "healthy", "version": ..., "live": True}`. | Backward compatibility for legacy load balancers. Tested in `tests/api/test_health.py`. | `NOT SAFE TO DELETE YET` | Standard backward-compatible probe. [`TEST_PROVEN`] |

---

### 2.6 Audit of `scratch/` and `التعلم/` (Educational & Experimental Directories)

| Path | Purpose | Consumer Analysis | Classification | Deletion Safety Rationale |
|---|---|---|---|---|
| `scratch/` | Ad-hoc experiments, temporary probe scripts, and scrap files. | Zero production, test, or CI dependencies. | **`DELETE_CANDIDATE`** (or gitignore) | Development scratch space. Contains no authoritative code or tests. [`CODE_PROVEN`] |
| `التعلم/` (`الاصلاح/`, `التقارير/`) | Arabic language learning notes, remediation summaries, and post-mortems. | Zero code, test, or CI dependencies. Purely historical documentation. | `NOT SAFE TO DELETE YET` (Historical Context) | Non-intrusive historical documentation. Deleting offers zero runtime or performance benefit while destroying remediation institutional knowledge. [`DOCUMENTATION_ONLY`] |

---

## 3. Comprehensive Summary: Deletion Candidates vs. Protected Artifacts

```
====================================================================================================
                        DELETION SAFETY MATRIX & SUMMARY
====================================================================================================

[ VERIFIED DELETE CANDIDATES — 0 CONSUMERS PROVEN ]
  1. scripts/archive/classify_templates.py
  2. scripts/archive/migrate_assets.py
  3. scripts/archive/smoke_crd019_templates.py
  4. scripts/archive/smoke_crd020_temporal.py
  5. scripts/archive/phase13/ (3 files: baseline.ts, coverage.ts, prioritize.ts)
  6. scripts/archive/phase14/ (4 files: baseline.ts, execution_bridge_audit.ts, patch_candidates.ts, prioritize.ts)
  7. scripts/archive/phase15/ (4 files: build_execution_cohorts.ts, generate_sample_batch.ts, validate_execution_contracts.ts, validate_verification_integrity.ts)
  8. scripts/archive/phase16/ (12 files: build_16_3_coverage_report.ts, mine_adapter_families.ts, validate_phase_16_3.ts, etc.)
  9. scratch/ (temporary developer scratch files)

Total Verified Delete Candidates: 28 files across 5 directories.

----------------------------------------------------------------------------------------------------

[ NOT SAFE TO DELETE YET — PROTECTED BY CI, TESTS, OR ADAPTERS ]
  1. ground-truth/* (All 13 files): Protected by CI job 'ground-truth' and check_ground_truth_sync.py.
  2. scripts/archive/migrate_legacy_projects.py: Protected by tests/archive/test_migrate_legacy.py.
  3. scripts/archive/migrate_state.py: Protected by tests/golden_scenarios/test_migration_from_legacy.py.
  4. scripts/archive/stitch_skill.py: Reads ground-truth/PLAYBOOKS_INDEX.md.
  5. .agents/docker/Dockerfile.remotion: Built in CI job 'docker-render'.
  6. .agents/.../tools/elevenlabs_voice.py: Verified by negative test test_provider_bypass_guards.py.
  7. .agents/.../tools/replicate_video.py: Verified by negative test test_provider_bypass_guards.py.
  8. .agents/.../mcp-servers/*: Protected by test_development_agent_preservation.py.
  9. api/routers/render.py (POST /render/{id}): Protected by test_render.py and remediation proof tests.
  10. api/routers/health.py (GET /health): Protected by test_health.py.
  11. references/ROUTER.md: Protected by agent rule references and SOP links.
====================================================================================================
```

---

## 4. Remediation Direction & Retirement Roadmap (DO NOT FIX YET)

To safely retire artifacts classified as `NOT SAFE TO DELETE YET` in a future refactoring cycle:

1. **Retiring Root `ground-truth/`**:
   - Update `scripts/validators/check_ground_truth_sync.py` and `.github/workflows/remediation-ci.yml:63-87` to remove the ground-truth diff gate.
   - Redirect any documentation links to `registry/template-registry-data.json`.
   - Then, and only then, delete `ground-truth/`.
2. **Retiring Blocked Legacy Tools (`elevenlabs_voice.py`, `replicate_video.py`)**:
   - Update `tests/ai/contracts/test_provider_bypass_guards.py` to remove module import assertions for these files.
   - Verify that no remaining agent instructions cite them.
   - Delete the files.
3. **Retiring Deprecated API Route (`POST /render/{project_id}`)**:
   - Issue deprecation notice to API clients.
   - Remove or migrate `tests/api/test_render.py` to test `POST /projects/{project_id}/runs`.
   - Remove route mount from `api/main.py` and delete `api/routers/render.py`.


---


<a name='part-2-cross-generation-architecture-drift-analysis'></a>

## Part 2: Cross-Generation Architecture Drift Analysis


> *Original Source: `documentation/reality_context_pack/15_CROSS_GENERATION_ARCHITECTURE_DRIFT.md`*


### Sub-Report Title: Cross-Generation Architecture Drift Reality Report


- **Baseline Git SHA**: `90ec3de8d47494d5940d5cd1f9ed9a8e274ef6e1`
- **Branch**: `main`
- **Report Version**: 1.0.0
- **Last Updated**: 2026-10-07
- **Scope**: Historical breakdown of the six distinct architectural generations present in the repository, evolutionary timeline, layer responsibilities, cross-generational dependency matrix, and architectural gap analysis.
- **Evidence Standard**: `CODE_PROVEN`, `TEST_PROVEN`, `CI_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`, `DOCUMENTATION_ONLY`, `INFERRED`, `UNKNOWN`

---

## 1. Architectural Generations Taxonomy

The codebase contains artifacts, patterns, and conventions from six distinct architectural generations. Each generation was designed to solve specific operational challenges, resulting in overlapping layers of authority, duplicate abstractions, and isolated subsystems.

```
========================================================================================================
                               EVOLUTIONARY TIMELINE & GENERATIONS
========================================================================================================

  Gen 1: Pre-S25          Gen 2: S25/S26 Core       Gen 3: S27 AI Infra       Gen 4: S28 Creative
  [Ad-hoc / Remotion]  -> [SaaS / Deterministic] -> [Context / Routing]   ->  [Planning / Taste]
  • Raw CLI scripts       • FastAPI & Workers       • ContextBuilder          • CreativePlanner
  • Direct Remotion       • CAS StateStore          • ModelRouter             • NarrativePlanner
  • Plugin MCPs           • 10 Pipeline Gates       • ProviderRegistry        • RecipeRegistry
                          • StorageService          • MemoryService           • SkillRegistry
                                 |                         |                         |
                                 +-------------------------+-------------------------+
                                                           |
                                                           v
                              Gen 5: S28-M Capability        Gen 6: S28-R Live Authoring
                              [Capability / FastMCP]     ->  [Renderer-Neutral / Editor]
                              • CapabilityRouter             • BlueprintV2 / VideoDocument
                              • ToolGateway (15 stages)      • UnifiedAuthoringSession
                              • 32 Native Capabilities       • RenderPlanner & Graph
                              • AST Provider Blockers        • Remotion & Canvas Adapters
========================================================================================================
```

---

## 2. Detailed Generation Profiles

### 2.1 Generation 1: Pre-S25 (Ad-Hoc Video Engine & Direct Remotion)
- **Primary Focus**: Prototype video generation, raw shell invocations, and agent-driven direct file editing.
- **Key Artifacts & Patterns**:
  - `scripts/deliver_project.py`, `scripts/open_studio.py`
  - `.agents/plugins/super-video-maker-plugin/tools/` (`heygen_client.py`, `elevenlabs_voice.py`, `replicate_video.py`)
  - Direct execution of `npx remotion render src/index.ts`
  - Hardcoded local paths and Windows paths (`C:/video/...` in `mcp_config.json`)
  - External MCP servers (`audio-tools-mcp`, `media-sources-mcp`, `ffmpeg-mcp-server`)
- **Current Status**: **QUARANTINED / PARTIALLY CONFINED** [`CODE_PROVEN`].
  - Direct provider scripts were actively blocked with hard exceptions (`PermissionError("DIRECT SECRET ACCESS BLOCKED...")`).
  - Direct rendering via `npm run render` in `remotion-app` exits with a hard stop (`remotion-app/package.json:9`).
  - Residual CLI fallbacks remain in `scripts/render_project.py:177`.

### 2.2 Generation 2: S25 / S26 Core (Deterministic SaaS Backend & Gate Pipeline)
- **Primary Focus**: SaaS reliability, deterministic stage gating, atomic state transitions, concurrency safety, and worker-based asynchronous execution.
- **Key Artifacts & Patterns**:
  - FastAPI application: `api/main.py`, `api/routers/projects.py`, `api/routers/runs.py`, `api/routers/assets.py`
  - State management: `scripts/core/state_store.py` (atomic CAS on `.pipeline_state.json`), `scripts/core/lifecycle_service.py`
  - Queue & persistence: `scripts/core/run_repository.py` (SQLite/PostgreSQL `runs` table), `scripts/core/worker.py` (`PipelineWorker` daemon)
  - Deterministic pipeline orchestrator: `scripts/pipeline.py` enforcing sequential gate stages (`asset_gate.py`, `plan_gate.py`, `taste_gate.py`, `validate_blueprint.py`, `probe_qc.py`, `final_qc.py`)
  - Storage abstraction: `scripts/core/storage/storage_service.py` (`LocalStorageBackend`, `S3CompatibleStorageBackend`)
  - Confinement policies: `scripts/core/security/path_policy.py`, `command_policy.py`
- **Current Status**: **ACTIVE PRODUCTION RUNTIME** [`RUNTIME_REACHABILITY_PROVEN`].
  - Powers all active HTTP requests and asynchronous render jobs.

### 2.3 Generation 3: S27 AI Platform Infrastructure
- **Primary Focus**: Structured AI context assembly, token budgeting, multi-provider model routing, and persistent semantic memory.
- **Key Artifacts & Patterns**:
  - Context engine: `ai/context/builder.py` (`ContextBuilder`), token estimation (`DeterministicTokenEstimator`), compression, ranking
  - Model routing: `ai/routing/router.py` (`ModelRouter`), ranking models by latency, cost, and quality
  - Provider management: `ai/providers/registry.py` (`ProviderRegistry`), `ai/providers/definitions.py` (`CANONICAL_PROVIDERS`)
  - Memory service: `ai/memory/service.py` (`MemoryService`), vector embeddings, temporal decay
  - Knowledge platform: `ai/knowledge/router.py` (`KnowledgeRouter`), `ai/knowledge/registry.py`
- **Current Status**: **ACTIVE DEVELOPMENT / ISOLATED SUBSYSTEM** [`CODE_PROVEN`].
  - Completely decoupled from `api/` and `scripts/pipeline.py`. Has 0 production callers.

### 2.4 Generation 4: S28 Creative Intelligence
- **Primary Focus**: High-level creative direction, narrative structuring, taste evaluation, declarative recipes, and agent skills.
- **Key Artifacts & Patterns**:
  - Creative planning: `ai/planning/creative_planner.py` (`CreativePlanner`), `CreativeBrief`, `CreativePlan`
  - Narrative planning: `ai/narrative/planner.py` (`NarrativePlanner`), archetype beat sequencing
  - AI Taste engine: `ai/taste/engine.py` (`TasteEngine`), evaluating `CANONICAL_TASTE_RULES`
  - Recipe platform: `ai/recipes/registry.py` (`RecipeRegistry`), globbing and migrating `recipes/*.json`
  - Skill platform: `ai/skills/registry.py` (`SkillRegistry`), `ai/skills/loader.py` (loading `.agents/skills/*/SKILL.md`)
  - Reuse & composition: `ai/planning/reuse_engine.py`, `ai/planning/compose_engine.py`, `ai/planning/creative_tier_policy.py`
- **Current Status**: **ACTIVE DEVELOPMENT / EVALUATION HARNESS** [`CODE_PROVEN`, `TEST_PROVEN`].
  - Extensively tested in offline benchmarks (`scripts/run_creative_e2e.py`, `scripts/run_creative_regression.py`), but completely uncalled on the production HTTP run path.

### 2.5 Generation 5: S28-M Capability & MCP Modernization
- **Primary Focus**: Eliminating raw JSON-RPC MCP calls in favor of strongly typed Python capability routing, strict AST guards, and FastMCP compatibility.
- **Key Artifacts & Patterns**:
  - Capability catalog: `ai/capabilities/catalog.py` (32 capabilities spanning Audio, Image, Video, Speech, Vision, Ingestion, System)
  - Capability router: `ai/routing/capability_router.py` (`CapabilityRouter`)
  - Tool execution gateway: `ai/tools/gateway.py` (`ToolGateway` enforcing a 15-stage pipeline: lookup, lease, auth, idempotency, execution, validation)
  - Native adapters: `NativeToolAdapter`, `DomainServiceAdapter` (`ai/tools/adapters/`)
  - MCP compatibility server: `ai/mcp/compatibility/server.py` (`CompatibilityMCPServer`) wrapping FastMCP for external clients
  - AST architecture guards: `tests/ai/audit/test_s28_m11_final_architecture_audit.py` (forbidding raw MCP and enforcing capability boundaries)
- **Current Status**: **ACTIVE TESTED SUBSYSTEM / COMPATIBILITY BOUNDARY** [`TEST_PROVEN`, `CODE_PROVEN`].
  - Successfully modernized tool interfaces for AI agents, but neither `api/main.py` nor `scripts/pipeline.py` dispatches through `CapabilityRouter`.

### 2.6 Generation 6: S28-R Renderer Independence & Live Authoring
- **Primary Focus**: Engine-neutral video document representation, interactive AST mutations, multi-engine render planning, and Remotion decoupling.
- **Key Artifacts & Patterns**:
  - Authoritative document schema: `contracts/blueprint.ts` (`BlueprintV2` / `VideoDocument`)
  - Authoring contracts: `contracts/authoring.ts` (`AuthoringIntentSchema`, `CanonicalMutationSchema`)
  - Authoring engine: `authoring/unified-authoring-session.ts`, `authoring/intent-planner.ts`
  - Live authoring API: `api/routers/authoring.py` (`/projects/{id}/document`, `/mutate`, `/batch`, `/intent`, `/template`, `/undo`, `/redo`)
  - Concurrency & persistence: `scripts/core/canonical_document_repository.py` (ETag & CAS versioning)
  - Multi-engine render planner: `planner/render-planner.ts` (`RenderPlanner`), DAG executor (`planner/production-render-graph-executor.ts`)
  - Renderer adapters: `remotion/remotion-renderer-adapter.ts`, `canvas/canvas-renderer-adapter.ts`
  - Master compositor: `compositor/master-compositor.ts` (timeline assembly, audio mixing, FFmpeg multiplexing)
- **Current Status**: **ACTIVE PRODUCT RUNTIME** [`RUNTIME_REACHABILITY_PROVEN`].
  - S28-R successfully integrated into both the HTTP authoring API and the render pipeline (`scripts/render_project.py` Priority 1).

---

## 3. Cross-Generational Dependency & Interop Matrix

The following matrix documents which generation directly calls or consumes artifacts from other generations:

| Caller Generation \ Callee Generation | Pre-S25 (Gen 1) | S25/S26 Core (Gen 2) | S27 AI Infra (Gen 3) | S28 Creative (Gen 4) | S28-M Capability (Gen 5) | S28-R Live Authoring (Gen 6) |
|---|---|---|---|---|---|---|
| **Pre-S25 (Gen 1)** | Direct scripts | **NO** | **NO** | **NO** | **NO** | **NO** |
| **S25/S26 Core (Gen 2)** | Subprocess CLI fallback (`scripts/render_project.py:177`) | Core runtime (`api/`, `worker.py`, `pipeline.py`) | **NO (0 imports)** | **NO (0 imports)** | **NO (0 imports)** | Calls S28-R RenderPlanner (`render_via_planner.ts`) |
| **S27 AI Infra (Gen 3)** | **NO** | Reads `DatabaseEngine` in tests | Self-contained (`ContextBuilder`, `ModelRouter`) | **NO** | Injected into CapabilityRouter | **NO** |
| **S28 Creative (Gen 4)** | **NO** | **NO** | Calls `KnowledgeRouter`, `ModelRouter` | Self-contained (`CreativePlanner`, `NarrativePlanner`) | Calls `CapabilityRouter` | Compiles to `BlueprintV2` schema via `compiler.py` (test only) |
| **S28-M Capability (Gen 5)** | Wraps legacy MCPs via FastMCP server | Delegates to `DomainServiceAdapter` | Calls `ModelRouter` via `ModelRouterSeam` | **NO** | Self-contained (`CapabilityRouter`, `ToolGateway`) | **NO** |
| **S28-R Live Authoring (Gen 6)**| Fallback to Remotion CLI | Uses `CanonicalDocumentRepository`, `StorageService`, CAS | **NO** | **NO** | **NO** | Self-contained (`UnifiedAuthoringSession`, `RenderPlanner`) |

---

## 4. Architectural Drift & Gap Analysis

### 4.1 The AI-to-Production Chasm (Gen 3/4/5 Disconnection)
- **The Intended Design**:
  A user submits a creative brief via API $\to$ `ContextBuilder` aggregates memory and knowledge $\to$ `NarrativePlanner` structures story beats $\to$ `CreativePlanner` resolves templates/recipes $\to$ `CapabilityRouter` acquires voiceover and imagery $\to$ `BlueprintCompiler` outputs a canonical `VideoDocument` $\to$ S28-R Live Authoring modifies the AST $\to$ S28-R RenderPlanner renders the final MP4.
- **The Actual Reality**:
  - The production pipeline (`api/` $\to$ `worker.py` $\to$ `pipeline.py`) is **100% deterministic** and requires pre-existing `master_plan.md` and `05_blueprint.json` files on disk.
  - Gen 3 (`ai/context/`, `ai/routing/`), Gen 4 (`ai/planning/`, `ai/taste/`), and Gen 5 (`ai/capabilities/`, `ai/tools/`) operate strictly as an offline library or evaluation harness.
  - There is zero HTTP or daemon wiring connecting the AI platform to the production run queue.

### 4.2 The S28-R Remotion Dual Authority Drift
- **The Intended Design**:
  Remotion is strictly an engine-neutral renderer adapter (`RemotionRendererAdapter`), equal to `CanvasRendererAdapter`. Canonical video truth resides exclusively in `BlueprintV2`.
- **The Actual Reality**:
  - All 105 production templates are implemented as React TSX components importing Remotion hooks (`useCurrentFrame`, `useVideoConfig`, `AbsoluteFill`).
  - `scripts/render_project.py` retains a hard fallback to raw `npx remotion render`.
  - `scripts/gates/probe_qc.py` invokes `npx remotion still` directly.
  - While S28-R decoupled the document format, the template asset library remains deeply bound to the Remotion React runtime.

### 4.3 The State Authority Drift (Disk `.pipeline_state.json` vs SQL `project_states`)
- **The Intended Design**:
  In S25 single-node mode, `.pipeline_state.json` was the sole authority.
  In S26 multi-tenant mode, `project_states` in SQLite/PostgreSQL became the transactional CAS store.
- **The Actual Reality**:
  - `scripts/pipeline.py` still reads and writes `.pipeline_state.json` directly on disk (`StateStore.load()`).
  - `AuthoringService` writes to `CanonicalDocumentRepository` and updates `project_states` in SQL.
  - A dual-state reality exists where disk state and SQL state must be manually synchronized.


---


<a name='part-3-documentation--agent-directive-instruction-drift'></a>

## Part 3: Documentation & Agent Directive Instruction Drift


> *Original Source: `documentation/reality_context_pack/16_DOCUMENTATION_AND_AGENT_INSTRUCTION_DRIFT.md`*


### Sub-Report Title: Documentation & Agent Instruction Drift Reality Report


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


---


<a name='part-4-true-product-journey-edge-by-edge-gap-analysis'></a>

## Part 4: True Product Journey Edge-by-Edge Gap Analysis


> *Original Source: `documentation/reality_context_pack/18_TRUE_PRODUCT_JOURNEY_GAP_ANALYSIS.md`*


### Sub-Report Title: True Product Journey Gap Analysis Reality Report


- **Baseline Git SHA**: `90ec3de8d47494d5940d5cd1f9ed9a8e274ef6e1`
- **Branch**: `main`
- **Report Version**: 1.0.0
- **Last Updated**: 2026-10-07
- **Scope**: Rigorous edge-by-edge architectural breakdown of the ideal end-to-end product journey (from user prompt to final video streaming), classifying each transition, proving reachability or isolating breakage points, without performing code repairs.
- **Evidence Standard**: `CODE_PROVEN`, `TEST_PROVEN`, `CI_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`, `DOCUMENTATION_ONLY`, `INFERRED`, `UNKNOWN`

---

## 1. The Ideal Product Journey vs. Real System Topology

The intended product vision promises a seamless autonomous-to-interactive video creation pipeline:
`Prompt / Brief` $\to$ `AI Creative Planning` $\to$ `Autonomous Asset Acquisition` $\to$ `Canonical BlueprintV2 Compilation` $\to$ `Live Interactive Authoring` $\to$ `Deterministic Quality Gates` $\to$ `Human Approval` $\to$ `Multi-Engine Rendering` $\to$ `Final QC & Video Delivery`.

Forensic investigation reveals that this ideal journey is severed into two disconnected architectural hemispheres:
1. **The Disconnected AI Hemisphere** (Edges 1 through 6): Implemented in `ai/` and heavily verified in unit/eval test suites, but completely disconnected from the production HTTP API and background worker daemons.
2. **The Active Deterministic Engine Hemisphere** (Edges 7 through 12): Fully wired and proven in production, but starting exclusively from pre-existing disk files or manual structured API mutations.

---

## 2. Edge-by-Edge Journey Classification & Trace

```
========================================================================================================
                               EDGE-BY-EDGE PRODUCT JOURNEY MAP
========================================================================================================

  [1. User Prompt / Brief]
           |
           | Edge 1: Prompt -> Brief (MISSING ON API)
           v
  [2. CreativeBrief]
           |
           | Edge 2: Brief -> NarrativePlan (TEST_PROVEN_ONLY)
           v
  [3. NarrativePlan]
           |
           | Edge 3: NarrativePlan -> CreativePlan (TEST_PROVEN_ONLY)
           v
  [4. CreativePlan]
           |
           | Edge 4: Plan -> Recipe & Template Resolution (TEST_PROVEN_ONLY)
           | Edge 5: Autonomous Asset Acquisition (TEST_PROVEN_ONLY)
           v
  [5. Resolved Creative Elements]
           |
           | Edge 6: CreativePlan -> BlueprintV2 Compilation (BROKEN / UNWIRED TO PROD)
           v
======================= THE ARCHITECTURAL CHASM ========================================================
           v
  [6. Canonical VideoDocument (BlueprintV2)]
           |
           | Edge 7: Interactive Live Authoring & AST Mutation (PRODUCTION_PROVEN)
           v
  [7. Mutated Document on Disk / Storage]
           |
           | Edge 8: POST /projects/{id}/runs & Stage Gating (PRODUCTION_PROVEN)
           v
  [8. Probe QC Verification & Unlocked Studio]
           |
           | Edge 9: Human Review & Decision Bundle (PRODUCTION_PROVEN)
           v
  [9. Review Approved Authorization]
           |
           | Edge 10: Multi-Engine RenderGraph Execution (PRODUCTION_PROVEN)
           | Edge 11: Renderer Adapter (Remotion / Canvas) (PRODUCTION_PROVEN)
           v
  [10. Rendered MP4 & Final QC]
           |
           | Edge 12: Final QC & HTTP 206 Streaming Delivery (PRODUCTION_PROVEN)
           v
  [11. Client Video Playback]
========================================================================================================
```

---

### Edge 1: User Natural-Language Prompt $\to$ `CreativeBrief`
- **Intended Behavior**: A user sends a prompt (e.g., "Create a 30s SaaS product explainer for Acme") via HTTP API, creating a structured `CreativeBrief`.
- **Observed Behavior**: All 13 routers mounted in `api/main.py:57-70` operate strictly on structured DTOs (`ProjectCreateRequest`, `RunCreateRequest`, `AuthoringRequest`). No HTTP endpoint accepts a prompt or brief.
- **Classification**: **`MISSING`** on Production Runtime [`CODE_PROVEN`].
- **Production Caller**: `NONE` / `UNKNOWN`.
- **Test Reality**: Tested in `tests/ai/planning/test_creative_planner.py` where `CreativeBrief` is instantiated manually in Python memory.
- **Breakage Analysis**: Complete absence of prompt ingestion router.

---

### Edge 2: `CreativeBrief` $\to$ `NarrativePlan`
- **Intended Behavior**: `NarrativePlanner` ingests `CreativeBrief` and synthesizes archetype beats and audio modes.
- **Observed Behavior**: `ai/narrative/planner.py:35-80` implements `NarrativePlanner.plan()`. It has zero callers in `api/` or `scripts/pipeline.py`.
- **Classification**: **`TEST_PROVEN_ONLY`** [`CODE_PROVEN`, `TEST_PROVEN`].
- **Production Caller**: `NONE`.
- **Test Reality**: Executed in `tests/ai/narrative/test_narrative_planner.py` and regression runner `ai/regression/runner.py:171`.

---

### Edge 3: `NarrativePlan` $\to$ `CreativePlan`
- **Intended Behavior**: `CreativePlanner` combines `CreativeBrief` and `NarrativePlan` to produce a proposed `CreativePlan`.
- **Observed Behavior**: `ai/planning/creative_planner.py:58-115` implements `CreativePlanner.plan()`. Zero callers in production code.
- **Classification**: **`TEST_PROVEN_ONLY`** [`CODE_PROVEN`, `TEST_PROVEN`].
- **Production Caller**: `NONE`.
- **Test Reality**: Tested in `tests/ai/planning/test_creative_planner.py` and `scripts/run_creative_e2e.py:70`.

---

### Edge 4: `CreativePlan` $\to$ Recipe & Template Resolution
- **Intended Behavior**: `CreativeTierPolicy`, `ReuseEngine`, and `RecipeSelector` match beats against registered templates and recipes.
- **Observed Behavior**: Implemented in `ai/planning/recipe_selector.py` and `reuse_engine.py`. Reads `recipes/*.json` and `registry/template-registry-data.json`. Zero production callers.
- **Classification**: **`TEST_PROVEN_ONLY`** [`CODE_PROVEN`, `TEST_PROVEN`].
- **Production Caller**: `NONE`.
- **Test Reality**: Tested in `tests/ai/recipes/test_recipe_platform.py` and `tests/ai/planning/test_recipe_selector.py`.

---

### Edge 5: Autonomous Asset Acquisition & Processing
- **Intended Behavior**: AI autonomously acquires voiceover, images, and SFX via `CapabilityRouter` $\to$ `ToolGateway` $\to$ `AssetService`.
- **Observed Behavior**:
  - **Manual Path**: Fully proven. `POST /projects/{id}/assets` $\to$ `AssetService.upload_asset()` $\to$ `StorageService` $\to$ `02_asset_manifest.json` (`PRODUCTION_PROVEN`).
  - **AI Autonomous Path**: Implemented in `ai/capabilities/` and `ai/tools/gateway.py`, but has zero callers in production API.
- **Classification**: **`TEST_PROVEN_ONLY`** for AI Autonomous Path [`CODE_PROVEN`, `TEST_PROVEN`].

---

### Edge 6: `CreativePlan` $\to$ Canonical `VideoDocument` (`BlueprintV2`) Compilation
- **Intended Behavior**: `BlueprintCompiler` transforms advisory `CreativePlan` into authoritative `contracts/blueprint.ts:BlueprintV2`.
- **Observed Behavior**:
  - `BlueprintCompiler` is defined in `ai/planning/compiler.py:62-443`.
  - It is **never called** by `AuthoringService` or the production pipeline.
  - Production authoring creates documents strictly from scratch or via template instantiation (`instantiateTemplateToCanonicalDocument`).
- **Classification**: **`BROKEN / UNWIRED TO PRODUCTION`** [`CODE_PROVEN`].
- **Production Caller**: `NONE` (Callers strictly in test runners: `scripts/run_creative_e2e.py:75`).
- **Breakage Analysis**: This is the primary chasm disconnecting the AI planning stack from the authoring and rendering engine.

---

### Edge 7: Interactive Live Authoring & AST Mutation
- **Intended Behavior**: Clients view and edit canonical `VideoDocument` via atomic AST mutations.
- **Observed Behavior**:
  - `GET /projects/{id}/document` $\to$ loads `BlueprintV2`.
  - `POST /projects/{id}/mutate` or `/batch` or `/intent` $\to$ `AuthoringService.execute_authoring()`.
  - Concurrency verified with ETag / CAS.
  - Dispatched via subprocess to `scripts/execute_authoring_mutation.ts` $\to$ `UnifiedAuthoringSession`.
  - Result persisted transactionally to SQL and `StorageService`.
- **Classification**: **`PRODUCTION_PROVEN`** [`CODE_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`].
- **Test Suite**: `tests/api/test_authoring_router.py`, `tests/contracts/test_authoring_contracts.ts`.

---

### Edge 8: Pipeline Run Enqueue & Deterministic Stage Gating
- **Intended Behavior**: A run is enqueued and executed through the 10 sequential quality gates.
- **Observed Behavior**:
  - `POST /projects/{id}/runs` $\to$ `RunService.create_run()` $\to$ inserts `RunRecord(status=QUEUED)` in SQLite/PostgreSQL `runs` table (HTTP 202).
  - Background daemon `scripts/core/worker.py` claims run with lease and executes `python scripts/pipeline.py <project_id>`.
  - `scripts/pipeline.py` advances states: `DRAFT` $\to$ `ASSETS_READY` (`asset_gate.py`) $\to$ `PLAN_READY` (`plan_gate.py`, `taste_gate.py`) $\to$ `BLUEPRINT_READY` (`validate_blueprint.py`, `motion_validator.py`, `code_template_gate.py`) $\to$ `MATERIALIZED` (`materialize_project.py`) $\to$ `PROBE_PASSED` (`probe_qc.py`).
- **Classification**: **`PRODUCTION_PROVEN`** [`CODE_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`].
- **Test Suite**: `tests/e2e/true_e2e_suite.py`, `tests/gates/*`, `tests/core/*`.

---

### Edge 9: Human Review & Approval Gate
- **Intended Behavior**: Pipeline halts after Probe QC awaiting human review; client approves or rejects.
- **Observed Behavior**:
  - `probe_qc.py` unlocks `.studio_unlocked` and creates `ReviewBundle`.
  - `GET /projects/{id}/review` returns preview bundle.
  - `POST /projects/{id}/review/approve` calls `ReviewService.approve()`, setting state to `REVIEW_APPROVED` and authorizing render.
- **Classification**: **`PRODUCTION_PROVEN`** [`CODE_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`].
- **Test Suite**: `tests/core/test_review_service.py`, `tests/api/test_artifacts.py`.

---

### Edge 10: Multi-Engine Render Planning & Graph Execution
- **Intended Behavior**: `scripts/render_project.py` builds render inputs and invokes `RenderPlanner`.
- **Observed Behavior**:
  - `scripts/render_project.py:130` validates authorization via `assert_render_authorized()`.
  - Invokes Priority 1: `npx tsx scripts/render_via_planner.ts <project_id>`.
  - `planner/render-planner.ts` compiles `BlueprintV2` into a Directed Acyclic Graph (DAG) executed by `ProductionRenderGraphExecutor`.
- **Classification**: **`PRODUCTION_PROVEN`** [`CODE_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`].
- **Test Suite**: `tests/planner/*`, `tests/e2e/test_pipeline_integration.py`.

---

### Edge 11: Renderer Adapter Execution (Remotion / Canvas)
- **Intended Behavior**: Independent renderer adapters render visual composition frames.
- **Observed Behavior**:
  - `RemotionRendererAdapter` (`remotion/remotion-renderer-adapter.ts`) mounts Remotion composition.
  - Fallback to Remotion CLI (`scripts/render_project.py:177`) if planner encounters node failures.
  - Audio and video multiplexed via `MasterCompositor` (`compositor/master-compositor.ts`).
- **Classification**: **`PRODUCTION_PROVEN`** [`CODE_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`].
- **Test Suite**: `tests/remotion/*`, `tests/compositor/*`.

---

### Edge 12: Final QC & Video Delivery
- **Intended Behavior**: Final quality control checks video specs, uploads MP4 to storage, and streams to client.
- **Observed Behavior**:
  - `scripts/gates/final_qc.py` verifies duration, loudness, resolution, and encoding specs, producing `09_final_qc_report.json`.
  - Pipeline worker uploads `out.mp4` to `StorageService` and marks run `SUCCEEDED`.
  - Client retrieves video via `GET /projects/{id}/outputs/{output_id}`, which supports HTTP 206 Partial Content Range streaming.
- **Classification**: **`PRODUCTION_PROVEN`** [`CODE_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`].
- **Test Suite**: `tests/api/test_outputs.py`, `tests/gates/test_final_qc.py`.

---

## 3. Journey Summary Table

| Edge # | Journey Transition | Source Component | Target Component | Reality Classification | Primary Obstacle / Breakage Point |
|---|---|---|---|---|---|
| **1** | Prompt $\to$ Brief | Client User | `CreativeBrief` | **`MISSING`** | Zero prompt intake endpoints in `api/`. |
| **2** | Brief $\to$ Narrative | `CreativeBrief` | `NarrativePlan` | **`TEST_PROVEN_ONLY`** | Unimported in production API/pipeline. |
| **3** | Narrative $\to$ Plan | `NarrativePlan` | `CreativePlan` | **`TEST_PROVEN_ONLY`** | Unimported in production API/pipeline. |
| **4** | Plan $\to$ Template/Recipe | `CreativePlan` | `RecipeRegistry` / Templates | **`TEST_PROVEN_ONLY`** | Unwired to production runs. |
| **5** | Asset Acquisition | AI Agent | `StorageService` / Manifest | **`TEST_PROVEN_ONLY`** (AI) / **`PROVEN`** (Manual) | AI capability router not triggered by API. |
| **6** | Plan $\to$ Document | `CreativePlan` | `BlueprintV2` | **`BROKEN`** | `BlueprintCompiler` has 0 production callers. |
| **7** | Live Authoring | HTTP Client | `UnifiedAuthoringSession` | **`PRODUCTION_PROVEN`** | Fully functional via `/mutate`, `/intent`. |
| **8** | Pipeline Gating | `POST .../runs` | `scripts/pipeline.py` | **`PRODUCTION_PROVEN`** | Fully functional via worker daemon. |
| **9** | Human Review | `ReviewService` | `StateStore` | **`PRODUCTION_PROVEN`** | Fully functional via `/review/approve`. |
| **10** | Render Planning | `render_project.py` | `RenderPlanner` | **`PRODUCTION_PROVEN`** | Priority 1 planner execution functional. |
| **11** | Render Adapters | `RenderGraph` | `RemotionRendererAdapter` | **`PRODUCTION_PROVEN`** | Adapters render Remotion compositions. |
| **12** | QC & Delivery | `final_qc.py` | `GET .../outputs` | **`PRODUCTION_PROVEN`** | Final QC and HTTP 206 streaming proven. |


---


<a name='part-5-unified-findings-ledger-reality-001-through-reality-024+'></a>

## Part 5: Unified Findings Ledger (REALITY-001 through REALITY-024+)


> *Original Source: `documentation/reality_context_pack/19_FINDINGS_LEDGER.md`*


### Sub-Report Title: Unified Findings Ledger & Mandatory Checks Reality Report


- **Baseline Git SHA**: `90ec3de8d47494d5940d5cd1f9ed9a8e274ef6e1`
- **Branch**: `main`
- **Report Version**: 1.0.0
- **Last Updated**: 2026-10-07
- **Scope**: Comprehensive unified ledger of all discovered architectural reality findings (`REALITY-001` through `REALITY-024`), exhaustive code and test evidence citations, production impacts, and complete answers to the 20 Special Mandatory Checks (A through T).
- **Evidence Standard**: `CODE_PROVEN`, `TEST_PROVEN`, `CI_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`, `DOCUMENTATION_ONLY`, `INFERRED`, `UNKNOWN`

---

## 1. Executive Summary: Answers to the 20 Mandatory Checks (A through T)

| Check | Focus Question | Verified Reality Answer | Evidence Standard | Key Citations |
| :---: | :--- | :--- | :--- | :--- |
| **A** | Does required GitHub CI run `tests/ai` in its entirety? | **NO**. `.github/workflows/remediation-ci.yml:125-126` completely excludes `tests/ai`. Zero of the 270 AI test files run in required CI. | `CI_PROVEN`, `CODE_PROVEN` | `.github/workflows/remediation-ci.yml:125-126` |
| **B** | Does local `run_required_checks.sh` match actual GitHub required checks? | **NO**. Local runner executes `tests/ai` while omitting `tests/fault_injection`, Ruff linting, Trivy scanning, and Docker acceptance tests. | `CI_PROVEN`, `CODE_PROVEN` | `scripts/ci/run_required_checks.sh:49-51` vs `.github/workflows/remediation-ci.yml:125-126` |
| **C** | What is the exact runtime path for `POST /projects/{id}/runs`? | HTTP `create_run` $\to$ `RunService.create_run()` $\to$ `RunRepository` (SQLite `QUEUED`) $\to$ Worker `scripts/core/worker.py` $\to$ Subprocess `scripts/pipeline.py` $\to$ sequential gates $\to$ `render_project.py` $\to$ `final_qc.py` $\to$ `RunRepository` (`SUCCEEDED`). | `CODE_PROVEN`, `RUNTIME_REACHABILITY_PROVEN` | `api/routers/runs.py:23-56`, `api/services/run_service.py:34-114`, `scripts/core/worker.py:180-360`, `scripts/pipeline.py:221-520` |
| **D** | Does `POST /projects/{id}/runs` reach Creative Intelligence? | **NO**. Zero imports or calls to `ai/`, `CreativePlanner`, or LLM providers exist along the entire execution path. Pre-authored disk files are required. | `CODE_PROVEN` | `scripts/pipeline.py:371,381`, `scripts/core/worker.py:289` |
| **E** | Does Production API have a natural-language AI generation entrypoint? | **NO**. All 34 API endpoints in `api/main.py` operate on structured DTOs (`ProjectCreateRequest`, `RunCreateRequest`, `AuthoringRequest`). Zero prompt intake routes exist. | `CODE_PROVEN` | `api/main.py:57-70`, `api/routers/*` |
| **F** | Does `/intent` accept natural language or only pre-structured typed intents? | **ONLY pre-structured typed intents**. Dispatches to `UnifiedAuthoringSession` via Zod `AuthoringRequestSchema` / `AuthoringIntentSchema`. Natural language fails schema validation. | `CODE_PROVEN` | `api/routers/authoring.py:104-131`, `contracts/authoring.ts:273-304`, `authoring/intent-planner.ts:5-14` |
| **G** | Who instantiates `ContextBuilder` in Production? | **NO ONE** (`Production caller: NONE`). Instantiated strictly within unit and integration tests under `tests/ai/context/`. | `CODE_PROVEN` | `ai/context/builder.py:47`, `tests/ai/context/test_builder.py:64,141` |
| **H** | Who injects `KnowledgeRouter` into `ContextBuilder`? | **NO ONE**. `ContextBuilder` accepts `knowledge_retriever` protocol, defaulting to `DeterministicKnowledgeRetriever()`. `KnowledgeRouter` is never injected. | `CODE_PROVEN` | `ai/context/builder.py:59-77`, `ai/knowledge/router.py:34-56` |
| **I** | Does `initialize_canonical_catalog()` execute in Production? | **NO**. It is invoked strictly in evaluation runners and unit tests (`ai/regression/runner.py:162`, `tests/ai/knowledge/test_knowledge_platform.py:69`). | `CODE_PROVEN` | `ai/knowledge/router.py:58-68`, `api/main.py:28-40` |
| **J** | What is the exact function of root `/ground-truth/`? | Auto-generated derivative documentation, indexing, and metadata cache generated by `scripts/generators/build_ground_truth.py` and gated by CI drift checks. Not an ML dataset or runtime authority. | `CODE_PROVEN`, `CI_PROVEN` | `scripts/generators/build_ground_truth.py:1-4`, `scripts/validators/check_ground_truth_sync.py:1-55` |
| **K** | Which files in `/ground-truth/` have active Production consumers? | **ZERO**. Neither `api/` nor `scripts/pipeline.py` imports or reads files from `ground-truth/`. Only test runners and legacy plugin tools reference them. | `CODE_PROVEN` | Grep across `api/` and `scripts/pipeline.py` yields 0 matches |
| **L** | Is `template_catalog.json` an authority or metadata input? | **Metadata input / compatibility derivative**. `registry/template-registry-data.json` is the canonical machine-readable authority; `registry/template-registry.tsx` is the component binding authority. | `CODE_PROVEN` | `scripts/core/template_registry_publisher.py:6-11` |
| **M** | Does `RecipeRegistry` consume `recipes/*.json` in practice? | **YES**. `RecipeRegistry.__init__` with default `auto_load=True` globs `recipes/*.json`, migrating 18 legacy JSON files into typed `RecipeDefinition` objects in memory. | `CODE_PROVEN`, `TEST_PROVEN` | `ai/recipes/registry.py:105-125` |
| **N** | Does Skills runtime load from typed definitions, markdown, or both? | **BOTH**. `SkillLoader` loads from markdown (`SKILL.md` with YAML frontmatter) via `load_from_markdown()` and loads typed Python definitions via `get_canonical_skills()`. | `CODE_PROVEN` | `ai/skills/loader.py:62-112, 114-302` |
| **O** | Is raw MCP required for Internal Product AI? | **NO**. Internal Product AI routes 100% through `CapabilityRouter` and `ToolGateway`. Direct raw MCP imports are strictly forbidden by AST guards. | `CODE_PROVEN`, `TEST_PROVEN` | `tests/ai/audit/test_s28_m11_final_architecture_audit.py:47-81` |
| **P** | Do `CapabilityRouter` and `ToolGateway` receive real product requests? | **NO**. Neither `api/main.py` nor `scripts/pipeline.py` dispatches to `CapabilityRouter` or `ToolGateway`. Invocations are confined to `tests/ai/`. | `CODE_PROVEN` | `api/main.py:57-69`, `ai/routing/capability_router.py:88-120` |
| **Q** | Does `ModelRouter` receive real product requests? | **NO**. Zero production routes or pipeline stages dispatch to `ModelRouter`. Legacy tool scripts contain hard runtime blockers. | `CODE_PROVEN` | `api/main.py:57-69`, `ai/routing/router.py:67-106` |
| **R** | Is `CreativePlan` compiled into canonical `VideoDocument` on production path? | **NO**. `BlueprintCompiler` has 0 production callers in `api/`, `scripts/core/worker.py`, or `scripts/pipeline.py`. It is invoked only in test scripts. | `CODE_PROVEN` | `ai/planning/compiler.py:62-443`, `scripts/run_creative_e2e.py:75` |
| **S** | Is Remotion strictly an adapter at runtime or does it retain authority? | **Dual reality**: Contractually an adapter (`RemotionRendererAdapter`), but operationally retains authority because all 105 templates are Remotion TSX components, probe QC calls `remotion still`, and render fallback calls `remotion render`. | `CODE_PROVEN`, `DOCUMENTATION_ONLY` | `remotion/remotion-renderer-adapter.ts:8-16`, `scripts/render_project.py:128-185` |
| **T** | Do tests named "E2E" enter through real Production entrypoints? | **NO**. AI "E2E" tests manually chain in-memory classes; `true_e2e_suite.py` uses test factories to create synthetic project files on disk and invokes CLI directly; SaaS multi-tenant test mocks worker daemon execution. | `CODE_PROVEN`, `TEST_PROVEN` | `tests/ai/e2e/test_full_creative_e2e_matrix.py:200-260`, `tests/e2e/true_e2e_suite.py:32-75` |

---

## 2. Unified Reality Findings Ledger (`REALITY-001` through `REALITY-024`)

---

### REALITY-001: Required GitHub Actions CI Completely Omits AI Platform Subsystem (`tests/ai`)
- **Severity**: **`CRITICAL`**
- **Domain**: CI Governance / Verification
- **Status**: OPEN / UNRESOLVED
- **Confidence**: `PROVEN` (`CI_PROVEN`, `CODE_PROVEN`)
- **Observed Behavior**:
  The primary GitHub Actions workflow `.github/workflows/remediation-ci.yml:125-126` specifies pytest testpaths that completely exclude `tests/ai/`:
  `pytest ... tests/core tests/gates tests/generators tests/validators tests/architecture tests/contracts tests/fault_injection tests/e2e/test_pipeline_integration.py`.
  None of the 270 test files in `tests/ai/` are executed in CI.
- **Expected Architecture**:
  All production-bound subsystems must be verified in required CI gates before merging to `main`.
- **Evidence**: `.github/workflows/remediation-ci.yml:125-126`; grep for `tests/ai` in `.github/` returns 0 matches.
- **Production Impact**: Any breaking changes, regressions, or syntax errors in the entire AI platform can be merged without failing CI.
- **Affected Files**: `.github/workflows/remediation-ci.yml`
- **Related Tests**: 270 test files in `tests/ai/`
- **Required CI**: `python-tests` job in `remediation-ci.yml`
- **Remediation Direction (DO NOT FIX YET)**: Add `tests/ai` or create a dedicated `ai-tests` workflow job in `.github/workflows/`.

---

### REALITY-002: Local CI Runner Script Diverges Structurally from GitHub Actions CI
- **Severity**: **`HIGH`**
- **Domain**: Developer Tooling / CI Parity
- **Status**: OPEN / UNRESOLVED
- **Confidence**: `PROVEN` (`CODE_PROVEN`, `CI_PROVEN`)
- **Observed Behavior**:
  `scripts/ci/run_required_checks.sh` diverges from `.github/workflows/remediation-ci.yml` in 6 distinct ways: (1) runs `tests/ai` instead of `tests/fault_injection`, (2) runs contract generation drift checks, (3) omits Ruff linter, (4) omits Trivy vulnerability scanner, (5) scans different directories with Bandit, and (6) skips Docker hermetic build and acceptance tests.
- **Expected Architecture**:
  Local check scripts must faithfully replicate the required GitHub Actions CI gates.
- **Evidence**: `scripts/ci/run_required_checks.sh:20-66` vs `.github/workflows/remediation-ci.yml:14-265`.
- **Production Impact**: Passing checks locally gives false confidence that pull requests will pass CI, and vice versa.
- **Affected Files**: `scripts/ci/run_required_checks.sh`
- **Related Tests**: `tests/fault_injection`, `tests/ai`, `test_acc_007_docker_subcommand_validation.py`
- **Required CI**: All jobs in `remediation-ci.yml`
- **Remediation Direction (DO NOT FIX YET)**: Harmonize `run_required_checks.sh` to execute the exact commands and flags used in `remediation-ci.yml`.

---

### REALITY-003: Production Run Execution Path Disconnected from AI Platform
- **Severity**: **`CRITICAL`**
- **Domain**: Runtime Reachability / Architecture Boundary
- **Status**: OPEN / UNRESOLVED
- **Confidence**: `PROVEN` (`CODE_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`)
- **Observed Behavior**:
  The production video execution path (`POST /projects/{id}/runs` $\to$ `worker.py` $\to$ `pipeline.py`) contains zero calls to `ai/`, `CreativePlanner`, `NarrativePlanner`, or external LLMs. It requires pre-existing `master_plan.md` and `05_blueprint.json` on disk and executes only deterministic gates and Remotion rendering.
- **Expected Architecture**:
  End-to-end automated video generation should translate user requests to video via Creative Intelligence.
- **Evidence**: `api/routers/runs.py:23-56`, `scripts/core/worker.py:289`, `scripts/pipeline.py:371,381`.
- **Production Impact**: The AI platform is completely unreachable from the live SaaS video generation queue.
- **Affected Files**: `api/routers/runs.py`, `scripts/core/worker.py`, `scripts/pipeline.py`
- **Related Tests**: `tests/e2e/test_pipeline_integration.py`, `tests/ai/e2e/test_full_creative_e2e_matrix.py`
- **Required CI**: `python-tests`
- **Remediation Direction (DO NOT FIX YET)**: Design a unified run workflow that triggers `CreativePlanner` when `master_plan.md` is absent.

---

### REALITY-004: Production API Lacks Natural-Language Video Generation Intake Endpoint
- **Severity**: **`HIGH`**
- **Domain**: API Design / Entrypoints
- **Status**: OPEN / UNRESOLVED
- **Confidence**: `PROVEN` (`CODE_PROVEN`)
- **Observed Behavior**:
  None of the 34 API endpoints mounted in `api/main.py:57-70` accept natural-language briefs, prompts, or generative instructions. All routes require pre-existing IDs, pre-authored assets, or typed mutation payloads.
- **Expected Architecture**:
  A modern AI video production platform should expose a route (e.g. `POST /projects/generate` or `POST /brief`) accepting natural language.
- **Evidence**: `api/main.py:57-70`; grep across `api/routers/` for prompt/brief parameters yields 0 results.
- **Production Impact**: External clients and frontends cannot prompt the system for autonomous video creation.
- **Affected Files**: `api/main.py`, `api/routers/projects.py`
- **Related Tests**: `tests/api/test_projects.py`
- **Required CI**: `python-tests`
- **Remediation Direction (DO NOT FIX YET)**: Implement a `POST /projects/generate` endpoint wired to `CreativePlanner`.

---

### REALITY-005: `/intent` Endpoint Operates Exclusively on Strongly Typed AST Mutations
- **Severity**: **`MEDIUM`**
- **Domain**: Authoring / API Design
- **Status**: OPEN / UNRESOLVED
- **Confidence**: `PROVEN` (`CODE_PROVEN`)
- **Observed Behavior**:
  `POST /projects/{project_id}/intent` rejects freeform text. It strictly validates payloads against Zod `AuthoringRequestSchema` / `AuthoringIntentSchema` (a discriminated union of 14 typed intents like `UPDATE_TEXT`, `REPLACE_MEDIA`) and delegates to deterministic TypeScript `IntentPlanner`.
- **Expected Architecture**:
  Documentation and developer intuition imply `/intent` accepts natural-language edit requests.
- **Evidence**: `api/routers/authoring.py:104-132`, `contracts/authoring.ts:273-304`, `authoring/intent-planner.ts:5-14`.
- **Production Impact**: Clients sending raw natural language receive HTTP 422 / Zod validation errors.
- **Affected Files**: `api/routers/authoring.py`, `contracts/authoring.ts`
- **Related Tests**: `tests/api/test_authoring_router.py`
- **Required CI**: `contracts-ts`
- **Remediation Direction (DO NOT FIX YET)**: Introduce an NL-to-AuthoringIntent translation service before dispatching to `IntentPlanner`.

---

### REALITY-006: `ContextBuilder` Has Zero Production Callers
- **Severity**: **`HIGH`**
- **Domain**: AI Platform / Dependency Injection
- **Status**: OPEN / UNRESOLVED
- **Confidence**: `PROVEN` (`CODE_PROVEN`)
- **Observed Behavior**:
  `ai/context/builder.py:47-91` implements `ContextBuilder`. Grep across `api/` and `scripts/` confirms zero imports or instantiations. It is called exclusively within `tests/ai/context/`.
- **Expected Architecture**:
  ContextBuilder should assemble prompt context for AI planners during request processing.
- **Evidence**: `ai/context/builder.py:47`; grep across `api/` and `scripts/` yields 0 matches.
- **Production Impact**: Context budgeting, compression, and ranking logic are completely unused in production.
- **Affected Files**: `ai/context/builder.py`
- **Related Tests**: `tests/ai/context/test_builder.py`
- **Required CI**: N/A (omitted from CI)
- **Remediation Direction (DO NOT FIX YET)**: Wire `ContextBuilder` into the planned AI generation entrypoint.

---

### REALITY-007: Broken Context Dependency Injection (`KnowledgeRouter` Not Injected)
- **Severity**: **`MEDIUM`**
- **Domain**: AI Platform / Dependency Injection
- **Status**: OPEN / UNRESOLVED
- **Confidence**: `PROVEN` (`CODE_PROVEN`)
- **Observed Behavior**:
  `ContextBuilder.__init__` accepts `knowledge_retriever: Optional[KnowledgeRetriever]`, defaulting to `DeterministicKnowledgeRetriever()`. `KnowledgeRouter` does not implement this protocol and is never injected into `ContextBuilder` anywhere in the repository.
- **Expected Architecture**:
  Context assembly should retrieve domain knowledge through `KnowledgeRouter`.
- **Evidence**: `ai/context/builder.py:59-77`, `ai/knowledge/router.py:34-56`.
- **Production Impact**: `ContextBuilder` can only retrieve hardcoded or deterministic mock knowledge.
- **Affected Files**: `ai/context/builder.py`, `ai/context/retrieval.py`
- **Related Tests**: `tests/ai/context/test_builder.py`
- **Required CI**: N/A
- **Remediation Direction (DO NOT FIX YET)**: Implement an adapter bridging `KnowledgeRouter` to `KnowledgeRetriever` protocol.

---

### REALITY-008: Catalog Initialization Never Invoked in Production Runtime
- **Severity**: **`MEDIUM`**
- **Domain**: Knowledge Platform / Lifecycle
- **Status**: OPEN / UNRESOLVED
- **Confidence**: `PROVEN` (`CODE_PROVEN`)
- **Observed Behavior**:
  `initialize_canonical_catalog()` in `ai/knowledge/router.py:58-68` is never called during FastAPI startup lifespan (`api/main.py:28-40`), worker initialization, or pipeline execution. It is invoked only in test/eval runners.
- **Expected Architecture**:
  The knowledge catalog should be initialized and indexed at application boot.
- **Evidence**: `ai/knowledge/router.py:58-68`, `api/main.py:28-40`.
- **Production Impact**: Knowledge indexer remains unpopulated in long-running services.
- **Affected Files**: `ai/knowledge/router.py`, `api/main.py`
- **Related Tests**: `tests/ai/knowledge/test_knowledge_platform.py`
- **Required CI**: N/A
- **Remediation Direction (DO NOT FIX YET)**: Add catalog initialization to FastAPI lifespan startup.

---

### REALITY-009: Root `ground-truth/` Functions as Derivative Documentation
- **Severity**: **`MEDIUM`**
- **Domain**: Data Architecture / Governance
- **Status**: OPEN / UNRESOLVED
- **Confidence**: `PROVEN` (`CODE_PROVEN`, `CI_PROVEN`)
- **Observed Behavior**:
  Root `ground-truth/` contains 13 auto-generated JSON and Markdown files produced by `scripts/generators/build_ground_truth.py`. It is not an ML evaluation dataset or runtime authority.
- **Expected Architecture**:
  System authority should reside in canonical typed registries, with documentation clearly classified.
- **Evidence**: `scripts/generators/build_ground_truth.py:1-4`, `scripts/validators/check_ground_truth_sync.py:1-55`.
- **Production Impact**: Creates confusion about whether `ground-truth/` is an ML training set, runtime config, or documentation index.
- **Affected Files**: `ground-truth/*`, `scripts/generators/build_ground_truth.py`
- **Related Tests**: `scripts/validators/check_ground_truth_sync.py`
- **Required CI**: `ground-truth` job in `remediation-ci.yml`
- **Remediation Direction (DO NOT FIX YET)**: Relocate `ground-truth/` into `documentation/indexes/` or `registry/generated/`.

---

### REALITY-010: Zero Production Runtime Consumers for Files in Root `ground-truth/`
- **Severity**: **`MEDIUM`**
- **Domain**: Runtime Reachability
- **Status**: OPEN / UNRESOLVED
- **Confidence**: `PROVEN` (`CODE_PROVEN`)
- **Observed Behavior**:
  Neither `api/` nor `scripts/pipeline.py` imports or reads files from `ground-truth/`. Only offline test runners and legacy plugin tools read them.
- **Expected Architecture**:
  Unconsumed artifacts should not gate production CI.
- **Evidence**: Grep across `api/` and `scripts/` yields 0 occurrences.
- **Production Impact**: CI enforces strict hash synchronization for files that no production process reads.
- **Affected Files**: `ground-truth/*`
- **Related Tests**: `scripts/validators/check_ground_truth_sync.py`
- **Required CI**: `ground-truth` job in `remediation-ci.yml`
- **Remediation Direction (DO NOT FIX YET)**: Relax CI gating on derivative indexes once documentation is updated.

---

### REALITY-011: `template_catalog.json` Operates as a Derivative Metadata Index
- **Severity**: **`MEDIUM`**
- **Domain**: Template Governance / Authority
- **Status**: OPEN / UNRESOLVED
- **Confidence**: `PROVEN` (`CODE_PROVEN`)
- **Observed Behavior**:
  `ground-truth/template_catalog.json` is a derivative compatibility catalog generated from `registry/template-registry.tsx`. The true single source of truth is `registry/template-registry-data.json`.
- **Expected Architecture**:
  One canonical authority for template metadata.
- **Evidence**: `scripts/core/template_registry_publisher.py:6-11`.
- **Production Impact**: Developers and agents frequently edit or cite `template_catalog.json` believing it is the authority.
- **Affected Files**: `ground-truth/template_catalog.json`, `registry/template-registry-data.json`
- **Related Tests**: `tests/contracts/test_template_registry.py`
- **Required CI**: `ground-truth`
- **Remediation Direction (DO NOT FIX YET)**: Clarify authority in `AGENTS.md` and deprecate `template_catalog.json`.

---

### REALITY-012: `RecipeRegistry` Globs and Migrates `recipes/*.json` on Boot in Memory
- **Severity**: **`LOW`**
- **Domain**: Recipe Management / Dataflow
- **Status**: OPEN / UNRESOLVED
- **Confidence**: `PROVEN` (`CODE_PROVEN`, `TEST_PROVEN`)
- **Observed Behavior**:
  `RecipeRegistry.__init__` with default `auto_load=True` globs all 18 JSON files in `recipes/` (skipping `schema.json`), migrates legacy provider keys, and registers them in memory.
- **Expected Architecture**:
  Recipes should be validated against static schema contracts without dynamic in-memory migration overhead.
- **Evidence**: `ai/recipes/registry.py:105-125`.
- **Production Impact**: Minor boot latency; runtime relies on on-the-fly migration rather than migrated source files.
- **Affected Files**: `ai/recipes/registry.py`, `recipes/*.json`
- **Related Tests**: `tests/ai/recipes/test_recipe_platform.py`
- **Required CI**: N/A
- **Remediation Direction (DO NOT FIX YET)**: Migrate `recipes/*.json` files permanently on disk to conform to modern schema.

---

### REALITY-013: Skills Subsystem Employs Dual-Loading Architecture
- **Severity**: **`LOW`**
- **Domain**: Skills Platform / Extensibility
- **Status**: OPEN / UNRESOLVED
- **Confidence**: `PROVEN` (`CODE_PROVEN`)
- **Observed Behavior**:
  `SkillLoader` supports both typed Python definitions (`get_canonical_skills()`) and dynamic markdown parsing (`load_from_markdown()` for `SKILL.md` files).
- **Expected Architecture**:
  Consistent skill loading mechanism across agents and platform.
- **Evidence**: `ai/skills/loader.py:62-112, 114-302`.
- **Production Impact**: Potential discrepancy between canonical typed skills and agent-authored markdown skills.
- **Affected Files**: `ai/skills/loader.py`, `ai/skills/registry.py`
- **Related Tests**: `tests/ai/skills/test_skill_platform.py`
- **Required CI**: N/A
- **Remediation Direction (DO NOT FIX YET)**: Maintain dual-loading but enforce strict contract schema validation on markdown imports.

---

### REALITY-014: Internal Product AI Strictly Forbids Raw MCP Invocations
- **Severity**: **`INFO`**
- **Domain**: Architecture Governance / Tool Execution
- **Status**: PROVEN / WORKING AS DESIGNED
- **Confidence**: `PROVEN` (`CODE_PROVEN`, `TEST_PROVEN`)
- **Observed Behavior**:
  AST architecture guards in `tests/ai/audit/test_s28_m11_final_architecture_audit.py` strictly forbid raw MCP calls from internal code. All capabilities must route through `CapabilityRouter` and `ToolGateway` via native Python adapters.
- **Expected Architecture**:
  Strongly typed, safe in-process capability execution with FastMCP as an external boundary only.
- **Evidence**: `tests/ai/audit/test_s28_m11_final_architecture_audit.py:47-81`.
- **Production Impact**: High performance and type safety for internal capabilities; eliminates JSON-RPC serialization overhead.
- **Affected Files**: `ai/capabilities/gateway.py`, `ai/tools/gateway.py`
- **Related Tests**: `tests/ai/audit/*`
- **Required CI**: N/A (omitted from CI)
- **Remediation Direction (DO NOT FIX YET)**: Update `.agents/AGENTS.md` and `ROUTER.md` to reflect that raw MCP is banned internally.

---

### REALITY-015: `CapabilityRouter` and `ToolGateway` Have Zero Production Call Sites
- **Severity**: **`CRITICAL`**
- **Domain**: Runtime Reachability / AI Platform
- **Status**: OPEN / UNRESOLVED
- **Confidence**: `PROVEN` (`CODE_PROVEN`)
- **Observed Behavior**:
  Despite 32 fully modeled capabilities and a 15-stage tool execution pipeline, neither `api/main.py` nor `scripts/pipeline.py` imports or invokes `CapabilityRouter` or `ToolGateway`.
- **Expected Architecture**:
  Production tasks requiring speech, vision, or image generation should dispatch through `CapabilityRouter`.
- **Evidence**: `ai/routing/capability_router.py:69-120`; grep across `api/` and `scripts/` yields 0 matches.
- **Production Impact**: The entire S28-M tool modernization effort is isolated from production users.
- **Affected Files**: `ai/routing/capability_router.py`, `ai/tools/gateway.py`
- **Related Tests**: `tests/ai/tools/test_tool_gateway.py`, `tests/ai/routing/test_capability_router.py`
- **Required CI**: N/A
- **Remediation Direction (DO NOT FIX YET)**: Wire `CapabilityRouter` into the planned AI video generation pipeline.

---

### REALITY-016: `CreativePlanCompiler` Disconnected from Production Authoring Path
- **Severity**: **`HIGH`**
- **Domain**: Creative Pipeline / Integration
- **Status**: OPEN / UNRESOLVED
- **Confidence**: `PROVEN` (`CODE_PROVEN`)
- **Observed Behavior**:
  `BlueprintCompiler` in `ai/planning/compiler.py:62-443` is the sole translator from `CreativePlan` to canonical `BlueprintV2` / `VideoDocument`. It has zero callers in `api/` or `authoring/`. Production authoring creates or edits documents via manual AST mutations.
- **Expected Architecture**:
  The creative planning output must compile into canonical `VideoDocument` for authoring and rendering.
- **Evidence**: `ai/planning/compiler.py:62-443`; grep for callers outside tests yields 0 results.
- **Production Impact**: A `CreativePlan` cannot be turned into an editable video document in production.
- **Affected Files**: `ai/planning/compiler.py`, `api/services/authoring_service.py`
- **Related Tests**: `tests/ai/planning/test_compiler.py`
- **Required CI**: N/A
- **Remediation Direction (DO NOT FIX YET)**: Expose a production service calling `BlueprintCompiler` to initialize authoring sessions.

---

### REALITY-017: Remotion Dual Reality (Contractual Adapter vs. Operational Authority)
- **Severity**: **`HIGH`**
- **Domain**: Renderer Independence / Coupling
- **Status**: OPEN / UNRESOLVED
- **Confidence**: `PROVEN` (`CODE_PROVEN`, `DOCUMENTATION_ONLY`)
- **Observed Behavior**:
  While contracts (`contracts/renderer.ts`) and RenderPlanner define Remotion as an engine-neutral adapter, all 105 canonical templates are React TSX components importing Remotion hooks, `scripts/gates/probe_qc.py` invokes `remotion still`, and `scripts/render_project.py` falls back to `npx remotion render`.
- **Expected Architecture**:
  True renderer independence allowing interchangeable rendering via Canvas or Remotion.
- **Evidence**: `remotion/remotion-renderer-adapter.ts:8-16`, `scripts/render_project.py:128-185`, `scripts/gates/probe_qc.py`.
- **Production Impact**: Complete lock-in to Node.js and Remotion runtime for production video generation.
- **Affected Files**: `remotion/remotion-renderer-adapter.ts`, `scripts/render_project.py`, `scripts/gates/probe_qc.py`
- **Related Tests**: `tests/remotion/*`
- **Required CI**: `contracts-ts`
- **Remediation Direction (DO NOT FIX YET)**: Decouple template definitions from React hooks or build Canvas adapter template equivalents.

---

### REALITY-018: Test Reality Divergence in Suites Named "E2E"
- **Severity**: **`HIGH`**
- **Domain**: Testing / Verification Integrity
- **Status**: OPEN / UNRESOLVED
- **Confidence**: `PROVEN` (`CODE_PROVEN`, `TEST_PROVEN`)
- **Observed Behavior**:
  Tests named "E2E" do not enter through full unmocked production paths: AI E2E tests chain in-memory classes; `true_e2e_suite.py` bypasses the API and worker daemon by invoking the CLI directly on disk fixtures; multi-tenant SaaS tests mock worker polling.
- **Expected Architecture**:
  True product E2E tests should send an HTTP request to `api/`, wait for background worker polling, render the video, and verify HTTP output streaming.
- **Evidence**: `tests/ai/e2e/test_full_creative_e2e_matrix.py:200-260`, `tests/e2e/true_e2e_suite.py:32-75`.
- **Production Impact**: Automated tests verify isolated components but leave the full user-to-video delivery journey unverified.
- **Affected Files**: `tests/e2e/true_e2e_suite.py`, `tests/ai/e2e/*`
- **Related Tests**: `tests/e2e/*`
- **Required CI**: `strict-e2e`
- **Remediation Direction (DO NOT FIX YET)**: Author a true product E2E suite that drives the entire stack via HTTP $\to$ Worker $\to$ Video Stream.

---

### REALITY-019: Development/Testing Identity Spoofing and Unauthenticated Auth Fallback
- **Severity**: **`CRITICAL`**
- **Domain**: Security / Authentication
- **Status**: OPEN / UNRESOLVED
- **Confidence**: `PROVEN` (`CODE_PROVEN`)
- **Observed Behavior**:
  In `api/core/auth.py:240-305`, when `MOTION_ENV != "production"`, callers can pass hardcoded tokens (`admin`, `system`) or unverified headers (`X-Principal-ID: root`, `X-Principal-Roles: admin`) to gain full global administrative privileges without authentication.
- **Expected Architecture**:
  Cryptographic authentication enforced uniformly, with dev keys for local environments.
- **Evidence**: `api/core/auth.py:240-305`.
- **Production Impact**: If `MOTION_ENV=production` is omitted in any deployment, administrative auth is completely bypassed.
- **Affected Files**: `api/core/auth.py`
- **Related Tests**: `tests/security/test_s02_negative_enforcement.py`
- **Required CI**: `security-audit`
- **Remediation Direction (DO NOT FIX YET)**: Remove token string heuristics and unverified header parsing from `auth.py`.

---

### REALITY-020: Disconnect Between Multi-Tenant SQL Model and Flat Filesystem Workspaces
- **Severity**: **`HIGH`**
- **Domain**: Multi-Tenancy / Filesystem Architecture
- **Status**: OPEN / UNRESOLVED
- **Confidence**: `PROVEN` (`CODE_PROVEN`)
- **Observed Behavior**:
  `TenantRepository` enforces workspace isolation in SQL, and `StorageService` partitions object keys by workspace ID, but on the local filesystem, projects reside in a flat directory `projects/{project_id}/`.
- **Expected Architecture**:
  Filesystem workspaces should be partitioned by tenant (`projects/{workspace_id}/{project_id}/`).
- **Evidence**: `scripts/core/database.py:86`, `scripts/core/storage/storage_service.py:106`, `scripts/pipeline.py:13`.
- **Production Impact**: Local scripts or file leaks can access projects across tenant boundaries.
- **Affected Files**: `scripts/core/storage/storage_service.py`, `scripts/pipeline.py`
- **Related Tests**: `tests/e2e/test_saas_multi_tenant_e2e.py`
- **Required CI**: `python-tests`
- **Remediation Direction (DO NOT FIX YET)**: Migrate local filesystem workspaces to `projects/{workspace_id}/{project_id}`.

---

### REALITY-021: Agent Directive Drift in `.agents/AGENTS.md` and `references/ROUTER.md`
- **Severity**: **`HIGH`**
- **Domain**: Agent Governance / Documentation
- **Status**: OPEN / UNRESOLVED
- **Confidence**: `PROVEN` (`CODE_PROVEN`, `DOCUMENTATION_ONLY`)
- **Observed Behavior**:
  Agent instructions prescribe ungrounded rules (e.g. 480-490 plan line count limit), mandate raw MCP servers that are banned by AST guards, cite excluded engine bridges, and recommend quarantined tools.
- **Expected Architecture**:
  Agent rules must strictly mirror active runtime constraints and modern architectural patterns.
- **Evidence**: `.agents/AGENTS.md:31,43-48,51-57`, `references/ROUTER.md:11,14,21-44`.
- **Production Impact**: Orchestrator agents generate brittle plans, invoke obsolete tools, and fail security gates.
- **Affected Files**: `.agents/AGENTS.md`, `references/ROUTER.md`
- **Related Tests**: N/A
- **Required CI**: N/A
- **Remediation Direction (DO NOT FIX YET)**: Rewrite `AGENTS.md` and `ROUTER.md` to align with S28-M and S28-R.

---

### REALITY-022: Lingering Historical Migration & Deprecated Scripts in `scripts/archive/`
- **Severity**: **`MEDIUM`**
- **Domain**: Codebase Hygiene / Technical Debt
- **Status**: OPEN / UNRESOLVED
- **Confidence**: `PROVEN` (`CODE_PROVEN`)
- **Observed Behavior**:
  `scripts/archive/` contains 28 unconsumed files across `phase13/`, `phase14/`, `phase15/`, `phase16/` and legacy smoke scripts, alongside partially consumed migration scripts (`migrate_legacy_projects.py`).
- **Expected Architecture**:
  Clean codebase free of unconsumed migration scrap.
- **Evidence**: `scripts/archive/` directory audit.
- **Production Impact**: Increases repository noise and cognitive overhead during architecture audits.
- **Affected Files**: `scripts/archive/*`
- **Related Tests**: `tests/archive/test_migrate_legacy.py`
- **Required CI**: N/A
- **Remediation Direction (DO NOT FIX YET)**: Delete proven 0-consumer files and retire tests that import archived scripts.

---

### REALITY-023: Vitest Remotion CI Exclusion (36 S28-R Test Files Unexecuted)
- **Severity**: **`HIGH`**
- **Domain**: CI Governance / TypeScript Verification
- **Status**: OPEN / UNRESOLVED
- **Confidence**: `PROVEN` (`CODE_PROVEN`, `CI_PROVEN`)
- **Observed Behavior**:
  In `.github/workflows/remediation-ci.yml:58`, CI runs `npm run test` in root. In `package.json:28`, `npm run test` executes only 13 test files. 36 Remotion test files in `tests/remotion/` (including all S28-R adapter, graph, and compositor tests) are omitted from the test runner.
- **Expected Architecture**:
  All TypeScript unit and contract tests should be executed in required CI.
- **Evidence**: `package.json:28`, `find tests/remotion -name "*.test.ts" | wc -l` (49 files).
- **Production Impact**: Regressions in S28-R renderer adapters or compositor logic are not caught by CI.
- **Affected Files**: `package.json`, `.github/workflows/remediation-ci.yml`
- **Related Tests**: 36 test files in `tests/remotion/`
- **Required CI**: `contracts-ts`
- **Remediation Direction (DO NOT FIX YET)**: Update root `package.json` test script to include `tests/remotion/**/*.test.ts`.

---

### REALITY-024: Zod Dependency Split Across Monorepo Roots
- **Severity**: **`MEDIUM`**
- **Domain**: Package Management / Type Safety
- **Status**: OPEN / UNRESOLVED
- **Confidence**: `PROVEN` (`CODE_PROVEN`)
- **Observed Behavior**:
  Root `package.json:48` pins `zod: 3.25.76`. In contrast, `remotion-app/package.json:33,43` pins `zod: 4.5.4` with an override block (`overrides: { "zod": "4.5.4" }`).
- **Expected Architecture**:
  Consistent dependency versions across workspaces in the repository.
- **Evidence**: `package.json:48`, `remotion-app/package.json:33,43`.
- **Production Impact**: Potential schema validation divergence or runtime incompatibility when contracts cross boundaries.
- **Affected Files**: `package.json`, `remotion-app/package.json`
- **Related Tests**: `tests/contracts/*`
- **Required CI**: `contracts-ts`
- **Remediation Direction (DO NOT FIX YET)**: Align Zod version across root and `remotion-app`.


---


<a name='part-6-catalog-of-critical-unknowns--required-follow-up-probes'></a>

## Part 6: Catalog of Critical Unknowns & Required Follow-Up Probes


> *Original Source: `documentation/reality_context_pack/20_UNKNOWNS_AND_UNPROVEN_CLAIMS.md`*


### Sub-Report Title: Unknowns & Unproven Claims Reality Report


- **Baseline Git SHA**: `90ec3de8d47494d5940d5cd1f9ed9a8e274ef6e1`
- **Branch**: `main`
- **Report Version**: 1.0.0
- **Last Updated**: 2026-10-07
- **Scope**: Rigorous catalog of architectural ambiguities, unproven performance/capacity claims, unverified operational limits, unlinked dependencies, and required follow-up probes across the system.
- **Evidence Standard**: `CODE_PROVEN`, `TEST_PROVEN`, `CI_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`, `DOCUMENTATION_ONLY`, `INFERRED`, `UNKNOWN`

---

## 1. Executive Summary

In keeping with the strict **Evidence Standard ("NO ARCHITECTURAL CLAIM WITHOUT EXECUTABLE EVIDENCE")**, any architectural proposition, scaling assertion, or cross-subsystem capability that cannot be proven directly from source code, executed tests, or CI results is classified as an **Unknown** or **Unproven Claim**.

This report documents the top 10 critical unknowns and outlines precise, actionable follow-up probes to resolve each ambiguity in subsequent investigative phases.

---

## 2. Catalog of Unknowns & Required Follow-Up Probes

---

### UNK-001: True Concurrent SaaS Rendering Capacity with Headless Chrome
- **Claim / Proposition**:
  Documentation suggests the video platform can operate as a high-throughput, multi-tenant SaaS rendering engine handling dozens of concurrent video jobs.
- **Why Unproven**:
  Remotion rendering (`npx remotion render`) relies on headless Chromium browser processes launched locally or inside Docker containers. In `tests/remediation/s02_acceptance/test_acc_007_docker_subcommand_validation.py` and `tests/e2e/true_e2e_suite.py`, tests run strictly 1 video sequentially on a single node. No multi-worker concurrent rendering benchmark exists in CI.
- **Architectural Risk**:
  Headless browser rendering is heavily CPU/RAM intensive (~1-2 GB RAM per Chromium instance). Spawning multiple workers without strict cgroup resource constraints will cause catastrophic OOM crashes or worker timeouts in production.
- **Classification**: **`UNKNOWN`** / **`UNPROVEN`** [`DOCUMENTATION_ONLY`].
- **Required Follow-Up Probe**:
  1. Deploy a multi-worker test bed using `scripts/testing/s28_r15_soak_and_load_runner.py`.
  2. Enqueue 10 concurrent render jobs via `POST /projects/{id}/runs` under varying memory limits (2GB, 4GB, 8GB).
  3. Measure peak memory, CPU saturation, render duration, and failure rates.

---

### UNK-002: Canvas Renderer Adapter Parity vs. Remotion Templates
- **Claim / Proposition**:
  Generation S28-R introduces the `CanvasRendererAdapter` (`canvas/canvas-renderer-adapter.ts`) as a fully interchangeable alternative to Remotion for 2D/canvas video generation.
- **Why Unproven**:
  All 105 production templates in `registry/template-registry.tsx` and `templates/` are implemented strictly as React TSX components utilizing Remotion-specific hooks (`useCurrentFrame`, `useVideoConfig`, `AbsoluteFill`, `spring`, `interpolate`). While `canvas/canvas-renderer-adapter.ts` compiles, there are zero production templates implemented using pure HTML5 Canvas or WebGL.
- **Architectural Risk**:
  If Remotion encounters rendering bottlenecks or licensing issues, the system cannot actually switch to the Canvas adapter without rewriting all 105 templates from scratch.
- **Classification**: **`INFERRED`** / **`UNPROVEN`** [`CODE_PROVEN` that adapter exists; `UNKNOWN` template compatibility].
- **Required Follow-Up Probe**:
  1. Inspect `canvas/canvas-renderer-adapter.ts` for template binding logic.
  2. Attempt rendering a complex blueprint scene (e.g. `StatCard` or `KineticHeadline`) using `CanvasRendererAdapter`.
  3. Catalog missing visual primitives and frame synchronization APIs.

---

### UNK-003: Operational Latency and Cost of Autonomous AI Generation Flow
- **Claim / Proposition**:
  The S27/S28 AI platform can automatically plan, acquire assets, and generate videos with deterministic token budgeting and cost controls.
- **Why Unproven**:
  Because the AI subsystem is disconnected from the production HTTP API, end-to-end user-to-video execution has never been measured under real network conditions with live LLM and media provider APIs. Offline scripts (`scripts/run_real_cost_performance_benchmark.py`) run with recorded traces or synthetic mock payloads.
- **Architectural Risk**:
  Real-world multi-stage AI pipelines (Prompt $\to$ Brief $\to$ Narrative $\to$ CreativePlan $\to$ ElevenLabs TTS $\to$ Fal/Replicate Video $\to$ Blueprint $\to$ Render) may suffer high failure rates due to external provider rate limits, network timeouts, or costs exceeding $10+ per video.
- **Classification**: **`UNKNOWN`** [`DOCUMENTATION_ONLY`].
- **Required Follow-Up Probe**:
  1. Run `scripts/smoke_openrouter.py` and measure wall-clock latency across 10 prompt variations.
  2. Execute an integrated probe script chaining `NarrativePlanner` $\to$ `CreativePlanner` $\to$ `BlueprintCompiler` using live OpenRouter and Fal AI API keys.
  3. Log token consumption, API dollar costs, and total end-to-end execution latency.

---

### UNK-004: FastMCP Linux Compatibility vs. Legacy Windows Tool Paths
- **Claim / Proposition**:
  Legacy MCP tools in `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/` can be transparently served to modern AI clients via `ai/mcp/compatibility/server.py`.
- **Why Unproven**:
  The configuration file `.agents/plugins/super-video-maker-plugin/mcp_config.json` contains hardcoded Windows filepaths (`"args": ["C:/video/clean-video-workspace/..."]`). While the Python and JS tool files exist locally on Linux, the configuration file itself will fail to spawn processes on Linux environments without dynamic path mapping.
- **Architectural Risk**:
  External agents or clients reading `mcp_config.json` on Linux servers will fail during server launch.
- **Classification**: **`UNKNOWN`** on Linux runtime [`CODE_PROVEN` path discrepancy].
- **Required Follow-Up Probe**:
  1. Launch `python -m ai.mcp.compatibility.server` under Linux.
  2. Send JSON-RPC `tools/list` and `tools/call` requests for each of the 6 legacy MCP servers.
  3. Verify whether subprocess spawning succeeds or throws path resolution errors.

---

### UNK-005: PostgreSQL Multi-Tenant Concurrency and CAS Lock Contention
- **Claim / Proposition**:
  The database engine seamlessly supports PostgreSQL for enterprise multi-tenant deployments with atomic Compare-And-Swap (CAS) optimistic locking.
- **Why Unproven**:
  All local tests and CI workflows execute against SQLite (`data/motion.db`, `data/runs.db`, or `:memory:`). PostgreSQL execution is implemented in `scripts/core/database.py` via `psycopg2` or `asyncpg` bindings, but PostgreSQL is not provisioned as a service in `.github/workflows/remediation-ci.yml`.
- **Architectural Risk**:
  PostgreSQL transaction isolation levels (Read Committed vs Serializable) and locking semantics may cause unexpected concurrency deadlocks or CAS version collision errors that do not occur in SQLite.
- **Classification**: **`UNKNOWN`** in CI / Production [`TEST_PROVEN` in SQLite only].
- **Required Follow-Up Probe**:
  1. Spin up a local PostgreSQL container (`docker run -p 5432:5432 postgres:16`).
  2. Configure `DATABASE_URL=postgresql://...` and execute `tests/e2e/test_saas_multi_tenant_e2e.py`.
  3. Run concurrent race condition tests simulating 50 simultaneous AST mutations against a single project document.

---

### UNK-006: Zod v3 vs. v4 Semantic Divergence Across Monorepo Workspaces
- **Claim / Proposition**:
  TypeScript contracts in `contracts/` and `remotion-app/` validate data uniformly across both packages.
- **Why Unproven**:
  Root `package.json` pins `zod@3.25.76`, while `remotion-app/package.json` pins `zod@4.5.4` (using an `overrides` block). Zod v4 includes breaking changes to error formatting, discriminated union parsing, and optional/null handling.
- **Architectural Risk**:
  A blueprint or authoring payload that passes validation in `contracts/` (Zod v3) may fail validation or behave unexpectedly when loaded inside `remotion-app/` (Zod v4).
- **Classification**: **`UNKNOWN`** runtime impact [`CODE_PROVEN` version mismatch].
- **Required Follow-Up Probe**:
  1. Compile and execute cross-boundary schema validation tests passing edge-case inputs (null properties, extra fields, discriminated unions) between root and `remotion-app`.
  2. Audit all Zod import paths in `remotion-app/` to ensure consistent resolution.

---

### UNK-007: Impact of Unexecuted Remotion Tests (36 S28-R Vitest Files)
- **Claim / Proposition**:
  The S28-R Live Authoring and Renderer Independence layer is fully regression-free.
- **Why Unproven**:
  GitHub Actions CI only executes 13 of 49 Remotion test files (`package.json:28` runs `npm run test` which defaults to a restricted glob). 36 test files in `tests/remotion/` covering `RemotionRendererAdapter`, `ProductionRenderGraphExecutor`, and compositor timing are skipped in CI.
- **Architectural Risk**:
  Recent commits to `contracts/` or `remotion/` may have silently broken S28-R renderer adapter components without failing CI.
- **Classification**: **`UNKNOWN`** CI health [`CODE_PROVEN` CI exclusion].
- **Required Follow-Up Probe**:
  1. Run `npx vitest run tests/remotion/` across all 49 test files locally.
  2. Catalog any failing test suites, deprecation warnings, or missing mocks.

---

### UNK-008: True Recovery Behavior on Worker Crashes Mid-Render
- **Claim / Proposition**:
  The pipeline recovery engine (`RecoveryEngine.evaluate()`) safely recovers projects and resumes execution if a worker crashes during rendering.
- **Why Unproven**:
  While `RecoveryEngine` exists in `scripts/core/recovery_engine.py`, fault-injection tests simulate worker death by killing the subprocess, but do not verify that a partially rendered MP4 or half-written temporary disk file doesn't corrupt subsequent runs.
- **Architectural Risk**:
  Stale lock files or half-written `.pipeline_state.json` files may permanently deadlock a project in `RENDER_IN_PROGRESS` or `AWAITING_REVIEW`.
- **Classification**: **`UNKNOWN`** production recovery fidelity [`CODE_PROVEN` engine exists].
- **Required Follow-Up Probe**:
  1. Execute a run on a test project and send `kill -9` to the worker process during the `render_project.py` stage.
  2. Launch a new worker process and verify whether the project transitions to `RECOVERING` and successfully finishes or deadlocks.

---

### UNK-009: Audio Loudness Normalization Fidelity on Non-Standard Audio Streams
- **Claim / Proposition**:
  All audio streams are normalized to -16 LUFS for voiceover and -24 LUFS for sound effects via local FFmpeg scripts.
- **Why Unproven**:
  Loudness normalization is implemented using FFmpeg's `loudnorm` filter. In edge cases involving highly dynamic audio, short audio clips (<3 seconds), or multichannel 5.1/7.1 audio, single-pass `loudnorm` produces audible clipping or incorrect integrated loudness.
- **Architectural Risk**:
  Short sound effects or introductory voiceover lines may be distorted or fail `final_qc.py` audio checks.
- **Classification**: **`UNKNOWN`** edge-case audio quality [`CODE_PROVEN` implementation exists].
- **Required Follow-Up Probe**:
  1. Pass audio clips of varying durations (1.5s, 5s, 60s) through `scripts/gates/final_qc.py` and `scripts/core/audio_normalizer.py`.
  2. Verify that `r128` integrated loudness strictly measures -16.0 LUFS $\pm$ 1.0 LUFS without digital clipping.

---

### UNK-010: True End-to-End Cold-Start Latency for Video Generation
- **Claim / Proposition**:
  The system can deliver interactive preview and fast render turnaround for web clients.
- **Why Unproven**:
  No benchmark measures the wall-clock time from cold start: (1) project creation, (2) blueprint mutation, (3) dependency materialization, (4) Remotion bundle compilation, (5) probe QC still extraction, (6) multi-frame rendering, and (7) MP4 final encoding.
- **Architectural Risk**:
  First-time Remotion bundle compilation can take 30-45 seconds on cold caches, leading to HTTP gateway timeouts (e.g. Cloudflare 524 timeouts) for interactive clients.
- **Classification**: **`UNKNOWN`** cold-start SLA [`DOCUMENTATION_ONLY`].
- **Required Follow-Up Probe**:
  1. Clear all `.cache`, `node_modules/.cache`, and ephemeral workspace folders.
  2. Execute a complete cold-start run via `tests/e2e/true_e2e_suite.py` measuring each phase with nanosecond timestamps.
  3. Document cold vs warm turnaround latencies.


---

