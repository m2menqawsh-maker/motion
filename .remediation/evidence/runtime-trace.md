# Runtime Subprocess Trace Analysis
**Phase 1.4: Subprocess Execution Graph**

Due to the absence of an integrated test harness and broken execution paths (e.g. pytest is not configured globally), a static trace of all `subprocess` calls was conducted to map what the system actually executes externally.

## Core Services (Legitimate Executions)
- **`scripts/probe_qc.py`**: Executes `ffprobe` and `ffmpeg` for media quality control.
- **`scripts/process_media.py`**: Executes FFmpeg for media normalization.
- **`scripts/open_studio.py`**: Executes `docker info` and Docker container launch commands.
- **`scripts/render_project.py`**: Executes Docker and local npm/Remotion builds.
- **`scripts/pipeline.py`**: Main official pipeline execution.

## Zombie/Rebel Executions (Dangerous)
- **`scripts/core/pipeline.py`**: Executes arbitrary processes as part of the parallel zombie pipeline.
- **`Video_Editor_MCP`**: Contains `execute_command` allowing unchecked arbitrary code execution (RCE).
- **Workflows**: Scripts within `.agents/plugins/super-video-maker-plugin/workflows/` (e.g. `avatar-insta-split`) manually execute `ffmpeg` bypassing the pipeline and gates.
- **Zombie Tools**: `demo_video_composer.py`, `video_orchestrator.py` which are no longer in the active loop.

## Conclusion
The application relies heavily on `subprocess` to bridge Python and external tools (FFmpeg, Docker, Remotion, Git). However, the unchecked execution paths in `Video_Editor_MCP` and `workflows/` present critical security and stability risks. These must be quarantined.
