# PILLAR 4: Verification Reality, CI Governance, Fallbacks & Security Tenancy

> **Consolidated Master Pillar** — Comprehensive integration of Reports 10, 11, 12, and 17

> **Baseline SHA**: `90ec3de8d47494d5940d5cd1f9ed9a8e274ef6e1` | **Branch**: `main`

> **Evidence Standard**: Strictly Preserved (`CODE_PROVEN`, `TEST_PROVEN`, `CI_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`, `DOCUMENTATION_ONLY`, `INFERRED`, `UNKNOWN`)


---

## Table of Contents

1. [Part 1: Test Reality & Mock Boundaries Audit](#part-1-test-reality--mock-boundaries-audit) *(Source: `10_TEST_REALITY_AND_MOCK_BOUNDARIES.md`)*
2. [Part 2: CI Governance & Required Branch Checks Reality](#part-2-ci-governance--required-branch-checks-reality) *(Source: `11_CI_GOVERNANCE_AND_ENFORCEMENT_REALITY.md`)*
3. [Part 3: Fallback, Defaults & Silent Failure Audit](#part-3-fallback-defaults--silent-failure-audit) *(Source: `12_FALLBACK_DEFAULT_BYPASS_AND_SILENT_FAILURE_AUDIT.md`)*
4. [Part 4: Security, Tenancy & Authority Bypass Reality](#part-4-security-tenancy--authority-bypass-reality) *(Source: `17_SECURITY_TENANCY_AND_AUTHORITY_BYPASS_REALITY.md`)*

---


<a name='part-1-test-reality--mock-boundaries-audit'></a>

## Part 1: Test Reality & Mock Boundaries Audit


> *Original Source: `documentation/reality_context_pack/10_TEST_REALITY_AND_MOCK_BOUNDARIES.md`*


### Sub-Report Title: Test Reality & Mock Boundaries Report

- **Baseline Git SHA**: `90ec3de8d47494d5940d5cd1f9ed9a8e274ef6e1`
- **Branch**: `main`
- **Report Version**: 1.0.0
- **Last Updated**: 2026-10-07
- **Scope**: Full taxonomy and classification of 510 test files, mock/stub boundaries, fake providers, in-memory repositories, analysis of tests named "E2E", and Mandatory Check T.
- **Evidence Standard**: `CODE_PROVEN`, `TEST_PROVEN`, `CI_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`, `DOCUMENTATION_ONLY`, `INFERRED`, `UNKNOWN`

---

## 1. Executive Summary

A comprehensive repository-wide audit reveals exactly **510 test files** distributed across Python (`pytest`) and TypeScript/React (`vitest`). While test volume appears vast, rigorous architectural analysis demonstrates a critical bifurcation:

1. **Massive Test Suites in Isolation**: 270 test files (52.9% of the entire test suite) belong to the modern AI platform subsystem (`tests/ai/`). These tests exercise deep domain intelligence, capabilities, routing, audio/vision pipelines, and creative planning in memory using stubs and in-memory databases. **Zero of these 270 test files are executed in the required GitHub Actions CI workflow.**
2. **Mock Boundaries & Ephemeral Fakes**: Out of 510 test files, over 60 files utilize mocking (`unittest.mock.MagicMock`, pytest `monkeypatch`, or in-memory repository fakes). Heavy mocking is concentrated in `tests/fault_injection/`, `tests/ai/context/`, `tests/ai/memory/`, and `tests/remediation/`.
3. **The E2E Label Reality (Check T)**: Tests bearing the label "E2E" (`tests/ai/e2e/`, `tests/e2e/`, `tests/fault_injection/test_fi_20_e2e_destructive.py`) **do NOT enter through full, unmocked production SaaS entrypoints**. 
   - `tests/ai/e2e/*` test suites instantiate pure Python domain classes in memory, bypassing FastAPI HTTP routers, database queues, and worker processes entirely.
   - `tests/e2e/true_e2e_suite.py` bypasses the HTTP API and worker queue, executing `scripts/pipeline.py` via CLI with pre-fabricated disk fixtures.
   - `tests/e2e/test_saas_multi_tenant_e2e.py` invokes FastAPI via in-process `TestClient`, but mocks or bypasses the background worker daemon and writes synthetic media bytes (`b"ACME_FINAL_MP4_PAYLOAD"`).

---

## 2. Comprehensive Test Suite Structural Classification (510 Files)

Every test file in the repository has been categorized according to the authoritative architectural taxonomy:
- `UNIT`: Isolated unit logic exercising a single class or pure function with no external dependencies.
- `COMPONENT`: Tests targeting a discrete subsystem or engine module (e.g., audio normalizer, template parser).
- `CONTRACT`: Schema validation, Zod/Pydantic parity, or AST interface adherence.
- `ARCHITECTURE_GUARD`: Static AST parsers or import linters enforcing structural invariants.
- `INTEGRATION`: Multi-module interaction (e.g., API router to DB repository, or RenderPlanner to DAG executor).
- `SIMULATED_E2E`: Multi-stage journey executed in-memory or via mock drivers without real production entrypoints.
- `TRUE_PRODUCT_E2E`: Full pipeline execution entering through real production entrypoints (HTTP or CLI) without synthetic bypasses.
- `FAULT_INJECTION`: Chaos testing, lease expiration, database outages, or crash resilience under simulated stress.
- `BENCHMARK`: Latency, throughput, token budget, or cost performance profiling.

### 2.1 Distribution Summary by Top-Level Directory

| Directory | File Count | Primary Classification | Secondary Classification | Active in GitHub CI? | Citations / File Scope |
|---|---|---|---|---|---|
| `tests/ai/` | 270 | `COMPONENT` / `UNIT` | `SIMULATED_E2E`, `CONTRACT` | ❌ **NO** (0 / 270 run) | `tests/ai/` [`CODE_PROVEN`, `CI_PROVEN`] |
| `tests/remotion/` | 49 | `COMPONENT` / `CONTRACT` | `INTEGRATION` | ⚠️ **PARTIAL** (13 / 49 run) | `tests/remotion/`, `package.json:8` [`CODE_PROVEN`] |
| `tests/remediation/` | 49 | `COMPONENT` / `INTEGRATION` | `REGRESSION`, `CONTRACT` | ⚠️ **MINIMAL** (1 / 49 run) | `tests/remediation/`, `.github/workflows/remediation-ci.yml:216` |
| `tests/architecture/` | 47 | `ARCHITECTURE_GUARD` | `CONTRACT` | ✅ **YES** (47 / 47 run) | `tests/architecture/` [`CI_PROVEN`] |
| `tests/core/` | 32 | `COMPONENT` / `INTEGRATION` | `CONTRACT` | ✅ **YES** (32 / 32 run) | `tests/core/` [`CI_PROVEN`] |
| `tests/fault_injection/` | 20 | `FAULT_INJECTION` | `INTEGRATION` | ✅ **YES** (20 / 20 run) | `tests/fault_injection/` [`CI_PROVEN`] |
| `tests/api/` | 11 | `INTEGRATION` | `CONTRACT` | ❌ **NO** (0 / 11 run) | `tests/api/` [`CODE_PROVEN`, `CI_PROVEN`] |
| `tests/security/` | 9 | `ARCHITECTURE_GUARD` / `COMPONENT` | `INTEGRATION` | ❌ **NO** (0 / 9 run) | `tests/security/` [`CODE_PROVEN`, `CI_PROVEN`] |
| `tests/e2e/` | 4 | `TRUE_PRODUCT_E2E` / `SIMULATED_E2E` | `INTEGRATION` | ⚠️ **PARTIAL** (2 / 4 run) | `tests/e2e/` [`CODE_PROVEN`, `CI_PROVEN`] |
| `tests/golden_scenarios/` | 4 | `SIMULATED_E2E` | `INTEGRATION` | ❌ **NO** (0 / 4 run) | `tests/golden_scenarios/` [`CODE_PROVEN`] |
| `tests/documentation/` | 3 | `ARCHITECTURE_GUARD` | `CONTRACT` | ❌ **NO** (0 / 3 run) | `tests/documentation/` [`CODE_PROVEN`] |
| `tests/contracts/` | 2 | `CONTRACT` | `UNIT` | ✅ **YES** (2 / 2 run) | `tests/contracts/` [`CI_PROVEN`] |
| `tests/generators/` | 2 | `COMPONENT` | `INTEGRATION` | ✅ **YES** (2 / 2 run) | `tests/generators/` [`CI_PROVEN`] |
| `tests/performance/` | 2 | `BENCHMARK` | `COMPONENT` | ❌ **NO** (0 / 2 run) | `tests/performance/` [`CODE_PROVEN`] |
| `tests/validators/` | 2 | `CONTRACT` | `COMPONENT` | ✅ **YES** (2 / 2 run) | `tests/validators/` [`CI_PROVEN`] |
| `tests/archive/` | 1 | `COMPONENT` | `DEPRECATED` | ❌ **NO** (0 / 1 run) | `tests/archive/` [`CODE_PROVEN`] |
| `tests/gates/` | 1 | `CONTRACT` | `COMPONENT` | ✅ **YES** (1 / 1 run) | `tests/gates/` [`CI_PROVEN`] |
| `tests/metrics/` | 1 | `BENCHMARK` | `COMPONENT` | ❌ **NO** (0 / 1 run) | `tests/metrics/` [`CODE_PROVEN`] |
| `tests/snapshots/` | 1 | `CONTRACT` | `UNIT` | ❌ **NO** (0 / 1 run) | `tests/snapshots/` [`CODE_PROVEN`] |
| **TOTAL** | **510** | | | **122 / 510 RUN (23.9%)** | |

---

### 2.2 Deep Dive into Sub-Classifications

#### 1. Architecture Guards (47 files in `tests/architecture/` + 3 in `tests/documentation/` + 3 in `tests/ai/audit/`)
- **Evidence**: `tests/architecture/test_s18_architecture_guards.py:1-120`, `test_s19_architecture_guard.py:1-150`, `test_s24_architecture_guards.py:1-60`.
- **Mechanism**: Reads Python files as raw text or uses Python `ast` to parse abstract syntax trees. Asserts zero banned imports (e.g. no direct imports of `ffmpeg` without wrapper, no direct SQL strings bypassing `DatabaseEngine`, no ambient `SKIP_STRICT_QC` flags).
- **Execution**: Actively executed in CI (`remediation-ci.yml:126`).

#### 2. Fault Injection & Chaos (20 files in `tests/fault_injection/`)
- **Evidence**: `tests/fault_injection/test_fi_01_db_outage_transition.py` through `test_fi_20_e2e_destructive.py`.
- **Mechanism**: Uses `monkeypatch` and custom interceptors to simulate database disconnects, worker SIGKILL, partial storage uploads, disk exhaustion, lease fencing race conditions, and tenant spoofing.
- **Execution**: Actively executed in CI (`remediation-ci.yml:126`).

#### 3. Core Engine & State CAS (32 files in `tests/core/`)
- **Evidence**: `tests/core/test_state_store_cas.py`, `test_state_store_tenant_cas.py`, `test_run_repository.py`, `test_storage_service.py`.
- **Mechanism**: Tests transactional isolation, SQLite concurrency, lease claiming, and optimistic locking in `StateStore` and `RunRepository`.
- **Execution**: Actively executed in CI (`remediation-ci.yml:126`).

#### 4. Remotion & TypeScript Engine (49 files in `tests/remotion/`)
- **Evidence**: `tests/remotion/contracts.test.ts`, `tests/remotion/s28_r04_mutations_core.test.ts`, `tests/remotion/s28_r11_master_compositor.test.ts`.
- **Mechanism**: Vitest test runner executing against TypeScript modules in `contracts/`, `authoring/`, `planner/`, and `compositor/`.
- **Execution Incompleteness**: `package.json:8` explicitly hardcodes 13 test files. 36 files (all modern S28-R authoring, preview, audio, and compositor suites) are omitted from `npm run test` and thus never run in CI.

#### 5. AI Platform Subsystem (270 files in `tests/ai/`)
- **Subdirectories**:
  - `candidates/` (15 files): Candidate template generation, validation, and review.
  - `context/` (13 files): `ContextBuilder`, token budgeting, retrieval, compression.
  - `speech/` (13 files): STT providers, voiceover preparation, word-level alignment.
  - `memory/` (12 files): Episodic and project memory storage, tenant isolation.
  - `cache/` (12 files): Semantic and exact match caching.
  - `orchestration/` (11 files): AI workflow state machines.
  - `planning/` (11 files): `CreativePlanner`, `NarrativePlanner`, `BlueprintCompiler`.
  - `contracts/` (10 files): Contract model parity and serialization.
  - `budget/` (10 files): Token and cost accounting.
  - `tools/` (10 files): `ToolGateway`, adapters, idempotency.
  - `routing/` (9 files): `ModelRouter`, `CapabilityRouter`.
  - `regression/` (9 files): Creative output regressions across 13 dimensions.
  - `acquisition/` (9 files): Asset search, licensing, download adapters.
  - `audio_modernization/` (9 files): Audio loudness, silence detection, mixing.
  - `e2e/` (5 files): Simulated creative intelligence pipelines.
  - Other domains: `mcp/` (7), `vision/` (7), `image_modernization/` (8), `media_processing/` (8), `evals/` (4), `taste/` (2), etc.
- **Execution**: Omitted from GitHub Actions CI.

---

## 3. Mock Boundaries, Stubs, Fake Providers & In-Memory Repositories

### 3.1 Taxonomy of Mocking Patterns

A comprehensive AST and pattern scan identifies five primary mock patterns across the test suites:

| Pattern | Frequency | Typical Locations | Subsystem Affected | Reality Assessment |
|---|---|---|---|---|
| `unittest.mock.MagicMock` / `Mock` | 44 files | `tests/fault_injection/`, `tests/ai/tools/`, `tests/core/` | Database drivers, subprocesses, S3 boto3 client | Replaces external systems with ephemeral in-memory interceptors. |
| `pytest.monkeypatch` | 47 files | `tests/fault_injection/`, `tests/remediation/`, `tests/core/` | Environment variables, filesystem roots, system clock | Overrides runtime paths and flags for hermetic execution. |
| `InMemoryRepository` | 14 files | `tests/ai/memory/`, `tests/ai/tools/`, `tests/core/` | `MemoryRepository`, `IdempotencyStore`, `StateRepository` | Emulates database behavior in pure Python dicts; does not test SQL locks or concurrency. |
| Fake AI Providers (`FakeLLMProvider`, `FakeSTTProvider`) | 12 files | `tests/ai/providers/`, `tests/ai/speech/`, `tests/ai/routing/` | `ModelRouter`, `STTProvider`, `ElevenLabsClient` | Returns deterministic, hardcoded strings/vectors without network calls. |
| Synthetic Media Generators (`make_test_video`, `make_test_audio`) | 8 files | `tests/ai/e2e/`, `tests/e2e/`, `tests/fault_injection/` | FFmpeg video/audio rendering | Uses FFmpeg `lavfi` `testsrc` to generate synthetic 3-second color bars and sine waves. |

### 3.2 Subsystem Mock Boundary Audit

#### 1. AI Memory Service (`tests/ai/memory/test_memory_service.py`)
- **Boundary**: `MemoryService` requires `MemoryRepository` and `EmbeddingProvider`.
- **Implementation in Test**: Uses `InMemoryMemoryRepository` (`ai/memory/repository.py:120-180`) storing records in `Dict[str, MemoryRecord]`. Vectors are compared via pure Python dot product.
- **What is NOT Tested**: Real pgvector extensions, MySQL vector tables, SQLite BLOB persistence, or high-concurrency connection pools.

#### 2. Model Routing & Providers (`tests/ai/routing/test_router.py`)
- **Boundary**: `ModelRouter` dispatches requests to providers (`OpenAIProvider`, `GroqProvider`, `AnthropicProvider`, `FalVideoProvider`).
- **Implementation in Test**: Tests register `MockProvider(provider_id="mock_openai")` returning pre-cooked JSON payloads.
- **What is NOT Tested**: Live network latency, API rate limits (HTTP 429), SSE streaming chunks, or real LLM context overflow.

#### 3. Tool Gateway & Domain Adapters (`tests/ai/tools/test_tool_gateway.py`)
- **Boundary**: `ToolGateway` executes tool capabilities via `NativeToolAdapter` and `DomainServiceAdapter`.
- **Implementation in Test**: Uses `InMemoryIdempotencyStore` and `MockToolAdapter`.
- **What is NOT Tested**: Persistent database locking on `tool_idempotency_records` across distributed worker processes.

#### 4. Storage Service (`tests/core/test_storage_service.py`)
- **Boundary**: `StorageService` has two backends: `LocalStorageBackend` and `S3CompatibleStorageBackend`.
- **Implementation in Test**: `LocalStorageBackend` is tested against real temporary disk directories (`tmp_path`). `S3CompatibleStorageBackend` is tested against Moto or mock boto3 client (`tests/core/test_storage_service.py:120-180`).
- **What is NOT Tested**: True AWS S3 multi-region latency, bucket replication lag, or presigned URL validity over public HTTPS.

---

## 4. Forensic Audit of Tests Named "E2E"

The codebase contains 11 test suites/scripts bearing the string "E2E" in their name or path. Each was audited to evaluate what it proves versus what it does NOT prove.

### 4.1 Comparative Matrix of "E2E" Tests

| Test Suite / Path | Entrypoint Used | Transport / Invocation | What It ACTUALLY Proves | What It DOES NOT Prove |
|---|---|---|---|---|
| `tests/e2e/true_e2e_suite.py` | CLI: `scripts/pipeline.py <id>` | Subprocess CLI (`sys.executable`) | Proves sequential gate execution, Probe QC, ReviewService approval, Remotion rendering, and Final QC pass/fail. [`CODE_PROVEN`, `TEST_PROVEN`] | Does NOT test HTTP API (`api/main.py`), does NOT test `RunRepository` queue, does NOT test worker polling daemon (`scripts/worker.py`), does NOT touch AI subsystem. |
| `tests/e2e/test_saas_multi_tenant_e2e.py` | FastAPI `TestClient(app)` | In-process ASGI HTTP requests | Proves HTTP route validation, RBAC enforcement (403/401), ETag CAS (409), and tenant isolation rules. [`CODE_PROVEN`, `TEST_PROVEN`] | Does NOT test network sockets (Uvicorn), worker daemon is manually driven, media outputs are synthetic strings (`b"ACME_FINAL_MP4_PAYLOAD"`). |
| `tests/e2e/test_pipeline_integration.py` | CLI: `scripts/pipeline.py` | Subprocess CLI | Proves gate transitions with sample blueprints. | Does NOT test SaaS API, multitenancy, or worker queuing. |
| `tests/e2e/test_unified_pipeline.py` | CLI: `scripts/pipeline.py` | Subprocess CLI | Proves asset materialization and blueprint assembly. | Does NOT test SaaS API or AI capabilities. |
| `tests/ai/e2e/test_full_creative_e2e_matrix.py` | Python Class `CreativePlanner.plan()` | In-memory Python function call | Proves `RecipeSelector` $\to$ `NarrativePlanner` $\to$ `CreativePlanner` $\to$ `BlueprintCompiler` data compatibility in memory. [`TEST_PROVEN`] | Completely bypasses FastAPI, SQLite, workers, Remotion, and CLI. Zero production entrypoints touched. |
| `tests/ai/e2e/test_s28_m11_product_e2e_matrix.py` | Python Class `CapabilityRouter.dispatch()` | In-memory Python function call | Proves 12 capability journeys execute across in-memory services (`AssetAcquisitionService`, `MediaProcessingService`). [`TEST_PROVEN`] | Zero HTTP entrypoints, zero worker queues, zero connection to production video pipeline. |
| `tests/ai/e2e/test_real_service_e2e_closeout.py` | Python Class `ReuseEngine`, `ComposeEngine` | In-memory Python function call | Proves reuse matching and composition layering algorithms. | Bypasses all production entrypoints and persistence. |
| `tests/ai/e2e/test_multi_tenant_production_e2e.py` | Python Class `AIRunService` | In-memory Python function call | Proves multi-tenant scoping logic inside AI platform models. | Does NOT test FastAPI `TenantContext` or production `DatabaseEngine`. |
| `tests/ai/e2e/test_s28_m_automatic_stock_preparation.py` | Python Class `AssetAcquisitionService` | In-memory Python function call | Proves stock search, licensing metadata validation, and local download logic. | Bypasses production API and pipeline orchestrator. |
| `tests/fault_injection/test_fi_20_e2e_destructive.py` | Subprocess CLI / Worker API | Multi-process chaos orchestration | Proves database recovery and state reconciliation when workers crash mid-render. | Relies on chaos monkeypatching; not a normal user journey. |
| `scripts/run_creative_e2e.py` | Standalone CLI script | Offline benchmark runner | Proves creative matrix matrix generation (7 video types x 6 audio modes) into `scratch/creative_e2e/`. | Standalone developer tool; not connected to production SaaS API. |

---

## 5. Mandatory Check T — Formal Architectural Answer

### Question:
> **Do tests named "E2E" enter through real Production entrypoints?**

### Reality Finding:
**NO (`CODE_PROVEN`, `TEST_PROVEN`). No test suite named "E2E" enters through a complete, unmocked production SaaS entrypoint.**

### Detailed Evidence Chain:
1. **AI "E2E" Tests (`tests/ai/e2e/*`)**:
   - In `tests/ai/e2e/test_s28_m11_product_e2e_matrix.py:36-120` and `tests/ai/e2e/test_full_creative_e2e_matrix.py:200-260`, tests import internal Python classes directly:
     ```python
     selector = RecipeSelector(shared_recipe_registry)
     narrative_planner = NarrativePlanner()
     taste_engine = TasteEngine()
     planner = CreativePlanner()
     compiler = BlueprintCompiler()
     ```
   - These tests invoke Python method calls (`planner.plan(...)`, `compiler.compile(...)`) on in-memory instances. They do NOT send HTTP requests to FastAPI, do NOT insert records into SQLite/PostgreSQL `runs`, and do NOT launch worker subprocesses. They are in-memory **component integration tests**, not product E2E tests.

2. **Pipeline "True E2E" Suite (`tests/e2e/true_e2e_suite.py`)**:
   - In `tests/e2e/true_e2e_suite.py:32-45`, execution enters through the CLI script `scripts/pipeline.py`:
     ```python
     subprocess.run([sys.executable, "scripts/pipeline.py", project_id], ...)
     ```
   - Before running the pipeline, it uses test factory `create_canonical_e2e_project(...)` (line 66) to manufacture synthetic project directories on disk.
   - At the review stage, it calls `ReviewService.approve(...)` directly in Python (line 99), completely bypassing the HTTP API endpoints (`POST /projects/{id}/runs`, `POST /projects/{id}/review/approve`).
   - The production worker queue (`PipelineWorker.run_loop()`) and background daemon (`scripts/worker.py`) are completely unexercised.

3. **SaaS Multi-Tenant E2E Suite (`tests/e2e/test_saas_multi_tenant_e2e.py`)**:
   - In `tests/e2e/test_saas_multi_tenant_e2e.py:22-24`, requests enter via FastAPI's in-process test client:
     ```python
     client = TestClient(app)
     ```
   - While HTTP routes are exercised, the background worker daemon is not running; worker processing is either manually stepped or completely mocked.
   - Output video files are not rendered via Remotion; they are synthetic mock bytes (`(proj_dir_a / "out.mp4").write_bytes(b"ACME_FINAL_MP4_PAYLOAD")`, line 92).

### Architectural Conclusion:
The repository has high-fidelity component and CLI integration tests, but **zero tests exercise the complete end-to-end production path from external HTTP client $\to$ FastAPI $\to$ Database Queue $\to$ Background Worker Daemon $\to$ Subprocess Orchestration $\to$ Remotion Render $\to$ Object Storage $\to$ HTTP Stream**.

---

## 6. Verification Methods and Reproducible Commands

To independently reproduce and verify the findings in this report:

1. **Verify Exact Test File Counts (510 Total)**:
   ```bash
   python -c "
   import os
   total = sum(1 for root, _, files in os.walk('tests') for f in files
               if (f.endswith('.py') or f.endswith('.ts') or f.endswith('.tsx'))
               and (f.startswith('test_') or f.endswith('_test.py') or f.endswith('.test.ts') or f == 'true_e2e_suite.py'))
   print('Total test files:', total)
   "
   # Output must be: Total test files: 510
   ```

2. **Verify Breakdown of `tests/ai` (270 Files)**:
   ```bash
   find tests/ai -type f \( -name "test_*.py" -o -name "*_test.py" \) | wc -l
   # Output must be: 270
   ```

3. **Verify Remotion Vitest Hardcoded Exclusion (13 vs 49 Files)**:
   ```bash
   # Count total Remotion test files:
   find tests/remotion -type f -name "*.test.ts" | wc -l
   # Output must be: 49

   # Count test files in package.json:
   grep -o "tests/remotion/[a-zA-Z0-9_]*\.test\.ts" package.json | wc -l
   # Output must be: 13
   ```

4. **Verify Check T Entrypoints**:
   ```bash
   # Inspect AI E2E entrypoints:
   grep -n "class " tests/ai/e2e/test_full_creative_e2e_matrix.py | head -n 5
   # Note: Pure Python test classes with direct instantiation

   # Inspect true_e2e_suite entrypoint:
   sed -n '32,45p' tests/e2e/true_e2e_suite.py
   # Note: Subprocess call to scripts/pipeline.py, bypassing API and worker
   ```


---


<a name='part-2-ci-governance--required-branch-checks-reality'></a>

## Part 2: CI Governance & Required Branch Checks Reality


> *Original Source: `documentation/reality_context_pack/11_CI_GOVERNANCE_AND_ENFORCEMENT_REALITY.md`*


### Sub-Report Title: CI Governance & Enforcement Reality Report

- **Baseline Git SHA**: `90ec3de8d47494d5940d5cd1f9ed9a8e274ef6e1`
- **Branch**: `main`
- **Report Version**: 1.0.0
- **Last Updated**: 2026-10-07
- **Scope**: Rigorous comparison between GitHub Actions CI workflows, local `run_required_checks.sh`, test coverage, generational coverage gaps (S27, S28, S28-M, S28-R), and Mandatory Checks A & B.
- **Evidence Standard**: `CODE_PROVEN`, `TEST_PROVEN`, `CI_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`, `DOCUMENTATION_ONLY`, `INFERRED`, `UNKNOWN`

---

## 1. Executive Summary

A forensic audit of CI governance across `.github/workflows/remediation-ci.yml`, `scripts/ci/run_required_checks.sh`, and root package configurations reveals a **deep governance divergence** between what developers run locally, what GitHub Actions actually enforces, and what documentation claims:

1. **Mandatory Check A is FALSE**: Required GitHub Actions CI completely excludes `tests/ai` (270 test files). Zero tests in `tests/ai` are executed in any GitHub Actions job.
2. **Mandatory Check B is FALSE**: The local runner script `scripts/ci/run_required_checks.sh` is not an authentic mirror of `.github/workflows/remediation-ci.yml`. It diverges across six major structural axes, executing test suites CI misses while omitting linters, container audits, and acceptance tests that CI enforces.
3. **The 76% Unenforced Test Suite Reality**: Out of 510 total test files in the repository, GitHub Actions CI executes only **122 test files (23.9%)**. 388 test files (76.1%) are completely omitted from automated pull-request and branch-protection gating.
4. **Remotion Test Omission**: `npm run test` executes only 13 hardcoded test files in Vitest out of 49 files in `tests/remotion/`, leaving 36 modern S28-R renderer and authoring test files unexecuted in both local and remote CI.
5. **Coverage Illusion**: Pytest coverage gating enforces `--cov=api --cov=scripts/core --cov-fail-under=48`. It does not monitor or require coverage for `ai/`, `scripts/gates/`, `authoring/`, `planner/`, or `compositor/`.

---

## 2. GitHub Actions CI Architecture (`.github/workflows/remediation-ci.yml`)

The primary CI pipeline is defined in `.github/workflows/remediation-ci.yml` (265 lines). It triggers on pushes to `main`, `remediation/*`, `feature/*`, and pull requests targeting `main` and `feature/*`.

### 2.1 Workflow Jobs Topology

```
remediation-ci.yml
├── 1. python-quality      (Ruff linter on api/ and scripts/core/)
├── 2. contracts-ts        (Node 20: npm ci, tsc --noEmit, npm run test [13 vitest files])
├── 3. ground-truth        (check_ground_truth_sync.py, check_dependencies_lock.py)
├── 4. python-tests        (Pytest on 8 selected folders, --cov-fail-under=48)
├── 5. strict-e2e          (python tests/e2e/true_e2e_suite.py)
├── 6. docker-render       (docker build clean-video-builder, test_acc_007)
└── 7. security-audit      (pip-audit, npm audit, bandit, check_secrets.py, trivy-action)
```

### 2.2 Deep Inspection of Job Configurations

1. **Job `python-quality`** (lines 14-34):
   - Command: `ruff check api/ scripts/core/` [`CI_PROVEN`].
   - Scope: Strictly limited to `api/` and `scripts/core/`. Does NOT check `ai/`, `scripts/gates/`, `scripts/generators/`, or `creative_governance/`.

2. **Job `contracts-ts`** (lines 35-62):
   - Commands:
     - `cd remotion-app && npm run lint && npx tsc --noEmit`
     - `npm run test` (executes root `package.json` script: `vitest run tests/remotion/contracts.test.ts ...` [13 files]).
   - Scope: 36 test files in `tests/remotion/` are excluded.

3. **Job `ground-truth`** (lines 63-87):
   - Commands:
     - `python scripts/validators/check_ground_truth_sync.py --check`
     - `python scripts/validators/check_dependencies_lock.py --check`
   - Scope: Verifies derivative catalogs match disk reality and `uv.lock` / `requirements.txt` consistency.

4. **Job `python-tests`** (lines 88-134):
   - Command (lines 125-126):
     ```bash
     pytest --cov=api --cov=scripts/core --cov-report=xml --cov-report=term --cov-fail-under=48 \
       tests/core tests/gates tests/generators tests/validators tests/architecture tests/contracts tests/fault_injection tests/e2e/test_pipeline_integration.py
     ```
   - Target folders included: `tests/core` (32), `tests/gates` (1), `tests/generators` (2), `tests/validators` (2), `tests/architecture` (47), `tests/contracts` (2), `tests/fault_injection` (20), `tests/e2e/test_pipeline_integration.py` (1) = 107 files.
   - Target folders excluded: `tests/ai/` (270 files), `tests/api/` (11 files), `tests/security/` (9 files), `tests/remediation/` (48 files), `tests/golden_scenarios/` (4 files), `tests/performance/` (2 files), `tests/metrics/` (1 file), `tests/snapshots/` (1 file), `tests/documentation/` (3 files).

5. **Job `strict-e2e`** (lines 135-181):
   - Command: `python tests/e2e/true_e2e_suite.py` [`CI_PROVEN`].
   - Installs ffmpeg, executes `npx remotion browser ensure`, runs CLI orchestrator test.

6. **Job `docker-render`** (lines 182-217):
   - Commands:
     - `docker build -t clean-video-builder -f .agents/docker/Dockerfile.remotion .`
     - `docker run --rm clean-video-builder npx remotion versions`
     - `pytest tests/remediation/s02_acceptance/test_acc_007_docker_subcommand_validation.py -v`

7. **Job `security-audit`** (lines 218-265):
   - Commands:
     - `pip-audit --desc -r requirements.txt`
     - `npm audit --audit-level=high` (root & remotion-app)
     - `bandit -r api/ scripts/core/ -lll`
     - `python scripts/validators/check_secrets.py`
     - `uses: aquasecurity/trivy-action@master` with `scan-type: 'fs'`, `severity: 'CRITICAL,HIGH'`, `exit-code: '1'`.

---

## 3. Local CI Architecture (`scripts/ci/run_required_checks.sh`)

The local test runner `scripts/ci/run_required_checks.sh` (72 lines) claims in its banner to be the "Local Mirror for S24/S26 CI Required Checks".

### 3.1 Script Stages Topology

```
run_required_checks.sh
├── 1. [ground-truth] Schema & Dependency Drift Check
│   ├── check_ground_truth_sync.py --check
│   ├── check_dependencies_lock.py --check
│   ├── generate_ai_contracts.py --check
│   └── generate_creative_contracts.py --check
├── 2. [security-audit] Security, Dependency & Secret Audits
│   ├── pip-audit --desc
│   ├── npm audit (root & remotion-app)
│   ├── bandit -r api/ scripts/ -lll
│   └── check_secrets.py
├── 3. [contracts-ts] TypeScript Contracts & Remotion Lint
│   ├── (cd remotion-app && npx tsc --noEmit)
│   ├── (cd remotion-app && npm run lint)
│   └── npm test
├── 4. [python-tests] Pytest Suite with Coverage Threshold
│   └── pytest --cov=api --cov=scripts/core --cov-fail-under=48 ... tests/ai ...
├── 5. [strict-e2e] True E2E Suite (No Bypasses)
│   └── python tests/e2e/true_e2e_suite.py
└── 6. [docker-render] Hermetic Docker Verification
    └── (optional conditional check; skips if docker absent)
```

---

## 4. Rigorous Comparison Matrix (GitHub Actions vs. Local Script)

A line-by-line comparison of `.github/workflows/remediation-ci.yml` and `scripts/ci/run_required_checks.sh` proves **six fundamental structural divergence points**:

| Axis / Verification Area | GitHub Actions CI (`remediation-ci.yml`) | Local Script (`run_required_checks.sh`) | Governance Divergence Type | Impact & Reality |
|---|---|---|---|---|
| **1. `tests/ai` vs `tests/fault_injection`** | Excludes `tests/ai`. Includes `tests/fault_injection`. (`line 126`) | Includes `tests/ai`. Excludes `tests/fault_injection`. (`line 50`) | **Direct Suite Inversion** | Local runner executes 270 AI tests that CI ignores; CI executes 20 chaos fault injection tests that local script skips. |
| **2. Contract Code Generator Verification** | Does not run contract generator drift checks. | Runs `generate_ai_contracts.py --check` and `generate_creative_contracts.py --check`. (`lines 23-24`) | **Local-Only Gate** | Code contract drift breaks local runs, but merges cleanly through GitHub CI without detection. |
| **3. Python Linting (`ruff`)** | Dedicated `python-quality` job runs `ruff check api/ scripts/core/`. (`line 33`) | Completely absent. Zero ruff invocation. | **CI-Only Gate** | Formatting/lint bugs pass locally but fail remotely in GitHub CI. |
| **4. Static Security Scanning (`bandit`)** | Restricts scanning scope to `api/ scripts/core/`. (`line 251`) | Scans all scripts: `bandit -r api/ scripts/ -lll`. (`line 35`) | **Scope Asymmetry** | Local script triggers on developer scripts in `scripts/maintenance/` or `scripts/archive/` that CI ignores. |
| **5. Container & FS Vulnerability Scan (`trivy`)** | Runs `aquasecurity/trivy-action@master` failing on CRITICAL/HIGH. (`line 257`) | Completely absent. | **CI-Only Gate** | Remote CI enforces filesystem CVE rules not audited locally. |
| **6. Hermetic Docker Build & Acceptance Test** | Always builds `clean-video-builder` and executes `test_acc_007_docker_subcommand_validation.py`. (`lines 205-217`) | Skips if Docker is absent (`lines 60-66`); never builds image and never runs `test_acc_007`. | **Conditional Bypass** | Local run passes even if Docker build or container execution is completely broken. |

---

## 5. Mandatory Check A — Formal Architectural Answer

### Question:
> **Does required GitHub CI run `tests/ai` in its entirety?**

### Reality Finding:
**NO (`CI_PROVEN`, `CODE_PROVEN`). Required GitHub Actions CI completely omits `tests/ai`.**

### Verbatim Evidence:
In `.github/workflows/remediation-ci.yml`, the only step executing pytest is lines 124-127:
```yaml
      - name: Run Pytest with Coverage Threshold
        env:
          PYTHONPATH: .
          TESTING: '1'
        run: |
          pytest --cov=api --cov=scripts/core --cov-report=xml --cov-report=term --cov-fail-under=48 \
            tests/core tests/gates tests/generators tests/validators tests/architecture tests/contracts tests/fault_injection tests/e2e/test_pipeline_integration.py
```
- Total test files in `tests/ai/`: **270 files** (`find tests/ai -name "test_*.py" | wc -l` yields 270).
- Search for `tests/ai` across the entire `.github/` folder: **0 occurrences** (`grep -rn "tests/ai" .github/` returns 0).
- No other job in `.github/workflows/remediation-ci.yml` invokes pytest or Python test runners against `tests/ai`.

### Architectural Conclusion:
The entire S27 and S28 AI platform (routing, capabilities, planning, context, memory, audio/vision intelligence, speech) is completely **ungated by remote GitHub Actions CI**. Code breaking `tests/ai` can be committed, pushed to `main`, and pass all required branch protection checks without failure.

---

## 6. Mandatory Check B — Formal Architectural Answer

### Question:
> **Does local `run_required_checks.sh` match actual GitHub required checks?**

### Reality Finding:
**NO (`CI_PROVEN`, `CODE_PROVEN`). The local runner script `scripts/ci/run_required_checks.sh` substantially diverges from `.github/workflows/remediation-ci.yml`.**

### Comparative Verbatim Evidence:
1. **Pytest Invocations Side-by-Side**:
   - `remediation-ci.yml:125-126`:
     ```bash
     pytest ... tests/core tests/gates tests/generators tests/validators tests/architecture tests/contracts tests/fault_injection tests/e2e/test_pipeline_integration.py
     ```
   - `run_required_checks.sh:49-50`:
     ```bash
     pytest ... tests/core tests/gates tests/generators tests/validators tests/architecture tests/ai tests/contracts tests/e2e/test_pipeline_integration.py
     ```
   *Difference*: CI runs `tests/fault_injection` and excludes `tests/ai`. Local runs `tests/ai` and excludes `tests/fault_injection`.

2. **Contract Generator Drift Checks**:
   - `run_required_checks.sh:23-24`:
     ```bash
     python scripts/generate_ai_contracts.py --check
     python scripts/generate_creative_contracts.py --check
     ```
   - `remediation-ci.yml`: Omitted.

3. **Linter Enforcement**:
   - `remediation-ci.yml:33`: Runs `ruff check api/ scripts/core/`.
   - `run_required_checks.sh`: Omitted.

4. **Security Audit Scope**:
   - `remediation-ci.yml:251`: `bandit -r api/ scripts/core/ -lll`.
   - `run_required_checks.sh:35`: `bandit -r api/ scripts/ -lll`.

5. **Docker Acceptance Test**:
   - `remediation-ci.yml:216`: Executes `pytest tests/remediation/s02_acceptance/test_acc_007_docker_subcommand_validation.py -v`.
   - `run_required_checks.sh`: Skips if Docker is absent, never builds image, never runs `test_acc_007`.

### Architectural Conclusion:
`scripts/ci/run_required_checks.sh` gives developers a false sense of parity. Passing checks locally does not guarantee passing GitHub CI, and passing GitHub CI does not guarantee local checks would pass.

---

## 7. Cross-Generational CI Coverage Gap Analysis

| Architectural Generation | Subsystem Scope | Total Test Files | Tests Run in GitHub CI | Tests Run in Local Script | CI Enforcement Status |
|---|---|---|---|---|---|
| **Pre-S25 (Legacy / Pipeline)** | `tests/core/`, `tests/gates/`, `tests/generators/`, `tests/validators/`, `tests/e2e/` | 41 | 39 | 38 | ✅ **ENFORCED** (95%) |
| **S26 (Governance & Architecture)**| `tests/architecture/`, `tests/fault_injection/`, `tests/contracts/` | 69 | 69 | 49 | ⚠️ **PARTIAL** (Fault injection dropped locally) |
| **S27 (AI Infrastructure)** | `tests/ai/routing/`, `tests/ai/providers/`, `tests/ai/context/`, `tests/ai/memory/` | 84 | 0 | 84 | ❌ **UNENFORCED IN CI** (0%) |
| **S28 (Creative Intelligence)** | `tests/ai/planning/`, `tests/ai/narrative/`, `tests/ai/taste/`, `tests/ai/recipes/`, `tests/ai/skills/` | 96 | 0 | 96 | ❌ **UNENFORCED IN CI** (0%) |
| **S28-M (Capability / MCP Platform)**| `tests/ai/capabilities/`, `tests/ai/tools/`, `tests/ai/acquisition/`, `tests/ai/media_processing/` | 90 | 0 | 90 | ❌ **UNENFORCED IN CI** (0%) |
| **S28-R (Renderer Independence & Authoring)**| `tests/remotion/s28_r*` (Mutations, Preview, Canvas, Compositor, RenderPlanner) | 36 | 0 | 0 | ❌ **UNENFORCED ANYWHERE** (0%) |
| **SaaS API Subsystem** | `tests/api/`, `tests/security/` | 20 | 0 | 0 | ❌ **UNENFORCED ANYWHERE** (0%) |

### Key Takeaway on S28-R & Remotion Tests:
The 36 test files under `tests/remotion/` created during the S28-R milestone (Renderer Independence, Unified Authoring, Preview Engine, Master Compositor, and Render Planner) are **unwired from root `package.json`** (`package.json:8` lists only 13 test files). As a consequence, neither GitHub Actions CI nor the local CI runner ever executes the modern S28-R test suite!

---

## 8. Python Quality & Coverage Gate Reality

In `pyproject.toml:47-57` and `.github/workflows/remediation-ci.yml:125`:
```toml
[tool.pytest.ini_options]
addopts = "--import-mode=importlib --cov=api --cov=scripts/core --cov-report=term-missing --cov-fail-under=48"
```
The test coverage gate enforces:
1. **Low Baseline**: Fail under threshold is set to **48%**.
2. **Narrow Scope**: Coverage measures strictly `api/` and `scripts/core/`.
3. **Excluded Subsystems**:
   - `ai/` is excluded from coverage accounting.
   - `scripts/gates/` is excluded from coverage accounting.
   - `scripts/generators/` is excluded from coverage accounting.
   - `authoring/`, `planner/`, `compositor/`, `preview/` are TypeScript and excluded from Python coverage.
4. **False Security**: Because `tests/api/` (11 test files) is excluded from the CI pytest command, coverage of `api/` relies primarily on indirect calls from `tests/core/` and `tests/fault_injection/`.

---

## 9. Verification Methods and Reproducible Commands

To independently reproduce and verify the findings in this report:

1. **Verify Check A (`tests/ai` Exclusion in CI)**:
   ```bash
   # Check if tests/ai is referenced anywhere in .github/workflows/remediation-ci.yml:
   grep -n "tests/ai" .github/workflows/remediation-ci.yml
   # Returns 0 lines (exit code 1)
   ```

2. **Verify Check B (Divergence between Workflow and Local Script)**:
   ```bash
   # Compare pytest testpaths:
   echo "--- GitHub CI pytest command ---"
   grep -n "pytest " .github/workflows/remediation-ci.yml
   echo "--- Local script pytest command ---"
   grep -n "pytest " scripts/ci/run_required_checks.sh
   # Observe: CI includes tests/fault_injection; script includes tests/ai
   ```

3. **Verify Remotion Unrun Tests in `package.json`**:
   ```bash
   # Inspect package.json test script:
   grep '"test":' package.json
   # Note: Exactly 13 files specified.
   # Count total remotion test files:
   find tests/remotion -name "*.test.ts" | wc -l
   # Note: Exactly 49 files on disk. (36 files unrun).
   ```

4. **Verify Total Test File Counts**:
   ```bash
   find tests -type f \( -name "test_*.py" -o -name "*_test.py" -o -name "*.test.ts" -o -name "true_e2e_suite.py" \) | wc -l
   # Returns: 510
   ```


---


<a name='part-3-fallback-defaults--silent-failure-audit'></a>

## Part 3: Fallback, Defaults & Silent Failure Audit


> *Original Source: `documentation/reality_context_pack/12_FALLBACK_DEFAULT_BYPASS_AND_SILENT_FAILURE_AUDIT.md`*


### Sub-Report Title: Fallback, Default Bypass & Silent Failure Audit Report

- **Baseline Git SHA**: `90ec3de8d47494d5940d5cd1f9ed9a8e274ef6e1`
- **Branch**: `main`
- **Report Version**: 1.0.0
- **Last Updated**: 2026-10-07
- **Scope**: Repository-wide sweep for silent `except: pass`, masked error handling, multi-tier fallback chains, default constructor injections, optional imports, and bypass environment flags.
- **Evidence Standard**: `CODE_PROVEN`, `TEST_PROVEN`, `CI_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`, `DOCUMENTATION_ONLY`, `INFERRED`, `UNKNOWN`

---

## 1. Executive Summary

A comprehensive, automated, and manual sweep across the repository identified **144 silent `except: pass` or error-swallowing blocks**, multiple complex **multi-tier fallback chains**, and widespread **default injections** that mask missing production wiring and decoupled subsystems:

1. **Silent Storage Upload Swallowing (`AssetService`)**: In `api/services/asset_service.py:171-172`, failures during object storage uploads (`StorageService.put`) are silently swallowed with `except Exception: pass`. The API returns HTTP 200/201 success to the caller while leaving the object unpersisted in cloud/remote storage.
2. **Silent Database Synchronization Swallowing (`StateStore`)**: In `scripts/core/state_store.py:221-222`, if reflecting state changes to the relational database engine fails, the error is swallowed with `# Non-fatal if database is unconfigured ... pass`.
3. **Tenant Context Fallback (`RunService` & `Auth`)**: In `api/services/run_service.py:86-88` and `api/core/auth.py:341,374`, failures to resolve a project or workspace ID silently fall back to hardcoded default values (`"ws_default"`, `"usr_system"`), undermining tenant isolation guarantees under failure conditions.
4. **Three-Tier Render Fallback Chain (`scripts/render_project.py`)**: The system attempts to render through modern `RenderPlanner` (S28-R14), but on ANY exception silently catches it and falls back to `RemotionRendererAdapter` (S28-R09), and on another exception falls back to legacy `npx remotion render`.
5. **Decoupled AI Platform Defaults**: The AI subsystem (`ContextBuilder`, `ModelRouter`, `CapabilityRouter`, `ToolGateway`) provides internal fallback defaults (`DeterministicKnowledgeRetriever`, `DeterministicTokenEstimator`) that enable tests to pass in isolation without real production wiring.

---

## 2. Silent `except: pass` & Error Swallowing Audit

A syntax and AST scan reveals 144 instances of `except: pass` or `except Exception: pass` across non-test Python files. The most critical occurrences that directly impact production data integrity and security are cataloged below.

### 2.1 Critical Production Silent Exception Inventory

| File Path | Line Range | Exception Caught | Swallowed Action | Production Reality & Risk | Evidence Citation |
|---|---|---|---|---|---|
| `scripts/core/state_store.py` | 218-223 | `Exception` (non-`StateConflictError`) | Database state reflection (`_sync_to_db`) | State updates save to local JSON on disk, but DB table `project_states` silently desynchronizes without error. | `scripts/core/state_store.py:221-222` [`CODE_PROVEN`] |
| `api/services/asset_service.py` | 153-161 | `Exception` | Workspace lookup from DB | If DB query fails, workspace ID silently defaults to `"ws_default"`. | `api/services/asset_service.py:160` [`CODE_PROVEN`] |
| `api/services/asset_service.py` | 165-173 | `Exception` | `StorageService.put()` | If cloud or local storage upload fails, `storage_key` remains `None`; file is saved only to local disk. | `api/services/asset_service.py:171-172` [`CODE_PROVEN`] |
| `api/services/run_service.py` | 80-87 | `Exception` | `TenantRepository.get_project()` | If project lookup fails, run record is created under `"ws_default"` instead of the owning tenant. | `api/services/run_service.py:86` [`CODE_PROVEN`] |
| `api/core/auth.py` | 330-342 | `Exception` | TenantContext derivation | If DB lookup fails during authorization, `request.state.tenant_context` remains `None` without denying access. | `api/core/auth.py:341` [`CODE_PROVEN`] |
| `api/core/auth.py` | 370-375 | `Exception` | Auto-creating personal workspace | If creating `ws_{principal_id}` fails, error is swallowed, leading to subsequent membership denial. | `api/core/auth.py:374` [`CODE_PROVEN`] |
| `api/services/pipeline_service.py` | 95-102 | `Exception` | Reading legacy GUI state from disk | Swallows malformed JSON errors during legacy GUI state fallback. | `api/services/pipeline_service.py:100` [`CODE_PROVEN`] |
| `api/services/pipeline_service.py` | 258-266 | `Exception` | Parsing JSON state from subprocess stdout | If gate subprocess emits invalid JSON, stdout state update is silently dropped. | `api/services/pipeline_service.py:265` [`CODE_PROVEN`] |
| `api/services/pipeline_service.py` | 345-350 | `Exception` | Loading `02_asset_manifest.json` | If loading manifest fails, sets `man = None`, validating blueprint without asset verification! | `api/services/pipeline_service.py:349` [`CODE_PROVEN`] |
| `api/services/health_service.py` | 134-138 | `Exception` | `RunRepository` bootstrap initialization | Swallows DB initialization failure in `/health/ready` check. | `api/services/health_service.py:137` [`CODE_PROVEN`] |
| `api/services/health_service.py` | 285-298 | `Exception` | Lease heartbeat timestamp parsing | If timestamp parsing fails, worker liveness probe drops into stale fallback. | `api/services/health_service.py:297` [`CODE_PROVEN`] |
| `api/services/output_service.py` | 65-75 | `Exception` | `StorageService.get(key)` | If storage fetch fails, swallows exception and raises generic 404 Not Found. | `api/services/output_service.py:74` [`CODE_PROVEN`] |

---

## 3. Multi-Tier Fallback Chains & Degradation Cascades

### 3.1 The Three-Tier Video Render Fallback Chain

In `scripts/render_project.py:127-186`, video rendering executes through a three-tier fallback cascade:

```
[Incoming Render Request]
          │
          ▼
┌────────────────────────────────────────────────────────┐
│ Tier 1: S28-R14 Multi-Engine RenderPlanner & Compositor│
│ Command: npx tsx scripts/render_via_planner.ts         │
└────────────────────────────────────────────────────────┘
          │ (on Exception: logs warning, catches ALL)
          ▼
┌────────────────────────────────────────────────────────┐
│ Tier 2: S28-R09 RemotionRendererAdapter                │
│ Command: npx tsx scripts/render_via_adapter.ts         │
└────────────────────────────────────────────────────────┘
          │ (on Exception: logs warning, catches ALL)
          ▼
┌────────────────────────────────────────────────────────┐
│ Tier 3: Legacy Direct Remotion CLI Execution           │
│ Command: npx remotion render src/index.ts              │
└────────────────────────────────────────────────────────┘
```

#### Verbatim Code Evidence (`scripts/render_project.py:136-186`):
```python
if not use_legacy and planner_script.exists():
    try:
        # Tier 1
        safe_subprocess(cmd_planner, ...)
        render_success = True
    except Exception as ex:
        print(f"⚠️ فشل مسار Multi-Engine Planner ({ex}) — تجربة مسار Adapter الفردي...")

if not render_success and not use_legacy and adapter_script.exists():
    try:
        # Tier 2
        safe_subprocess([npx_cmd, "tsx", str(adapter_script), ...], ...)
        render_success = True
    except Exception as ex:
        print(f"⚠️ فشل مسار Adapter ({ex}) — تفعيل جسر التوافق (Legacy Remotion CLI)...")

if not render_success:
    # Tier 3 (Fallback)
    result = safe_subprocess([npx_cmd, "remotion", "render", ...], ...)
```

#### Architectural Assessment:
- **Masking Render Failures**: If the modern TypeScript RenderPlanner or MasterCompositor has syntax errors, runtime crashes, or missing dependencies, the build does not fail. It silently drops down to legacy Remotion CLI.
- **Bypass Flag**: Setting environment variable `USE_LEGACY_RENDER_PATH=1` or command line flag `--legacy-cli` completely bypasses Tiers 1 and 2 without running the modern pipeline.

---

## 4. Default Injections and Protocol Stubs in Core Registries

A major architectural observation is that all core AI subsystems provide default fallback implementations in their constructors. When instantiated without parameters (as occurs in standalone unit tests), they initialize deterministic stubs rather than failing closed.

### 4.1 Subsystem Default Fallback Matrix

| Subsystem | Constructor Location | Parameter | Default Fallback Value | Behavioral Impact |
|---|---|---|---|---|
| `ContextBuilder` | `ai/context/builder.py:77` | `knowledge_retriever` | `DeterministicKnowledgeRetriever()` | Returns hardcoded static knowledge snippets without hitting KnowledgeRouter. |
| `ContextBuilder` | `ai/context/builder.py:84` | `token_estimator` | `DeterministicTokenEstimator()` | Returns heuristic string length token counts without model tokenizers. |
| `ContextBuilder` | `ai/context/builder.py:85` | `compressor` | `DeterministicContextCompressor()` | Truncates text deterministically without NLP or semantic summarization. |
| `KnowledgeRouter`| `ai/knowledge/router.py:65` | `registry` | `KnowledgeRegistry()` | Creates empty in-memory registry rather than binding to production database. |
| `KnowledgeRouter`| `ai/knowledge/router.py:68` | `loader` | `KnowledgeLoader(workspace_root=...)` | Binds to local disk filesystem rather than managed object storage. |
| `ModelRouter` | `ai/routing/router.py:80` | `model_registry` | `get_model_registry()` | Binds to static frozen singleton `CANONICAL_MODELS`. |
| `ModelRouter` | `ai/routing/router.py:81` | `provider_registry` | `get_provider_registry()` | Binds to static frozen singleton `CANONICAL_PROVIDERS`. |
| `CapabilityRouter`| `ai/routing/capability_router.py:84` | `tool_gateway` | `ToolGateway(catalog=...)` | Auto-instantiates ToolGateway without external DI container. |
| `ToolGateway` | `ai/tools/gateway.py:256` | `idempotency_store` | `_default_idempotency_store` | Defaults to in-memory `InMemoryIdempotencyStore`. |
| `RecipeRegistry` | `ai/recipes/registry.py:106` | `recipe_dir` | Local `recipes/` folder | Automatically parses JSON files from disk on boot. |

---

## 5. Optional Imports & Soft Dependency Bypasses

Seven files in the repository utilize `try: import ... except ImportError:` patterns to allow execution in environments where dependencies are missing:

1. **FastMCP Compatibility Server (`ai/mcp/compatibility/server.py:89-94`)**:
   ```python
   try:
       from mcp.server.fastmcp import FastMCP
   except ImportError:
       logger.warning("mcp package not installed in current environment; FastMCP instance unavailable.")
       return None
   ```
   If `mcp` is not installed, calling `create_fastmcp_instance()` silently returns `None` rather than failing closed with an explicit configuration error.

2. **Fal Seedance Video Wrapper (`.agents/plugins/super-video-maker-plugin/tools/fal_seedance_video.py:82-94`)**:
   ```python
   try:
       import fal_client
   except ImportError:
       emit({"status": "failed", "error": "fal-client is not installed..."})
       sys.exit(2)
   ```
   Fails with custom exit code 2 if `fal-client` is missing.

3. **Contract Generators (`scripts/generate_ai_contracts.py:35-39`)**:
   ```python
   try:
       import pydantic
   except ImportError:
       os.execv(str(VENV_PY), [str(VENV_PY)] + sys.argv)
   ```
   Auto-respawns into virtualenv Python if Pydantic is not found in ambient interpreter.

---

## 6. Bypass Flags, Environment Variables & Execution Escape Hatches

The following environment variables and runtime flags act as execution bypasses across the codebase:

| Flag / Env Var | Target Component | Default Behavior | Bypass Behavior When Set | Safety Classification |
|---|---|---|---|---|
| `SKIP_STRICT_QC` | `scripts/core/security/env_policy.py:40` | QC fails closed on defect. | Historically converted QC failures to exit 0 (LED-022). Now restricted in production by `EnvPolicy`. | **CRITICAL SECURITY RISK** (Banned in prod) |
| `USE_LEGACY_RENDER_PATH` | `scripts/render_project.py:128` | Uses `RenderPlanner` & `MasterCompositor`. | Skips modern render planner and executes legacy Remotion CLI directly. | **HIGH DRIFT RISK** |
| `--legacy-cli` | `scripts/render_project.py:128` | Uses modern planner. | CLI flag skipping RenderPlanner. | **HIGH DRIFT RISK** |
| `AGY_IS_MANAGED` | `scripts/pipeline.py:108` | Requires review approval or CLI prompt. | Marks execution as daemon-managed; disables interactive prompts. | `ACTIVE_PRODUCT_RUNTIME` |
| `AGY_FAILURE_INJECTION_ENABLED` | `scripts/core/failure_injection.py:26` | Failure injection disabled. | Enables simulated crash points during pipeline stages. (Fails closed in prod). | `DEV_ONLY` |
| `AGY_INJECT_FAILURE` | `scripts/core/failure_injection.py:30` | None. | Injects specific error (e.g. `before_render:attempt=1`). | `DEV_ONLY` |
| `AGY_EPHEMERAL_WORKSPACE` | `scripts/core/worker.py:280` | Uses project dir. | Runs execution inside ephemeral tempdir, wiping scratch on finish. | `ACTIVE_PRODUCT_RUNTIME` |

---

## 7. Architectural Impact Assessment

1. **Masked Disconnection**: The extensive use of constructor defaults in `ai/` (`DeterministicKnowledgeRetriever`, etc.) allowed the AI subsystem to achieve near-100% test pass rates in isolated unit tests despite having **ZERO runtime integration** into FastAPI (`api/main.py`) or the worker pipeline (`scripts/pipeline.py`).
2. **False Operational Health**: Because `AssetService.upload_asset()` catches `StorageService.put()` exceptions silently (`api/services/asset_service.py:171`), an AWS S3 outage or MinIO credentials misconfiguration would not surface as an HTTP 500 error to end users; instead, assets would be saved locally and lost upon worker container destruction.
3. **Desynchronized Databases**: Because `StateStore._sync_to_db()` swallows non-CAS exceptions (`scripts/core/state_store.py:221`), disk-based projects can proceed through pipeline stages while the relational database `project_states` table remains stale or empty.

---

## 8. Verification Methods and Reproducible Commands

To independently reproduce and verify the findings in this report:

1. **Verify AssetService Silent Storage Swallowing**:
   ```bash
   sed -n '165,174p' api/services/asset_service.py
   # Observe: try storage.put() except Exception: pass
   ```

2. **Verify StateStore Silent DB Synchronization Swallowing**:
   ```bash
   sed -n '218,224p' scripts/core/state_store.py
   # Observe: except Exception as e: ... pass
   ```

3. **Verify Render Project Three-Tier Fallback Chain**:
   ```bash
   sed -n '127,186p' scripts/render_project.py
   # Observe: planner -> adapter -> legacy remotion CLI cascade
   ```

4. **Verify RunService Workspace Fallback**:
   ```bash
   sed -n '79,88p' api/services/run_service.py
   # Observe: except Exception: pass; actual_ws_id = actual_ws_id or "ws_default"
   ```


---


<a name='part-4-security-tenancy--authority-bypass-reality'></a>

## Part 4: Security, Tenancy & Authority Bypass Reality


> *Original Source: `documentation/reality_context_pack/17_SECURITY_TENANCY_AND_AUTHORITY_BYPASS_REALITY.md`*


### Sub-Report Title: Security, Tenancy & Authority Bypass Reality Report


- **Baseline Git SHA**: `90ec3de8d47494d5940d5cd1f9ed9a8e274ef6e1`
- **Branch**: `main`
- **Report Version**: 1.0.0
- **Last Updated**: 2026-10-07
- **Scope**: Rigorous security audit of authentication, authorization (RBAC), multi-tenancy (`TenantContext`), filesystem/command confinement policies, and authority bypass vectors across the repository.
- **Evidence Standard**: `CODE_PROVEN`, `TEST_PROVEN`, `CI_PROVEN`, `RUNTIME_REACHABILITY_PROVEN`, `DOCUMENTATION_ONLY`, `INFERRED`, `UNKNOWN`

---

## 1. Executive Summary

The security architecture of the video engine represents an ongoing consolidation between a local single-node CLI tool (Pre-S25) and a hardened multi-tenant SaaS backend (S26 through S28-R).

Key findings:
1. **Strong Filesystem and Subprocess Confinement**: Path traversal (`path_policy.py`) and command injection (`command_policy.py`) are centrally enforced and mathematically bounded. Arbitrary shell execution is blocked.
2. **Robust Multi-Tenant RBAC in S28-R Live Authoring**: The authoring subsystem derives tenant identity strictly from server-verified `TenantContext` and enforces CAS revisions.
3. **Critical Non-Production Authentication Backdoors**: In `api/core/auth.py`, when `MOTION_ENV != "production"`, callers can arbitrarily forge administrative identities using hardcoded token strings (`admin`, `system`) or unverified request headers (`X-Principal-ID`, `X-Principal-Roles`).
4. **CLI Authority Bypass**: The canonical pipeline script (`scripts/pipeline.py`) can be executed locally from the shell against any project without authentication, RBAC checks, or tenant validation.
5. **Disk vs. Database Tenancy Mismatch**: While `TenantRepository` models workspaces and projects in SQL, on disk all projects sit in a flat unpartitioned directory (`projects/{project_id}`).

---

## 2. Authentication & Authorization (RBAC) Architecture

### 2.1 Authentication Middleware & Token Verification (`api/core/auth.py`)

Authentication is managed via `extract_principal_from_request` and FastAPI dependency factories `require_permission` and `require_tenant_context`.

#### 2.1.1 Production Enforcement Mode (`is_production == True`)
- **Code Path**: `api/core/auth.py:228-233`
  ```python
  if is_production:
      return verify_signed_token(token, is_production=True)
  ```
- **Behavior**:
  - Validates cryptographically signed JWT tokens via `verify_signed_token()`.
  - Rejects unverified headers (`X-Principal-ID`) and client-asserted claim strings.
  - Enforces token expiration (`exp`) and cryptographic signature against `JWT_SECRET_KEY` [`CODE_PROVEN`].

#### 2.1.2 Development / Testing Backdoor Mode (`is_production == False`)
- **Code Path**: `api/core/auth.py:234-318`
- **Observed Fallbacks**:
  1. **Hardcoded Token Spoofing**:
     - `token in ("system", "system-token", "sys_worker")` returns a full `SYSTEM_WORKER` principal (`api/core/auth.py:240-241`).
     - `token.startswith("admin")` returns `admin_user` with global administrative scope `{"*": {Role.ADMIN}}` (`api/core/auth.py:243-250`).
     - `token.startswith("usr_")` returns an `EDITOR` principal without signature validation (`api/core/auth.py:252-259`).
  2. **Arbitrary Header Identity Spoofing**:
     - Callers can pass `X-Principal-ID: attacker`, `X-Principal-Roles: admin`, and `X-Principal-Type: HUMAN` to impersonate any user without credentials (`api/core/auth.py:266-305`).
- **Security Impact**:
  If a staging or development deployment fails to set `MOTION_ENV=production` explicitly, authentication is completely bypassed.

---

### 2.2 Role-Based Access Control (RBAC) & Tenant Derivation

The system defines 5 roles (`Role.ADMIN`, `Role.EDITOR`, `Role.REVIEWER`, `Role.CREATOR`, `Role.VIEWER`) and 25 distinct actions (`Action.PROJECT_CREATE`, `Action.RUN_EXECUTE`, `Action.AUTHORING_EDIT`, `Action.TEMPLATE_PROMOTE`, etc.).

#### 2.2.1 `require_tenant_context` vs. `require_permission` Asymmetry
A significant architectural drift exists in how routers enforce tenancy:
- **Strict Tenancy (`require_tenant_context`)**:
  - Used in: `api/routers/authoring.py`, `api/routers/candidate_promotions.py`, `api/routers/candidate_reviews.py`.
  - Derives `TenantContext` from authenticated principal membership in `TenantRepository`. If the principal is not a member of the workspace, it fails closed with `AccessDeniedError` (HTTP 403) [`CODE_PROVEN`].
- **Permissive Tenancy (`require_permission`)**:
  - Used in: `api/routers/projects.py`, `api/routers/runs.py`, `api/routers/assets.py`, `api/routers/artifacts.py`, `api/routers/outputs.py`, `api/routers/gates.py`.
  - Inspects permissions via `AuthorizationPolicy.enforce()`.
  - In `api/core/auth.py:324-342`, it attempts to attach `TenantContext` to `request.state` inside a `try ... except Exception: pass` block!
  ```python
  # api/core/auth.py:341-342
  except Exception:
      pass
  ```
  If `get_project(project_id)` throws or fails, the exception is silently swallowed, and the request proceeds with `request.state.tenant_context = None`!

---

## 3. Workspace Isolation & Storage Confinement

### 3.1 Dual-Tenancy Architecture (Database vs. Filesystem)

| Subsystem / Layer | Tenancy Enforcement Mechanism | Isolation Quality | Vulnerability / Bypass Point |
|---|---|---|---|
| **SQL Database (`TenantRepository`)** | `workspaces` table, `projects` table (`workspace_id`), foreign key constraints. | **STRONG** (`CODE_PROVEN`) | None in SQL; queries strictly filter by `workspace_id`. |
| **Object Storage (`StorageService`)** | Object keys prefixed with `workspaces/{workspace_id}/projects/{project_id}/...`. | **STRONG** (`CODE_PROVEN`) | Enforces key schema and prevents cross-tenant path traversal. |
| **Local Filesystem (`projects/`)** | Flat directory structure: `projects/{project_id}/`. | **WEAK** (`CODE_PROVEN`) | Projects are NOT partitioned by workspace folder on disk (`projects/ws_1/prj_1` does not exist). Any process accessing `projects/` directly can read any project regardless of workspace boundaries. |
| **Worker Subprocess Execution** | Worker sets `AGY_WORKSPACE_ID` environment variable. | **MODERATE** (`CODE_PROVEN`) | Subprocess receives workspace ID, but `scripts/pipeline.py` does not perform database lookups to verify project-workspace pairing. |

---

## 4. Path Traversal & Subprocess Confinement Policies

### 4.1 Path Security Confinement (`scripts/core/security/path_policy.py`)
- **Strict Identifier Validation**:
  - `validate_project_id(project_id)`: enforces regex `^[a-zA-Z0-9_-]+$`.
  - `validate_asset_id(asset_id)`: enforces regex `^[a-zA-Z0-9_-]+$`.
  - Rejects `..`, `/`, `\`, and Windows drive letters (`C:`) [`CODE_PROVEN`].
- **Safe Resolution Boundary**:
  - `resolve_safe_path(base_dir, user_path)`: calls `.resolve()` and enforces `resolved.relative_to(base)`.
  - Traversal attempts throw `ValueError("Path traversal detected (escapes base)")` [`CODE_PROVEN`].

### 4.2 Subprocess Confinement Policy (`scripts/core/security/command_policy.py`)
- **Canonical Execution Wrapper**: `safe_subprocess()` in `scripts/security/security.py`.
- **Command Whitelisting**:
  - Whitelists: `python`, `node`, `npx`, `ffmpeg`, `ffprobe`, `docker`.
  - Enforces `shell=False` unconditionally to prevent shell injection.
  - Sanitizes environment variables to prevent `LD_PRELOAD` or malicious `PATH` injection [`CODE_PROVEN`].

---

## 5. Authority Bypass Vectors & Attack Surface

### 5.1 Bypass Vector 1: Direct CLI Subprocess Execution
- **Mechanism**:
  A user, agent, or cron job with shell access executes:
  ```bash
  python scripts/pipeline.py <project_id>
  ```
- **Reality**:
  `scripts/pipeline.py` requires no JWT token, no API key, and no user principal. It directly loads `projects/{project_id}/.pipeline_state.json` and runs all gates.
- **Classification**: `RUNTIME_REACHABILITY_PROVEN` (Intentional design for local worker execution, but constitutes an authorization bypass in multi-tenant environments).

### 5.2 Bypass Vector 2: Unauthenticated Dev Headers in Non-Production
- **Mechanism**:
  Deploying the API without `MOTION_ENV=production` allows any HTTP client to send:
  ```http
  POST /projects/prj_victim/mutate HTTP/1.1
  X-Principal-ID: attacker
  X-Principal-Roles: admin
  ```
- **Reality**:
  FastAPI middleware in `api/core/auth.py:298` automatically constructs an administrative principal, bypassing all tenant checks.

### 5.3 Bypass Vector 3: Silent Exception in Permissive Tenant Context
- **Mechanism**:
  In `api/core/auth.py:341`, database lookups for `TenantContext` in `require_permission` routes are wrapped in `try ... except Exception: pass`.
- **Reality**:
  If the database connection is intermittent or drops, the route executes without a tenant context rather than failing closed.

---

## 6. Secrets Management & Provider Leak Prevention

### 6.1 Secrets Scanning & CI Enforcement
- **Gate**: `scripts/validators/check_secrets.py` runs in CI (`.github/workflows/remediation-ci.yml:254`).
- **Scope**: Scans git diffs and codebase files for high-entropy strings, AWS keys, OpenAI keys, Replicate tokens, and ElevenLabs credentials.
- **Result**: `CI_PROVEN` code cleanliness; zero live secrets committed in source tree.

### 6.2 Provider Bypass Hardening
- Legacy tools in `.agents/plugins/super-video-maker-plugin/tools/` (`elevenlabs_voice.py`, `replicate_video.py`) contain active runtime blockers:
  `raise PermissionError("DIRECT SECRET ACCESS BLOCKED: Raw ELEVENLABS_API_KEY access outside canonical S27 capability adapters is prohibited.")`.
- AST guards in `tests/ai/contracts/test_provider_bypass_guards.py` enforce that no script can read raw environment variables to contact external LLM or media APIs without going through `CapabilityRouter` [`TEST_PROVEN`].

---

## 7. Remediation Direction (DO NOT FIX YET)

To achieve enterprise multi-tenant hardening in a future milestone:
1. **Remove Non-Production Auth Backdoors**:
   Deprecate hardcoded token parsing (`admin`, `system`) and `X-Principal-*` headers. Require cryptographic token validation across all environments, using ephemeral dev keys for testing.
2. **Harmonize Tenancy Enforcement**:
   Replace `try ... except Exception: pass` in `require_permission` with fail-closed error handling (`raise HTTPException(status_code=500, detail="Tenant context resolution failed")`).
3. **Partition Disk Workspaces**:
   Restructure local project workspaces from `projects/{project_id}` to `projects/{workspace_id}/{project_id}` to match `StorageService` keys.
4. **Authorize CLI Invocations**:
   Require `scripts/pipeline.py` to accept and verify a signed run token or service principal when invoked outside the internal worker daemon.


---

