# Unknowns & Unproven Claims Reality Report

- **Baseline Git SHA**: `90ec3de8d47494d5940d5cd1f9ed9a8e274ef6e1`
- **Branch**: `main`
- **Report Version**: 1.0.0
- **Last Updated**: 2026-10-07
- **Scope**: Rigorous catalog of architectural ambiguities, unproven performance/capacity claims, unverified operational limits, unlinked dependencies, and required follow-up probes across the system.
- **Evidence Standard**: `CODE_PROVEN`, `TEST_PROVEN`, `CI_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`, `DOCUMENTATION_ONLY`, `INFERRED`, `UNKNOWN`

---

## 1. Executive Summary

In keeping with the strict **Evidence Standard ("NO ARCHITECTURAL CLAIM WITHOUT EXECUTABLE EVIDENCE")**, any architectural proposition, scaling assertion, or cross-subsystem capability that cannot be proven directly from source code, executed tests, or CI results is classified as an **Unknown** or **Unproven Claim**.

This report documents the top 10 critical unknowns and outlines precise, actionable follow-up probes to resolve each ambiguity in subsequent investigative phases.

---

## 2. Catalog of Unknowns & Required Follow-Up Probes

---

### UNK-001: True Concurrent SaaS Rendering Capacity with Headless Chrome
- **Claim / Proposition**:
  Documentation suggests the video platform can operate as a high-throughput, multi-tenant SaaS rendering engine handling dozens of concurrent video jobs.
- **Why Unproven**:
  Remotion rendering (`npx remotion render`) relies on headless Chromium browser processes launched locally or inside Docker containers. In `tests/remediation/s02_acceptance/test_acc_007_docker_subcommand_validation.py` and `tests/e2e/true_e2e_suite.py`, tests run strictly 1 video sequentially on a single node. No multi-worker concurrent rendering benchmark exists in CI.
- **Architectural Risk**:
  Headless browser rendering is heavily CPU/RAM intensive (~1-2 GB RAM per Chromium instance). Spawning multiple workers without strict cgroup resource constraints will cause catastrophic OOM crashes or worker timeouts in production.
- **Classification**: **`UNKNOWN`** / **`UNPROVEN`** [`DOCUMENTATION_ONLY`].
- **Required Follow-Up Probe**:
  1. Deploy a multi-worker test bed using `scripts/testing/s28_r15_soak_and_load_runner.py`.
  2. Enqueue 10 concurrent render jobs via `POST /projects/{id}/runs` under varying memory limits (2GB, 4GB, 8GB).
  3. Measure peak memory, CPU saturation, render duration, and failure rates.

---

### UNK-002: Canvas Renderer Adapter Parity vs. Remotion Templates
- **Claim / Proposition**:
  Generation S28-R introduces the `CanvasRendererAdapter` (`canvas/canvas-renderer-adapter.ts`) as a fully interchangeable alternative to Remotion for 2D/canvas video generation.
- **Why Unproven**:
  All 105 production templates in `registry/template-registry.tsx` and `templates/` are implemented strictly as React TSX components utilizing Remotion-specific hooks (`useCurrentFrame`, `useVideoConfig`, `AbsoluteFill`, `spring`, `interpolate`). While `canvas/canvas-renderer-adapter.ts` compiles, there are zero production templates implemented using pure HTML5 Canvas or WebGL.
- **Architectural Risk**:
  If Remotion encounters rendering bottlenecks or licensing issues, the system cannot actually switch to the Canvas adapter without rewriting all 105 templates from scratch.
- **Classification**: **`INFERRED`** / **`UNPROVEN`** [`CODE_PROVEN` that adapter exists; `UNKNOWN` template compatibility].
- **Required Follow-Up Probe**:
  1. Inspect `canvas/canvas-renderer-adapter.ts` for template binding logic.
  2. Attempt rendering a complex blueprint scene (e.g. `StatCard` or `KineticHeadline`) using `CanvasRendererAdapter`.
  3. Catalog missing visual primitives and frame synchronization APIs.

---

### UNK-003: Operational Latency and Cost of Autonomous AI Generation Flow
- **Claim / Proposition**:
  The S27/S28 AI platform can automatically plan, acquire assets, and generate videos with deterministic token budgeting and cost controls.
- **Why Unproven**:
  Because the AI subsystem is disconnected from the production HTTP API, end-to-end user-to-video execution has never been measured under real network conditions with live LLM and media provider APIs. Offline scripts (`scripts/run_real_cost_performance_benchmark.py`) run with recorded traces or synthetic mock payloads.
