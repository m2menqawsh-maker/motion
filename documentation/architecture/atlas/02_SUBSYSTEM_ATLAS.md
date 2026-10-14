# MOTION Architecture Atlas — Subsystem Atlas

> **Scope:** Comprehensive architectural and operational breakdown of the ten primary production subsystems powering MOTION.
> **Standard:** For each subsystem, this document details purpose, inputs, outputs, dependencies, entry points, processing stages, state ownership, trust boundaries, failure modes, observability, and automated test coverage.

---

## Subsystem 1: HTTP Transport & Ingestion Subsystem

### 1.1 Purpose
The HTTP Transport subsystem is MOTION's public and internal API gateway. It receives incoming client requests, enforces HTTP protocol semantics, validates JSON payloads against Pydantic schemas, handles asynchronous routing, and formats standardized HTTP responses.

### 1.2 Problem It Solves
Prevents malformed data, unvalidated parameters, or unhandled exceptions from reaching core domain services. It provides clean separation between network protocols and business domain logic.

### 1.3 Inputs & Outputs
- **Inputs:** HTTP requests (GET, POST, PUT, DELETE) carrying JSON bodies, query strings, authorization headers (`Authorization: Bearer ...` or HMAC headers), and byte-range headers (`Range: bytes=...`).
- **Outputs:** Standardized JSON responses (`200 OK`, `201 Created`, `202 Accepted`), HTTP status error envelopes (`400`, `401`, `403`, `404`, `409`, `422`, `500`), and binary media byte streams (`206 Partial Content`).

### 1.4 Dependencies
- **Upstream:** External API clients, web frontends, webhook dispatchers.
- **Internal:** `api/dependencies.py`, `api/services/*`, `api/middleware/*`, `fastapi`, `pydantic`.

