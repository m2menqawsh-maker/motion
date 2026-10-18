# MOTION Batch 2: AI Product Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close and measurably reduce REALITY-003, REALITY-006, REALITY-007, REALITY-008, REALITY-015, and REALITY-004 by integrating existing AI subsystems (ContextBuilder, KnowledgeRouter, CapabilityRouter, ToolGateway) into the authorized production API workflow (Authenticated HTTP request → Creative Proposal → Explicit Apply → Human Approval → Run Queue → Worker → Render/QC → MP4).

**Architecture:**
- **Workstream B1 (Context & Knowledge Integration):**
  1. Idempotent canonical knowledge catalog initialization wired into FastAPI application lifespan and probed in HealthService readiness.
  2. Adapter bridging `KnowledgeRouter` to the `KnowledgeRetriever` protocol in `ai/context/`.
  3. `ContextBuilder` injected into `CreativeService.generate_proposal`, binding server-verified `TrustedTenantContext`, canonical project facts, and domain knowledge into prompt context, producing deterministic `context_hash` and diagnostics that influence the advisory proposal.
- **Workstream B2 (Capability Router & Tool Gateway Integration):**
  1. Policy-enforced `CapabilityService` mapping `TenantContext` to `TrustedToolExecutionContext` with capability allowlists and tenant isolation.
  2. API endpoints `POST /projects/{project_id}/capabilities/execute` and `GET /projects/{project_id}/capabilities` mounted in `api/main.py`.
  3. Zero automatic approval or run triggers; human decision authority preserved; offline CI deterministic execution.

**Tech Stack:** Python 3.12+, FastAPI, Pydantic v2, SQLite / WAL, Remotion / FFmpeg.

**Spec:** USER_REQUEST / Batch 2 AI Product Integration Directive.

## Global Constraints

- Preserve server-verified `TenantContext` and workspace isolation.
- Canonical source precedence: System Authority > Domain Source of Truth > Human Confirmed > Explicit User.
- Protection against prompt injection and secret leakage (`contains_secret`).
- Hard token budgeting and monotonic execution timeouts.
- No cross-tenant knowledge retrieval or capability execution.
- Preserve BlueprintV2 canonical authority, CAS revisions, and idempotency.
- Strictly offline, deterministic testing — zero paid API provider calls or credentials.
- Preserve human decision authority: AI may only propose changes (status=PROPOSED), never automatically apply, approve, or initiate runs.
- Commit, push, or create PRs ONLY after explicit owner authorization.

## Review Focus

1. Cross-tenant leakage: Actor in Workspace Alpha attempting to retrieve Workspace Beta knowledge or execute capabilities against Beta projects must be rejected with 403 / `TenantSecurityError` / `AccessDeniedError`.
2. Missing catalog gracefully handled: If knowledge references are missing or corrupted in non-strict mode, catalog initialization logs observable warnings without crashing the API process, reporting degraded readiness.
3. Prompt injection neutralization: Directives attempting to bypass role checks, approve studio runs, or override policies must fail closed with 400 Bad Request.
4. Human authority bypass prevention: Capability execution cannot trigger runs, write `.studio_approved`, or mutate canonical documents without explicit human apply.
5. Project context responsiveness: Changing authorized project context (e.g. project revision or project facts) must measurably influence the `context_hash` and creative proposal output.

---

## Tasks

### Workstream B1: Context & Knowledge Integration

#### Task B1.1: Idempotent Knowledge Catalog Initialization & Readiness Probing
- **Files:**
  - Create: `ai/knowledge/catalog_service.py`
  - Modify: `api/main.py:30-44`
  - Modify: `api/services/health_service.py:80-125`
  - Test: `tests/ai/knowledge/test_catalog_initialization_readiness.py`
- **Steps:**
  - [ ] Write failing test `tests/ai/knowledge/test_catalog_initialization_readiness.py` verifying idempotent initialization, readiness state (`is_ready`, `total_chunks`), and HealthService integration.
  - [ ] Implement `KnowledgeCatalogService` with idempotent initialization, observable logging, readiness state tracking, and safe error handling.
  - [ ] Wire `KnowledgeCatalogService.initialize_catalog()` into FastAPI `lifespan` in `api/main.py`.
  - [ ] Add `_probe_knowledge_catalog()` probe to `HealthService.check_readiness()`.
  - [ ] Run pytest to verify all tests in `test_catalog_initialization_readiness.py` pass.

#### Task B1.2: KnowledgeRouter to KnowledgeRetriever Adapter
- **Files:**
  - Create: `ai/context/adapters/knowledge_router_adapter.py`
  - Modify: `ai/context/retrieval.py`
  - Test: `tests/ai/context/test_knowledge_router_adapter.py`
