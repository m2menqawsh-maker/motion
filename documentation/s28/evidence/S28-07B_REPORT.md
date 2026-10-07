# S28-07B — Static Candidate Validation Gates Report

## Metadata
- **Stage:** S28-07B (Static Candidate Validation Gates)
- **Status:** **PASS**
- **Date:** 2026-10-02
- **Authority:** Architecture Level 3 / ADR-004 DEC-01
- **Target:** `ai/contracts/creative/template_candidate.py`, `ai/candidates/`, `scripts/validators/candidate_ast_worker.cjs`, `scripts/core/template_candidate_repository.py`

---

## 1. Executive Summary

`S28-07B` delivers the hermetic, deterministic **Static Validation Layer** for `TemplateCandidate` proposals. Following `S28-07A` (which established candidate domain isolation, storage, and CAS persistence), `S28-07B` evaluates draft candidates through 6 automated static gates without rendering video, executing runtime templates, modifying canonical registries, or granting final approval.

### Non-Negotiable Invariants Verified
```text
Candidate creation ≠ validation
Static validation ≠ runtime validation
Validation ≠ approval
Approval ≠ promotion
AI ≠ validation authority
AI ≠ registry authority
STATIC PASS ≠ FULL VALIDATED
```

- When all 6 static gates succeed:
  - The candidate achieves **`STATIC_PASS`** evidence.
  - The candidate status transitions from `DRAFT` to **`VALIDATING`**.
  - The candidate is **NEVER** marked `VALIDATED` (full validation is reserved for `S28-07C` runtime, aspect, probe, and QC gates).
- When any gate fails:
  - Candidate remains in `DRAFT` (or transitions to `REJECTED`).
  - No `STATIC_PASS` evidence is granted.
  - No approval or promotion eligibility exists.

---

## 2. Baseline Inspected & Findings

1. **Preceding S28 Foundations**:
   - `S28-07A`: Isolated `TemplateCandidate` domain, server-side content hashing, CAS concurrency, tenant isolation, and canonical registry guards.
   - Initial `CandidateValidationReport` model in `ai/contracts/creative/template_candidate.py` (legacy fields preserved for backward compatibility).
2. **Existing Validation & Tooling Infrastructure**:
   - TypeScript compiler infrastructure: `ts-morph` and the root `tsconfig.json` provide authoritative TypeScript AST parsing and compiler diagnostics.
   - Storage service: `StorageService` (`scripts/core/storage/storage_service.py`) handles tenant-isolated durable storage without path traversal.
   - Database engine: `DatabaseEngine` (`scripts/core/database.py`) provides transaction-safe SQL storage.
3. **Design Decisions**:
   - Zero regex-only heuristics: Created hermetic Node.js worker `scripts/validators/candidate_ast_worker.cjs` using `ts-morph` to inspect AST syntax, imports, call expressions, and type diagnostics deterministically in memory without writing to template directories.
   - Hermetic validation: Validation executes without network access and without invoking `npm install`, `pnpm add`, `yarn add`, or `pip install`.
   - Fail-closed snapshot binding: Validation freezes an immutable `ValidationSnapshot` before gate execution and verifies zero drift upon completion.

---

## 3. Contracts Extended & TypeScript Parity

### 3.1 `ai/contracts/creative/template_candidate.py`
Extended validation contracts while preserving full backward compatibility with legacy aliases:
- **`ValidationPhase`**: `STATIC`, `RUNTIME`.
- **`GateStatus`**: `PASS`, `FAIL`, `ERROR`.
- **`ValidationOverallResult`**: `PASS`, `FAIL`, `ERROR`.
- **`ValidationSnapshot`**: Immutable snapshot model capturing:
  - `candidate_id`: str
  - `workspace_id`: str
  - `candidate_content_hash`: str
  - `candidate_revision`: int
  - `phase`: strict_enum(ValidationPhase)
  - `policy_version`: str
  - `started_at`: TzAwareDatetime
- **`CandidateGateResult`**: Individual gate evaluation record:
  - `gate_id`: str (`contract_gate`, `static_code_gate`, `security_gate`, `dependency_gate`, `typescript_gate`, `template_schema_gate`)
  - `status`: strict_enum(GateStatus)
  - `failure_code`: Optional[str] (machine-readable failure classification)
  - `summary`: str
  - `machine_details`: Dict[str, Any]
  - `evidence_refs`: List[str]
