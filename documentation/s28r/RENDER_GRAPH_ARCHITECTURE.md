# RenderGraph Architecture & DAG Specifications

**Milestone**: S28-R12 (Multi-Engine RenderGraph & Render Planner)  
**Status**: VERIFIED PASS  
**Audited SHA**: `69b8798b2e2296bc5a24af411ac44133c072a029`  
**Authority**: `contracts/render-graph.ts`

---

## 1. Executive Summary

Milestone **S28-R12** formally achieves the core architectural milestone:
```text
One Project → Many Rendering Engines
```

The **RenderGraph** subsystem provides an engine-neutral Directed Acyclic Graph (DAG) abstraction representing the complete work decomposition of a video project into independent, concurrent, and dependent renderable units.

Each node in the RenderGraph represents a discrete fragment of work (such as a single scene, an audio stem, or the final Master Compositor assembly stage). Nodes are assigned to specific rendering engines (e.g. `CanvasRendererAdapter`, `RemotionRendererAdapter`) through capability-based resolution against the authoritative `RendererRegistry`.

```text
┌────────────────────────────────────────────────────────┐
│               Canonical VideoDocument                  │
│       (BlueprintV2 / Evaluated Timeline State)         │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│                     RenderPlanner                      │
│            [Sole Graph Planning Authority]             │
│  • Work Decomposition (Scene / Fragment / Stems)       │
│  • Capability Derivation (Zero hardcoding)             │
│  • Renderer Assignment via RendererRegistry            │
│  • Topological Level & Parallel Group Calculation      │
└──────────────────────────┬─────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────┐
│                      RenderGraph                       │
│             (Deterministic Topological DAG)            │
│                                                        │
│   Level 0 (Parallel Execution):                        │
│   ┌─────────────────────┐   ┌──────────────────────┐   │
│   │  Node A (Scene 1)   │   │  Node B (Scene 2)    │   │
│   │ [Canvas 2D Engine]  │   │  [Remotion Engine]   │   │
│   └──────────┬──────────┘   └───────────┬──────────┘   │
│              │                          │              │
│              └────────────┬─────────────┘              │
│                           │                            │
│   Level 1 (Dependent Execution):                       │
│   ┌───────────────────────▼────────────────────────┐   │
│   │          Node C (Master Compositor)            │   │
│   │     [Engine-Neutral Assembly Orchestrator]     │   │
│   └───────────────────────┬────────────────────────┘   │
└───────────────────────────┼────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────┐
│                  Final Video Artifact                  │
│                   (Normalized MP4)                     │
└────────────────────────────────────────────────────────┘
```

---

## 2. Core Graph Contracts

The RenderGraph contracts live in [`contracts/render-graph.ts`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/contracts/render-graph.ts) and maintain 100% engine-neutrality (zero imports from Remotion, Canvas, React, FFmpeg, or DOM packages).

### 2.1 RenderNode Contract
Every `RenderNode` contains complete structural, temporal, capability, execution, and cache metadata:

```typescript
export interface RenderNode {
  id: string; // e.g. "node_scene_scene_1"
  scope: RenderNodeScope; // type: "scene" | "layer" | "fragment" | "audio" | "audio_stem" | "compositor"
  timeRange: RenderTimeRange; // startFrame, durationFrames, startTimeSec, durationSec
  requiredCapabilities: CanonicalRendererCapability[]; // e.g. ["text", "export_video"]
  dependencies: string[]; // Upstream node IDs required before execution
  assignedRendererId?: string; // e.g. "canvas-renderer-adapter", "remotion-engine-adapter"
  assignedRendererVersion?: string; // e.g. "1.0.0", "4.0.525"
  cacheability: RenderNodeCacheability; // cacheable: boolean, contentFingerprint, invalidationScope
  preferredExecutionProfile: RenderExecutionProfile; // compute cost, memory class, timeout
  outputArtifactType: IntermediateArtifactType; // "video" | "sequence" | "image" | "audio"
  fragmentDoc?: BlueprintV2; // Isolated sub-document for this render unit
  status: RenderNodeStatus; // "pending" | "scheduled" | "running" | "completed" | "failed" | "skipped"
  metadata?: Record<string, unknown>;
}
```

### 2.2 RenderEdge Contract
Represents dependency relationships between upstream artifact producers and downstream consumers:

```typescript
export interface RenderEdge {
  fromNodeId: string; // Upstream dependency node
  toNodeId: string;   // Downstream dependent node
  type: "artifact_input" | "audio_stem" | "sequence_input" | "dependency";
  metadata?: Record<string, unknown>;
}
```

### 2.3 RenderExecutionGroup Contract
Groups nodes into topological levels, identifying nodes that have zero mutual dependencies and can execute in parallel:

```typescript
export interface RenderExecutionGroup {
  level: number;      // Topological depth (0, 1, 2, ...)
  nodeIds: string[];  // Node IDs executing at this level
  parallel: boolean;  // True if group contains >= 2 mutually independent nodes
}
```

---

## 3. Graph Validation & Cycle Detection

The RenderGraph is validated fail-closed prior to execution via `validateRenderGraph()`:

1. **Unique Node Identities**: All node IDs must be strictly unique.
2. **Referential Integrity**: All edge references (`fromNodeId`, `toNodeId`) and node `dependencies` must resolve to existing nodes. Missing references throw `MISSING_DEPENDENCY`.
3. **Kahn's Topological Algorithm**: Computes node in-degrees and strictly rejects cyclic graphs (`RENDER_GRAPH_CYCLE`).
4. **Time Range Integrity**: Start frames must be non-negative integers ($\ge 0$); duration frames must be strictly positive integers ($> 0$).
5. **Output Reachability**: The target output node (e.g. Master Compositor) must be reachable from upstream render nodes.

---

## 4. Architectural Boundaries & Invariants

1. **Contracts Purity**: `contracts/render-graph.ts` contains zero concrete engine references.
2. **Planner Separation**: `RenderPlanner` produces plans; it never executes renders or FFmpeg filtergraphs directly.
3. **Zero Canonical Mutation**: Neither `RenderGraph`, `RenderPlanner`, nor `RenderGraphExecutor` mutate the upstream `Canonical VideoDocument`.
4. **Provenanced Artifacts**: Every artifact emitted during graph execution retains full lineage, source node ID, engine ID, version, and input content fingerprints.
