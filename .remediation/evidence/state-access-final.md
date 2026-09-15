# UNI-02: State Readers/Writers Analysis

## 1. `state.json` (Deprecated System)

### Readers (Who reads from `state.json`?)
- `tests/gates/test_stage_gate.py`: Reads to assert stage state changes.
- `scripts/gates/checks.py`: Reads to validate state existence and contents (`state = _load_json(...)`).
- `scripts/gates/plan_report.py`: Reads to generate reports based on current state.
- `api/routers/projects.py`: Checks for existence of the file.
- `api/services/gate_service.py`: Uses `Path` to point to the file.
- `tests/test_scaffold.py`: Reads it to assert the file schema during scaffolding.

### Writers (Who writes to `state.json`?)
- `scripts/gates/stage_gate.py`: Mutates state (starts/finishes stages, approves gates).
- `scripts/scaffold_project.py`: Creates the initial `state.json` file.
- Implicitly via `gate_service.py` invoking `scripts/gates/stage_gate.py` (via `safe_subprocess`).

### Data Structure / Content (What is stored?)
Based on `scripts/gates/stage_gate.py` operations:
- Records active stage (`current_stage`)
- Stages status (`status`: `started`, `finished`, `locked`)
- Gate approvals (`approved_by`, `timestamp`)

## 2. `.pipeline_state.json` (Official System)

### Readers
- `scripts/pipeline.py`: Loads the state file to resume operations or check pipeline hashes.

### Writers
- `scripts/pipeline.py`: Main controller tracking hash mutations and status updates across the 3 stages (`asset`, `plan`, `taste`).

## 3. Parallel Pipeline `scripts/core/` Imports
Found imports in:
- `tests/test_gates_and_pipeline.py`: `from scripts.core.pipeline import UnifiedPipeline`
- `scripts/materialize_project.py`: `from scripts.core.pipeline import UnifiedPipeline`
- `scripts/render_project.py`: `from scripts.core.pipeline import UnifiedPipeline`
- `scripts/probe_qc.py`: `from core.pipeline import UnifiedPipeline`
- `api/services/render_service.py`: Direct dynamic import `from scripts.core.pipeline import UnifiedPipeline`

**Conclusion**: The API and some scripts (render, probe) actively depend on the deprecated `scripts.core.pipeline.UnifiedPipeline`.

## 4. Parallel Gates `scripts/gates/` Imports
Found imports/executions in:
- `tests/e2e/test_full_pipeline.py`: Runs `scripts/gates/stage_gate.py` multiple times.
- `tests/gates/test_stage_gate.py`: Validates `scripts/gates/stage_gate.py`.
- `scripts/e2e_data_render.py`: Runs `scripts/gates/stage_gate.py` to simulate gate approvals.
- `scripts/security.py`: Specifically allowed `scripts/gates/stage_gate.py` and `plan_report.py` (needs to be removed in future).
- `api/services/gate_service.py`: Executes `scripts/gates/stage_gate.py` as a subprocess.

## Summary & Action Items for Unification
- `state.json` is heavily coupled with the CLI `stage_gate.py` command, which the FastAPI services use.
- Moving to `.pipeline_state.json` will require rewriting `api/services/gate_service.py` and `render_service.py` to stop using `stage_gate.py` and `scripts.core` and instead interface through the new `api/services/pipeline_service.py`.
- Migration is definitely needed because the API currently drives the pipeline strictly using `state.json` and numbered gates.
