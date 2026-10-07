# S28-R15 Evidence: Load, Soak & Resource Leak Results

**Milestone**: S28-R15 Verification, Fault Destruction, Fencing, Load & Soak  
**Date**: October 7, 2026  
**Status**: COMPLETE (All Gates PASS)  
**Acceptance Declaration**: `S28-R15 SOAK & LOAD GATE PASS`

---

## 1. Production-Like Environment Declaration Table

| Subsystem / Component | Selected Implementation | Connection Mode / Port | Scope of Evidence Provided | Known Staging Differences / Limitations |
| :--- | :--- | :--- | :--- | :--- |
| **Relational Database** | PostgreSQL 16.10 (`r15_test_postgres` container) | Direct TCP (`localhost:5433`), psycopg 3.3.6 pool | Clean rebuild, versioned migrations, independent-connection CAS race, restart durability, lease recovery, stale worker fencing | Running in local Docker container; latency is localhost (<1 ms vs ~5-15 ms on AWS RDS) |
| **Object Storage** | S3-Compatible Server (`moto_server 5.0.28`, AWS S3 API v4) | HTTP TCP (`127.0.0.1:9005`), boto3 backend | Real S3 PUT/GET/DELETE, SHA-256 hash checks, preview proxies, intermediate segments, final outputs, path traversal rejection, cross-tenant isolation | Moto S3 server runs locally without AWS IAM role authentication (uses mock static credentials); localhost throughput |
| **Media Engine** | FFmpeg 8.1.3 (with ffprobe, libx264, aac, lavfi) | CLI stdio pipe, isolated sandboxes | Synthetic generation, transcoding, composition, audio LUFS normalization (-16 voiceover, -24 sfx), duration verification | Local CPU encoding (libx264) rather than hardware NVENC/VAAPI |
| **Runtime Platforms** | Python 3.14.7 (`.venv`), Node.js v26.7.0 | Local process execution | Python domain models, PostgreSQL adapters, Remotion headless bundler, Vitest runner | Single-node multi-process rather than distributed Kubernetes cluster |

---

## 2. Load Testing Scenarios & Measured Metrics

