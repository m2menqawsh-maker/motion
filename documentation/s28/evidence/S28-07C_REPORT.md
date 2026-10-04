# S28-07C — Runtime & Visual Candidate Validation Report

## Metadata
- **Stage:** S28-07C (Runtime & Visual Candidate Validation)
- **Status:** **PASS**
- **Date:** 2026-10-02
- **Authority:** Architecture Level 3 / ADR-004 DEC-01
- **Target:** `ai/contracts/creative/template_candidate.py`, `ai/candidates/`, `scripts/validators/candidate_runtime_runner.py`, `tests/ai/candidates/test_candidate_runtime_validation.py`

---

## 1. Executive Summary

`S28-07C` implements the deterministic **Runtime & Visual Validation Layer** for `TemplateCandidate` proposals. Following `S28-07A` (candidate domain isolation and CAS storage) and `S28-07B` (static validation gates and transition to `VALIDATING`), `S28-07C` executes and validates candidates within an ephemeral, hermetically isolated runtime environment without modifying canonical registries or granting template approvals.

### Non-Negotiable Invariants Verified
```text
Candidate creation ≠ validation
Static validation ≠ runtime validation
Validation ≠ approval
Validation ≠ promotion
Candidate render ≠ Registered template
QC pass ≠ Human approval
AI ≠ QC authority
AI ≠ Registry authority
VALIDATED = STATIC_PASS + RUNTIME_PASS (Never APPROVED or PROMOTED)
```

- When all 5 runtime gates succeed on a candidate with valid `STATIC_PASS`:
  - The candidate achieves **`RUNTIME_PASS`** evidence with a durable `EvidenceBundle`.
  - The candidate status transitions atomically from `VALIDATING` to **`VALIDATED`**.
  - The candidate is **NEVER** marked `APPROVED` or `PROMOTED` (approval is strictly reserved for human reviewers in `S28-07D`).
- When any runtime gate fails:
  - Candidate remains in `VALIDATING` (or transitions to `REJECTED`).
  - No `RUNTIME_PASS` evidence is granted.
  - No transition to `VALIDATED` is permitted.

---

## 2. Authority Rules & Preconditions

### 2.1 Authority Boundaries
- **No Human Reviewer / Approval Bypass**: AI does not self-approve. No `PromotionService` invocation or publication occurs.
- **No Canonical Registry Mutation**: Zero writes to `templates/`, `registry/`, `contracts/template-runtime-contract.json`, or canonical catalog files.
- **Fail-Closed Preconditions**:
  - `candidate.status == CandidateStatus.VALIDATING` strictly required. A `DRAFT`, `REJECTED`, `APPROVED`, or `PROMOTED` candidate is unconditionally denied runtime validation.
  - Authoritative `STATIC_PASS` `CandidateValidationReport` must exist for `(workspace_id, candidate_id)`.
  - The static pass report must match the candidate's current `content_hash` and `revision`. If the candidate was edited after static validation, the static report is deemed stale and runtime validation fails closed (`NO_STATIC_PASS_FOUND` / `STALE_STATIC_PASS`).

---

## 3. Architecture & Runtime Isolation

### 3.1 Ephemeral Workspace Confinement
Candidates are unverified third-party code and cannot execute directly inside canonical template trees.
- **Isolated Directory**: Each validation run allocates a dedicated ephemeral directory under `data/tmp_candidate_runtime/rt_{val_id}_{uuid}/`.
- **Dynamic Harness Generation**: `scripts/validators/candidate_runtime_runner.py` creates `CandidateHarness.tsx` using Remotion's `registerRoot` and `Composition`.
- **Dependency Resolution**: Node resolution links dynamically to root `node_modules` (`@remotion/*`, `react`, etc.) while keeping candidate source files in the isolated directory.
- **Hermetic Subprocess Execution**: Render subprocesses run through `safe_subprocess(["npx", "remotion", "still", ...])` bounded by strict timeouts and resource limits.
- **Guaranteed Cleanup**: Ephemeral workspace directories are cleaned up immediately following gate execution (`runner.cleanup_workspace(...)`).

### 3.2 ADR-004 DEC-01 Compliance
`ai/candidates/` strictly adheres to the architectural guard forbidding raw filesystem write calls (`Path.write_text()`, `write_bytes()`, `open(..., 'w')`).
- Filesystem interactions and Remotion harness synthesis are isolated to `scripts/validators/candidate_runtime_runner.py`.
- `ai/candidates/runtime_runner.py` acts as an architectural boundary adapter delegating to the validator script.

---

## 4. The 5 Runtime Validation Gates