### 1.5 Entry Points & Source Files
- Entrypoint: [`api/main.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/api/main.py) (`create_app()`).
- Routers:
  - [`api/routers/auth.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/api/routers/auth.py): Authentication tokens and session verification.
  - [`api/routers/projects.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/api/routers/projects.py): Project lifecycle and state inspection.
  - [`api/routers/creative.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/api/routers/creative.py): Creative briefs, AI proposal generation, and proposal application.
  - [`api/routers/review.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/api/routers/review.py): Review bundles, contact sheet thumbnails, and approval decisions.
  - [`api/routers/runs.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/api/routers/runs.py): Render execution enqueueing and run status polling.
  - [`api/routers/artifacts.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/api/routers/artifacts.py): Media artifact metadata and HTTP 206 range streaming.
  - [`api/routers/assets.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/api/routers/assets.py): Asset uploading, hashing, and resolution.
  - [`api/routers/health.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/api/routers/health.py): Liveness and readiness probes.

### 1.6 Internal Processing Stages
1. Request Ingestion & Header Parsing (FastAPI/Starlette).
2. Rate Limiting & Audit Logging Middleware.
3. Tenant Identity Extraction (`api/dependencies.py`).
4. Schema Validation against Pydantic models.
5. Domain Service Invocation.
6. Error Mapping (translates domain exceptions into structured JSON error envelopes).

### 1.7 State & Data Ownership
Stateless. The transport layer does not hold state; it delegates persistence entirely to domain services and database repositories.

### 1.8 Trust Boundaries
The boundary between the untrusted public network and the trusted application core. All inputs are considered hostile until validated.

### 1.9 Failure Modes & Handling
- **Malformed JSON / Validation Error:** Returns `422 Unprocessable Entity` with field-level error details.
- **Authentication Failure:** Returns `401 Unauthorized`.
- **Domain Concurrency Conflict:** Returns `409 Conflict`.
- **Unhandled Exceptions:** Caught by global exception handlers; returns `500 Internal Server Error` with an internal incident ID while logging the trace.

### 1.10 Observability & Relevant Tests
- **Logs:** Structured JSON access logs with request ID, client IP, route, response status, and duration.
- **Tests:** `tests/api/`, `tests/e2e/test_product_http_to_mp4_e2e.py`.

---

## Subsystem 2: Multi-Tenancy, Authentication & Security Subsystem

### 2.1 Purpose
Ensures complete isolation between tenants, authenticates API callers, validates workspace authority, protects against path traversal and symlink attacks, and sanitizes process execution environments.

### 2.2 Problem It Solves
Prevents Tenant A from viewing, modifying, or executing projects, assets, or videos belonging to Tenant B. Prevents malicious commands from escaping into the operating system.

### 2.3 Inputs & Outputs
- **Inputs:** API keys, HMAC signatures, JWT tokens, tenant identifiers, workspace paths.
- **Outputs:** Verified `AuthContext` objects (`tenant_id`, `workspace_id`, `roles`), sanitized filesystem paths, sanitized environment dictionaries.

### 2.4 Dependencies
- **Internal:** `hashlib`, `hmac`, `secrets`, `scripts/core/security/command_policy.py`, `scripts/core/security/path_sanitizer.py`.

### 2.5 Entry Points & Source Files
- [`api/auth/service.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/api/auth/service.py): Authentication verification and token issuing.
- [`api/middleware/auth.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/api/middleware/auth.py): Request authentication filter.
- [`scripts/core/security/command_policy.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/scripts/core/security/command_policy.py): Shell command whitelisting and environment sanitization.
- [`scripts/core/security/path_sanitizer.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/scripts/core/security/path_sanitizer.py): Jail-checking and canonical path resolution.

### 2.6 Internal Processing Stages
1. **Signature Verification:** Validates request signature or bearer token against tenant secrets.
2. **Context Binding:** Sets request-scoped `AuthContext`.
3. **Storage Boundary Enforcement:** Intercepts all file accesses; resolves absolute paths and confirms they reside strictly inside the tenant workspace root.
4. **Environment Sanitization:** When launching child processes (FFmpeg, Remotion, Python), strips dangerous environment variables (`LD_PRELOAD`, raw tokens) while preserving whitelisted configurations (`DATABASE_URL`, `PATH`).

### 2.7 State & Data Ownership
Owns the tenant API credentials store and workspace permission maps.

### 2.8 Trust Boundaries
Validates all incoming identity tokens before domain services receive them. Isolates operating system execution from untrusted project definitions.

### 2.9 Failure Modes & Handling
- **Signature Mismatch / Expired Token:** Rejection with `401 Unauthorized`.
- **Cross-Tenant Access Attempt:** Immediate `403 Forbidden` or `404 Not Found` (to avoid leaking resource existence).
- **Path Traversal Escape (`../`):** Triggers `SecurityViolationError` and aborts request.

### 2.10 Observability & Relevant Tests
- **Logs:** Security audit logs recording authentication failures, path traversal attempts, and rejected commands.
- **Tests:** `tests/auth/`, `tests/security/`, `test_adversarial_cross_tenant_isolation_and_rejections` in `tests/e2e/test_product_http_to_mp4_e2e.py`.

---

## Subsystem 3: AI Creative Intelligence & Narrative Planning Subsystem

### 3.1 Purpose
Translates high-level natural language creative requests into mathematically precise, visually harmonious video blueprints. It selects production recipes, structures narrative arcs, calculates audio/speech timings, assigns typography and color palettes, and compiles the final composition blueprint.

### 3.2 Problem It Solves
Replaces subjective, unpredictable video drafting with a deterministic creative engine. Ensures that scenes match brand guidelines, text does not overlap, speech fits into video cuts, and audio transitions smoothly.

### 3.3 Inputs & Outputs
- **Inputs:** `CreativeBrief` (topic, target duration, aspect ratio, tone, brand colors, voiceover script or topic prompt).
- **Outputs:** `CreativeProposal`, `ScenePlan`, and canonical `BlueprintSpec` (scenes, components, props, animations, audio stems).

### 3.4 Dependencies
- **Internal:** `recipes/` (18 production recipes), `ai/narrative/planner.py`, `ai/composition/compiler.py`, `ai/taste/engine.py`, `ai/contracts/creative/*`.
- **External (Optional/Advisory):** OpenAI, Anthropic, or local heuristic fallback planners.

### 3.5 Entry Points & Source Files
- [`ai/orchestration/planner.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/ai/orchestration/planner.py): High-level creative workflow coordinator.
- [`ai/recipes/matcher.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/ai/recipes/matcher.py): Recipe selection and suitability scoring.
- [`ai/narrative/planner.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/ai/narrative/planner.py): Scene breakdown, pacing, and word-budget calculations.
- [`ai/composition/compiler.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/ai/composition/compiler.py): Emits the final Remotion-compatible `05_blueprint.json`.
- [`ai/taste/engine.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/ai/taste/engine.py): Taste Gates and typographic constraint enforcement.

### 3.6 Internal Processing Stages
1. **Brief Ingestion & Intent Parsing:** Analyzes prompt keywords, duration bounds, and aspect ratio.
2. **Recipe Selection:** Evaluates 18 production recipes (e.g., `dynamic-montage-ad`, `living-canvas-explainer`, `tabletop-explainer`) and selects the highest scoring match.
3. **Narrative Construction:** Allocates scenes (Hook, Problem, Solution, Call to Action) with exact frame timings.
4. **Speech Alignment & Audio Budgeting:** Verifies spoken words per second (target 2.5 - 3.2 wps) and positions background music cues.
5. **Blueprint Compilation:** Serializes components, spring animations, and layout coordinates into `05_blueprint.json`.

### 3.7 State & Data Ownership
Generates immutable `CreativeProposal` instances. Does not directly mutate the canonical project state until the user explicitly applies the proposal.

### 3.8 Trust Boundaries
Advisory only. Outputs must pass schema validation and taste gate verification before being accepted into the project.

### 3.9 Failure Modes & Handling
- **Provider API Timeout / Failure:** Graceful fallback to deterministic local heuristic planning.
- **Duration Constraint Violation:** Re-normalizes scene timings to match requested total duration.
- **Unsatisfied Recipe Requirements:** Falls back to the universal baseline recipe.

### 3.10 Observability & Relevant Tests
- **Logs:** Logs recipe matching scores, narrative scene durations, and blueprint validation warnings.
- **Tests:** `tests/ai/`, `tests/ai/e2e/test_s28_m11_product_e2e_matrix.py` (16 Golden Journeys).

---

## Subsystem 4: Context, Knowledge, Skills & Tool Gateway Subsystem

### 4.1 Purpose
Manages system knowledge, operational skills, execution context, and mediates all external capability requests (e.g., media search, text-to-speech, transcription) through a governed, audit-logged gateway.

### 4.2 Problem It Solves
Prevents direct, unmonitored external network calls, vendor lock-in, and uncontrolled tool execution. Ensures all external interactions conform to architectural governance.

### 4.3 Inputs & Outputs
- **Inputs:** Capability requests (`text_to_speech`, `stock_media_search`, `speech_alignment`).
- **Outputs:** Verified capability results (audio buffers, media metadata, timing alignments).

### 4.4 Dependencies
- **Internal:** `ai/contracts/creative/skills_knowledge.py`, `ai/knowledge/loader.py`, `ai/skills/loader.py`, `ai/tools/gateway.py`, `scripts/core/routing/capability_router.py`.

### 4.5 Entry Points & Source Files
- [`ai/context/assembler.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/ai/context/assembler.py): Builds unified context for creative generation.
- [`ai/knowledge/loader.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/ai/knowledge/loader.py): Ingests and SHA-256 verifies knowledge descriptors.
- [`ai/skills/loader.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/ai/skills/loader.py): Loads and validates operational skill definitions.
- [`ai/tools/gateway.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/ai/tools/gateway.py): Mediates capability invocations and enforces rate limits.

### 4.6 Internal Processing Stages
1. Capability Request Received (e.g., synthesize voiceover).
2. Gateway checks capability authorization for the caller.
3. Capability Router selects provider (e.g., ElevenLabs if configured, or local TTS fallback).
4. Gateway logs invocation to security audit trail.
5. Response normalized into canonical contract schema.

### 4.7 State & Data Ownership
Owns the in-memory registry of validated skills and knowledge descriptors.

### 4.8 Trust Boundaries
The gateway is the boundary between internal planners and external web/media APIs.

### 4.9 Failure Modes & Handling
- **Provider Outage:** Circuit breaker trips after 3 failures; routes to secondary provider or local fallback.
- **Knowledge Hash Mismatch:** Strict mode rejects tampered reference documents.

### 4.10 Observability & Relevant Tests
- **Logs:** Circuit breaker state transitions, capability latency metrics, audit trail logs.
- **Tests:** `tests/ai/unit/test_s28_02_skills_knowledge.py`, `tests/ai/unit/test_s28_10_tool_gateway.py`.

---

## Subsystem 5: Canonical Document Repository & Project State Subsystem

### 5.1 Purpose
Acts as the single authoritative source of truth for project configuration, scene blueprints, media asset manifests, and project lifecycle state. Enforces optimistic concurrency control (CAS) on updates.

### 5.2 Problem It Solves
Eliminates file desynchronization, concurrent write corruption, and "split-brain" project states between API workers and render processes.

### 5.3 Inputs & Outputs
- **Inputs:** Canonical documents (`01_brief.json`, `04_timings.json`, `05_blueprint.json`, `06_manifest.json`), target revisions, update payloads.
- **Outputs:** Persisted documents with monotonic state revisions, SHA-256 document hashes, and event notifications.

### 5.4 Dependencies
- **Internal:** Relational database (`projects`, `project_documents`, `project_state` tables), `api/services/canonical_document_service.py`, `api/services/project_service.py`.

### 5.5 Entry Points & Source Files
- [`api/services/canonical_document_service.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/api/services/canonical_document_service.py): Document storage, hashing, and CAS versioning.
- [`api/services/project_service.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/api/services/project_service.py): High-level project metadata and workspace mapping.
- [`scripts/core/models/project.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/scripts/core/models/project.py): Database entity definitions.

### 5.6 Internal Processing Stages
1. Read Document Request: Fetches document content from database or disk cache, verifies SHA-256 hash.
2. Update Document Request:
   - Compares expected revision with database revision.
   - If mismatch -> throws `RevisionConflictError` (`409 Conflict`).
   - If match -> increments revision, recomputes SHA-256 hash, writes atomically, and invalidates stale caches.

### 5.7 State & Data Ownership
Sole persistence authority for canonical project documents. All other subsystems read from this repository.

### 5.8 Trust Boundaries
Accessible only to authenticated tenant requests scoped to the project's workspace.

### 5.9 Failure Modes & Handling
- **Concurrent Update Conflict:** Reject with `409 Conflict`, caller must reload and re-apply.
- **Corrupt Document Hash:** Storage verification error, triggers rollback or recovery from backup.

### 5.10 Observability & Relevant Tests
- **Logs:** State revision increment logs, CAS conflict warnings, document SHA-256 audit logs.
- **Tests:** `tests/services/test_canonical_document_service.py`, `test_adversarial_cross_tenant_isolation_and_rejections`.

---

## Subsystem 6: Review, Governance & Human Approval Subsystem

### 6.1 Purpose
Guarantees that no video is rendered without explicit, cryptographically verifiable authorization. Builds `ReviewBundle` artifacts (including pre-render contact sheets) and validates `ReviewDecision` records.

### 6.2 Problem It Solves
Prevents runaway cloud rendering costs, accidental generation of unapproved drafts, and unauthorized alteration of content between review and render.

### 6.3 Inputs & Outputs
- **Inputs:** Project ID, canonical blueprint, Probe QC contact sheet, human/policy decision (`APPROVED` / `REJECTED`).
- **Outputs:** Sealed `ReviewBundle`, cryptographic approval signature bound to blueprint SHA-256 hash.

### 6.4 Dependencies
- **Internal:** `api/services/review_service.py`, `scripts/gates/probe_qc.py`, `contracts/governance/*`, HMAC secrets.

### 6.5 Entry Points & Source Files
- [`api/services/review_service.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/api/services/review_service.py): Bundle construction and signature verification.
- [`api/routers/review.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/api/routers/review.py): Review endpoints (`GET /review`, `POST /review/decision`).
- [`creative_governance/`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/creative_governance/): Governance policy rules and taste guidelines.

### 6.6 Internal Processing Stages
1. Construct Review Bundle: Gathers current blueprint, scene timings, asset licenses, and executes `probe_qc.py` to create a visual contact sheet.
2. Client Inspects Bundle: Reviewer evaluates the contact sheet.
3. Submit Approval: Client posts `status="APPROVED"`.
4. Cryptographic Binding: Service hashes the current blueprint, signs `(project_id, blueprint_hash, timestamp, approver)` using system HMAC secret, and persists the approval.
5. Render Gate Check: Prior to rendering, worker checks if `signature(blueprint_hash) == valid`. If invalid, render is blocked immediately.

### 6.7 State & Data Ownership
Owns `review_bundles` and `review_decisions` database tables.

### 6.8 Trust Boundaries
The governance gate between creative planning and expensive computational execution.

### 6.9 Failure Modes & Handling
- **Missing Approval:** Render fails closed (`RENDER_NOT_AUTHORIZED`).
- **Blueprint Modified Post-Approval:** Hash mismatch triggers instant rejection (`RENDER_NOT_AUTHORIZED`).

### 6.10 Observability & Relevant Tests
- **Logs:** Approval events, signature validations, gate block incidents.
- **Tests:** `test_adversarial_unapproved_run_fails_closed` in `tests/e2e/test_product_http_to_mp4_e2e.py`.

---

## Subsystem 7: Durable Execution, Run Repository & Worker Subsystem

### 7.1 Purpose
Manages long-running render jobs, run queues, background worker pools, exclusive project lease fencing, and crash recovery.

### 7.2 Problem It Solves
Guarantees that rendering jobs do not get lost when a server restarts, workers do not conflict on the same project simultaneously, and jobs are safely recovered or marked failed without leaking resources.

### 7.3 Inputs & Outputs
- **Inputs:** Enqueue run request (`project_id`, `idempotency_key`, `render_options`).
- **Outputs:** `RunRecord` (status: `QUEUED` -> `CLAIMED` -> `RUNNING` -> `COMPLETED` / `FAILED`), run logs, final artifact metadata.

### 7.4 Dependencies
- **Internal:** `scripts/core/worker.py`, `scripts/core/run_repository.py`, `scripts/core/project_lock.py`, `scripts/pipeline.py`.
- **Database:** `runs`, `project_leases`, `idempotency_keys` tables.

### 7.5 Entry Points & Source Files
- [`api/services/run_service.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/api/services/run_service.py): API-level run management.
- [`scripts/core/run_repository.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/scripts/core/run_repository.py): SQL database engine for runs and leases.
- [`scripts/core/worker.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/scripts/core/worker.py): Worker polling loop, lease heartbeat, and job dispatch.
- [`scripts/core/project_lock.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/scripts/core/project_lock.py): `ProjectExecutionLock` managing exclusive project-level leases.

### 7.6 Internal Processing Stages
1. **Enqueue:** Inserts run into SQL repository. If idempotency key matches an existing active run, returns existing run without duplicate enqueue.
2. **Worker Polling:** Worker queries for `QUEUED` runs and attempts atomic claim.
3. **Lease Acquisition:** Worker acquires an exclusive lease on `project_id` via `ProjectExecutionLock` (resolving `workspace_id` to satisfy foreign keys).
4. **Heartbeat Thread:** Dedicated thread updates lease timestamp every N seconds.
5. **Execution:** Worker executes the pipeline orchestrator (`scripts/pipeline.py`).
6. **Completion / Cleanup:** Worker releases project lock and transitions run to `COMPLETED` or `FAILED`.

### 7.7 State & Data Ownership
Owns durable run states, worker registrations, and active project leases.

### 7.8 Trust Boundaries
Ensures that multiple workers in a cluster do not step on each other or overwrite concurrent renders.

### 7.9 Failure Modes & Handling
- **Worker Crash:** Heartbeat ceases; lease expires. Recovery sweep marks run `FAILED` or re-queues it based on retry policy.
- **Concurrent Run Attempt:** Blocked by `ProjectExecutionLock` (`LockAcquisitionError`).

### 7.10 Observability & Relevant Tests
- **Logs:** Run state transitions, lease acquisition/renewal timestamps, heartbeat logs.
- **Tests:** `tests/services/test_run_service.py`, `tests/core/test_project_lock.py`.

---

## Subsystem 8: Remotion & FFmpeg Video Rendering Subsystem

### 8.1 Purpose
The computational engine that turns the canonical blueprint into an actual video file. It materializes project assets, builds the Remotion bundle, evaluates React visual compositions, renders individual video frames, and multiplexes audio with FFmpeg.

### 8.2 Problem It Solves
Provides pixel-perfect typography, fluid spring-based animations, and exact frame-rate timing that command-line FFmpeg alone cannot achieve, while maintaining broadcast-quality encoding standards.

### 8.3 Inputs & Outputs
- **Inputs:** `05_blueprint.json`, normalized media assets in `public/projects/{id}/`, render configuration (fps, resolution, codec).
- **Outputs:** Encoded `.mp4` video file, frame-by-frame render logs.

### 8.4 Dependencies
- **External:** Node.js, Remotion CLI/bundler, Chromium (headless), FFmpeg, FFprobe.
- **Internal:** `remotion-app/`, `templates/`, `scripts/render_project.py`, `scripts/generators/materialize_project.py`.

### 8.5 Entry Points & Source Files
- [`scripts/render_project.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/scripts/render_project.py): Canonical render orchestrator.
- [`scripts/generators/materialize_project.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/scripts/generators/materialize_project.py): Copies required assets into the public asset root.
- [`remotion-app/src/index.ts`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/remotion-app/src/index.ts): Remotion application entry point.
- [`templates/effects/engine-bridge.tsx`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/templates/effects/engine-bridge.tsx): Active bridge syncing animation clock with audio timestamps.

### 8.6 Internal Processing Stages
1. **Asset Materialization:** Verifies and copies audio stems, fonts, and background media to `public/projects/{id}/`.
2. **Pre-Flight Validation:** Inspects blueprint schema, template existence, and audio track presence.
3. **Remotion Bundle Compilation:** Webpack bundles React components with tree-shaking.
4. **Frame Rendering:** Headless Chromium renders video frames at 30 fps (or specified frame rate).
5. **Audio Multiplexing:** FFmpeg encodes visual frames (`libx264`, yuv420p) and multiplexes audio stems (`aac`, 48kHz, stereo) with `+faststart` moov atom.

### 8.7 State & Data Ownership
Generates ephemeral build artifacts in `remotion-app/out/` and outputs final video to project output path.

### 8.8 Trust Boundaries
Runs in an environment-sanitized subprocess without access to sensitive API keys or shell scripts.

### 8.9 Failure Modes & Handling
- **Missing Asset:** Fails early during asset materialization with descriptive error.
- **React Component Crash:** Headless browser logs error stack trace; process terminates with exit code 1.
- **FFmpeg Encoding Failure:** Caught and wrapped in `RenderExecutionError`.

### 8.10 Observability & Relevant Tests
- **Logs:** Remotion render progress bar, frame-rate metrics, FFmpeg stderr stream.
- **Tests:** `tests/e2e/true_e2e_suite.py`, `remotion-app/src/__tests__/`.

---

## Subsystem 9: Quality Control & Automated Gate Verification Subsystem

### 9.1 Purpose
Performs automated pre-render (Probe QC) and post-render (Final QC) quality assurance, verifying that generated media satisfies strict technical, aesthetic, and playback criteria.

### 9.2 Problem It Solves
Guarantees that corrupt videos, black frames, silent audio tracks, desynchronized subtitles, or invalid codecs are caught automatically and never delivered to users.

### 9.3 Inputs & Outputs
- **Inputs:** `05_blueprint.json`, raw audio stems, rendered `.mp4` file.
- **Outputs:** `ProbeQCReport`, `FinalQCReport`, visual contact sheet image, pass/fail status.

### 9.4 Dependencies
- **Tools:** `ffprobe`, `ffmpeg`, Python `soundfile`, `PIL` / `Pillow`, `numpy`.
- **Internal:** `scripts/gates/probe_qc.py`, `scripts/gates/final_qc.py`, `scripts/gates/plan_gate.py`.

### 9.5 Entry Points & Source Files
- [`scripts/gates/probe_qc.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/scripts/gates/probe_qc.py): Pre-render validation and thumbnail contact sheet generator.
- [`scripts/gates/final_qc.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/scripts/gates/final_qc.py): Post-render media inspection.
- [`scripts/gates/plan_gate.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/scripts/gates/plan_gate.py): Plan structural verification.

### 9.6 Internal Processing Stages
1. **Probe QC (Pre-Render):**
   - Validates existence and readability of all audio assets.
   - Computes audio duration vs. scene duration.
   - Generates contact sheet image (`contact_sheet.jpg`) showing scene thumbnails.
2. **Final QC (Post-Render):**
   - Runs `ffprobe` in JSON output mode.
   - Checks video stream: codec (`h264`), pixel format (`yuv420p`), resolution, duration tolerance (within ±0.1s).
   - Checks audio stream: codec (`aac`), sample rate (`44100` or `48000`), loudness bounds.
   - Verifies container has valid moov atom for streaming.

### 9.7 State & Data Ownership
Generates immutable QC reports persisted alongside project run artifacts.

### 9.8 Trust Boundaries
Automated enforcement barrier. The worker will not mark a run `COMPLETED` unless Final QC emits `status="PASS"`.

### 9.9 Failure Modes & Handling
- **Audio Desync / Mismatch:** Probe QC fails; blocks rendering.
- **Black Video / Zero Bytes:** Final QC detects zero frames; marks run `FAILED` with specific defect code.

### 9.10 Observability & Relevant Tests
- **Logs:** Detailed ffprobe streams, loudness metrics (LUFS), QC report JSON.
- **Tests:** `tests/gates/test_final_qc.py`, negative defect detection proofs in `tests/e2e/true_e2e_suite.py`.

---

## Subsystem 10: Media Storage, Asset Distribution & Artifact Retrieval Subsystem

### 10.1 Purpose
Stores uploaded raw assets and rendered video artifacts, enforces tenant access permissions, and serves media to clients using high-performance HTTP range streaming.

### 10.2 Problem It Solves
Enables video players (browsers, mobile apps) to stream large MP4 videos with smooth seeking while preventing unauthorized cross-tenant data leaks.

### 10.3 Inputs & Outputs
- **Inputs:** Binary asset uploads, authenticated artifact download requests with optional `Range: bytes=start-end` header.
- **Outputs:** Content-addressable file storage, `206 Partial Content` HTTP stream, byte chunks, `Content-Range` headers.

### 10.4 Dependencies
- **Internal:** `api/services/storage_service.py`, `api/services/asset_service.py`, `api/routers/artifacts.py`.

### 10.5 Entry Points & Source Files
- [`api/services/storage_service.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/api/services/storage_service.py): Local and S3-compatible content-addressable storage driver.
- [`api/services/asset_service.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/api/services/asset_service.py): Asset deduplication, metadata, and lifecycle management.
- [`api/routers/artifacts.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/api/routers/artifacts.py): Download and streaming endpoints.

### 10.6 Internal Processing Stages
1. **Media Ingestion:** Hashes incoming binary with SHA-256; stores file under content hash; saves metadata in tenant asset catalog.
2. **Download Request:** Authenticates caller; verifies project and artifact belong to caller's `tenant_id`.
3. **Range Header Parsing:** Parses `bytes=0-1048575` (1MB chunk); computes exact byte offset.
4. **Chunk Streaming:** Returns `206 Partial Content` with `Content-Range: bytes 0-1048575/2664800` and `Accept-Ranges: bytes`.

### 10.7 State & Data Ownership
Owns physical media files on disk / object store and the `assets` / `artifacts` database records.

### 10.8 Trust Boundaries
Enforces that media bytes are never served without tenant authorization.

### 10.9 Failure Modes & Handling
- **Unsatisfied Range:** Returns `416 Range Not Satisfiable`.
- **Missing File on Disk:** Returns `404 Not Found` with storage audit alert.
- **Cross-Tenant Artifact Access:** Returns `404 Not Found` (zero leakage).

### 10.10 Observability & Relevant Tests
- **Logs:** Bandwidth transfer logs, cache hit/miss rates, storage read latencies.
- **Tests:** `tests/routers/test_artifacts.py`, `test_full_product_journey_http_to_verified_mp4` in `tests/e2e/test_product_http_to_mp4_e2e.py`.
