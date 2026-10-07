# S28-07E — PromotionService & Canonical Registry Publication Report

## Metadata
- **Stage:** S28-07E (PromotionService & Canonical Registry Publication)
- **Status:** **PASS**
- **Date:** 2026-10-02
- **Authority:** Architecture Level 3 / ADR-004 DEC-01
- **Target Files:**
  - `ai/contracts/creative/template_candidate.py`
  - `schemas/creative/PromotionManifest.json`
  - `schemas/creative/CandidatePromotionRecord.json`
  - `remotion-app/src/types/creative_contracts.ts`
  - `scripts/core/template_registry_publisher.py`
  - `ai/candidates/promotion_service.py`
  - `ai/candidates/hashing.py`
  - `ai/candidates/errors.py`
  - `scripts/core/template_candidate_repository.py`
  - `ai/candidates/repository.py`
  - `api/routers/candidate_promotions.py`
  - `api/main.py`
  - `tests/ai/candidates/test_candidate_promotion_service.py`
  - `tests/ai/candidates/test_candidate_architecture_guards.py`
  - `tests/api/test_candidate_promotions_router.py`
  - `tests/validators/test_template_registry_consistency.py`
  - `tests/remotion/creative_contracts_parity.test.ts`

---

## 1. Executive Summary

`S28-07E` establishes the sole authoritative, tamper-proof system for promoting human-approved `TemplateCandidate` proposals into the production canonical template registry. Following `S28-07A` through `S28-07D`, this stage implements `PromotionService` and `TemplateRegistryPublisher` to guarantee zero-mutation preflights, isolated staged publications, transactional rollback journals, post-publish verification, CAS lifecycle transitions (`APPROVED → PROMOTED`), and deterministic audit records (`CandidatePromotionRecord`).

### Non-Negotiable Invariants Enforced
```text
AI ≠ Promotion Authority
Reviewer ≠ Promotion Authority
Router ≠ Promotion Authority
Validation ≠ Promotion
Approval ≠ Promotion

PromotionService = sole promotion authority
```

```text
APPROVED Candidate
   ↓  promote_candidate()
Preflight Zero-Mutation Verification
   ├─ RBAC & Non-AI Principal Check (Human Admin only)
   ├─ Idempotency Check (Existing COMMITTED record return)
   ├─ Target Template ID Policy & Collision Prevention
   ├─ Cryptographic Tamper & Digest Re-verification
   └─ Source & Schema Availability Verification
   ↓
PromotionManifest Deterministic Freeze (SHA-256 Digest)
   ↓
Staged Publication in Isolated Temp Directory
   ├─ Materialize Canonical Template Component (.tsx)
   ├─ Mutate Registry Authority (template-registry-data.json)
   ├─ Regenerate Runtime Contract (template-runtime-contract.json)
   ├─ Regenerate Registry Imports & Map (template-registry.tsx)
   └─ Update Ground-Truth Catalog (template_catalog.json)
   ↓
Pre-Commit Consistency Checks
   ↓
Atomic Production Commit with RollbackJournal
   ↓
Post-Publish Live Disk Verification
   ├─ If verification FAILS → RollbackJournal reverts disk, candidate remains APPROVED
   └─ If verification PASSES → Proceed to CAS
   ↓
CandidateStatus.PROMOTED (CAS atomic transition)
   ↓
CandidatePromotionRecord Persisted (Status: COMMITTED)
```

- **Sole Promotion Authority**: Only `PromotionService` can set `CandidateStatus.PROMOTED`, write to canonical registry files, or publish production template packages.
- **AI Agents Strictly Prohibited**: AI callers (e.g. `gpt-4o`, `claude`, `creative_planner`, `system-worker`) fail closed with `403 Forbidden` (`CandidatePermissionError`).
- **Server-Authoritative Identity**: Client claims (such as `promoter_id` or `role` in HTTP request payloads) are completely ignored in favor of the cryptographically verified `TenantContext.principal.principal_id`.
- **Zero Mutation on Preflight Failure**: If any preflight gate, collision check, path traversal guard, or cryptographic digest fails, zero disk writes occur and the candidate remains in `APPROVED` status.
- **Atomic Rollback Journal**: Any disk mutation is logged in an in-memory `RollbackJournal` before execution. Any post-publish verification failure immediately triggers a clean rollback of all mutated canonical files and removes created artifacts.
- **Strict Idempotency**: Promoting the same candidate with identical parameters returns the existing `CandidatePromotionRecord` without duplicating registry entries, creating orphaned files, or incrementing versions.