```text
STATIC_PASS Candidate (VALIDATING)
       ↓
Runtime Validation Snapshot Frozen
       ↓
1. RENDER_SMOKE Gate (Mount & frame 0 render smoke)
       ↓
2. RUNTIME_CONTRACT Gate (fps, duration bounds, fixture integrity)
       ↓
3. ASPECT Gate (Matrix test across declared supported aspect ratios)
       ↓
4. PROBE Gate (Representative frames: start, middle, end; PNG headers & dimensions)
       ↓
5. QC Gate (Luminance, solid-color variance, corruption checks; CANDIDATE profile)
       ↓
Evidence Bundle & Report Persisted
       ↓
Atomic CAS Transition: VALIDATING → VALIDATED
```

### Gate 1: `RENDER_SMOKE` (`render_smoke_gate.py`)
- **Objective**: Proves that the component mounts, resolves imports, accepts props, and renders frame 0 without crashing.
- **Evaluations**:
  - Subprocess execution of `npx remotion still ... --frame=0`.
  - Bounded timeout enforcement (default 60s).
  - Empty output / zero-byte frame detection (`RENDER_EMPTY_OUTPUT`).
  - Runtime mount crash detection (`RENDER_MOUNT_ERROR`).
  - Import resolution failure detection (`RENDER_IMPORT_ERROR`).
  - Distinction between candidate runtime failures and execution infrastructure failures (`RENDER_TOOL_EXECUTION_ERROR`).

### Gate 2: `RUNTIME_CONTRACT` (`runtime_contract_gate.py`)
- **Objective**: Validates runtime contract attributes against the project's canonical template constraints.
- **Evaluations**:
  - `fps` must belong to canonical set `{24, 25, 30, 60}` (`INVALID_RUNTIME_FPS`).
  - `duration_frames` must satisfy `1 <= duration <= 1800` (max 60s at 30fps) (`INVALID_RUNTIME_DURATION`).
  - Fixtures dictionary must contain valid schema-conforming test data (`INVALID_RUNTIME_FIXTURES`).

### Gate 3: `ASPECT` (`aspect_gate.py`)
- **Objective**: Verifies declared supported aspect ratios through an actual render matrix test.
- **Evaluations**:
  - Canonical aspect ratio dimensions checked (`9:16` -> 1080x1920, `16:9` -> 1920x1080, `1:1` -> 1080x1080).
  - Unsupported aspect ratio declaration fails (`UNSUPPORTED_ASPECT_RATIO`).
  - For each declared aspect ratio, renders a representative frame and verifies dimensions (`ASPECT_RENDER_FAILED`, `ASPECT_DIMENSIONS_MISMATCH`).

### Gate 4: `PROBE` (`probe_gate.py`)
- **Objective**: Generates and inspects representative frames across candidate timeline.
- **Evaluations**:
  - Extracts representative frames at:
    - Start: Frame 0
    - Middle: Frame `duration // 2`
    - End: Frame `duration - 1`
  - Validates frame existence (`PROBE_FRAME_MISSING`).
  - Validates binary integrity and 8-byte PNG signature `89 50 4E 47 0D 0A 1A 0A` (`PROBE_CORRUPT_HEADER`).
  - Validates frame dimensions match declared composition width and height (`PROBE_DIMENSIONS_MISMATCH`).
  - Captures SHA-256 digests and frame byte sizes.

### Gate 5: `QC` (`candidate_qc_gate.py`)
- **Objective**: Deterministic visual quality checks under `CANDIDATE_RUNTIME_QC_PROFILE`.
- **Evaluations**:
  - Zero bypass: No `SKIP_STRICT_QC` allowed.
  - Black frame detection: Average grayscale luminance < 2.0 triggers `QC_BLACK_OUTPUT`.
  - Empty/flat frame detection: Grayscale pixel variance < 0.5 triggers `QC_EMPTY_OUTPUT`.
  - Corrupted frame detection: Invalid PNG headers or truncation triggers `QC_CORRUPT_FRAME`.
  - Critical tool execution error differentiation (`QC_TOOL_EXECUTION_ERROR`).

---

## 5. Durable Evidence Bundle & CAS Transition

### 5.1 Evidence Bundle Structure
All evidence is tenant-scoped, candidate-scoped, validation-scoped, server-addressed, hashable, and durable:
- **Storage Keys**:
  - Smoke frame: `candidates/{ws_id}/{cand_id}/runtime_validation/{val_id}/smoke_frame_0.png`
  - Representative frames: `candidates/{ws_id}/{cand_id}/runtime_validation/{val_id}/frames/frame_{idx}.png`
  - Probe report: `candidates/{ws_id}/{cand_id}/runtime_validation/{val_id}/probe_report.json`
  - QC report: `candidates/{ws_id}/{cand_id}/runtime_validation/{val_id}/qc_report.json`
- Captured in `CandidateValidationReport.evidence_refs` and persisted via `StorageService`.

