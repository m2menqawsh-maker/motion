# S28-07D — Human Review & Approval Workflow Report

## Metadata
- **Stage:** S28-07D (Human Review & Approval Workflow)
- **Status:** **PASS**
- **Date:** 2026-10-02
- **Authority:** Architecture Level 3 / ADR-004 DEC-01
- **Target Files:**
  - `ai/contracts/creative/template_candidate.py`
  - `ai/candidates/review_service.py`
  - `ai/candidates/hashing.py`
  - `ai/candidates/errors.py`
  - `scripts/core/template_candidate_repository.py`
  - `ai/candidates/repository.py`
  - `api/routers/candidate_reviews.py`
  - `api/main.py`
  - `tests/ai/candidates/test_candidate_review_workflow.py`
  - `tests/api/test_candidate_reviews_router.py`
  - `tests/core/test_template_candidate_repository.py`
  - `tests/ai/candidates/test_candidate_registry_isolation.py`
  - `tests/ai/candidates/test_candidate_architecture_guards.py`

---

## 1. Executive Summary

`S28-07D` implements the authoritative, tamper-proof **Human Review & Approval Workflow** for `TemplateCandidate` proposals. Following `S28-07A` (domain data model & CAS repository), `S28-07B` (static validation gates), and `S28-07C` (runtime visual execution and evidence generation), `S28-07D` governs the critical threshold between algorithmic candidate validation and human trust authorization.

### Non-Negotiable Invariants Enforced
```text
Validation ≠ Approval
Approval ≠ Promotion
AI creator ≠ Reviewer
Reviewer ≠ Registry Authority
APPROVED ≠ PROMOTED
Candidate ≠ Registered Template
```

```text
VALIDATED
   ↓  CandidateReviewService.open_review()
Review Bundle Freeze (Deterministic SHA-256 Digest)
   ↓
AWAITING_APPROVAL (CAS atomic transition)
   ↓  Trusted Human Reviewer Decision
   ├── APPROVED  (CandidateStatus.APPROVED — ZERO registry mutation)
   └── REJECTED  (CandidateStatus.REJECTED — Audit trail preserved)
```

- **Validation is strictly distinct from Approval**: Machine verification (`STATIC_PASS` + `RUNTIME_PASS`) qualifies a candidate for review, but only an authenticated human in the authorized workspace can approve it.
- **Approval is strictly distinct from Promotion**: Marking a candidate `APPROVED` does **NOT** register the template, does **NOT** mutate the canonical registry, and does **NOT** expose it for production reuse. Promotion and registry publication are exclusively deferred to `S28-07E`.
- **AI creator is strictly prohibited from approving**: AI agents and automated service principals cannot approve candidates or impersonate reviewers.
- **Reviewer identity is strictly server-derived**: Client claims (such as `approved_by` or `reviewer_id` in request payloads) are completely ignored in favor of `TenantContext.principal.principal_id`.
- **Immutable cryptographic binding**: Approval decisions are permanently bound to the exact content hash, candidate revision, review bundle hash, and validation report digests.

---

## 2. Review Preconditions & Integrity Verification

A candidate cannot enter review without passing fail-closed precondition checks in `CandidateReviewService.open_review`:

1. **Candidate Status**: Must be `CandidateStatus.VALIDATED`. A candidate in `DRAFT`, `VALIDATING`, `APPROVED`, or `REJECTED` fails closed (`CandidateInvalidStatusError`).
2. **Authoritative Evidence Required**:
   - Must possess a verified `CandidateValidationReport` for `ValidationPhase.STATIC` with `overall_result == PASS`.
   - Must possess a verified `CandidateValidationReport` for `ValidationPhase.RUNTIME` with `overall_result == PASS`.