---

## 2. Registry Architecture & Source of Truth

An architectural inspection of the repository determined the canonical dependency graph:

```text
                         [Source of Truth]
                   registry/template-registry-data.json
                                 │
                 ┌───────────────┼───────────────┐
                 ▼               ▼               ▼
            [Component]     [TypeScript]    [Runtime Contract]
          templates/<dir>/   registry/         contracts/
          <Component>.tsx   template-         template-runtime-
                            registry.tsx      contract.json
                                 │
                                 ▼
                          [Ground Truth]
                           ground-truth/
                        template_catalog.json
```

1. **Source of Truth Authority**: `registry/template-registry-data.json` is the sole declarative source of truth for template metadata, parameters, categories, component bindings, and aliases.
2. **Deterministic Derivatives**:
   - `registry/template-registry.tsx`: Exports React component imports, definitions, and component mappings.
   - `contracts/template-runtime-contract.json`: Defines runtime engine aliases, default durations, and aspect constraints.
   - `ground-truth/template_catalog.json`: Canonical catalog consumed by creative intelligence layers.
3. **CRLF/LF Byte-Safety**: `template-registry-data.json` uses CRLF (`\r\n`) line endings. To avoid hash drift across operating systems, `TemplateRegistryPublisher` computes digests strictly on raw binary bytes (`Path.read_bytes()`) rather than decoded strings.

---

## 3. Cryptographic Tamper Resistance & Preconditions

Before any staging or disk mutation begins, `PromotionService.promote_candidate` validates:

1. **Candidate Status**: Must be `CandidateStatus.APPROVED`. Candidates in `DRAFT`, `VALIDATING`, `VALIDATED`, `AWAITING_APPROVAL`, `REJECTED`, or `RETIRED` are denied (`PromotionPreconditionError`).
2. **Authoritative Review Decision**:
   - Must exist in repository with verdict `CandidateReviewVerdict.APPROVED`.
   - `decision.candidate_content_hash == candidate.content_hash`
   - `decision.candidate_revision == candidate.revision`
3. **Review Bundle Cryptographic Digest**:
   - Recomputes SHA-256 digest over candidate hashes, static report hash, runtime report hash, and source hashes.
   - Recomputed hash must equal `bundle.review_bundle_hash` and `decision.review_bundle_hash`.
4. **Validation Reports Integrity**:
   - `static_report.overall_result == PASS` and SHA-256 matches bundle digest.
   - `runtime_report.overall_result == PASS` and SHA-256 matches bundle digest.
5. **Approved Content Immutability**:
   - Resolved source code hash matches `bundle.source_code_hash`.
   - Template schema hash matches `bundle.schema_hash`.
   - If content was altered after human approval, promotion fails closed (`PromotionTamperedError`).

---

## 4. Promotion Manifest & Deterministic Hashing

Prior to staging, `PromotionService` synthesizes an immutable, deterministic `PromotionManifest`:

```python
class PromotionManifest(BaseModel):
    promotion_id: str
    candidate_id: str
    workspace_id: str
    candidate_content_hash: str
    candidate_revision: int
    approval_decision_id: str
    review_bundle_id: str
    review_bundle_hash: str
    static_validation_id: str
    runtime_validation_id: str
    target_template_id: str
    target_template_version: str
    source_code_hash: str
    schema_hash: str
    promotion_policy_version: str
    created_at: datetime
```

The manifest hash is calculated server-side using deterministic canonical JSON serialization (`sort_keys=True, separators=(',', ':')`):
```text
promotion_manifest_hash = SHA256(canonical_json(manifest))
```

---

## 5. Staged Publication & Transactional Rollback

To prevent partial, corrupt, or inconsistent states, publication follows a strict staging pipeline managed by `TemplateRegistryPublisher`:

1. **Isolated Staging Area**: A temporary directory (`staged_publication`) is initialized.
2. **Materialize Template Package**: The approved source code is written to `templates/<category>/<ComponentName>.tsx`.
3. **Generate Derivative Files**:
   - Updates `template-registry-data.json` with the new entry and calculates post-publish hash.
   - Appends ES import and dictionary entry to `template-registry.tsx`.
   - Regenerates `template-runtime-contract.json` with aliases and schema.
   - Appends entry to `template_catalog.json`.