- **Steps:**
  - [ ] Write failing test `tests/ai/context/test_knowledge_router_adapter.py` verifying protocol compliance with `KnowledgeRetriever`, mapping `RetrievedChunk` to `ContextItem`, secret sanitization, and tenant isolation.
  - [ ] Implement `KnowledgeRouterAdapter` adhering to `KnowledgeRetriever` protocol, forwarding queries to `KnowledgeRouter.route_knowledge()`, mapping outputs to `ContextItem` with `ContextSection.KNOWLEDGE` and `ContextAuthority.DOMAIN_SOURCE_OF_TRUTH`.
  - [ ] Run pytest to verify `test_knowledge_router_adapter.py` passes.

#### Task B1.3: ContextBuilder Integration in CreativeService
- **Files:**
  - Modify: `api/services/creative_service.py`
  - Modify: `api/schemas/creative.py`
  - Modify: `api/services/project_service.py` (ensure SQL fallback for LifecycleDTO)
  - Test: `tests/integration/test_b1_context_knowledge_creative_proposal.py`
- **Steps:**
  - [ ] Write failing test `tests/integration/test_b1_context_knowledge_creative_proposal.py` verifying:
    - Authenticated `POST /projects/{project_id}/creative/proposals` executes `ContextBuilder` and returns `context_hash` and `context_diagnostics`.
    - Knowledge items are included in proposal generation.
    - Changing project facts (e.g. revision) measurably changes `context_hash`.
    - Cross-tenant requests fail with 403 / `TenantSecurityError` without data leakage.
  - [ ] Update `CreativeProposalResponse` schema in `api/schemas/creative.py` to include `context_hash` and `context_diagnostics`.
  - [ ] Update `CreativeService`:
    - Instantiate `ContextBuilder` with `KnowledgeRouterAdapter` and `ProjectService`.
    - In `generate_proposal`, construct `ContextRequest` with server-verified `TrustedTenantContext` and invoke `_context_builder.build()`.
    - Feed assembled project facts and knowledge into the brief, narrative plan, and creative plan.
    - Populate `context_hash` and `context_diagnostics` in response.
  - [ ] Update `ProjectService.get_lifecycle_dto` with safe SQL state fallback when disk `.pipeline_state.json` is not yet materialized.
  - [ ] Run pytest to verify `test_b1_context_knowledge_creative_proposal.py` passes and existing `test_pr003_ai_runtime_vertical_slice.py` passes.

---

### Workstream B2: Capability Router & Tool Gateway Integration

#### Task B2.1: Capability Execution Service with Strict Policy
- **Files:**
  - Create: `api/services/capability_service.py`
  - Create: `api/schemas/capability.py`
  - Test: `tests/ai/tools/test_capability_service.py`
- **Steps:**
  - [ ] Write failing test `tests/ai/tools/test_capability_service.py` verifying:
    - Mapping `TenantContext` to `TrustedToolExecutionContext`.
    - Project ownership verification.
    - Capability allowlist enforcement (reject forbidden or unlisted capabilities).
    - Dispatching to `CapabilityRouter.route_and_execute()`.
    - Human authority guard (rejection of auto-runs or direct `.studio_approved` writes).
  - [ ] Define schemas in `api/schemas/capability.py` (`ExecuteCapabilityRequest`, `ExecuteCapabilityResponse`).
  - [ ] Implement `CapabilityService` with strict allowlist, tenant boundaries, timeout bounding, and audit logging.
  - [ ] Run pytest to verify `test_capability_service.py` passes.

#### Task B2.2: Capability API Endpoint Mounting & Integration
- **Files:**
  - Create: `api/routers/capabilities.py`
  - Modify: `api/main.py`
  - Test: `tests/integration/test_b2_capability_gateway_integration.py`
- **Steps:**
  - [ ] Write failing test `tests/integration/test_b2_capability_gateway_integration.py` verifying:
    - Authorized editor executes an allowed capability (e.g. `GENERATE_SPEECH_MANIFEST` or `TRIM_VIDEO`) $\to$ 200 OK with typed result.
    - Unauthorized viewer attempting mutating capability $\to$ 403 Forbidden.
    - Cross-tenant attempt (Alpha user accessing Beta project) $\to$ 403 Forbidden.
    - Invalid schema input $\to$ 400/422 Unprocessable.
    - Idempotent replay with `Idempotency-Key` header.
    - Offline CI repeatability.
  - [ ] Implement `api/routers/capabilities.py` with `POST /projects/{project_id}/capabilities/execute` and `GET /projects/{project_id}/capabilities`.
  - [ ] Register router in `api/main.py`.
  - [ ] Run pytest to verify `test_b2_capability_gateway_integration.py` passes.

---

### Verification and CI Parity

#### Task V1: Local Regression & CI Verification
- **Steps:**
  - [ ] Run focused tests: `pytest tests/ai/context/ tests/ai/knowledge/ tests/ai/routing/ tests/ai/tools/ tests/integration/`
  - [ ] Run gate `python-quality` (`ruff check api/ scripts/core/`).
  - [ ] Run gate `python-tests` (`pytest tests/ -m "not e2e"`).
  - [ ] Run gate `contracts-ts` (`npm run test` in remotion-app if needed).
  - [ ] Run `scripts/ci/run_required_checks.sh --skip-docker`.
  - [ ] Prepare comprehensive evidence report for owner review.