| Load Dimension | Concurrency / Scale | System Component | Measured Throughput / Latency | Outcome | Verification Test / Evidence |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Control-Plane Authoring CAS** | 20 sequential CAS commits | `CanonicalDocumentRepository` | 20 commits in 142 ms (~7.1 ms / commit) | Revision progressed 1 -> 21; 0 lost updates | [`test_r15_c23_control_plane_stress_load`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/tests/core/test_s28_r15_destruction_and_fault.py#L540) |
| **Independent-Connection CAS Race** | 2 concurrent transactions (Human vs AI) | PostgreSQL 16 (`localhost:5433`) | Resolved in 12 ms | Exactly 1 winner (rev 2 -> 3); exactly 1 `RevisionConflictError`; 0 lost updates | [`test_pg_real_cas_concurrency_race`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/tests/core/test_s28_r15_postgres_and_s3_closure.py#L104) |
| **Parallel Writer Contention** | 5 concurrent writers on same revision | `CanonicalDocumentRepository` | All 5 resolved in 18 ms | Exactly 1 winner; 4 conflicts; zero corrupted state | [`scripts/testing/s28_r15_soak_and_load_runner.py`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/scripts/testing/s28_r15_soak_and_load_runner.py#L170) |
| **Duplicate Operation ID Race** | Replay of identical `operation_id` | `AuthoringIdempotencyRepository` | Instant cache hit (<1 ms) | Idempotent replay; distinct payload raises `IdempotencyConflictError` | [`test_pg_duplicate_operation_id_idempotency_race`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/tests/core/test_s28_r15_postgres_and_s3_closure.py#L157) |
| **Multi-Engine Render Load** | 5 concurrent pipelines | `ProductionRenderGraphExecutor` | 5 jobs completed in 3.66s (~730 ms / job) | All 5 jobs completed with `ok: true` | [`R15-LD-01`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/tests/remotion/s28_r15_destruction_and_load.test.ts#L1120) |
| **Real S3 Object Storage Round Trip** | Preview proxy, intermediate segment, final MP4 | S3 Backend (`http://127.0.0.1:9005`) | Full round-trip in 24 ms | Hash matched SHA-256; cross-tenant path access rejected | [`test_s3_storage_round_trip`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/tests/core/test_s28_r15_postgres_and_s3_closure.py#L296) |
| **Proxy Cache Burst** | 10 rapid proxy bursts | `ProductionPreviewCoordinator` | 10 requests completed in 14 ms | 1 cache miss + 9 cache hits (0 duplicate renders) | [`R15-PV-01`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/tests/remotion/s28_r15_destruction_and_load.test.ts#L615) |

---

## 3. Real Long-Duration Soak Test Execution (30.01 Minutes Wall-Clock)

- **Execution Command**: `.venv/bin/python scripts/testing/s28_r15_soak_and_load_runner.py --duration 1800 --interval 60 --output-json documentation/s28r/evidence/soak_telemetry_30m.json`
- **Start Timestamp (UTC)**: `2026-10-07T17:36:03.297297+00:00`
- **End Timestamp (UTC)**: `2026-10-07T18:06:03.880901+00:00`
- **Elapsed Wall-Clock Duration**: **1800.58 seconds (30.01 minutes)**
- **Telemetry Data File**: [`documentation/s28r/evidence/soak_telemetry_30m.json`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/documentation/s28r/evidence/soak_telemetry_30m.json)

### Measured Soak Execution Totals & Percentiles

| Metric | Measured Value | Requirement / Boundary | Result |
| :--- | :--- | :--- | :--- |
| **Wall-Clock Duration** | **1800.58 s (30.01 min)** | $\ge 1800$ s (30 minutes) | **PASS** |
| **Continuous Cycles Completed** | **2,052 cycles** | Sustained continuous load | **PASS** |
| **Total CAS Mutations Committed** | **4,788 mutations** | Monotonic revisions | **PASS** |
| **Completed Render Jobs** | **2,345 jobs** | Enqueue -> Claim -> S3 -> Complete | **PASS** |
| **Simulated Cancelled Jobs** | **410 jobs** | Instant cleanup & lease removal | **PASS** |
| **Simulated Unrecoverable Failures** | **186 jobs** | Fail-closed status, no orphan files | **PASS** |
| **Total S3 Operations** | **6,156 operations** | Zero network or S3 errors (0 errors) | **PASS** |
| **Authoring Latency (p50)** | **44.45 ms** | Sub-100 ms target | **PASS** |
| **Authoring Latency (p95)** | **72.86 ms** | Sub-150 ms target | **PASS** |
| **Render Lifecycle Latency (p50)** | **194.16 ms** | Sub-500 ms synthetic target | **PASS** |
| **Render Lifecycle Latency (p95)** | **272.18 ms** | Sub-600 ms synthetic target | **PASS** |
| **Initial Memory RSS** | **82.67 MB** | Baseline | **PASS** |
| **Final Memory RSS** | **83.87 MB** | Delta: **+1.20 MB** across 30 minutes | **PASS** |
| **Open File Descriptors (FDs)** | **12 FDs** (flat baseline) | Zero socket/pipe leak | **PASS** |
| **Orphan Child Processes** | **0** | No dangling FFmpeg processes | **PASS** |
| **PostgreSQL Connection Count** | **1** (connection pool idle) | Zero leaked DB connections | **PASS** |

---

## 4. Post-Soak Zero Resource Leak Gate

| Resource Checked | Verification Condition | Measured Post-Soak Value | Status |
| :--- | :--- | :--- | :--- |
| **Orphan Render Child Processes** | `len(psutil.Process().children()) == 0` | **0** | **PASS** |
| **Leaked Worker Temp Sandboxes** | Zero directories matching `soak_render_*` | **0** | **PASS** |
| **Stuck PostgreSQL Leases** | `SELECT count(*) FROM project_execution_leases` == 0 | **0** | **PASS** |
| **Stuck Running / Queued Jobs** | `SELECT count(*) FROM runs WHERE status IN ('RUNNING', 'QUEUED')` == 0 | **0** | **PASS** |
| **Open File Descriptors** | `process.num_fds()` remains bounded | **12 FDs** (stable) | **PASS** |
| **DB Connections** | Connections returned cleanly to pool | **1 connection** (clean) | **PASS** |

---

## 5. Post-Soak Canonical Durability Reload

- Reloaded all 6 projects across all 3 workspaces directly from PostgreSQL 16.
- Confirmed `blueprint_version == "2.0.0"` for every project.
- Confirmed document revision progression is strictly monotonic across all 4,788 mutations (e.g. project revisions reached 1028+).
- Confirmed event streams in `run_events` are strictly ordered $1 \dots N$ without gaps, duplicates, or out-of-order sequences.
- Confirmed all artifact versions in S3 are accessible with verified content hashes.
- Result: **100% DURABLE RECOVERY & DATA INTEGRITY VERIFIED**.
