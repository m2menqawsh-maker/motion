# PR-003: AI Runtime Integration & Production Vertical Slice — Implementation & Test Report

**Date:** 2026-10-08
**Branch:** `remediation/pr-003-ai-runtime-vertical-slice`
**Base Commit (PR-002 Tip):** `99f051459a0ccdbcf74876d0da822509f18b3b52`
**Ancestor (PR-001 Hardening):** `cf95b2e63bebe11e9b4f70d86da0de00b583e316`
**Status:** PARTIAL (Full End-to-End AI-to-Canonical-Authoring Slice Verified; Render E2E Not Observed due to Webpack Bundler Blocker)

---

## 1. Executive Summary & Root Cause

### Root Cause of Pre-Patch Disconnection
Prior to PR-003, the creative intelligence subsystem under `ai/` (`IntentParser`, `CreativeBriefBuilder`, `RecipeSelector`, `NarrativePlanner`, `CreativePlanner`, `CreativeTierPolicy`, `BlueprintCompiler`) existed as an isolated algorithmic pipeline tested only via isolated unit tests in `tests/ai/`.

The authoritative HTTP API (`api/routers/authoring.py`) only exposed:
1. `GET /{project_id}/document` (canonical read)
2. `POST /{project_id}/mutate` (low-level human/script mutation)
3. `POST /{project_id}/intent` (pre-compiled typed action bridging to TypeScript)

There was **zero** public HTTP entrypoint accepting natural language and driving the deterministic Python AI creative intelligence stack to produce a valid canonical video blueprint. In addition, no bridge existed to safely commit AI proposals through `CanonicalDocumentRepository` with tenant boundary verification, optimistic concurrency control (CAS), and durable idempotency (`AuthoringIdempotencyRepository`).

### Remediation Delivered
PR-003 establishes exactly ONE coherent, secure, production vertical slice:
1. **Advisory Proposal Generation:** `POST /projects/{project_id}/creative/proposals`
   - Server-verified `TenantContext` enforcement (`Action.AUTHORING_EDIT`).
   - Executes real `IntentParser` -> `CreativeBriefBuilder` -> `RecipeSelector` -> `NarrativePlanner` -> `CreativePlanner` -> `CreativeTierPolicy` -> `BlueprintCompiler` -> `validate_blueprint_v2`.
   - Strictly advisory (`status="PROPOSED"`, `approval_required=true`): zero automatic mutation, zero `.studio_approved` file writing, zero unauthorized run triggering.
2. **Authoritative Human Apply / Commit:** `POST /projects/{project_id}/creative/apply`
   - Server-verified `TenantContext` (`Action.AUTHORING_EDIT`).
   - Enforces transactional CAS revision increment (`expected_revision == curr_rev`) via `CanonicalDocumentRepository.commit_candidate`.
   - Enforces durable cross-worker idempotency via `AuthoringIdempotencyRepository`.
   - Immutable artifact storage via `StorageService`.

---

## 2. Before / After Runtime Call Graph

### Before PR-003 (Disconnection)
```text
HTTP Client -> [api/routers/authoring.py: POST /projects/{id}/intent]
                     |
                     +--> AuthoringService.execute_authoring()
                             |
                             +--> scripts/execute_authoring_mutation.ts (TS Bridge)
                                     |
                                     x [DISCONNECTED from ai/ domain stack]

ai/ Intent -> Brief -> Recipe -> Narrative -> Plan -> Compiler
    (Called ONLY within hermetic unit tests in tests/ai/planning/ and tests/ai/recipes/)
```