3. **Freshness & Snapshot Matching**:
   - `static_report.candidate_content_hash == candidate.content_hash`
   - `runtime_report.candidate_content_hash == candidate.content_hash`
   - `static_report.candidate_revision == candidate.revision`
   - `runtime_report.candidate_revision == candidate.revision`
   - `runtime_report.static_validation_id == static_report.validation_id`
   - SHA-256 of static report matches `runtime_report.static_validation_report_hash`
   - Evidence tampering or report staleness triggers `CandidateReviewTamperedError` or `CandidateReviewStaleError`.
4. **Tenant Isolation**: Both candidate and validation reports must strictly belong to the caller's `workspace_id`. Cross-tenant attempts fail closed (`CandidateTenantMismatchError` / `CandidateNotFoundError`).

---

## 3. Review Bundle Freeze & Cryptographic Digest

When review opens, an immutable canonical `CandidateReviewBundle` is frozen and persisted:

```python
class CandidateReviewBundle(BaseModel):
    review_bundle_id: str
    candidate_id: str
    workspace_id: str
    candidate_content_hash: str
    candidate_revision: int
    static_validation_id: str
    runtime_validation_id: str
    static_report_hash: str
    runtime_report_hash: str
    render_evidence_refs: Dict[str, str]
    representative_frame_refs: List[str]
    probe_report_ref: Optional[str]
    qc_report_ref: Optional[str]
    source_code_hash: str
    schema_hash: str
    fixtures_hash: Optional[str]
    created_at: str
    review_policy_version: str
    review_bundle_hash: str
```

### Deterministic Digest Computation (`compute_review_bundle_hash`)
- Computes SHA-256 over canonical, alphabetically sorted JSON serialization of all constituent evidence pointers, report digests, content hashes, and policy versions.
- The bundle is stored both in SQL (`candidate_review_bundles`) and in `StorageService` under `workspaces/{ws}/candidates/{cand}/review_{id}_bundle.json`.
- Candidate lifecycle transitions from `VALIDATED` to `AWAITING_APPROVAL` using Compare-And-Swap (CAS) on `expected_revision`.

---

## 4. Reviewer Authorization & Separation of Duties

### 4.1 RBAC Enforcement
Review decisions (`approve` and `reject`) can only be executed by callers meeting all of the following requirements:
- **Authentication**: Caller must possess a valid, non-anonymous `TenantContext.principal`.
- **Role Permission**: Caller's role must be `Role.REVIEWER` or `Role.ADMIN` (`Role.VIEWER` and `Role.EDITOR` without reviewer permission are denied with `CandidatePermissionError`).
- **Workspace Confinement**: Caller's principal must belong to the candidate's `workspace_id`. Cross-workspace review attempts fail with `CandidateTenantMismatchError`.

### 4.2 Separation of Duties (Creator ≠ Approver)
- **AI Principal Prohibition**: If `principal.principal_type == PrincipalType.SERVICE` or `principal.principal_type == PrincipalType.AGENT`, review operations are unconditionally denied.
- **Creator Check**: If `candidate.author == principal.principal_id` or `candidate.creator_ai_run_id == principal.principal_id`, self-approval is rejected (`CandidateAuthorityError: Creator cannot approve their own candidate. Separation of duties is required.`).
- **Spoofing Immunity**: The router extracts identity solely from `tenant_context.principal.principal_id`. Any client payload fields like `reviewer_id` or `approved_by` are discarded.

---

## 5. Approval & Rejection Decisions

### 5.1 Approval Decision Contract (`CandidateReviewDecision`)
```python
class CandidateReviewDecision(BaseModel):
    decision_id: str
    review_bundle_id: str
    candidate_id: str
    workspace_id: str
    decision: CandidateReviewVerdict  # APPROVED | REJECTED
    reviewer_principal_id: str
    reviewer_role: str
    reason: Optional[str]
    candidate_content_hash: str
    candidate_revision: int
    review_bundle_hash: str
    decided_at: str
    decision_revision: int
```