- **`CandidateValidationReport`**: Complete audit report containing:
  - `validation_id`: str (`val_{hex12}`)
  - `candidate_id`: str, `workspace_id`: str
  - `candidate_content_hash`: str, `candidate_revision`: int
  - `phase`: strict_enum(ValidationPhase)
  - `policy_version`: str
  - `started_at`: TzAwareDatetime, `completed_at`: TzAwareDatetime
  - `gates`: List[CandidateGateResult]
  - `overall_result`: strict_enum(ValidationOverallResult)
  - `evidence_refs`: Dict[str, str]
  - Legacy backward-compatibility aliases: `report_id`, `passed`, `typescript_compiles`, `security_clean`, `no_dangerous_imports`, `has_documentation`, `quality_score`, `findings`, `evaluated_at`.

### 3.2 TypeScript & JSON Schema Parity
- Regenerated 41 JSON schemas in `schemas/creative/` via `scripts/generate_creative_contracts.py`.
- Synchronized TypeScript contract definitions in `contracts/generated/creative_contracts.ts` and `remotion-app/src/types/creative_contracts.ts`.
- Verified 100% parity via `python scripts/generate_creative_contracts.py --check` and Vitest parity test suite (`tests/remotion/creative_contracts_parity.test.ts`).

---

## 4. The 6 Static Validation Gates

```text
TemplateCandidate (DRAFT)
   ↓
ValidationSnapshot Frozen (content_hash, revision, workspace_id, started_at)
   ↓
Deterministic Static Gates:
   ├── Gate 1: Contract Gate          (Provenance, NEEDS_CREATE refs, hash verification)
   ├── Gate 2: Static Code Gate       (AST parse, component export, no eval/Function)
   ├── Gate 3: Security Gate          (No fs, child_process, network, env secrets)
   ├── Gate 4: Dependency Gate        (Approved deps, no undeclared imports)
   ├── Gate 5: TypeScript Gate        (Isolated compiler diagnostics, type check)
   └── Gate 6: Template Schema Gate   (Schema structure, fixture validation)
   ↓
Anti-Stale CAS Check (candidate_content_hash & revision unchanged)
   ↓
CandidateValidationReport Persisted (DB + StorageService)
   ↓
Candidate Status: VALIDATING (STATIC_PASS evidence recorded)
```

### 4.1 Gate 1: Contract Gate (`ai/candidates/gates/contract_gate.py`)
- Verifies candidate entity completeness before code analysis.
- Confirms workspace and project ownership validity.
- Verifies `CreativePlan` reference and `CreativeTierDecision` reference exist.
- Confirms `selected_tier == CreativeTier.CREATE` with `needs_create_evaluation=True`.
- Enforces non-empty rationales for `why_reuse_failed` and `why_compose_failed`.
- Recomputes server-side SHA-256 content hash:
  - Any mismatch against the snapshot results in **FAIL-CLOSED** (`CONTENT_HASH_MISMATCH`).

### 4.2 Gate 2: Static Code Gate (`ai/candidates/gates/static_code_gate.py`)
- In-memory AST analysis via Node.js `ts-morph` worker (`scripts/validators/candidate_ast_worker.cjs`).
- Syntax parseability and valid ESM module structure.
- Enforces expected component export (valid exported React component matching template name or component pattern).
- Forbids dynamic code execution:
  - `eval(...)` → `FORBIDDEN_EVAL`
  - `new Function(...)` → `FORBIDDEN_NEW_FUNCTION`
  - Dynamic `require(...)` or dynamic imports with non-literal arguments.
- Forbids unexpected Node runtime assumptions (`process.exit`, raw filesystem path literals).

### 4.3 Gate 3: Security Gate (`ai/candidates/gates/security_gate.py`)
- Independent security boundary enforcing principle of least privilege:
  - Templates render visual motion; they are NOT general-purpose Node programs.
- Strictly rejects Node.js system and process modules:
  - `fs`, `node:fs` → `SECURITY_FORBIDDEN_FS`
  - `child_process`, `node:child_process` → `SECURITY_FORBIDDEN_CHILD_PROCESS`
  - `net`, `tls`, `http`, `https`, `node:net`, `node:http` → `SECURITY_FORBIDDEN_NETWORK`
  - `worker_threads`, `cluster`, `vm` → `SECURITY_FORBIDDEN_NODE_MODULE`
- Strictly rejects environment secret leakage:
  - Access to `process.env.*KEY*`, `process.env.*SECRET*`, `process.env.*TOKEN*`, `process.env.*PASSWORD*` → `SECURITY_FORBIDDEN_ENV_ACCESS`.