### 5.2 Anti-Stale Concurrency & Validation Authority
- `CandidateService.transition_to_validated(...)` is the sole authorized transition method for `VALIDATING → VALIDATED`.
- Implements CAS on `expected_revision`.
- If candidate is concurrently mutated during runtime validation (`content_hash` or `revision` changes), validation fails with `STALE_RUNTIME_VALIDATION` and CAS rejects the status transition.
- Once marked `VALIDATED`, the candidate becomes strictly immutable (`CandidateImmutableError`).

---

## 6. Test Suite & Verification Results

### 6.1 Runtime Validation Suite (`tests/ai/candidates/test_candidate_runtime_validation.py`)
19 comprehensive tests covering all gates, failure codes, and edge cases:
```text
tests/ai/candidates/test_candidate_runtime_validation.py::test_precondition_draft_candidate_denied_runtime_validation PASSED
tests/ai/candidates/test_candidate_runtime_validation.py::test_precondition_missing_static_pass_denied PASSED
tests/ai/candidates/test_candidate_runtime_validation.py::test_precondition_stale_static_pass_denied PASSED
tests/ai/candidates/test_candidate_runtime_validation.py::test_full_successful_candidate_validation_flow PASSED
tests/ai/candidates/test_candidate_runtime_validation.py::test_render_smoke_mount_error_failure PASSED
tests/ai/candidates/test_candidate_runtime_validation.py::test_render_smoke_import_error_failure PASSED
tests/ai/candidates/test_candidate_runtime_validation.py::test_render_smoke_timeout_failure PASSED
tests/ai/candidates/test_candidate_runtime_validation.py::test_render_smoke_empty_output_failure PASSED
tests/ai/candidates/test_candidate_runtime_validation.py::test_render_smoke_tool_execution_error PASSED
tests/ai/candidates/test_candidate_runtime_validation.py::test_runtime_contract_invalid_fps PASSED
tests/ai/candidates/test_candidate_runtime_validation.py::test_aspect_gate_unsupported_aspect_ratio PASSED
tests/ai/candidates/test_candidate_runtime_validation.py::test_aspect_gate_render_failure_on_declared_aspect PASSED
tests/ai/candidates/test_candidate_runtime_validation.py::test_qc_gate_black_output_violation PASSED
tests/ai/candidates/test_candidate_runtime_validation.py::test_qc_gate_empty_uniform_output_violation PASSED
tests/ai/candidates/test_candidate_runtime_validation.py::test_qc_gate_corrupt_frame_file PASSED
tests/ai/candidates/test_candidate_runtime_validation.py::test_anti_stale_mutation_during_runtime_validation PASSED
tests/ai/candidates/test_candidate_runtime_validation.py::test_cross_tenant_runtime_validation_denied PASSED
tests/ai/candidates/test_candidate_runtime_validation.py::test_cross_tenant_report_read_denied PASSED
tests/ai/candidates/test_candidate_runtime_validation.py::test_validated_candidate_cannot_be_mutated PASSED

Result: 19 passed in 78.86s
```

### 6.2 Full Candidate Subsystem Suite (`tests/ai/candidates/`)
```text
66 passed in 131.42s (100% Green across S28-07A, S28-07B, S28-07C)
```

### 6.3 Architecture Guards Suite (`tests/ai/test_creative_architecture_guards.py`)
```text
26 passed in 0.35s (100% Green)
```

### 6.4 Contract Schema & TypeScript Parity
```text
python scripts/generate_creative_contracts.py --check
✅ Ground Truth Parity: Creative contracts, schemas, and TypeScript definitions are fully synchronized.

npx vitest run tests/remotion/creative_contracts_parity.test.ts
✓ tests/remotion/creative_contracts_parity.test.ts (10 tests)
Test Files  1 passed (1)
Tests       10 passed (10)
```

### 6.5 Isolation Audit
- Canonical template directories (`templates/`, `registry/`) modified: **0 files**.
- Ephemeral workspace leakage in `data/tmp_candidate_runtime/`: **0 files** (fully cleaned up).

---

## 7. Stage Conclusion & Final Verdict

`S28-07C` has satisfied all requirements:
1. Candidate execution verified through hermetic, isolated runtime harnesses.
2. 5 deterministic runtime gates (`RENDER_SMOKE`, `RUNTIME_CONTRACT`, `ASPECT`, `PROBE`, `QC`) implemented and verified.
3. Durable evidence bundle persisted to tenant storage.
4. Atomic transition to `VALIDATED` enforced via CAS with anti-stale protection.
5. Canonical registry completely protected and isolated.

**Final Stage Verdict:** **`S28-07C PASS`**
Candidate final lifecycle state: **`VALIDATED`**
*(Next Stage: S28-07D Human Reviewer Workflow / Promotion. AI does not self-approve or self-promote.)*
