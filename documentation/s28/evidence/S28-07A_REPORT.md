# S28-07A — Template Candidate Domain & Isolation Report

## Metadata
- **Stage:** S28-07A (Template Candidate Domain & Isolation)
- **Status:** **PASS**
- **Date:** 2026-10-02
- **Authority:** Architecture Level 3 / ADR-004 DEC-01
- **Target:** `ai/contracts/creative/template_candidate.py`, `ai/candidates/`, `scripts/core/template_candidate_repository.py`

---

## 1. Executive Summary

`S28-07A` establishes an architecturally isolated, durable domain for `TemplateCandidate`. This ensures that when the system escalates to `NEEDS_CREATE` (when `REUSE` and `COMPOSE` are verified insufficient), new template proposals are incubated strictly in isolated quarantine storage as `DRAFT` candidates without being able to mutate the Canonical Template Registry or become automatically reusable.

### Non-Negotiable Authority Guard Verification
- `AI ≠ Registry Authority`: The AI subsystem and CandidateService have zero access to mutate the canonical registry (`registry/`, `templates/`, `template_catalog.json`).
- `TemplateCandidate ≠ Registered Template`: A candidate exists exclusively in tenant-scoped object storage and candidate repository tables; it is not resolvable as a canonical template.
- `Candidate Creation ≠ Validation`: Creation strictly initializes candidate status to `DRAFT`. Validation gates are deferred to `S28-07B`.
- `Validation ≠ Approval`: Approval is deferred to subsequent governance phases.
- `Approval ≠ Promotion`: Promotion is deferred to `S28-07B+`.

---

## 2. Baseline Inspected & Findings

1. **Preceding S28 Foundations**:
   - `S28-01`: Defined initial contracts, including preliminary `TemplateCandidate` and `PromotionDecision`.
   - `S28-06`: Implemented `TierPolicy` enforcing `REUSE → COMPOSE → NEEDS_CREATE`. When both REUSE and COMPOSE are insufficient, `CreativeTierDecision(selected_tier=CreativeTier.CREATE, needs_create_evaluation=True)` is produced with full structured evidence.
2. **Current Subsystem Authorities**:
   - Identity & Multi-Tenancy: `TenantContext`, `Workspace`, `ProjectRecord`, `Principal`, `Role` (`scripts/core/tenant_model.py`, `scripts/core/security/principal.py`).
   - Object Storage: `StorageService`, `LocalStorageBackend`, `S3CompatibleStorageBackend` (`scripts/core/storage/storage_service.py`), generating keys via `build_storage_key`.
   - Database Persistence: `DatabaseEngine` (`scripts/core/database.py`), supporting PostgreSQL and SQLite with atomic transactions and CAS.
   - Template Registry: `registry/template-registry-data.json`, `registry/template-registry.tsx`, `contracts/template-runtime-contract.json`, `ground-truth/template_catalog.json`.
3. **Legacy Template Paths Discovered**:
   - Legacy documentation references:
     - `.agents/plugins/super-video-maker-plugin/skills/remocn/SKILL.md` (recommending direct writes to `templates/custom/`).
     - `.agents/rules/video-production-protocol.md` (Level 1 composition allowing writing into `templates/custom/`).
     - `scripts/maintenance/sync_templates.py` (indexing `templates/custom`).
   - **Isolation Guarantee**: CandidateService and candidate repository do NOT use or write to `templates/custom/` or any canonical path. All candidate source code and metadata are stored in isolated object storage under the tenant namespace `workspaces/{workspace_id}/projects/{project_id}/candidates/{candidate_id}/`.

---

## 3. Contracts Added & Updated

### 3.1 `ai/contracts/creative/template_candidate.py`
Updated canonical `TemplateCandidate` with complete provenance and isolation fields:
- `candidate_id`: str (server-generated identifier `cand_{hex12}`)
- `workspace_id`: str (mandatory workspace scope from `TenantContext`)
- `source_project_id`: str (origin project identifier)
- `origin_project_id`: Optional[str] (legacy alias with automatic synchronization)
- `creator_ai_run_id`: Optional[str] (AI run ID if authored by agent)
- `creative_plan_reference`: str (originating CreativePlan plan_id)
- `creative_tier_decision_reference`: str (originating CreativeTierDecision decision_id)
- `why_reuse_failed`: str (provenance rationale why REUSE was insufficient)
- `why_compose_failed`: str (provenance rationale why COMPOSE was insufficient)
- `source_code`: str (TSX source code of the component)
- `source_code_path`: Optional[str] (canonical storage key for source code)
- `template_schema`: Dict[str, Any] (Zod / JSON schema for component props)
- `dependencies`: List[str] (external npm dependencies)
- `fixtures`: Dict[str, Any] (sample props / test fixtures)
- `content_hash`: str (server-computed deterministic SHA-256 digest)
- `revision`: int (monotonic optimistic concurrency sequence, initial value = 1)
- `status`: strict_enum(CandidateStatus) (starts as `CandidateStatus.DRAFT`)
- `name`: str, `description`: str, `author`: str, `proposed_category`: str, `proposed_tags`: List[str]
- `target_tier`: strict_enum(CreativeTier) (typically `REUSE`)
- `required_provenance`: ProvenanceRecord (mandatory lineage record)
- `storage_keys`: Dict[str, str] (authoritative mapping to stored artifacts)
- `created_at`: TzAwareDatetime, `updated_at`: TzAwareDatetime