### After PR-003 (Connected Production Vertical Slice)
```text
[1. Proposal Generation]
HTTP Client: POST /projects/{project_id}/creative/proposals
    |
    v (FastAPI Dependency)
api/core/auth.py: require_tenant_context(Action.AUTHORING_EDIT)
    |-- Verifies HMAC-SHA256 Bearer Token
    |-- Queries TenantRepository for Project & Workspace Membership (Role >= EDITOR)
    v
api/routers/authoring.py: generate_creative_proposal() [line 229]
    v
api/services/creative_service.py: CreativeService.generate_proposal() [line 103]
    |-- validate_project_id() (path traversal defense)
    |-- Prompt injection defense (regex guard against role/gate override)
    |-- IntentParser._detect_contradictions() [ai/intent/parser.py]
    |-- CreativeBriefBuilder.build_brief() [ai/intent/brief_builder.py: line 44]
    |-- RecipeSelector.select_recipe() [ai/recipes/selector.py: line 38]
    |-- NarrativePlanner.plan() [ai/narrative/planner.py: line 48]
    |-- CreativePlanner.plan() [ai/planning/creative_planner.py: line 55]
    |-- CreativeTierPolicy.decide() [ai/planning/tier_policy.py: line 42]
    |-- BlueprintCompiler.compile() [ai/planning/compiler.py: line 77]
    |-- validate_blueprint_v2() [scripts/core/blueprint_validator.py: line 35]
    v
Returns CreativeProposalResponse (status="PROPOSED", approval_required=True, can_apply=True)
[DB, Filesystem, and Runs remain completely unmutated]

[2. Human Review & Explicit Apply]
HTTP Client: POST /projects/{project_id}/creative/apply
    |
    v (FastAPI Dependency)
api/core/auth.py: require_tenant_context(Action.AUTHORING_EDIT)
    v
api/routers/authoring.py: apply_creative_proposal() [line 257]
    v
api/services/creative_service.py: CreativeService.apply_proposal() [line 302]
    |-- AuthoringIdempotencyRepository.try_claim_leader()
    |-- validate_blueprint_v2() (schema verification)
    |-- CanonicalDocumentRepository.commit_candidate() [scripts/core/canonical_document_repository.py: line 136]
    |       |-- StorageService.put() (immutable generation uploaded)
    |       |-- SQL IMMEDIATE Transaction:
    |       |       UPDATE project_states SET revision = curr+1 WHERE revision = expected
    |       |       INSERT INTO project_artifact_versions
    |-- AuthoringIdempotencyRepository.mark_completed()
    v
Returns {"success": True, "result_revision": 2, "storage_key": "...", "idempotent": False}

[3. Authoritative Document Read]
HTTP Client: GET /projects/{project_id}/document
    v
api/routers/authoring.py: get_canonical_document() [line 29]
    v
AuthoringService.get_canonical_document() -> CanonicalDocumentRepository.get_document()
    v Returns committed BlueprintV2 with ETag: "2"
```

---

## 3. Boundary Contracts and Ownership

| Boundary | Request / Input Contract | Response / Output Contract | Transactional Owner | Persistence Target |
| :--- | :--- | :--- | :--- | :--- |
| **Proposal API** | `CreativeProposalRequest` (`prompt`, `aspect_ratio`, `audio_mode`, `target_duration`) | `CreativeProposalResponse` (`proposal_id`, `status="PROPOSED"`, `candidate_blueprint`) | Stateless / Read-Only | None (In-Memory Advisory) |
| **AI Perception** | Natural Language Text | `CreativeBrief` | `CreativeBriefBuilder` | Transient Value Object |
| **AI Selection** | `CreativeBrief` | `RecipeDefinition` | `RecipeSelector` | `RecipeRegistry` |
| **AI Planning** | `CreativeBrief` + `RecipeDefinition` | `CreativePlan` + `NarrativePlan` | `CreativePlanner` | Transient Value Object |
| **Compilation** | `CreativePlan` + Template Decisions | Canonical `BlueprintV2` | `BlueprintCompiler` | In-Memory Model |
| **Apply API** | `ApplyCreativeProposalRequest` (`proposal_id`, `blueprint`, `base_revision`) | Commit Confirmation (`result_revision`, `storage_key`) | `CanonicalDocumentRepository` | SQL `project_states` + `StorageService` |
| **Run Enqueue** | `RunCreateRequest` (`idempotency_key`) | `RunResponse` (`run_id`, `status="QUEUED"`) | `RunService` | SQL `runs` (preserving `workspace_id`) |

---

## 4. Gates G01–G14 Status Table

