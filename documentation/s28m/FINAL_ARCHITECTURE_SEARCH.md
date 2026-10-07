# Final Architecture Search Audit Evidence (S28-M11)

**Milestone**: S28-M11 — Full Product E2E + Final Architecture Gate  
**Scan Date**: 2026-10-05  
**Inspection Scope**: Entire Repository (`ai/`, `creative_governance/`, `recipes/`, `skills/`, `.agents/.../mcp-servers/`)  
**Status**: ALL GUARDS PASSED (0 Critical Violations)  

---

## 1. Automated Scan Summary

| Check ID | Architectural Invariant | Scanned Scope | Matches | Classification | Status |
|---|---|---|:---:|---|:---:|
| ARCH-SCAN-01 | CreativePlanner -> raw MCP | `['ai/planning', 'creative_governance']` | 0 | CLEAN (0 Matches) | **PASS** |
| ARCH-SCAN-02 | Recipe -> Provider Name as Execution Authority | `['recipes']` | 0 | CLEAN (0 Matches) | **PASS** |
| ARCH-SCAN-03 | Skill -> Raw MCP Transport | `['ai/skills', 'skills']` | 0 | CLEAN (0 Matches) | **PASS** |
| ARCH-SCAN-04 | AI Subsystem -> Arbitrary Shell Execution | `['ai/planning', 'ai/skills', 'ai/routing']` | 0 | CLEAN (0 Matches) | **PASS** |
| ARCH-SCAN-05 | AI Subsystem -> Direct FFmpeg Command Generation | `['ai/planning', 'ai/skills', 'recipes']` | 0 | CLEAN (0 Matches) | **PASS** |
| ARCH-SCAN-06 | MCP -> Canonical Lifecycle Mutation Bypass | `['.agents/plugins/super-video-maker-plugin/tools/mcp-servers', 'ai/mcp']` | 0 | CLEAN (0 Matches) | **PASS** |
| ARCH-SCAN-07 | MCP -> Canonical Registry Mutation Bypass | `['.agents/plugins/super-video-maker-plugin/tools/mcp-servers', 'ai/mcp']` | 0 | CLEAN (0 Matches) | **PASS** |
| ARCH-SCAN-08 | MCP -> Direct Cross-Tenant StorageService Bypass | `['.agents/plugins/super-video-maker-plugin/tools/mcp-servers', 'ai/mcp']` | 0 | CLEAN (0 Matches) | **PASS** |
| ARCH-SCAN-09 | Domain Services -> Compatibility MCP Dependency | `['ai/media_processing', 'ai/image_processing', 'ai/speech', 'ai/acquisition']` | 0 | CLEAN (0 Matches) | **PASS** |
| ARCH-SCAN-10 | Model Capability Route Inversion | `['ai/routing', 'ai/tools']` | 0 | CLEAN (0 Matches) | **PASS** |
| ARCH-SCAN-11 | Tool Capability Route Inversion | `['ai/routing']` | 0 | CLEAN (0 Matches) | **PASS** |
| ARCH-SCAN-12 | AI -> Direct Project Filesystem Mutation | `['ai/planning']` | 0 | CLEAN (0 Matches) | **PASS** |

---

## 2. In-Depth Boundary Audit Details

### ARCH-SCAN-01 — CreativePlanner -> raw MCP
**Description**: Internal AI planners must not directly bind to raw MCP transport sessions.
**Regex Pattern**: `(ClientSession|stdio_client|sse_client|mcp_tools|call_tool)`
**Scope Directories**: `['ai/planning', 'creative_governance']`
**Result**: 0 match(es) detected.
> [!NOTE]
> Zero matches detected in target production codebase. Boundary invariant fully upheld.


### ARCH-SCAN-02 — Recipe -> Provider Name as Execution Authority
**Description**: Recipes must declare capabilities or abstract requirements, never vendor provider names as execution authority.
**Regex Pattern**: `(\"provider\"\s*:\s*\"(openai|anthropic|elevenlabs|pexels|pixabay|whisper)\"|\"model_provider\"\s*:)`
**Scope Directories**: `['recipes']`
**Result**: 0 match(es) detected.
> [!NOTE]
> Zero matches detected in target production codebase. Boundary invariant fully upheld.


### ARCH-SCAN-03 — Skill -> Raw MCP Transport
**Description**: AI Skills must dispatch via CapabilityRouter or ToolGateway, not raw MCP transport.
**Regex Pattern**: `(ClientSession|stdio_client|sse_client|FastMCP)`
**Scope Directories**: `['ai/skills', 'skills']`
**Result**: 0 match(es) detected.
> [!NOTE]
> Zero matches detected in target production codebase. Boundary invariant fully upheld.


### ARCH-SCAN-04 — AI Subsystem -> Arbitrary Shell Execution
**Description**: AI reasoning layers must not invoke host OS shells or unconstrained subprocesses.
**Regex Pattern**: `(os\.system\(|subprocess\.Popen\(|subprocess\.run\(|subprocess\.check_call\()`
**Scope Directories**: `['ai/planning', 'ai/skills', 'ai/routing']`
**Result**: 0 match(es) detected.
> [!NOTE]
> Zero matches detected in target production codebase. Boundary invariant fully upheld.


