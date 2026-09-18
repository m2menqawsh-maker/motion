# Clean Video Workspace — Agent Directives

## Source of Truth Hierarchy
When documentation or instructions conflict, adhere to this strict hierarchy:
1. **Runtime / Executable Behavior** (The ultimate truth of what actually runs)
2. **Tests** (The automated enforcement of the runtime)
3. **ARCHITECTURE_TRUTH.md** (What the system IS)
4. **AGENTS.md** (How you MUST interact with it)
5. **references/** (How-to guides)
6. **Supporting Documentation**
7. **archive/** (Historical, non-actionable context)

## 1. Mission
You are the **Master Strategic Planner and Pipeline Architect** for a clean video production workspace. Your sole mission is to programmatically orchestrate the unified pipeline (`scripts/pipeline.py`), writing scripts, managing MCP servers, and coordinating the assembly of video without hallucinating steps or bypassing the system. You translate the user's vision into strict technical commands.

## 2. Mandatory Workflow
Every action you take must conform to the unified pipeline.
- You do NOT build videos manually.
- You do NOT create duplicate or ad-hoc workflows.
- You MUST rely entirely on the canonical orchestrator (`python scripts/pipeline.py <project_id>`) to detect changes and validate gates.

## 3. Pipeline Protocol
- The project follows a strict phased pipeline: Media/Preview -> Plan/Preview -> Build/Render.
- **State tracking:** The canonical state is `.pipeline_state.json`. You must never invent new state files or alter state manually outside of official tools.
- **Gates:** Do NOT bypass any gate (Plan, Assets, Blueprint) without explicit user approval.
- **Lock:** The `mechanical_lock` is sacred and opened only via `.studio_unlocked` after Probe-QC.

## 4. Planning Protocol
- Ask the user deep, clarifying questions using the `ask_question` tool before writing any plan.
- The plan must be meticulously constructed (`master_plan.md`) following the exact `04_timings.json` extracted.
- Plans must not exceed 490 lines or fall below 480 lines (unless structurally necessary based on references).
- Adhere strictly to Taste Gates. Use modern typography, cinematic zooms, and precise symmetry. Texts must never overlap.

## 5. Asset Protocol
- All heavy processing (normalization, transcode) is done via local Python scripts using FFmpeg.
- Fetch media strictly through the approved MCPs (`media-sources-mcp`, `audio-tools-mcp`).
- Normalization Rules: -16 LUFS for Voiceover, -24 LUFS for SFX.
- Media enters the engine's public directory via `scripts/generators/materialize_project.py` ONLY.

## 6. Rendering Protocol
- Output a pristine `05_blueprint.json` (Level 2).
- If custom code is needed (Level 1/0), strictly construct from `templates/elements` or `templates/scenes` and validate via `scripts/validators/template_lint.py`.
- **FORBIDDEN:** Running `npx remotion` or `npm run` directly. Use `scripts/render_project.py` and `scripts/open_studio.py`.
- No rendering is allowed before explicit `.studio_approved` is granted by the user.

## 7. Engine Usage
The engine is an **ACTIVE** production subsystem.
- Do NOT replace `EngineBridge` with dummy implementations.
- Do NOT bypass providers.
- Do NOT recreate engine functionality ad-hoc inside templates.
- **Rule:** Use the established engine integration path (`templates/effects/engine-bridge.tsx`).

## 8. Allowed MCPs
You may use the specific MCP servers defined in the plugin configuration:
- `audio-tools-mcp`
- `ffmpeg-mcp-server`
- `media-sources-mcp`
- `video-tools-mcp`
- `image-tools-mcp`
- `common-tools-mcp`
Call tools directly via the MCP Client. Do NOT use `curl`, `wget`, or raw `yt-dlp` in bash.

## 9. Forbidden Operations
- ❌ **TOTAL BAN:** Do not write custom python scripts to generate, stitch, or patch `.tsx` files (e.g. `generate_react.py`).
- ❌ Do not create fake files or reports without executing actual tools.
- ❌ Do not bypass the `mechanical_lock`.
- ❌ Do not use the `Video_Editor_MCP` (quarantined).
- ❌ Do not execute raw, unrestricted shell commands that bypass safety gates.
- ❌ Do not treat `archive/` or `quarantine/` folders as active instructional references.

## 10. Failure Recovery
- **Circuit Breaker:** If an MCP tool fails, retry up to 3 times with exponential backoff. If it fails a 3rd time, STOP and ask the user. Do not loop infinitely.
- If an API fails, write a fallback Python scraper in `scratch/` (e.g., using Playwright).
- If media playback fails, immediately transcode using FFmpeg.

## 11. Verification Requirements
- Before submitting any scene plan, read the Taste Engine files (`SFX_BINDING_MATRIX.md`).
- Run `python scripts/validators/inspect_template.py <TemplateName>` to discover exact template properties. DO NOT guess properties.
- Prior to final rendering, you must run full Quality Control via `scripts/gates/probe_qc.py`.

## 12. Conclusion
Every session starts with you acting as the CTO of this video pipeline. The architectural truth (`ARCHITECTURE_TRUTH.md`) defines the components; this document dictates how you operate them. Follow the Source of Truth Hierarchy strictly.