| Gate | Title | Status | Limiting Conditions / Evidence |
| :--- | :--- | :---: | :--- |
| **G01** | Ancestry & Branch Hygiene | **PASS** | Base commit `99f051459a0ccdbcf74876d0da822509f18b3b52` verified. Dedicated branch `remediation/pr-003-ai-runtime-vertical-slice`. |
| **G02** | Runtime Call Graph & Disconnect Evidence | **PASS** | Captured 404 pre-patch disconnection in RED test; full trace documented in Section 2. |
| **G03** | Server-Verified Tenant Context | **PASS** | Guarded by `require_tenant_context(Action.AUTHORING_EDIT)`; cross-tenant calls reject with 403. |
| **G04** | Natural Language Reaches Real AI Domain | **PASS** | Unmocked `IntentParser`, `BriefBuilder`, `RecipeSelector`, `NarrativePlanner`, and `CreativePlanner` executed. |
| **G05** | Typed Validated Contracts Exchanged | **PASS** | All stages strictly exchange Pydantic models (`CreativeBrief`, `RecipeDefinition`, `CreativePlan`, `BlueprintV2`). |
| **G06** | Registered Templates & Canonical Validation | **PASS** | Templates verified against `TemplateRegistryContract`; validated via `validate_blueprint_v2`. |
| **G07** | Proposal vs Apply Separation & Human Gates | **PASS** | Proposal generation is advisory (`status="PROPOSED"`); no `.studio_approved` written; apply is separate explicit call. |
| **G08** | Canonical Persistence with CAS & Idempotency | **PASS** | Transactional CAS tested (`base_revision` mismatch -> 409 `REVISION_CONFLICT`); durable idempotency tested. |
| **G09** | Independent Run Enqueue with Workspace Ownership | **PASS** | `POST /projects/{id}/runs` creates `RunRecord` in `RunRepository` preserving owning `workspace_id`. |
| **G10** | Tenant Isolation, Least Privilege & Injection Defense | **PASS** | Viewer Eve rejected (403); foreign Bob rejected (403); prompt injection rejected (400); contradictions rejected (400). |
| **G11** | Unmocked API-to-Canonical-Authoring Integration | **PASS** | Unmocked integration verified via `TestClient(app)` calling real SQLite DB, real LocalStorageBackend, and real AI stack. |
| **G12** | Render E2E Verification | **BLOCKED** | **RUNTIME_RENDER_E2E_NOT_OBSERVED** (Webpack alias resolution error in Remotion bundler for `@/engine/audio/AudioManager`). |
| **G13** | Regression Test Suites | **PASS** | 303 passing tests across PR-001/PR-002, API, AI planning, narrative/intent/recipe, and Vitest suites. |
| **G14** | Git Hygiene & Safe Commit | **PASS** | `git diff --check` passed clean; zero secrets leaked; changes scoped strictly to vertical slice. |

---

## 5. End-to-End Observation Indicators

- **`RUNTIME_AI_TO_CANONICAL_DOCUMENT_OBSERVED`:** **YES**
  *Evidence:* A natural-language prompt submitted via `POST /projects/{id}/creative/proposals` generates a valid candidate `BlueprintV2`, which is explicitly applied via `POST /projects/{id}/creative/apply`, committed with CAS to SQLite `project_states` and `StorageService`, and successfully read back via `GET /projects/{id}/document` at `revision=2` with matching ETag.

- **`RUNTIME_WORKER_TO_RENDERED_MP4_OBSERVED`:** **NO**
  *Label:* `RUNTIME_RENDER_E2E_NOT_OBSERVED`
  *Exact Limiting Prerequisite:* Remotion's CLI bundler fails during module bundling because `@/engine/audio/AudioManager` referenced in `templates/effects/engine-bridge.tsx` cannot be resolved by Remotion's Webpack configuration. The Webpack config in Remotion needs an explicit path alias mapping `@/` to the repository root.

---

## 6. Real Managed Request Example (curl)

