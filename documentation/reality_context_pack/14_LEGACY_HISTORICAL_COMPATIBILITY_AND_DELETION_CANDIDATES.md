# Legacy, Historical Compatibility & Deletion Candidates Reality Report

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