4. **Staged Consistency Verification**: Checks all staged outputs for syntactic and structural validity before touching live files.
5. **Atomic Commit with RollbackJournal**:
   - Records pre-mutation binary snapshots of all destination files in `RollbackJournal`.
   - Atomically overwrites canonical files.
6. **Live Post-Publish Verification**:
   - Verifies target source file exists and contains expected export.
   - Verifies registry data entry matches and is queryable.
   - Verifies runtime contract contains expected entry and aliases.
   - Verifies live disk hashes match staged hashes.
7. **Clean Rollback on Failure**:
   - If verification fails, `RollbackJournal.rollback()` restores all original files byte-for-byte and deletes newly created source files.
   - Candidate remains `APPROVED`.
   - Promotion record is saved with status `ROLLED_BACK`.

---

## 6. API Transport & Authorization Boundary

The REST endpoint `POST /candidates/{candidate_id}/promote` is mounted under `/candidates`:

- **Role Authorization**: Requires `Action.TEMPLATE_PROMOTE`, granted strictly to `Role.ADMIN`.
- **Identity Invariant**: Ignores `promoter_id` or `role` fields in the JSON body, binding strictly to `TenantContext.principal.principal_id`.
- **Error Code Mappings**:
  - `400 Bad Request`: Precondition violation (candidate not `APPROVED`, empty source).
  - `403 Forbidden`: Insufficient role, AI agent caller, path traversal, naming regex violation.
  - `404 Not Found`: Candidate not found or cross-tenant access attempt.
  - `409 Conflict`: CAS expected revision mismatch, existing canonical template ID collision.
  - `422 Unprocessable Entity`: Cryptographic tampering of bundle, validation, or source code.
  - `500 Internal Server Error`: Post-publish verification failure (clean rollback executed).

---

## 7. Verification Evidence & Test Execution

### 1. Candidate Promotion Service Test Suite
```bash
.venv/bin/pytest tests/ai/candidates/test_candidate_promotion_service.py -v
```
**Result: 42 passed in 0.75s**
- `test_unauthenticated_caller_denied_promotion`: PASS
- `test_ai_agent_caller_strictly_denied_promotion`: PASS
- `test_forbidden_principal_identities_denied_promotion`: PASS (claude, gpt-4o, creative_planner, anonymous, system-worker)
- `test_insufficient_role_denied_promotion`: PASS (viewer, editor, reviewer)
- `test_cross_tenant_promotion_denied`: PASS
- `test_path_traversal_template_id_denied`: PASS (`../../escape`, `../escape`, `templates/sub`, `/root/escape`, `\\windows\\path`)
- `test_invalid_template_id_naming_denied`: PASS (PascalCase, spaces, snake_case, special chars, leading/trailing hyphens)
- `test_existing_canonical_template_collision_denied`: PASS
- `test_non_approved_candidate_denied_promotion`: PASS (DRAFT, VALIDATING, VALIDATED, AWAITING_APPROVAL, REJECTED, PROMOTED, RETIRED)
- `test_missing_review_decision_denied_promotion`: PASS
- `test_rejected_decision_denied_promotion`: PASS
- `test_failing_validation_reports_denied_promotion`: PASS
- `test_tampered_candidate_content_hash_denied`: PASS
- `test_tampered_review_bundle_hash_denied`: PASS
- `test_tampered_static_report_hash_denied`: PASS
- `test_tampered_runtime_report_hash_denied`: PASS
- `test_cas_expected_revision_mismatch_denied`: PASS
- `test_successful_canonical_promotion`: PASS
- `test_promotion_idempotency_retry`: PASS
- `test_post_publish_verification_failure_triggers_clean_rollback`: PASS

### 2. Candidate Architecture Guards Suite
```bash
.venv/bin/pytest tests/ai/candidates/test_candidate_architecture_guards.py -v
```
**Result: 11 passed in 0.15s**
- `test_no_raw_sql_in_candidates_domain`: PASS
- `test_no_raw_filesystem_writes_in_candidates_domain`: PASS
- `test_candidate_subsystem_has_no_registry_mutation_rights`: PASS
- `test_validation_layer_has_no_promotion_or_approval_authority`: PASS
- `test_review_service_has_no_promotion_or_registry_authority`: PASS
- `test_router_has_no_direct_candidate_status_assignment`: PASS
- `test_ai_layer_has_no_direct_candidate_approval`: PASS
- `test_validation_layer_has_no_package_manager_execution`: PASS
- `test_ai_layer_has_no_promotion_authority`: PASS
- `test_router_has_no_direct_candidate_promotion_mutation`: PASS
- `test_promotion_service_is_sole_promoted_status_authority`: PASS