### 5.2 Transition Logic
- **Approval (`approve`)**:
  - Validates human reviewer authority and separation of duties.
  - Re-verifies cryptographic integrity of the frozen review bundle.
  - Confirms candidate is currently in `AWAITING_APPROVAL`.
  - Atomically updates candidate status to `APPROVED` using CAS.
  - Persists append-only `CandidateReviewDecision` in SQL and durable storage.
  - **Idempotency**: Repeated approval with identical bundle and reviewer returns existing decision.
  - **Zero Registry Writes**: Canonical registry, runtime contracts, and template directories are untouched.
- **Rejection (`reject`)**:
  - Requires non-empty reason (`reason.strip()` validation).
  - Transitions candidate status to `REJECTED`.
  - Candidate record and all evidence bundles remain permanently intact for audit trail.
  - Rejection prevents subsequent approval without initiating a fresh candidate revision and review cycle.

---

## 6. Durable Persistence & CAS

The SQL repository (`scripts/core/template_candidate_repository.py`) introduces two append-only, tenant-isolated tables:

```sql
CREATE TABLE IF NOT EXISTS candidate_review_bundles (
    review_bundle_id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    candidate_content_hash TEXT NOT NULL,
    candidate_revision INTEGER NOT NULL,
    review_bundle_hash TEXT NOT NULL,
    bundle_data TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS candidate_review_decisions (
    decision_id TEXT PRIMARY KEY,
    review_bundle_id TEXT NOT NULL,
    candidate_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    decision TEXT NOT NULL,
    reviewer_principal_id TEXT NOT NULL,
    reviewer_role TEXT NOT NULL,
    candidate_content_hash TEXT NOT NULL,
    candidate_revision INTEGER NOT NULL,
    review_bundle_hash TEXT NOT NULL,
    decision_data TEXT NOT NULL,
    decided_at TEXT NOT NULL
);
```

- Candidate status transitions (`VALIDATED -> AWAITING_APPROVAL`, `AWAITING_APPROVAL -> APPROVED | REJECTED`) enforce optimistic concurrency via `expected_revision`. Stale revisions trigger `CandidateConflictError`.
- Decisions are immutable and append-only. No updates from `REJECTED` to `APPROVED` or reviewer identity rewriting are permitted.

---

## 7. Transport Layer & API Boundary

`api/routers/candidate_reviews.py` provides clean REST endpoints mounted under `/candidates`:
- `POST /candidates/{id}/reviews/open` — Opens review, freezes bundle, transitions to `AWAITING_APPROVAL`.
- `GET /candidates/{id}/reviews/bundle/active` — Retrieves active review bundle for candidate.
- `GET /candidates/{id}/reviews/bundle/{bundle_id}` — Retrieves review bundle by ID with cryptographic integrity check.
- `POST /candidates/{id}/reviews/approve` — Records human approval (reviewer identity taken strictly from request context).
- `POST /candidates/{id}/reviews/reject` — Records human rejection with mandatory justification.
- `GET /candidates/{id}/reviews/decisions` — Lists audit trail of review decisions.

The router acts purely as an HTTP transport adapter and contains zero business logic, zero status mutations, and zero direct SQL executions.

---

## 8. Architectural Invariant Proofs & Guards

### 8.1 Registry Isolation
Tests in `tests/ai/candidates/test_candidate_registry_isolation.py` take SHA-256 snapshots of the canonical registry before and after candidate creation, static validation, review bundle freeze, and approval:
- `registry/template-registry-data.json`: **MATCH (0 bytes modified)**
- `registry/template-registry.tsx`: **MATCH (0 bytes modified)**
- `contracts/template-runtime-contract.json`: **MATCH (0 bytes modified)**
- `ground-truth/template_catalog.json`: **MATCH (0 bytes modified)**
- `templates/`: **MATCH (0 bytes modified)**

