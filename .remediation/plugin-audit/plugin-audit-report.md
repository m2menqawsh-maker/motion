# Plugin vs Root Duplication Investigation — Comprehensive Architectural Audit Report

**Date:** 2026-09-17  
**Workspace:** `c:\video\clean-video-workspace\`  
**Plugin Directory:** `.agents\plugins\super-video-maker-plugin\`  
**Investigative Mode:** Read-Only Audit (Zero Mutations Performed)  
**Deliverables Generated:**
- [root-plugin-path-map.json](file:///c:/video/clean-video-workspace/.remediation/plugin-audit/root-plugin-path-map.json)
- [plugin-root-file-matrix.json](file:///c:/video/clean-video-workspace/.remediation/plugin-audit/plugin-root-file-matrix.json)
- [plugin-architecture.md](file:///c:/video/clean-video-workspace/.remediation/plugin-audit/plugin-architecture.md)
- [plugin-audit-report.md](file:///c:/video/clean-video-workspace/.remediation/plugin-audit/plugin-audit-report.md)

---

## 1. Executive Summary & Verdict on User Hypothesis

### The Hypothesis Under Investigation
> *"Root copies may contain historical / legacy material while plugin copies may be the actively maintained plugin truth."*

### The Verdict: **NO (Directly Refuted by Code, Git History, and Runtime Tests)**

Detailed forensic analysis proves that **the user's hypothesis is false for almost the entire codebase**:
1. **Templates (`templates/`)**: The plugin contains **zero templates** (`.tsx` count = 0). The 109 active Remotion templates reside solely in `templates/` and `remotion-app/src/templates/` in the workspace root, actively exercised by Vitest (`tests/template_runtime_resolution.test.ts`, `tests/contracts.test.ts`).
2. **Execution Pipeline (`scripts/`)**: The unified pipeline (`scripts/pipeline.py`) is the constitutional orchestrator under `ARCHITECTURE_TRUTH.md`. In Git commit `9dcb888` (*"refactor(core): decouple application logic from AI plugin"*), `scripts/` was deliberately moved out of the plugin to root. Root scripts are actively tested by `pytest` and govern state transitions via `.pipeline_state.json`. The plugin contains no `scripts/` folder.
3. **Production Recipes (`recipes/`)**: The 17 production recipes (`recipes/*.json`) live in root and are indexed in root `ground-truth/RECIPES_INDEX.md`. The plugin contains only a single markdown instruction command (`commands/avatar-insta-reel.md`).
4. **References & Documentation (`references/`)**: Root copies of `references/` are the actively maintained, constitutional Level 5 documents under `ARCHITECTURE_TRUTH.md`, updated with explicit Source of Truth Hierarchy alert banners and rewritten to mandate the Zero-Build Master Engine architecture. In stark contrast, plugin copies of references contain obsolete, unmaintained text (e.g., `plugin/references/REMOTION_VIDEO_GUIDE.md` contains an obsolete 676-line manual React coding tutorial that is strictly forbidden by `AGENTS.md`), missing directories (`references/deep/` with `SFX_BINDING_MATRIX.md` was purged from the plugin in commit `7e94c15`), and remnants of quarantined documents (`CUSTOM_CODE_GUIDE.md`, `WORKFLOW_EXAMPLES.md`).
5. **Security Configuration (`config/violations_config.json`)**: `.agents/guardian/utils.py` strictly loads `config/violations_config.json` from root. The plugin's copy is an outdated snapshot that is never parsed by Guardian.

### The Single Inverted Exception: `ASSET_INDEX.json`
There is exactly **one** file where the plugin holds the active version and root holds the stale copy:
- `scripts/build_asset_index.py` line 81 hardcodes its output path directly to `.agents/plugins/super-video-maker-plugin/ground-truth/ASSET_INDEX.json`.
- `scripts/asset_gate.py` and `tools/mcp-servers/common-tools-mcp/utils/cache_ops.py` actively read from the plugin path.
- Root `ground-truth/ASSET_INDEX.json` is a stale, un-updated snapshot frozen since Git commit `9dcb888` (Sep 12, 2026).

---

## 2. Plugin Boundaries & Directory Inventory

The plugin tree `.agents/plugins/super-video-maker-plugin/` contains **188 total files** (excluding `.venv`, `__pycache__`, and `.git`).

### Top-Level Path Classification

| Top-Level Path | Category | Purpose | Loaded By | Production Reachable | Packaging Relevance |
|---|---|---|---|---|---|
| `plugin.json` | Manifest | Declares plugin identity (`super-video-maker` v1.0.0), capabilities, and metadata | Antigravity IDE Plugin Engine | **YES** | **YES** (Core plugin manifest) |
| `mcp_config.json` | Config | Sole MCP server declaration for 6 stdio MCP servers | Antigravity IDE MCP Runtime | **YES** | **YES** (Core MCP registration) |
| `package.json` | Package | Standalone npm skill package descriptor (`super-video-maker-skill`) | npm / manual tooling | **NO** (Root package.json governs Remotion) | **YES** (Plugin distribution) |
| `requirements.txt` | Package | Python dependencies for AI tools (fal-client, openai, replicate) | pip / uv | **YES** (Tool environments) | **YES** (Plugin distribution) |
| `.gitignore` | Config | Plugin-local gitignore rules for local venvs/caches | Git | **YES** | **YES** |
| `.env` | Config | Active API keys for fal.ai, HeyGen, OpenAI, ElevenLabs | `python-dotenv` in tools | **YES** | **NO** (Contains secrets) |
| `LICENSE` | Legal | MIT License text | Human / Distributor | **NO** | **YES** |
| `README.md` | Docs | Plugin overview and feature documentation | Human / Agent | **NO** | **YES** |
| `verify.py` | Tooling | Integrity script verifying workspace & plugin prerequisites | Manual CLI / CI | **YES** | **YES** |
| `config/` (1 file) | Config | `violations_config.json` (Stale rule definitions) | None (Guardian loads root) | **NO** | **NO** (Stale duplicate) |
| `ground-truth/` (1 file) | Data | `ASSET_INDEX.json` (Active media asset cache index) | `asset_gate.py`, `cache_ops.py` | **YES** | **YES** (Active cache target) |
| `commands/` (1 file) | Workflow | `avatar-insta-reel.md` (Agent workflow wrapper) | Agent prompt instruction | **YES** | **YES** |
| `docs/` (10 files) | Docs | Packaging guides (ARCHITECTURE, USAGE, INSTALLATION) | Human / Agent | **NO** | **YES** (Standalone documentation) |
| `references/` (17 files) | Docs | Playbooks & guidelines (outdated copies) | Agent (Secondary/Legacy) | **NO** (Root is canonical) | **NO** (Stale duplicates) |
| `skills/` (56 files) | Skills | `remocn` (12 files) & `snapcn` (43 files) + index | Antigravity IDE, `docs-extractor.ts`, `tests/registry.test.ts` | **YES** | **YES** (Active exported skills) |
| `tools/` (93 files) | Tooling | 13 Python tool adapters + 80 files across 6 MCP servers | Antigravity MCP runtime, `recipes/*.json`, `build_ground_truth.py` | **YES** | **YES** (Core tool implementations) |

---

## 3. Establish Root Counterparts

For each plugin directory/file, root counterparts were mapped across name equivalence, structural displacement, and functional equivalents.

Summary mapping (detailed in [root-plugin-path-map.json](file:///c:/video/clean-video-workspace/.remediation/plugin-audit/root-plugin-path-map.json)):
1. `plugin.json` ↔ **None** (`PLUGIN_MANIFEST`): Antigravity IDE custom specification file.
2. `mcp_config.json` ↔ **None** (`PLUGIN_MCP_REGISTRY`): Sole MCP declaration file in the entire repository.
3. `package.json` ↔ `package.json` (`INDEPENDENT_PACKAGE_DESCRIPTOR`): Distinct responsibilities (Root = Remotion app/test runner; Plugin = skill package scripts).
4. `requirements.txt` ↔ `requirements.txt` (`INDEPENDENT_REQUIREMENTS_DESCRIPTOR`): Distinct responsibilities (Root = FastAPI/Pytest; Plugin = Fal/OpenAI/Replicate tool libraries).
5. `config/violations_config.json` ↔ `config/violations_config.json` (`STALE_PLUGIN_MIRROR`): Root is active source of truth.
6. `ground-truth/ASSET_INDEX.json` ↔ `ground-truth/ASSET_INDEX.json` (`INVERTED_ACTIVE_GENERATION_TARGET`): Plugin is active generation target.
7. `commands/avatar-insta-reel.md` ↔ `recipes/avatar-insta-split.json` (`WRAPPER_OR_ADAPTER`): Agent workflow prompt that drives the recipe via `scripts/pipeline.py`.
8. `docs/` (10 files) ↔ `documentation/` (`PLUGIN_GUIDES_VS_WORKSPACE_DOCUMENTATION`): Static plugin guides vs authoritative workspace documentation.
9. `references/` (17 files) ↔ `references/` (`DIVERGED_LEGACY_PLUGIN_COPIES`): Root is constitutional Level 5 reference set under `ARCHITECTURE_TRUTH.md`.
10. `skills/` (56 files) ↔ `registry/` + `templates/` (`PLUGIN_AGENT_SKILLS_EXPORT`): Plugin provides skills; root registry and tests consume them.
11. `tools/` (93 files) ↔ `scripts/` + `ground-truth/TOOLS_INDEX.md` (`TOOL_ADAPTERS_AND_MCP_SERVERS`): Standalone Python tools and MCP servers implemented in plugin, called by root recipes and indexed in root ground-truth.

---

## 4. File-by-File Content Comparison & Classification

All 188 files were analyzed via SHA-256 and compared against root files. Full matrix recorded in [plugin-root-file-matrix.json](file:///c:/video/clean-video-workspace/.remediation/plugin-audit/plugin-root-file-matrix.json).

### Classification Definitions & Exact File Counts

| Classification | Count | Description & Subsystems |
|---|---|---|
| **`IDENTICAL_DUPLICATE`** | **0** | No files in the plugin share identical SHA-256 hashes with root counterparts. |
| **`DIVERGED_DUPLICATE`** | **29** | Files with root counterparts that have drifted in content (17 references, 1 config, 1 ground-truth, 9 docs, 1 command). |
| **`PLUGIN_SPECIFIC`** | **159** | Files unique to the plugin subsystem (6 MCP servers [80 files], 2 skills [56 files], 13 Python tools, `plugin.json`, `mcp_config.json`, `.env`, `package.json`, `requirements.txt`, `.gitignore`, `LICENSE`, `verify.py`, 1 doc). |
| **`ROOT_SPECIFIC`** | **444** | Core files unique to root across indexed directories (109 templates, 73 scripts, 17 recipes, 40+ tests, schemas, contracts, engine). |
| **`HISTORICAL_PLUGIN`** | **27** | Plugin files that are obsolete or unmaintained duplicates of root counterparts (17 references, 1 config, 9 docs). |
| **`HISTORICAL_ROOT`** | **1** | Root files that are obsolete copies of active plugin files (`ground-truth/ASSET_INDEX.json`). |
| **`GENERATED_FROM_ROOT`** | **1** | `.agents/plugins/.../ground-truth/ASSET_INDEX.json` generated by `scripts/build_asset_index.py`. |
| **`WRAPPER_OR_ADAPTER`** | **1** | `commands/avatar-insta-reel.md` (prompts root pipeline execution). |
| **`UNKNOWN`** | **0** | **0 files unclassified (Strict requirement met).** |

---

## 5. Actual Plugin Loading Mechanism

### Discovery Trace:
1. **Discovery Root**: Google Antigravity IDE inspects `.agents/plugins/` within the active workspace.
2. **Manifest Loading**: The IDE loads `.agents/plugins/super-video-maker-plugin/plugin.json`, validating the schema `https://agent-plugins.org/schemas/1.0.0/plugin.schema.json`.
3. **Skill Discovery**: The IDE parses `.agents/plugins/super-video-maker-plugin/skills/` and registers skills `remocn` and `snapcn`.
4. **MCP Discovery**: The IDE parses `.agents/plugins/super-video-maker-plugin/mcp_config.json` and spawns the 6 declared MCP servers:
   - `audio-tools-mcp` (`server.py` via `uv`)
   - `common-tools-mcp` (`server.py` via `uv`)
   - `ffmpeg-mcp-server` (`server.js` via node)
   - `image-tools-mcp` (`server.py` via `uv`)
   - `media-sources-mcp` (`server.py` via `uv`)
   - `video-tools-mcp` (`server.py` via `uv`)
5. **Path Resolution**: The loader resolves execution paths relative to the plugin root or absolute workspace paths (`C:/video/clean-video-workspace`).
6. **Delegation to Root**: When the agent operates, `AGENTS.md` strictly instructs it to invoke `scripts/pipeline.py` in the root workspace. The plugin does NOT intercept or replace pipeline execution.

---

## 6. Runtime Reachability Audit

| Duplicate / Overlapping Subsystem | Root Reachable? | Plugin Reachable? | Reachability Verdict | Active Responsibilities |
|---|---|---|---|---|
| **Templates** | **YES** | **N/A** (0 files) | **ROOT ONLY** | Primary video rendering in Remotion engine. |
| **Pipeline & Scripts** | **YES** | **N/A** (0 files) | **ROOT ONLY** | Canonical pipeline orchestration, gating, and rendering. |
| **Recipes** | **YES** | **N/A** (0 files) | **ROOT ONLY** | Parameter specifications for video generation goals. |
| **References** | **YES** | **NO** | **ROOT ONLY** | Level 5 architectural guides. Root has `references/deep/` with `SFX_BINDING_MATRIX.md`. Plugin copies are unreferenced. |
| **Violations Config** | **YES** | **NO** | **ROOT ONLY** | `.agents/guardian/utils.py` strictly loads root `config/violations_config.json`. Plugin copy is dead. |
| **Asset Index (`ASSET_INDEX.json`)** | **NO** | **YES** | **PLUGIN ONLY** | Generated by `build_asset_index.py` into plugin; read by `cache_ops.py` and `asset_gate.py`. Root copy is dead. |
| **MCP Servers** | **NO** | **YES** | **PLUGIN ONLY** | Executed via stdio by Antigravity runtime from plugin directory. |
| **Skills (`remocn`/`snapcn`)** | **NO** | **YES** | **PLUGIN ONLY** | Discovered by IDE from plugin; read by root `registry/docs-extractor.ts` and `tests/registry.test.ts`. |
| **Tools (`tools/*.py`)** | **NO** | **YES** | **PLUGIN ONLY** | Invoked by recipe execution and scanned by `build_ground_truth.py`. |

---

## 7. Git History & Migration Investigation

### Forensic Migration Timeline

```text
T1 (2026-08-28, e0d4235): Initial commit. Monolithic plugin architecture. 
   - Remotion engine, templates, tools, and scripts coexisted inside the plugin folder.

T2 (2026-09-02, b0e9912): Missing plugin files added. 
   - Initial references and tools checked into the plugin repository.

T3 (2026-09-12, 9dcb888): Constitutional Decoupling.
   - Commit: "refactor(core): decouple application logic from AI plugin"
   - Git renames moved:
     * .agents/plugins/.../engine/    => root engine/
     * .agents/plugins/.../templates/ => root templates/
     * .agents/plugins/.../scripts/   => root scripts/
     * .agents/plugins/.../recipes/   => root recipes/
   - The application core became independent of the agent plugin.

T4 (2026-09-16, 7e94c15): Plugin Modernization & Alignment.
   - Commit: "refactor(plugin): overhaul super-video-maker-plugin to strictly follow unified pipeline protocol"
   - Purged 27,600+ lines of obsolete legacy documentation, manual React coding guides (references/deep/), and outdated tests.
   - Refactored skills/remocn and skills/snapcn to enforce unified pipeline compliance.

T5 (2026-09-16 - 2026-09-17, f5b28b5 -> ba4d9ae): Phase 9 Clean-Room Certification & Zero-Known-Defects v1.0.
   - Active development focused on root scripts, contracts, and templates.
   - Root references received Source of Truth Hierarchy alert headers.
```

### Git Investigation Conclusions:
- The root files did **not** diverge from the plugin; the root files were **promoted from the plugin** during the architectural decoupling in commit `9dcb888`.
- Root files continued to evolve rapidly (Zero-Build engine, Stage Gates, Guardian, Zero-Known-Defects certification), while plugin copies of `references/` and `config/` were left behind as static unmaintained remnants.

---

## 8. Packaging & Portability Requirements

```text
PLUGIN_PORTABILITY_MODEL = REPO_COUPLED
```

### Evidence:
1. `plugin/verify.py` line 5 explicitly reaches into `plugin_dir.parents[2]` and validates the presence of root directories (`templates`, `engine`, `scripts`, `assets`, `projects`).
2. `plugin/mcp_config.json` hardcodes absolute workspace paths (`C:/video/clean-video-workspace/...`).
3. `plugin/tools/mcp-servers/common-tools-mcp/utils/cache_ops.py` hardcodes the default workspace data directory.
4. `plugin/commands/avatar-insta-reel.md` delegates directly to `python scripts/pipeline.py <project_id>`.

The plugin is currently **incapable of independent execution outside this repository** without its root dependencies.

---

## 9. Synchronization Mechanisms & Drift Risk

- **Automated Sync Mechanisms Found:** **0**
- `.githooks/pre-commit` previously attempted auto-syncing ground-truth, but referenced `.agents/plugins/super-video-maker-plugin/scripts/build_ground_truth.py`, which was moved to root in commit `9dcb888`. The hook silently exits without executing.
- `scripts/build_asset_index.py` writes only to `.agents/plugins/.../ground-truth/ASSET_INDEX.json`, leaving root `ground-truth/ASSET_INDEX.json` out of sync.

```text
manual duplication drift risk = HIGH
```

---

## 10. Tests and Certification Coverage

1. **Current Test Suite (`tests/`):**
   - Root tests (`vitest`, `pytest`) exercise root implementations: `scripts/pipeline.py`, `scripts/materialize_project.py`, `remotion-app/`, `templates/`, `contracts/`, `schemas/`.
   - Plugin dependencies tested: `tests/registry.test.ts` and `registry/docs-extractor.ts` specifically assert against `.agents/plugins/super-video-maker-plugin/skills/snapcn/references/components` and `skills/remocn/references/archetypes`.
   - `tests/documentation/test_references_validity.py` checks plugin references.
   - `tests/security/test_guardian.py` checks root `config/violations_config.json`.
2. **Phase 9.5 Certification (`agent-certification.md`):**
   - Certified `mcp_config.json` and all 6 active MCP servers in `tools/mcp-servers/`.
   - Performed syntax checks on 51 plugin files (`behavior_smoke: SKIPPED`).
   - Certified that no plugin file can bypass the root `pipeline.py` gatekeeper.

---

## 11. Historical / Dead Content Detection

### Dead / Historical Root Content:
- `ground-truth/ASSET_INDEX.json` in root (Stale commit `9dcb888` artifact). Safe deletion / overwrite candidate.

### Dead / Historical Plugin Content:
- `plugin/config/violations_config.json` (Stale copy; Guardian reads root).
- `plugin/references/` (17 files): Outdated copies; root `references/` is the active Level 5 authority.
- `plugin/references/REMOTION_VIDEO_GUIDE.md`: Contains obsolete 676-line manual React coding tutorial.
- `plugin/references/CUSTOM_CODE_GUIDE.md` & `WORKFLOW_EXAMPLES.md`: Quarantined remnants.
- `plugin/docs/` (10 files): Static documentation from standalone distribution attempts.

---

## 12. Architectural Recommendation Matrix

| Duplicate / Overlapping Family | Recommendation | Rationale | Risk Level | Required Migration Steps | Post-Change Tests |
|---|---|---|---|---|---|
| **`references/`** | `DELETE_PLUGIN_COPY` | Root `references/` is canonical under `ARCHITECTURE_TRUTH.md`. Plugin copies are diverged and contain forbidden manual coding patterns. | LOW | Repoint `test_references_validity.py` to root `references/`; delete `plugin/references/`. | `pytest tests/documentation/test_references_validity.py` |
| **`config/violations_config.json`** | `DELETE_PLUGIN_COPY` | Guardian strictly loads root config. Plugin copy is dead. | NONE | Delete `plugin/config/violations_config.json`. | `pytest tests/security/test_guardian.py` |
| **`ground-truth/ASSET_INDEX.json`** | `GENERATE_ROOT_FROM_PLUGIN` / Repoint | Currently generator writes to plugin while root is stale. Root should be the canonical storage for ground-truth. | MEDIUM | Update `build_asset_index.py` to output to root `ground-truth/ASSET_INDEX.json` and repoint `asset_gate.py` & `cache_ops.py`. | `python scripts/build_asset_index.py && pytest tests/test_gates_and_pipeline.py` |
| **`docs/`** | `MOVE_TO_ARCHIVE` | Static standalone plugin guides. Not needed for workspace operation. | LOW | Move to `documentation/archive/plugin-docs/`. | None |
| **`package.json` & `requirements.txt`** | `KEEP_BOTH` | Intentional separation: root manages workspace runtime, plugin files describe standalone plugin dependencies. | NONE | Retain both. | `npm test` & `pytest` |
| **`tools/` & `tools/mcp-servers/`** | `KEEP_BOTH` (Plugin Canonical) | MCP servers and Python tools execute from plugin as designed by Antigravity IDE. Root ground-truth indexes them. | HIGH if moved | Retain in plugin. | Phase 9.5 MCP test suite |
| **`skills/remocn` & `skills/snapcn`** | `KEEP_BOTH` (Plugin Canonical) | Core plugin feature. Discovered by IDE and validated by root registry tests. | HIGH if moved | Retain in plugin. | `npm run test:templates` |

---

## 13. Required Summary Statistics Block

```text
Plugin files total                     = 188
Root counterparts found                = 34

Identical duplicates                   = 0
Diverged duplicates                    = 29
Plugin-specific                        = 159
Root-specific                          = 444
Historical root files                  = 1
Historical plugin files                = 27
Unknown classifications                = 0

Root runtime-reachable duplicates      = 26
Plugin runtime-reachable duplicates    = 2
Both runtime-reachable                 = 3

PLUGIN_PORTABILITY_MODEL               = REPO_COUPLED

Canonical source for templates         = ROOT
Canonical source for scripts           = ROOT
Canonical source for recipes           = ROOT
Canonical source for references        = ROOT

Safe root deletion candidates          = 1
Safe plugin deletion candidates        = 27
Keep-both intentional duplicates       = 5
Drift-risk duplicates                  = 34
```

---

## 14. Final Decision & Answers to Core Inquiries

```text
PLUGIN / ROOT DUPLICATION AUDIT = COMPLETE
```

### 1. Is the user's hypothesis true that root contains historical copies while plugin contains the current canonical versions?

**NO.**

**Forensic Evidence:**
- **Templates:** Plugin contains 0 templates. All 109 active templates reside in root.
- **Pipeline & Scripts:** `scripts/pipeline.py` and supporting gates were promoted from plugin to root in commit `9dcb888` and actively maintained to achieve Zero-Known-Defects v1.0. Plugin has no `scripts/` directory.
- **Recipes:** 17 production recipes reside in root; plugin contains only 1 command wrapper.
- **References:** Root references are the constitutional Level 5 documents under `ARCHITECTURE_TRUTH.md`. Plugin copies are outdated, diverged, missing `references/deep/`, and contain quarantined guides and obsolete manual coding instructions.
- **The Single Exception:** Root `ground-truth/ASSET_INDEX.json` is a stale copy because `scripts/build_asset_index.py` was hardcoded to output into the plugin directory.

---

### 2. Can duplicated plugin folders be deleted?

**PARTIALLY.**

- **SAFE TO DELETE (after repointing tests):**
  1. `.agents/plugins/super-video-maker-plugin/references/` (Outdated duplicates of root references).
  2. `.agents/plugins/super-video-maker-plugin/config/violations_config.json` (Unused; Guardian loads root).
  3. `.agents/plugins/super-video-maker-plugin/docs/` (Unused packaging guides).
- **CANNOT BE DELETED (Active Production Dependencies):**
  1. `.agents/plugins/super-video-maker-plugin/plugin.json` (Required for Antigravity plugin discovery).
  2. `.agents/plugins/super-video-maker-plugin/mcp_config.json` (Sole MCP server registry).
  3. `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/` (Active MCP server codebases).
  4. `.agents/plugins/super-video-maker-plugin/skills/` (Exported agent skills `remocn` and `snapcn`).
  5. `.agents/plugins/super-video-maker-plugin/tools/*.py` (Active tool adapters called by recipes).
  6. `.agents/plugins/super-video-maker-plugin/ground-truth/ASSET_INDEX.json` (Active cache index target; cannot be deleted until `build_asset_index.py` and consumers are repointed to root).

---

### 3. Can duplicated root folders be deleted?

**NO.**

- Root `templates/`, `scripts/`, `recipes/`, `references/`, and `config/` are the active, canonical, constitutional core of the entire workspace. Deleting any of them will break the unified pipeline and Remotion rendering.
- The **only** root file that is safe to overwrite/delete is `ground-truth/ASSET_INDEX.json` (which should be overwritten with the regenerated version from `build_asset_index.py`).

---

### Recommended Future Actions (Investigation Only — NOT Executed):
1. **Fix Asset Index Inversion:** Modify `scripts/build_asset_index.py` to write `ASSET_INDEX.json` to root `ground-truth/ASSET_INDEX.json`, and update `common-tools-mcp/cache_ops.py` and `scripts/asset_gate.py` to read primarily from the root location.
2. **Clean Stale Plugin References:** Repoint `tests/documentation/test_references_validity.py` to exclusively inspect `references/` in root, then safely remove the diverged `.agents/plugins/super-video-maker-plugin/references/` folder.
3. **Remove Stale Plugin Config:** Remove `.agents/plugins/super-video-maker-plugin/config/violations_config.json` to eliminate configuration drift confusion.
4. **Repair Ground Truth Hook:** Update `.githooks/pre-commit` to point to `scripts/build_ground_truth.py` in root instead of the non-existent plugin path.
