# DEC-UNI-01: Canonical Pipeline & State

## Context
The project currently suffers from a split-brain architecture where two parallel pipelines and state files coexist:
1. The **Official Pipeline** (`scripts/pipeline.py`) utilizing `.pipeline_state.json`.
2. The **Parallel/Deprecated Pipeline** (`scripts/core/pipeline.py`) utilizing `state.json`.

This divergence causes severe inconsistencies in state management and bypasses official quality gates.

## Decision
Effective immediately, the system will unify under a single pipeline and state mechanism.

### 1. Canonical State
- **Official State**: `.pipeline_state.json`
- **Deprecated State**: `state.json` (Must be completely removed/quarantined)

### 2. Canonical Pipeline Controller
- **Official Pipeline**: `scripts/pipeline.py`
- **Deprecated Pipeline**: `scripts/core/` directory (Will be quarantined)

### 3. Canonical Quality Gates
- **Official Gates**: `asset_gate.py`, `plan_gate.py`, `taste_gate.py`
- **Deprecated Gates**: `scripts/gates/checks.py`, `scripts/gates/plan_report.py`, `scripts/gates/stage_gate.py` (Will be quarantined)

### 4. Application Programming Interface (API)
- All programmatic access to the pipeline will be routed exclusively through a newly designed `api/services/pipeline_service.py` layer.
- This service layer will act as a bridge, utilizing `safe_subprocess` to interact with `scripts/pipeline.py` and reading directly from `.pipeline_state.json`.

## Consequences
- The API will be decoupled from Python imports of the deprecated `scripts.core` module.
- All stages will accurately reflect the true status verified by the official gates.
- All modifications to the architecture MUST respect the new single source of truth.

## Migration Strategy
- If `state.json` exists in any project:
  - Read its gate status
  - Map numbered gates (1,2,3) -> named gates (asset, plan, taste)
  - Write equivalent `.pipeline_state.json`
  - Archive `state.json` as `state.json.deprecated`
- If no active projects use it -> quarantine directly

## Gate Mapping
| Deprecated | Canonical |
|---|---|
| Gate 1 | asset_gate |
| Gate 2 | plan_gate |
| Gate 3 | taste_gate |

## Write Ownership
- ONLY `scripts/pipeline.py` writes to `.pipeline_state.json`
- API is READ-ONLY for state
- Any state mutation MUST go through subprocess call to `pipeline.py`

## Execution Model
- Pipeline execution is ASYNCHRONOUS
- API returns task_id immediately
- Status polled from `.pipeline_state.json`
- Only ONE pipeline execution per project at a time (lock)

## GUI Impact
- GUI MUST read from `.pipeline_state.json` (not `state.json`)
- Gate display MUST use named gates
- No gate numbers exposed to user

## Rollback Plan
- If unification breaks critical flow:
  - Revert `api/services/` to previous imports
  - Restore `scripts/core/` from quarantine
  - State files are independent, no data loss

## Adapter Layer: legacy_gui_state

### Purpose
The `legacy_gui_state` object exists to maintain backward compatibility with existing GUI clients that expect numbered gates (Gate 1, 2, 3) and status tracking.

### Rules
1. `scripts/pipeline.py` MUST ignore `legacy_gui_state` completely.
2. `PipelineService` is the ONLY writer of `legacy_gui_state`.
3. `legacy_gui_state` MUST NOT affect pipeline execution.
4. GUI clients should migrate to hash-based tracking in future versions.

### Gate Mapping
| Legacy (Numbered) | Canonical (Named) |
|---|---|
| Gate 1 | asset_gate |
| Gate 2 | plan_gate |
| Gate 3 | taste_gate |

### Deprecation Timeline
- Phase 3: Introduce adapter (current)
- Phase 6: Update GUI to use canonical gates
- Phase 8: Remove legacy_gui_state completely