### 8.2 Architectural Guard Tests (`test_candidate_architecture_guards.py`)
- `test_review_service_has_no_promotion_or_registry_authority`: Verifies `CandidateReviewService` does not import `PromotionService`, does not set `CandidateStatus.PROMOTED`, and has no registry write methods.
- `test_router_has_no_direct_candidate_status_assignment`: Verifies `candidate_reviews.py` has no direct status assignment.
- `test_ai_layer_has_no_direct_candidate_approval`: Verifies AI layers cannot directly approve candidates.
- `test_validation_layer_has_no_promotion_or_approval_authority`: Proves validation gates have zero approval rights.

---

## 9. Verification & Test Evidence

### 9.1 Test Suite Results
All test suites passed with 100% green status across candidate unit tests, workflows, API router, SQL persistence, architecture guards, and TypeScript parity.

| Test Suite | Tests Run | Result | Duration |
|:---|:---:|:---:|:---:|
| `tests/ai/candidates/test_candidate_review_workflow.py` | 21 | **PASS** | 1.84s |
| `tests/api/test_candidate_reviews_router.py` | 3 | **PASS** | 0.82s |
| `tests/core/test_template_candidate_repository.py` | 3 | **PASS** | 0.15s |
| `tests/ai/candidates/test_candidate_registry_isolation.py` | 3 | **PASS** | 3.19s |
| `tests/ai/candidates/test_candidate_architecture_guards.py` | 8 | **PASS** | 0.08s |
| `tests/ai/test_creative_architecture_guards.py` | 26 | **PASS** | 0.31s |
| Full Candidate Subsystem Suite (`tests/ai/candidates/`) | 97 | **PASS** | 122.99s |
| TypeScript Parity (`creative_contracts_parity.test.ts`) | 11 | **PASS** | 0.29s |
| Contract Schema Generator Parity (`generate_creative_contracts.py --check`) | 1 | **PASS** | 0.12s |

### 9.2 Verification Commands Executed
```bash
# 1. Full Candidate Subsystem Regression
.venv/bin/pytest tests/ai/candidates/ tests/api/test_candidate_reviews_router.py tests/core/test_template_candidate_repository.py -v
# Output: 97 passed in 122.99s

# 2. Candidate Architecture Guards
.venv/bin/pytest tests/ai/candidates/test_candidate_architecture_guards.py tests/ai/test_creative_architecture_guards.py -v
# Output: 34 passed in 0.39s

# 3. Creative Contracts Schema Parity Check
.venv/bin/python scripts/generate_creative_contracts.py --check
# Output: Ground Truth Parity: Creative contracts, schemas, and TypeScript definitions are fully synchronized.

# 4. TypeScript Contracts Vitest Parity
npx vitest run tests/remotion/creative_contracts_parity.test.ts
# Output: 11 passed in 290ms

# 5. Canonical Registry Zero-Drift Check
git diff registry/ contracts/template-runtime-contract.json ground-truth/
# Output: Clean (0 diff)
```

---

## 10. Deferral to S28-07E (Strict Boundaries)

The following capabilities are **intentionally NOT implemented** in `S28-07D` and are exclusively deferred to `S28-07E`:
- `PromotionService` and candidate promotion authority.
- `CandidateStatus.PROMOTED` state transition.
- Canonical registry mutation (`registry/template-registry-data.json`, `registry/template-registry.tsx`).
- Production template catalog publication (`ground-truth/template_catalog.json`).
- Template runtime contract updates (`contracts/template-runtime-contract.json`).
- Placement of candidate source code into production `templates/` directory.

---

## 11. Stage Conclusion

`S28-07D` successfully establishes the authoritative, tamper-proof, tenant-isolated Human Review & Approval Workflow. The candidate progression is verified:

```text
VALIDATED ✅  →  Review Bundle Freeze ✅  →  AWAITING_APPROVAL ✅  →  APPROVED ✅ (or REJECTED ✅)
```

**Stage Gate: S28-07D PASS.**
