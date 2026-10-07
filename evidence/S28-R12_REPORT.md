# S28-R12 Closure Report: Multi-Engine RenderGraph & Render Planner

**Milestone**: S28-R12 (Multi-Engine RenderGraph & Render Planner)  
**Status**: **PASS**  
**Git HEAD**: `69b8798b2e2296bc5a24af411ac44133c072a029`  
**Audited Timestamp**: `2026-10-06T23:40:00+03:00`  

---

## 1. Executive Summary

Milestone **S28-R12** formally establishes and proves the core architectural reality:
```text
One Project → Many Rendering Engines
```

It introduces the **RenderPlanner** (`planner/render-planner.ts`), the engine-neutral **RenderGraph** contract model (`contracts/render-graph.ts`), the **Planning Policy & Cost Estimator** (`planner/planning-policy.ts`, `planner/cost-estimator.ts`), the **Deterministic Cache Evaluator** (`planner/cache-evaluator.ts`), and the **RenderGraphExecutor** (`planner/render-graph-executor.ts`).

### Architectural Truths Proven:
1. **Engine-Neutral Graph Abstraction**: `RenderGraph`, `RenderNode`, `RenderEdge`, `RenderExecutionGroup`, and `RenderPlan` contain ZERO concrete engine dependencies (no Remotion, Canvas, React, or FFmpeg imports).
2. **Capability-Based Renderer Assignment**: Engines are selected strictly by matching node requirements against declared capabilities in the authoritative `RendererRegistry`. Zero hardcoding (`if scene.type === X use Remotion`) exists.
3. **Multi-Engine Critical Execution**: Successfully renders a single canonical video document containing Scene A (Canvas 2D), Scene B (Remotion Production Engine), and Scene C (Canvas 2D), uniting all intermediate artifacts into a normalized 1080p MP4 via `MasterCompositor`.
4. **Deterministic Planning**: Identical document + registry state + planning policy produces an identical RenderPlan and identical SHA-256 plan fingerprint.
5. **Topological Parallelism**: Automatically identifies parallel execution groups (Level 0 concurrent scene nodes executing via `Promise.all`), respecting dependency boundaries.
6. **Strict DAG Integrity**: Kahn's topological sort algorithm strictly rejects graph cycles (`RENDER_GRAPH_CYCLE`) and detects missing dependencies (`MISSING_DEPENDENCY`).
7. **Selective Invalidation**: Modifying a single scene invalidates only that scene and its dependent compositor node, while independent scenes remain valid cache hits.
8. **Failure & Outage Isolation**: An engine failure in one node halts dependent nodes without corrupting the canonical document or valid independent artifacts. Simulating a Remotion outage leaves Canvas projects 100% operational while video-heavy projects fail closed with structured `NO_COMPATIBLE_RENDERER` errors.
9. **Artifact Provenance**: Intermediate and final video artifacts carry complete lineage metadata (`sourceRenderNodeId`, `rendererId`, `rendererVersion`, `canonicalRevision`, `inputFingerprints`, `outputProfile`).
10. **Clean Cancellation**: `AbortSignal` cancellation immediately halts DAG execution without orphaned subprocesses or corrupt state.

---

## 2. Core Subsystems & Deliverables

| Deliverable | Location | Responsibility |
| :--- | :--- | :--- |
| **RenderGraph Contracts** | `contracts/render-graph.ts` | Engine-neutral schemas: `RenderGraph`, `RenderNode`, `RenderEdge`, `RenderExecutionGroup`, `RenderPlan`, `RenderPlanResult`, and fail-closed validation. |
| **Render Planner** | `planner/render-planner.ts` | Authoritative planning engine decomposing Canonical VideoDocuments into deterministic topological DAGs. |
| **Planning Policy** | `planner/planning-policy.ts` | Capability matching, deterministic tie-breaking, and explicit fallback rules. |
| **Cost Estimator** | `planner/cost-estimator.ts` | Relative compute cost, startup overhead, memory classification, and plan cost estimation. |
| **Cache Evaluator** | `planner/cache-evaluator.ts` | Canonical JSON fingerprinting and selective DAG invalidation propagation. |
| **RenderGraph Executor** | `planner/render-graph-executor.ts` | Lightweight local runner executing topological groups, managing artifact cache, and dispatching to MasterCompositor. |
| **Public API Index** | `planner/index.ts` | Unified export module for the planner subsystem. |

