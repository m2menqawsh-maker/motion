# Clean Video Workspace - System Overview

## 1. Introduction
The Clean Video Workspace is an automated, AI-driven video production pipeline that relies strictly on local scripts, Remotion for building, and FFmpeg for processing, while orchestrating external tools via MCPs (Model Context Protocol).

## 2. Core Architecture
The system consists of 10 primary layers:
1. **Infrastructure**: `projects/`, `.agents/`, `plugins/`, `templates/`.
2. **Core Scripts**: The backbone of the operations located in `.agents/plugins/super-video-maker-plugin/scripts/`. Includes scripts like `pipeline_guard.py` and `process_media.py`.
3. **Gates & Guards**: Validation layers like `plan_gate.py`, `probe_qc.py`, and `smart_qc.py` that enforce the protocol.
4. **Configuration**: Centrally managed by `.agents/config.yaml`.
5. **Documentation**: Extensive guidelines and rules located in `.agents/rules/` and the root folder.
6. **Testing**: Basic unit testing capabilities (Needs expansion).
7. **Performance Profiling**: Tracks script execution times and logs them in `.agents/performance_log.json`.
8. **Error Tracking**: Collects errors contextually via `UnifiedLogger`.
9. **MCP Integration**: Relies on 7 specialized MCP servers for audio, media, and video processing.
10. **Edge Cases & Resilience**: Designed to fail gracefully when assets or configurations are missing.

## 3. Workflow Summary
A video goes through the following stages:
- **Phase 1**: Planning & Scripting (Generates `01_plan.md`)
- **Phase 2**: Media Gathering (MCPs & local caching)
- **Phase 3**: Processing (FFmpeg normalization)
- **Phase 4**: Timings & Blueprint (Timing calculations)
- **Phase 5**: Building (Remotion components generation via React)
- **Phase 6**: QC & Render (Quality control gates & final MP4 output)

## 4. Key Enforcements
- Direct `npm` or `npx` commands are intercepted and blocked by Guardian.
- All actions must pass the `PipelineGuard` and specific gates before proceeding.
- The pipeline is strict: Zero hallucination, local-first processing, and mandatory manual approvals at specific gates.
