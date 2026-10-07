# S28-R15 Evidence: Baseline & Test Inventory

**Milestone**: S28-R15 Verification, Fault Destruction, Fencing, Load & Soak  
**Date**: October 7, 2026  
**Commit SHA**: `69b8798b2e2296bc5a24af411ac44133c072a029` (Branch: `feature/s27-ai-platform`)

---

## 1. Toolchain & Runtime Baseline

| Component | Verified Version | Notes |
| :--- | :--- | :--- |
| **Python** | `3.14.7` | Standard library + pytest `9.1.1` in `.venv` |
| **Node.js** | `v26.7.0` | Vitest `5.0.0`, TypeScript runtime |
| **FFmpeg** | `8.1.3` | System FFmpeg with `libx264`, `aac`, `lavfi`, `ffprobe` |
| **Operating System** | `Linux 6.6.137+ x86_64` | POSIX file locking, subprocess management |

---

## 2. Test Suite Portfolio Baseline

| Test Suite Category | Suite File Path | Test Count | Pass Rate | Execution Time |
| :--- | :--- | :--- | :--- | :--- |
| **Core Destruction & Fault (Py)** | `tests/core/test_s28_r15_destruction_and_fault.py` | 15 | 100% (15/15) | 0.93s |
| **Architecture Guards (Py)** | `tests/architecture/test_s28_r15_architecture_guards.py` | 8 | 100% (8/8) | 0.59s |
| **R14 Regressions (Py)** | `tests/architecture/test_s28_r14_architecture_guards.py` | 10 | 100% (10/10) | 0.71s |
| **Destruction & Load (TS)** | `tests/remotion/s28_r15_destruction_and_load.test.ts` | 25 | 100% (25/25) | 24.80s |
| **Final Campaigns C29–C33 (TS)** | `tests/remotion/s28_r15_part3_final_campaigns.test.ts` | 5 | 100% (5/5) | 10.64s |
| **Architecture Guards (TS)** | `tests/architecture/test_s28_r15_architecture_guards.test.ts` | 6 | 100% (6/6) | 0.43s |
| **R14 Regressions (TS)** | `tests/architecture/test_s28_r14_architecture_guards.test.ts` | 10 | 100% (10/10) | 0.34s |
| **TOTAL VERIFIED** | *All active suites* | **79** | **100% (79/79)** | **~38.4s** |

---

## 3. Campaigns Inventory (R15-C01 through R15-C33)

- **Campaigns R15-C01 to R15-C11**: Migration, parity, multi-engine topology, cross-engine authoring, cache invalidation, CAS concurrency.
- **Campaigns R15-C12 to R15-C23**: Process crashes, worker deaths, lease expiry, renderer failure matrix, compositor errors, QC semantics, cancellation, retries, storage/DB failover, clock skew.
- **Campaigns R15-C24 to R15-C28**: Real multi-engine load, soak/leak verification, aspect ratio matrix (16:9, 9:16, 1:1), audio drift (<150ms), full AI->Editor->Export E2E.
- **Campaigns R15-C29 to R15-C33**: Legacy project E2E, output publication consistency, generational stale worker fencing attack, security/leakage red team, observability & trace correlation.