### 4.4 Gate 4: Dependency Gate (`ai/candidates/gates/dependency_gate.py`)
- Hermetic package validation against centralized dependency policy (`ai/candidates/policies.py`).
- Detects imports used in source code but undeclared in candidate dependencies (`UNDECLARED_IMPORT`).
- Blocks forbidden packages (`FORBIDDEN_DEPENDENCY`): e.g., `axios`, `node-fetch`, `express`, `shelljs`.
- Blocks uninstalled / unknown external packages (`UNKNOWN_EXTERNAL_DEPENDENCY`).
- Zero package manager execution: Strictly forbids `npm install`, `pnpm add`, `yarn add`, or network calls during validation.

### 4.5 Gate 5: TypeScript Gate (`ai/candidates/gates/typescript_gate.py`)
- Isolated type-checking using `ts-morph` in-memory source files configured with root `tsconfig.json`.
- Zero disk pollution: No temporary build artifacts written to canonical template directories.
- Disambiguates syntax errors, JSX errors, and type errors (`TYPESCRIPT_SYNTAX_ERROR`, `TYPESCRIPT_JSX_ERROR`, `TYPESCRIPT_TYPE_ERROR`).
- Distinguishes candidate type failure (`FAIL`) from tool execution crash (`ERROR`).

### 4.6 Gate 6: Template Schema Gate (`ai/candidates/gates/template_schema_gate.py`)
- Validates candidate props schema using Draft-7 JSON Schema specification (`INVALID_SCHEMA_STRUCTURE`).
- Validates sample test fixtures against the declared props schema (`FIXTURE_SCHEMA_MISMATCH`).
- Prevents candidates from inventing arbitrary schema representations unparsable by Remotion runtime.

---

## 5. Orchestration, Persistence & Concurrency

### 5.1 Orchestration Authority (`ai/candidates/validation_service.py`)
- `CandidateValidationService`: Single authoritative service orchestrating static validation.
- Execution steps:
  1. Load tenant-scoped candidate and verify caller workspace ownership.
  2. Snapshot candidate state: freeze `ValidationSnapshot`.
  3. Execute all 6 gates in deterministic sequence: `ContractGate` → `StaticCodeGate` → `SecurityGate` → `DependencyGate` → `TypeScriptGate` → `TemplateSchemaGate`.
  4. Collect gate results and compute overall verdict (`PASS`, `FAIL`, or `ERROR`).
  5. Anti-Stale check: Query current candidate state; if `content_hash` or `revision` has changed, return `STALE_VALIDATION` and abort publishing PASS.
  6. Persist `CandidateValidationReport`:
     - Database: `SqlTemplateCandidateRepository.save_validation_report`.
     - Object storage: `StorageService.write_json` under key `validation_{validation_id}_report.json`.
  7. If overall result is `PASS`:
     - Transition candidate status from `DRAFT` to `VALIDATING` via CAS update (`update_candidate_status_cas`).
     - **NEVER** set status to `VALIDATED`.

### 5.2 Concurrency & Anti-Stale Protection
- `update_candidate_status_cas` in `SqlTemplateCandidateRepository` and `InMemoryTemplateCandidateRepository`:
  - Updates status atomically checking `expected_revision`.
  - Content revision remains stable across status updates, preventing false revision collision on subsequent queries.
- If a candidate is mutated concurrently while validation is in progress, the anti-stale check detects the mismatch and rejects the validation report as stale.

---

## 6. Test Execution & Verification

### 6.1 Test Suite Breakdown
| Test Suite | Tests | Result | Invariants Covered |
| :--- | :---: | :---: | :--- |
| `tests/ai/candidates/test_candidate_static_validation.py` | 18 | **PASS** | Full healthy candidate pass; negative tests for forbidden fs, child_process, network, env secrets, eval, new Function, missing export, undeclared import, forbidden package, unknown dependency, type error, invalid JSX, invalid schema, fixture mismatch, tampered hash; concurrency anti-stale; idempotency. |
| `tests/ai/candidates/test_candidate_validation_tenant_isolation.py` | 2 | **PASS** | Cross-tenant validation execution rejection; cross-tenant report read isolation. |
| `tests/ai/candidates/test_candidate_architecture_guards.py` | 5 | **PASS** | No raw SQL in `ai/candidates/`; no raw FS writes; no canonical registry writes; no promotion or approval authority; no package manager calls (`npm`, `pnpm`, `yarn`, `pip`). |
| `tests/ai/candidates/test_candidate_registry_isolation.py` | 2 | **PASS** | Zero SHA-256 drift across `registry/`, `contracts/`, `ground-truth/`, and `templates/` during candidate lifecycle and static validation flow. |
| `tests/core/test_template_candidate_repository.py` | 2 | **PASS** | SQL durable CRUD, workspace isolation, status CAS, validation report persistence and lookup. |
| **Combined Candidate Suite (`tests/ai/candidates/`)** | **47** | **PASS** | **100% Green** |
| `tests/ai/test_creative_architecture_guards.py` | 26 | **PASS** | Architectural compliance across creative intelligence and candidate domains. |
| **Complete Verification Run** | **75** | **PASS** | **All 75 tests passing synchronously in 62.80s** |

