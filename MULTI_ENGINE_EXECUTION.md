# Multi-Engine Execution, Parallelism & Failure Isolation

**Milestone**: S28-R12 (Multi-Engine RenderGraph & Render Planner)  
**Status**: VERIFIED PASS  
**Audited SHA**: `69b8798b2e2296bc5a24af411ac44133c072a029`  
**Authorities**: `planner/render-graph-executor.ts` & `planner/cache-evaluator.ts`

---

## 1. Multi-Engine Architecture Reality

Milestone S28-R12 proves and delivers the multi-engine execution paradigm:
```text
One Project → Many Engines
```

A single canonical project containing diverse scene types (2D titles, video layers, animations) is planned into a RenderGraph where each scene executes on its optimal specialized rendering engine, followed by unified assembly in the Master Compositor:

```text
Scene A (2D Title)   ──> CanvasRendererAdapter   ──> IntermediateArtifact A
                                                                 │
Scene B (Video Clip) ──> RemotionRendererAdapter ──> IntermediateArtifact B
                                                                 │
Scene C (2D Outro)   ──> CanvasRendererAdapter   ──> IntermediateArtifact C
                                                                 │
                                                                 ▼
                                                        MasterCompositor
                                                                 │
                                                                 ▼
                                                       Final 1080p MP4 Video
```

---

## 2. Parallelism & Topological Levels

The `RenderGraphExecutor` executes nodes level by level according to the `RenderExecutionGroup`s computed by the Planner:

- **Level 0 (In-Degree 0)**: Scene A, Scene B, and Scene C have zero mutual dependencies. They execute concurrently via `Promise.all` (`parallel: true`).
- **Level 1**: The Master Compositor depends on IntermediateArtifacts from Level 0. It executes strictly after all Level 0 nodes complete (`parallel: false`).

---

## 3. Selective Invalidation & DAG Cache Propagation

The caching subsystem (`planner/cache-evaluator.ts`) guarantees that changing a single scene only invalidates that scene and its downstream dependents:

```text
Edit Scene B:
  • Scene A: Fingerprint unchanged  ──> CACHE HIT (Reused)
  • Scene B: Fingerprint changed    ──> CACHE MISS (Re-rendered)
  • Scene C: Fingerprint unchanged  ──> CACHE HIT (Reused)
  • Master Compositor: Input B invalid ──> DEPENDENCY INVALIDATED (Re-assembled)
```

Verification recorded in test `R12-07`: Scene A and Scene C remain cache hits; only Scene B and the Compositor execute.

---

## 4. Failure Isolation & Outage Resilience

### 4.1 Isolated Engine Crashes
If an engine fails during node execution (e.g. simulated engine crash on Node B):
- Independent nodes (Node A) complete successfully.
- Node B records structured failure.
- Downstream nodes (Node C Master Compositor) are skipped due to missing upstream dependency.
- **Zero corrupted final output is generated.**
- Valid independent artifacts remain safely preserved in the cache.

### 4.2 Renderer Outage Simulation
If an engine is unavailable or unregistered (e.g. Remotion engine offline):
- Projects requiring only Canvas capabilities continue to plan and execute with 100% success.
- Projects requiring video capabilities fail closed immediately during planning with `NO_COMPATIBLE_RENDERER`, isolating the outage without crashing the runtime.
