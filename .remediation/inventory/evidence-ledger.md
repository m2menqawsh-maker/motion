# Final Classification & Evidence Ledger
**Phase 1.6: System-wide Triage**

This ledger formalizes the decisions and evidence gathered across Phase 1.

## 1. Security Risks (Immediate Action Required)
- **`Video_Editor_MCP` (Server)**
  - *Status:* `security-risk`
  - *Evidence:* Contains `execute_command` which allows arbitrary subprocess execution (RCE).
  - *Decision:* Must be deleted and replaced with `ffmpeg-mcp-server`.
- **`workflows/` (Rebel Agents)**
  - *Status:* `security-risk`
  - *Evidence:* Scripts like `avatar-insta-split/` manually execute `ffmpeg` and bypass the official `pipeline.py`.
  - *Decision:* Quarantine or delete entirely.

## 2. Quarantined (Zombie Systems)
- **`scripts/core/pipeline.py` & `scripts/gates/`**
  - *Status:* `quarantined`
  - *Evidence:* Creates a parallel pipeline using `state.json` instead of `.pipeline_state.json`. Never intersects with the main CLI.
  - *Decision:* Delete or quarantine to force unification on `scripts/pipeline.py`.
- **`engine/` (Disconnected Core)**
  - *Status:* `quarantined`
  - *Evidence:* Static dependency map shows 0 incoming imports for core engine layout, camera, and primitive components. The `BlueprintVideo.tsx` bridge is completely gutted.
  - *Decision:* Delete or quarantine.
- **112 Motion Primitives**
  - *Status:* `quarantined`
  - *Evidence:* Only 7 primitives are used out of 119. The rest are dead code.
  - *Decision:* Move to `archive/primitives/`.
- **Zombie Standalone Tools**
  - *Status:* `quarantined`
  - *Evidence:* `demo_video_composer.py`, `video_orchestrator.py`, `ugc_ad_runner.py` are dead.

## 3. Needs Update (Active but Misaligned)
- **`api/services/render_service.py` & `api/services/gate_service.py`**
  - *Status:* `needs-update`
  - *Evidence:* Still trying to import `UnifiedPipeline` from `scripts/core/` and writing to `state.json`.
  - *Decision:* Must be patched to call the official `scripts/pipeline.py` and read `.pipeline_state.json`.
- **`AGENTS.md`**
  - *Status:* `needs-update`
  - *Evidence:* Missing strict rules about the API unification.

## 4. Active (Healthy Single Source of Truth)
- **`scripts/pipeline.py`**: The official orchestrator.
- **`registry/template-registry.tsx`**: 87 templates registered perfectly.
- **`recipes/`**: 20 valid schema-compliant recipes.
- **`references/`**: Clean agent protocols (e.g. `ROUTER.md`, `PLAN_TEMPLATE.md`).
- **`ffmpeg-mcp-server`**: Safe MCP.