- **Architectural Risk**:
  Real-world multi-stage AI pipelines (Prompt $\to$ Brief $\to$ Narrative $\to$ CreativePlan $\to$ ElevenLabs TTS $\to$ Fal/Replicate Video $\to$ Blueprint $\to$ Render) may suffer high failure rates due to external provider rate limits, network timeouts, or costs exceeding $10+ per video.
- **Classification**: **`UNKNOWN`** [`DOCUMENTATION_ONLY`].
- **Required Follow-Up Probe**:
  1. Run `scripts/smoke_openrouter.py` and measure wall-clock latency across 10 prompt variations.
  2. Execute an integrated probe script chaining `NarrativePlanner` $\to$ `CreativePlanner` $\to$ `BlueprintCompiler` using live OpenRouter and Fal AI API keys.
  3. Log token consumption, API dollar costs, and total end-to-end execution latency.

---

### UNK-004: FastMCP Linux Compatibility vs. Legacy Windows Tool Paths
- **Claim / Proposition**:
  Legacy MCP tools in `.agents/plugins/super-video-maker-plugin/tools/mcp-servers/` can be transparently served to modern AI clients via `ai/mcp/compatibility/server.py`.
- **Why Unproven**:
  The configuration file `.agents/plugins/super-video-maker-plugin/mcp_config.json` contains hardcoded Windows filepaths (`"args": ["C:/video/clean-video-workspace/..."]`). While the Python and JS tool files exist locally on Linux, the configuration file itself will fail to spawn processes on Linux environments without dynamic path mapping.
- **Architectural Risk**:
  External agents or clients reading `mcp_config.json` on Linux servers will fail during server launch.
- **Classification**: **`UNKNOWN`** on Linux runtime [`CODE_PROVEN` path discrepancy].
- **Required Follow-Up Probe**:
  1. Launch `python -m ai.mcp.compatibility.server` under Linux.
  2. Send JSON-RPC `tools/list` and `tools/call` requests for each of the 6 legacy MCP servers.
  3. Verify whether subprocess spawning succeeds or throws path resolution errors.

---

### UNK-005: PostgreSQL Multi-Tenant Concurrency and CAS Lock Contention
- **Claim / Proposition**:
  The database engine seamlessly supports PostgreSQL for enterprise multi-tenant deployments with atomic Compare-And-Swap (CAS) optimistic locking.
- **Why Unproven**:
  All local tests and CI workflows execute against SQLite (`data/motion.db`, `data/runs.db`, or `:memory:`). PostgreSQL execution is implemented in `scripts/core/database.py` via `psycopg2` or `asyncpg` bindings, but PostgreSQL is not provisioned as a service in `.github/workflows/remediation-ci.yml`.
- **Architectural Risk**:
  PostgreSQL transaction isolation levels (Read Committed vs Serializable) and locking semantics may cause unexpected concurrency deadlocks or CAS version collision errors that do not occur in SQLite.
- **Classification**: **`UNKNOWN`** in CI / Production [`TEST_PROVEN` in SQLite only].
- **Required Follow-Up Probe**:
  1. Spin up a local PostgreSQL container (`docker run -p 5432:5432 postgres:16`).
  2. Configure `DATABASE_URL=postgresql://...` and execute `tests/e2e/test_saas_multi_tenant_e2e.py`.
  3. Run concurrent race condition tests simulating 50 simultaneous AST mutations against a single project document.

---

### UNK-006: Zod v3 vs. v4 Semantic Divergence Across Monorepo Workspaces
- **Claim / Proposition**:
  TypeScript contracts in `contracts/` and `remotion-app/` validate data uniformly across both packages.
- **Why Unproven**:
  Root `package.json` pins `zod@3.25.76`, while `remotion-app/package.json` pins `zod@4.5.4` (using an `overrides` block). Zod v4 includes breaking changes to error formatting, discriminated union parsing, and optional/null handling.
- **Architectural Risk**:
  A blueprint or authoring payload that passes validation in `contracts/` (Zod v3) may fail validation or behave unexpectedly when loaded inside `remotion-app/` (Zod v4).
- **Classification**: **`UNKNOWN`** runtime impact [`CODE_PROVEN` version mismatch].
- **Required Follow-Up Probe**:
  1. Compile and execute cross-boundary schema validation tests passing edge-case inputs (null properties, extra fields, discriminated unions) between root and `remotion-app`.
  2. Audit all Zod import paths in `remotion-app/` to ensure consistent resolution.

