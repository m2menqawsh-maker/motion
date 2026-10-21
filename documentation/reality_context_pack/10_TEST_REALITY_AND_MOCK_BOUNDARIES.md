# Test Reality & Mock Boundaries Report
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