### 3. API Transport & Authorization Router Test Suite
```bash
.venv/bin/pytest tests/api/test_candidate_promotions_router.py -v
```
**Result: 8 passed in 1.00s**
- `test_viewer_or_reviewer_denied_promotion_403`: PASS
- `test_ai_agent_caller_strictly_denied_promotion_403`: PASS
- `test_cross_tenant_candidate_promotion_denied_404`: PASS
- `test_unapproved_candidate_denied_promotion_400`: PASS
- `test_stale_expected_revision_denied_promotion_409`: PASS
- `test_colliding_target_template_id_denied_promotion_409`: PASS
- `test_path_traversal_template_id_denied_promotion_403`: PASS
- `test_successful_promotion_flow_and_spoof_ignorance_200`: PASS

### 4. Full Candidate Subsystem Suite
```bash
.venv/bin/pytest tests/ai/candidates/ -v
```
**Result: 136 passed in 115.82s**

### 5. Production Template Registry Consistency Check
```bash
.venv/bin/pytest tests/validators/test_template_registry_consistency.py -v
```
**Result: 4 passed in 0.27s (All 105 canonical templates remain pristine and unaltered)**

### 6. Creative Contracts TypeScript Parity Suite
```bash
npx vitest run tests/remotion/creative_contracts_parity.test.ts
```
**Result: 12 passed in 284ms**

---

## 8. Summary Table of Enforced Invariants

| Invariant | Enforcement Mechanism | Failure Response | Status |
| :--- | :--- | :--- | :--- |
| **Sole Authority** | `PromotionService` is the only component setting `status=PROMOTED` and invoking publisher | AST & architecture guard tests fail build | **VERIFIED** |
| **Non-AI Promoters** | Principal check rejects `AI_AGENT` and AI IDs (`gpt-4o`, `claude`, etc.) | `403 Forbidden` (`CandidatePermissionError`) | **VERIFIED** |
| **RBAC Authority** | `Action.TEMPLATE_PROMOTE` restricted to `Role.ADMIN` in matrix | `403 Forbidden` (`CandidatePermissionError`) | **VERIFIED** |
| **Server Identity** | Client payload fields (`promoter_id`, `role`) discarded; server principal used | Spoofing ignored; server identity bound | **VERIFIED** |
| **Preconditions** | Candidate must be `APPROVED` with verified passing static & runtime evidence | `400 Bad Request` (`PromotionPreconditionError`) | **VERIFIED** |
| **Tamper Resistance** | Hashes of bundle, decision, validation reports, and code must match SHA-256 | `422 Unprocessable` (`PromotionTamperedError`) | **VERIFIED** |
| **Naming Safety** | Strict kebab-case regex `^[a-z0-9]+(-[a-z0-9]+)*$` & path traversal block | `403 Forbidden` (`PromotionSecurityError`) | **VERIFIED** |
| **Collision Block** | Cannot collide with existing canonical templates or aliases | `409 Conflict` (`PromotionCollisionError`) | **VERIFIED** |
| **Staged Publication** | Isolated temp staging area generates derivatives before live touch | Pre-commit validation aborts staging | **VERIFIED** |
| **Rollback Journal** | Disk backup records created; post-publish failure triggers clean restore | Live files restored byte-for-byte; candidate remains `APPROVED` | **VERIFIED** |
| **Idempotency** | Exact duplicate promotion calls return existing `COMMITTED` record | 200 OK with identical `promotion_id`; no duplicate registry entries | **VERIFIED** |
| **Audit Durability** | Manifest and promotion record persisted with pre/post registry hashes | Durable records stored in DB & storage | **VERIFIED** |

---

## 9. Conclusion

`S28-07E` is fully implemented and verified. The canonical template registry publication pipeline now operates with cryptographic tamper-resistance, zero-mutation preflights, isolated staging, transactional rollback journals, and strict human authorization. The system is ready for `S28-07F` (Full CREATE E2E & Template Reuse).