### 3.2 `CandidateStatus` Lifecycle Enum
```python
class CandidateStatus(str, Enum):
    DRAFT = "DRAFT"
    VALIDATING = "VALIDATING"
    VALIDATED = "VALIDATED"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PROMOTED = "PROMOTED"
    RETIRED = "RETIRED"
```
- In `S28-07A`, creation strictly initializes status to `DRAFT`.
- Attempting to pass `status=APPROVED` or `status=PROMOTED` is strictly rejected by domain authority (`CandidateAuthorityError`).

### 3.3 TypeScript & Schema Parity
- Generated JSON schema: `schemas/creative/template_candidate.schema.json`
- Generated TypeScript types: `contracts/generated/creative_contracts.ts` and `remotion-app/src/types/creative_contracts.ts`
- Verified 100% synchronized via `python scripts/generate_creative_contracts.py --check` and Vitest parity suite (`tests/remotion/creative_contracts_parity.test.ts`).

---

## 4. Architecture & Implementation

### 4.1 Deterministic Server-Side Content Hashing (`ai/candidates/hashing.py`)
- Serializes canonical payload containing `source_code`, `template_schema`, `dependencies` (sorted), `fixtures`, `why_reuse_failed`, `why_compose_failed`, `creative_plan_reference`, and `creative_tier_decision_reference`.
- Uses `json.dumps(payload, sort_keys=True, separators=(',', ':'))` and `hashlib.sha256`.
- Proved deterministic across runs; invariant to key or dependency ordering; changing any content field alters the hash.

### 4.2 StorageService Isolation (`ai/candidates/service.py`)
- Category namespace: `category = "candidates"`.
- Storage key format generated server-side:
  `workspaces/{workspace_id}/projects/{project_id}/candidates/{candidate_id}/{filename}`
  - `source.tsx`: Component source code.
  - `schema.json`: Component props schema.
  - `fixtures.json`: Sample props / test fixtures.
- Protected against path traversal via `validate_storage_key`: slashes, `..`, and absolute paths are rejected.

### 4.3 Database Persistence & CAS (`scripts/core/template_candidate_repository.py`)
- Implemented in `scripts/core/` complying with ADR-004 DEC-01 (zero SQL in `ai/`).
- Durable SQL schema: `template_candidates` with indexes on `(workspace_id, source_project_id)` and `(workspace_id, status)`.
- Optimistic Concurrency Control (CAS):
  ```sql
  UPDATE template_candidates
  SET revision = ?, ...
  WHERE candidate_id = ? AND workspace_id = ? AND revision = ?;
  ```
- If rows affected == 0, disambiguates missing candidate vs stale revision collision, raising `CandidateConflictError`. Revision increments monotonically (N → N+1) and cannot retreat.

### 4.4 Tenant Confinement & Eligibility
- `workspace_id` is derived strictly from `tenant_context.workspace_id`.
- `source_project_id` is verified against the database to confirm it belongs to the caller's workspace.
- Cross-tenant lookups and updates raise `CandidateNotFoundError` / access denied without leaking existence.
- Candidate creation strictly enforces `CreativeTierDecision.selected_tier == CreativeTier.CREATE` with `needs_create_evaluation=True`, and both `reuse_result.sufficiency == False` and `compose_result.sufficiency == False`. Missing evidence raises `CandidateEligibilityError`.

---

## 5. Test Execution & Verification

