# State Readers and Writers Analysis
**Phase 1.4: Static Approximation of Runtime State Access**

## Official Pipeline State (`.pipeline_state.json`)
This is the intended single source of truth (hash-based state).

**Writers:**
- `scripts/pipeline.py` (The main orchestrator)

**Readers:**
- `scripts/pipeline.py`

## Zombie Pipeline State (`state.json`)
This is the legacy/parallel state tracking system (Gate 1, 2, 3 logic).

**Writers:**
- `api/services/gate_service.py` (API currently writes here instead of the official state)
- `scripts/scaffold_project.py` (Initializes it)
- `scripts/gates/plan_report.py`
- `scripts/gates/stage_gate.py`

**Readers:**
- `scripts/gates/checks.py`
- `scripts/validators/validate_schemas.py`
- `tests/gates/test_stage_gate.py` (Extensively tested, showing it was heavily developed before being abandoned)

## Other State Files Found
- `.prep_state.json`: Used by `scripts/core/pipeline.py` (Zombie)
- `.session_state.json`: Used by `scripts/core/session_manager.py`
- `job_state.json`: Heavy usage found in `.json` recipes (e.g., `avatar-explainer.json`) and legacy documentation (`WORKFLOW_EXAMPLES.md`). It seems to be an old workflow standard.

## Architectural Violation Detected
The system suffers from a severe state split. `scripts/pipeline.py` operates entirely on `.pipeline_state.json`, while the API and several gates operate on `state.json`. They do not intersect.