### 1. Request Advisory Creative Proposal
```bash
curl -X POST "http://localhost:8000/projects/prj_alpha_prod/creative/proposals" \
  -H "Authorization: Bearer <SERVER_SIGNED_JWT_OR_HMAC_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create a 15-second product launch video for our database tool with background music",
    "aspect_ratio": "9:16",
    "audio_mode": "VO_MUSIC",
    "target_duration": 15.0
  }'
```
*Expected Response (HTTP 200 OK):*
```json
{
  "proposal_id": "prop_a7b8c9d0e1f2",
  "status": "PROPOSED",
  "project_id": "prj_alpha_prod",
  "workspace_id": "ws_alpha",
  "base_revision": 1,
  "prompt": "Create a 15-second product launch video for our database tool with background music",
  "recipe_id": "explainer_standard",
  "narrative_hook": "Tired of slow database migrations?",
  "candidate_blueprint": {
    "blueprint_version": "2.0.0",
    "project_id": "prj_alpha_prod",
    "fps": 30,
    "aspect_ratio": "9:16",
    "scenes": [...]
  },
  "approval_required": true,
  "can_apply": true
}
```

### 2. Explicitly Apply Advisory Proposal (Human Gate Decision)
```bash
curl -X POST "http://localhost:8000/projects/prj_alpha_prod/creative/apply" \
  -H "Authorization: Bearer <SERVER_SIGNED_JWT_OR_HMAC_TOKEN>" \
  -H "If-Match: 1" \
  -H "Idempotency-Key: op_user_apply_001" \
  -H "Content-Type: application/json" \
  -d '{
    "proposal_id": "prop_a7b8c9d0e1f2",
    "blueprint": { ... candidate_blueprint from proposal ... },
    "base_revision": 1,
    "operation_id": "op_user_apply_001"
  }'
```
*Expected Response (HTTP 200 OK, ETag: "2"):*
```json
{
  "success": true,
  "operation_id": "op_user_apply_001",
  "proposal_id": "prop_a7b8c9d0e1f2",
  "base_revision": 1,
  "result_revision": 2,
  "storage_key": "workspaces/ws_alpha/projects/prj_alpha_prod/blueprints/rev_2_5f8a.../blueprint.json",
  "idempotent": false
}
```

### 3. Read Authoritative Canonical Document
```bash
curl -X GET "http://localhost:8000/projects/prj_alpha_prod/document" \
  -H "Authorization: Bearer <SERVER_SIGNED_JWT_OR_HMAC_TOKEN>"
```
*Expected Response (HTTP 200 OK, ETag: "2"):*
```json
{
  "status": "success",
  "revision": 2,
  "blueprint": { ... authoritative BlueprintV2 committed at revision 2 ... }
}
```

---

## 7. Test Summary & Regression Evidence

| Test Suite | Commands Executed | Result | Count |
| :--- | :--- | :---: | :---: |
| **PR-003 Vertical Slice** | `.venv/bin/pytest tests/integration/test_pr003_ai_runtime_vertical_slice.py -v` | **PASS** | 9 / 9 |
| **PR-001 Authentication Hardening** | `.venv/bin/pytest tests/security/test_pr001_* -v` | **PASS** | 91 / 91 |
| **PR-002 Tenant Isolation & Gates** | `.venv/bin/pytest tests/security/test_pr002_* -v` | **PASS** | 23 / 23 |
| **API Endpoints Regression** | `.venv/bin/pytest tests/api/ -v` | **PASS** | 53 / 53 |
| **AI Planning Regression** | `.venv/bin/pytest tests/ai/planning/ -v` | **PASS** | 81 / 81 |
| **AI Perception Regression** | `.venv/bin/pytest tests/ai/intent/ tests/ai/narrative/ tests/ai/recipes/ -v` | **PASS** | 29 / 29 |
| **TypeScript Vitest Authoring** | `npx vitest run tests/remotion/s28_r13_unified_authoring.test.ts` | **PASS** | 17 / 17 |
| **TOTAL** | — | **ALL PASS** | **303 / 303** |

---

## 8. Residual Risks & Next Actions

1. **Webpack Bundler Alias Configuration (Next Step for Render E2E):**
   Configure Remotion's Webpack override (`remotion.config.ts`) to resolve `@/` to the project root directory so that `templates/effects/engine-bridge.tsx` can resolve `@/engine/audio/AudioManager` cleanly during headless Chromium renders.
2. **Asset Hydration Orchestration:**
   When a proposal selects complex b-roll or avatar templates, downstream execution requires media assets to be materialized via `scripts/generators/materialize_project.py` before final Remotion compilation.
