# Quarantine Log - Deprecated Pipeline Systems

## Why were these files isolated?
These files represent the legacy "UnifiedPipeline" and its synchronous gate system (`scripts/core/` and `scripts/gates/`). 

They have been deprecated and quarantined because:
1. **Tight Coupling to GUI State:** The old pipeline read and wrote directly to `state.json`, which was deeply coupled to the Next.js GUI. This caused desync issues where the backend (Agent) and frontend (GUI) overwrote each other's state.
2. **Synchronous Execution Blockers:** The legacy gates were synchronous python scripts executed via `subprocess`, making error handling opaque and failing to fit into a unified API structure (like FastAPI).
3. **Redundancy:** We have introduced `PipelineService` (in `api/services/pipeline_service.py`) and a new `scripts/pipeline.py` orchestration script that replaces all these legacy systems, keeping a clear boundary using `.pipeline_state.json`.

## Re-integration Policy
**DO NOT USE THESE FILES.** If you need pipeline logic, use `PipelineService`. If you need to validate a project, use `scripts/pipeline.py`.