### 5.1 Focused Candidate Test Suite (`tests/ai/candidates/` & `tests/core/`)
| Test File | Tests | Status | Invariants Verified |
| :--- | :--- | :--- | :--- |
| `test_candidate_contracts.py` | 5 | **PASS** | Valid contract, missing provenance rejection, enum validation, extra field rejection. |
| `test_candidate_hashing.py` | 5 | **PASS** | Hash determinism, dependency order invariance, source code / schema / fixture mutation sensitivity. |
| `test_candidate_service.py` | 4 | **PASS** | Valid creation starts as DRAFT, non-CREATE rejection, missing evidence rejection, anti-self-approval rejection. |
| `test_candidate_tenant_isolation.py` | 2 | **PASS** | Cross-tenant get/update/list isolation, cross-tenant project reference rejection. |
| `test_candidate_storage.py` | 3 | **PASS** | Server-generated storage keys, traversal rejection, service restart persistence. |
| `test_candidate_concurrency.py` | 1 | **PASS** | CAS concurrency protection (revision N → N+1, stale writer rejected with conflict). |
| `test_candidate_registry_isolation.py` | 1 | **PASS** | Canonical registry, runtime contract, catalog, and `templates/` 100% unchanged after candidate ops. |
| `test_candidate_architecture_guards.py` | 3 | **PASS** | No raw SQL in `ai/candidates/`, no raw FS writes, no registry mutation rights. |
| `test_template_candidate_repository.py` | 1 | **PASS** | SQL-backed SQLite/PostgreSQL durable CRUD, tenant scoping, and CAS revision check. |
| **Total Focused Tests** | **25** | **PASS** | **100% Green** |

### 5.2 Architecture & Regressions
- `tests/ai/` full test suite: **1050 passed, 7 skipped** (28.99s).
- `tests/ai/test_creative_architecture_guards.py`: **26 passed** (including new `Rule 3.5: CREATIVE-CANDIDATE-NO-REGISTRY-WRITE`).
- `tests/ai/audit/test_s27_final_architecture_audit.py`: **5 passed**.
- `tests/validators/test_template_registry_consistency.py`: **4 passed**.
- Vitest parity suite (`tests/remotion/creative_contracts_parity.test.ts`): **10 passed**.
- Vitest package suite (`npm test`): **153 passed**.

---

## 6. Known Limitations & Explicit Deferrals

The following systems are intentionally **NOT** implemented in `S28-07A` and are deferred to subsequent stages:
- **Deferred to S28-07B**: Automated validation gates (Contract Gate, TypeScript Gate, Security Gate, Dependency Gate, Render Smoke Gate).
- **Deferred to S28-07C**: Reviewer workflow, human approval bindings, and cryptographic approval signatures.
- **Deferred to S28-07D**: `PromotionService`, registry promotion, and canonical catalog mutation.
- **Deferred to S28-08**: Legacy cleanup of `.agents/plugins/super-video-maker-plugin/skills/remocn/SKILL.md` and related legacy custom template documentation.

---

## 7. Definition of Done Checklist

| Requirement | Verified | Evidence |
| :--- | :---: | :--- |
| `TemplateCandidate` canonical contract exists | ✅ | `ai/contracts/creative/template_candidate.py` |
| Candidate created only from valid NEEDS_CREATE | ✅ | `TemplateCandidateService.create_candidate` validates tier decision |
| Candidate starts as DRAFT | ✅ | Enforced server-side; caller status input overridden/rejected |
| Candidate provenance traceable | ✅ | Links to `creative_plan_reference` and `creative_tier_decision_reference` |
| Candidate tenant-isolated | ✅ | Verified by `test_cross_tenant_isolation` |
| Candidate persistent via current architecture | ✅ | `SqlTemplateCandidateRepository` using `DatabaseEngine` |
| Storage keys server-controlled | ✅ | Generated via `build_storage_key` under `candidates/` category |
| `content_hash` deterministic and server-generated | ✅ | Tested via `test_candidate_hashing.py` |
| Revision/CAS protects DRAFT updates | ✅ | Atomic SQL update with expected_revision check |
| Cross-tenant access denied | ✅ | Probed get/update/list across tenants returns 404 / empty |
| Candidate cannot self-set APPROVED/PROMOTED | ✅ | `CandidateAuthorityError` raised on unauthorized requested_status |
| Candidate flow cannot mutate Canonical Registry | ✅ | `test_candidate_flow_never_mutates_canonical_registry` verifies zero SHA drift |
| Architecture guard exists | ✅ | AST guard in `test_candidate_architecture_guards.py` & `test_creative_architecture_guards.py` |
| Focused tests green | ✅ | 25/25 passed |
| Relevant regressions green | ✅ | 1050/1050 passed in `tests/ai/`, 153/153 passed in Vitest |
| `S28-07A_REPORT.md` produced | ✅ | Documented and persisted |

---

## 8. Final Gate Verdict

```text
S28-07A PASS
```