### ARCH-SCAN-05 — AI Subsystem -> Direct FFmpeg Command Generation
**Description**: AI planners and recipes must not emit raw ffmpeg CLI strings; FFmpeg is strictly encapsulated in FFmpegAdapter.
**Regex Pattern**: `(\"ffmpeg\s+-i|ffmpeg\s+-[a-zA-Z]|shlex\.split\(.*ffmpeg)`
**Scope Directories**: `['ai/planning', 'ai/skills', 'recipes']`
**Result**: 0 match(es) detected.
> [!NOTE]
> Zero matches detected in target production codebase. Boundary invariant fully upheld.


### ARCH-SCAN-06 — MCP -> Canonical Lifecycle Mutation Bypass
**Description**: External MCP layers must not directly mutate project lifecycle states.
**Regex Pattern**: `(project_lifecycle\.(transition|update|set_state)|lifecycle_service\.transition|manifest\.status\s*=)`
**Scope Directories**: `['.agents/plugins/super-video-maker-plugin/tools/mcp-servers', 'ai/mcp']`
**Result**: 0 match(es) detected.
> [!NOTE]
> Zero matches detected in target production codebase. Boundary invariant fully upheld.


### ARCH-SCAN-07 — MCP -> Canonical Registry Mutation Bypass
**Description**: External MCP servers must not alter canonical capability catalog registrations.
**Regex Pattern**: `(\.register_capability\(|\.unregister_capability\(|catalog\.register|registry\.register)`
**Scope Directories**: `['.agents/plugins/super-video-maker-plugin/tools/mcp-servers', 'ai/mcp']`
**Result**: 0 match(es) detected.
> [!NOTE]
> Zero matches detected in target production codebase. Boundary invariant fully upheld.


### ARCH-SCAN-08 — MCP -> Direct Cross-Tenant StorageService Bypass
**Description**: MCP layers must not escape storage confinement or access cross-tenant data.
**Regex Pattern**: `(storage_service\.(get|put|delete)\([^)]*(\.\.|\/etc|\/var))`
**Scope Directories**: `['.agents/plugins/super-video-maker-plugin/tools/mcp-servers', 'ai/mcp']`
**Result**: 0 match(es) detected.
> [!NOTE]
> Zero matches detected in target production codebase. Boundary invariant fully upheld.


### ARCH-SCAN-09 — Domain Services -> Compatibility MCP Dependency
**Description**: Core Domain Services must never depend on external/compatibility MCP layers.
**Regex Pattern**: `(from ai\.mcp|import ai\.mcp|MCPCompatibilityFacade|CompatibilityMCPServer)`
**Scope Directories**: `['ai/media_processing', 'ai/image_processing', 'ai/speech', 'ai/acquisition']`
**Result**: 0 match(es) detected.
> [!NOTE]
> Zero matches detected in target production codebase. Boundary invariant fully upheld.


### ARCH-SCAN-10 — Model Capability Route Inversion
**Description**: SPEECH_TO_TEXT must route exclusively through ModelRouter, never as a ToolGateway hack.
**Regex Pattern**: `(CapabilityType\.SPEECH_TO_TEXT.*ToolGateway|execute_model_capability.*ToolGateway)`
**Scope Directories**: `['ai/routing', 'ai/tools']`
**Result**: 0 match(es) detected.
> [!NOTE]
> Zero matches detected in target production codebase. Boundary invariant fully upheld.


### ARCH-SCAN-11 — Tool Capability Route Inversion
**Description**: Deterministic tool capabilities must route to ToolGateway, never ModelRouter.
**Regex Pattern**: `(CapabilityType\.(TRIM_VIDEO|PROBE_MEDIA|RESIZE_IMAGE).*ModelRouter)`
**Scope Directories**: `['ai/routing']`
**Result**: 0 match(es) detected.
> [!NOTE]
> Zero matches detected in target production codebase. Boundary invariant fully upheld.


### ARCH-SCAN-12 — AI -> Direct Project Filesystem Mutation
**Description**: AI planning components must not directly write project files bypassing AssetService/StorageService.
**Regex Pattern**: `(open\(.*[\"\x27]w[\"\x27]|Path\(.*\)\.write_text|Path\(.*\)\.write_bytes)`
**Scope Directories**: `['ai/planning']`
**Result**: 0 match(es) detected.
> [!NOTE]
> Zero matches detected in target production codebase. Boundary invariant fully upheld.


---

## 3. Human-Readable Recipe Provider Audit (Section 23)

A broad scan of `recipes/` for informal vendor names (e.g. `Whisper`, `ElevenLabs`, `Pexels`) revealed occurrences exclusively in narrative descriptions and human documentation strings (e.g. recipe `description` fields explaining visual intent).

**Audit Finding**: NONE of these strings act as execution authority. When executed by the S28 Creative Intelligence engine, recipes emit abstract `CapabilityRequest` objects (e.g. `CapabilityType.SPEECH_TO_TEXT`, `CapabilityType.SEARCH_STOCK_VIDEO`), which are resolved dynamically by `CapabilityRouter` without caller-controlled vendor routing. This strictly complies with ADR-002 and S28 provider neutrality.

## 4. Conclusion

The repository-wide architecture scan confirms:
- Zero raw MCP dependencies inside internal AI reasoning.
- Zero shell execution or direct FFmpeg strings inside AI components.
- Zero lifecycle or registry bypasses.
- Full ModelRouter vs ToolGateway architectural category adherence.