### 6.2 Parity & Contract Verification
- `python scripts/generate_creative_contracts.py --check`: ✅ **PASS** (Ground truth schemas and TypeScript contracts 100% in sync).
- `npx vitest run tests/remotion/creative_contracts_parity.test.ts`: ✅ **10/10 PASS** (Type checking and schema parity verified).
- `npx vitest run tests/remotion/ai_contracts_parity.test.ts`: ✅ **6/6 PASS**.
- `npx vitest run tests/remotion/s28_06_render_smoke.test.ts`: ✅ **6/6 PASS**.

---

## 7. Known Limitations & Explicit Deferrals

The following components are intentionally **NOT** in scope for `S28-07B`:
- **Deferred to S28-07C**: Runtime validation, Remotion render smoke, aspect ratio tests, Probe visual analysis, and candidate QC.
- **Deferred to S28-07D**: Reviewer / human approval authority bindings and promotion into the Canonical Template Registry.
- **Strict Prohibition Upheld**: Candidate status remains `VALIDATING`. Candidate is **never** marked `VALIDATED` in S28-07B.

---

## 8. Definition of Done Checklist

| Requirement | Verified | Evidence |
| :--- | :---: | :--- |
| Static Validation Layer exists | ✅ | `ai/candidates/validation_service.py`, `ai/candidates/gates/` |
| Immutable `ValidationSnapshot` frozen before gates | ✅ | `ValidationSnapshot` model & service freeze logic |
| Gate 1: Contract Gate validates provenance & hash | ✅ | `ai/candidates/gates/contract_gate.py` (fail-closed on tampered hash) |
| Gate 2: Static Code Gate inspects AST | ✅ | `ai/candidates/gates/static_code_gate.py` via `candidate_ast_worker.cjs` |
| Gate 3: Security Gate blocks fs, child_process, network, env | ✅ | `ai/candidates/gates/security_gate.py` |
| Gate 4: Dependency Gate enforces approved deps | ✅ | `ai/candidates/gates/dependency_gate.py` |
| Gate 5: TypeScript Gate runs isolated type checking | ✅ | `ai/candidates/gates/typescript_gate.py` |
| Gate 6: Template Schema Gate verifies schema & fixtures | ✅ | `ai/candidates/gates/template_schema_gate.py` |
| Deterministic gate execution order | ✅ | Orchestrated deterministically by `CandidateValidationService` |
| Concurrency / anti-stale protection | ✅ | CAS revision check and `STALE_VALIDATION` detection |
| Durable persistence of validation report | ✅ | SQL table `candidate_validation_reports` + `StorageService` JSON |
| Multi-tenant isolation for validation & reports | ✅ | Verified by `test_candidate_validation_tenant_isolation.py` |
| Hermetic: Zero package manager execution | ✅ | Verified by architecture guard `test_validation_layer_has_no_package_manager_execution` |
| Zero Canonical Registry mutation | ✅ | Verified by `test_static_validation_flow_never_mutates_canonical_registry` |
| Candidate status semantics: `STATIC_PASS ≠ VALIDATED` | ✅ | Successful static validation transitions to `VALIDATING`, never `VALIDATED` |
| Architecture guards enforce authority limits | ✅ | AST guards in `test_candidate_architecture_guards.py` |
| Focused tests green | ✅ | 47/47 passed in `tests/ai/candidates/` |
| Combined test suite green | ✅ | 75/75 passed |
| Contract parity green | ✅ | 100% verified via Python check script & Vitest |
| `S28-07B_REPORT.md` produced | ✅ | Documented and persisted |

---

## 9. Final Gate Verdict

```text
S28-07B PASS
```