---

### UNK-007: Impact of Unexecuted Remotion Tests (36 S28-R Vitest Files)
- **Claim / Proposition**:
  The S28-R Live Authoring and Renderer Independence layer is fully regression-free.
- **Why Unproven**:
  GitHub Actions CI only executes 13 of 49 Remotion test files (`package.json:28` runs `npm run test` which defaults to a restricted glob). 36 test files in `tests/remotion/` covering `RemotionRendererAdapter`, `ProductionRenderGraphExecutor`, and compositor timing are skipped in CI.
- **Architectural Risk**:
  Recent commits to `contracts/` or `remotion/` may have silently broken S28-R renderer adapter components without failing CI.
- **Classification**: **`UNKNOWN`** CI health [`CODE_PROVEN` CI exclusion].
- **Required Follow-Up Probe**:
  1. Run `npx vitest run tests/remotion/` across all 49 test files locally.
  2. Catalog any failing test suites, deprecation warnings, or missing mocks.

---

### UNK-008: True Recovery Behavior on Worker Crashes Mid-Render
- **Claim / Proposition**:
  The pipeline recovery engine (`RecoveryEngine.evaluate()`) safely recovers projects and resumes execution if a worker crashes during rendering.
- **Why Unproven**:
  While `RecoveryEngine` exists in `scripts/core/recovery_engine.py`, fault-injection tests simulate worker death by killing the subprocess, but do not verify that a partially rendered MP4 or half-written temporary disk file doesn't corrupt subsequent runs.
- **Architectural Risk**:
  Stale lock files or half-written `.pipeline_state.json` files may permanently deadlock a project in `RENDER_IN_PROGRESS` or `AWAITING_REVIEW`.
- **Classification**: **`UNKNOWN`** production recovery fidelity [`CODE_PROVEN` engine exists].
- **Required Follow-Up Probe**:
  1. Execute a run on a test project and send `kill -9` to the worker process during the `render_project.py` stage.
  2. Launch a new worker process and verify whether the project transitions to `RECOVERING` and successfully finishes or deadlocks.

---

### UNK-009: Audio Loudness Normalization Fidelity on Non-Standard Audio Streams
- **Claim / Proposition**:
  All audio streams are normalized to -16 LUFS for voiceover and -24 LUFS for sound effects via local FFmpeg scripts.
- **Why Unproven**:
  Loudness normalization is implemented using FFmpeg's `loudnorm` filter. In edge cases involving highly dynamic audio, short audio clips (<3 seconds), or multichannel 5.1/7.1 audio, single-pass `loudnorm` produces audible clipping or incorrect integrated loudness.
- **Architectural Risk**:
  Short sound effects or introductory voiceover lines may be distorted or fail `final_qc.py` audio checks.
- **Classification**: **`UNKNOWN`** edge-case audio quality [`CODE_PROVEN` implementation exists].
- **Required Follow-Up Probe**:
  1. Pass audio clips of varying durations (1.5s, 5s, 60s) through `scripts/gates/final_qc.py` and `scripts/core/audio_normalizer.py`.
  2. Verify that `r128` integrated loudness strictly measures -16.0 LUFS $\pm$ 1.0 LUFS without digital clipping.

---

### UNK-010: True End-to-End Cold-Start Latency for Video Generation
- **Claim / Proposition**:
  The system can deliver interactive preview and fast render turnaround for web clients.
- **Why Unproven**:
  No benchmark measures the wall-clock time from cold start: (1) project creation, (2) blueprint mutation, (3) dependency materialization, (4) Remotion bundle compilation, (5) probe QC still extraction, (6) multi-frame rendering, and (7) MP4 final encoding.
- **Architectural Risk**:
  First-time Remotion bundle compilation can take 30-45 seconds on cold caches, leading to HTTP gateway timeouts (e.g. Cloudflare 524 timeouts) for interactive clients.
- **Classification**: **`UNKNOWN`** cold-start SLA [`DOCUMENTATION_ONLY`].
- **Required Follow-Up Probe**:
  1. Clear all `.cache`, `node_modules/.cache`, and ephemeral workspace folders.
  2. Execute a complete cold-start run via `tests/e2e/true_e2e_suite.py` measuring each phase with nanosecond timestamps.
  3. Document cold vs warm turnaround latencies.