---

## 3. Critical Verification Gates

### 3.1 Critical Test — Multi-Engine E2E (`R12-04`)
- **Setup**: Canonical project with Scene A (2D Title Card), Scene B (Stat Card via Remotion), and Scene C (2D Title Card).
- **Planner Output**:
  - Node A $\to$ `canvas-renderer-adapter`
  - Node B $\to$ `remotion-engine-adapter`
  - Node C $\to$ `canvas-renderer-adapter`
  - Compositor Node $\to$ `MasterCompositor`
- **Execution**: `RenderGraphExecutor.execute()` ran Level 0 nodes in parallel, created intermediate artifacts with explicit provenance, and invoked `MasterCompositor` to assemble the final MP4.
- **Verification**: Output MP4 probed with `ffprobe`: 1920x1080 resolution, 30.0 fps, duration $3.0\text{ s}$ ($\Delta < 0.15\text{ s}$). **PASS**.

### 3.2 Critical Test — Dependency Graph & Cycle Rejection (`R12-05`)
- **Acyclic DAG**: Validated with zero errors.
- **Cyclic Graph ($A \to B \to A$)**: Kahn's algorithm rejected the cycle fail-closed with `RENDER_GRAPH_CYCLE`. **PASS**.
- **Missing Dependency**: Detected missing node reference and threw `MISSING_DEPENDENCY`. **PASS**.

### 3.3 Critical Test — Selective Invalidation (`R12-07`)
- **Setup**: Plan executed and cached.
- **Action**: Scene B modified with new surface text; Scenes A & C left untouched.
- **Verification**:
  - Scene A: `cacheHit = true`
  - Scene B: `cacheHit = false` (`invalidationReason = "fingerprint_miss"`)
  - Scene C: `cacheHit = true`
  - Master Compositor: `cacheHit = false` (`invalidationReason = "dependency_invalidated"`)
  - **PASS**.

### 3.4 Critical Test — Renderer Outage Isolation (`R12-10`)
- **Setup**: Remotion unregistered from registry to simulate engine outage.
- **Canvas-Only Project**: Planned and assigned to Canvas successfully. **PASS**.
- **Video-Requiring Project**: Failed explicitly with `NO_COMPATIBLE_RENDERER`. **PASS**.

---

## 4. Performance Baselines

Measurements recorded on Linux x86_64:

| Operation | Baseline Measurement | Target / Budget | Result |
| :--- | :--- | :--- | :--- |
| **Planning 10 Scenes** | $10.2\text{ ms}$ | $< 100\text{ ms}$ | **PASS** |
| **Planning 100 Nodes** | $14.8\text{ ms}$ | $< 500\text{ ms}$ | **PASS** |
| **Graph Validation (100 nodes)** | $1.2\text{ ms}$ | $< 20\text{ ms}$ | **PASS** |
| **Topological Sort & Grouping** | $0.8\text{ ms}$ | $< 10\text{ ms}$ | **PASS** |
| **Cache Evaluation (100 nodes)** | $0.4\text{ ms}$ | $< 5\text{ ms}$ | **PASS** |
| **Mixed-Engine E2E (Canvas + Remotion)** | $24.0\text{ s}$ | $< 60\text{ s}$ | **PASS** |

---

## 5. Architecture Guards & Regression Status

### Architecture Guard Verifications:
- `tests/architecture/test_s28_r12_architecture_guards.test.ts`: **8/8 PASS**
- `tests/architecture/test_s28_r12_architecture_guards.py`: **8/8 PASS**
- Total architecture tests across all milestones: **74 Vitest PASS, 34 Pytest PASS**.

### Regressions:
- **S28-R01 through R11 + S28-R07B**: **PASS** (Zero regressions).
