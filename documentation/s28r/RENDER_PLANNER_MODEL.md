# RenderPlanner Authority Model & Decomposition Specifications

**Milestone**: S28-R12 (Multi-Engine RenderGraph & Render Planner)  
**Status**: VERIFIED PASS  
**Audited SHA**: `69b8798b2e2296bc5a24af411ac44133c072a029`  
**Authority**: `planner/render-planner.ts`

---

## 1. Single Planning Authority

The `RenderPlanner` (`planner/render-planner.ts`) is the single authoritative subsystem responsible for transforming a Canonical VideoDocument (`BlueprintV2`) into a deterministic `RenderPlan`.

### Core Responsibilities:
1. **Document Inspection**: Examines project metadata, canonical FPS, aspect ratio, audio plans, and scenes.
2. **Work Decomposition**: Decomposes the video document into discrete renderable fragments (scenes, audio stems, and composition stages).
3. **Capability Derivation**: Derives the exact set of canonical capabilities required by each fragment with zero hardcoding.
4. **Renderer Assignment**: Dispatches requirements to the authoritative `RendererRegistry`, selecting the optimal compatible engine based on policy.
5. **Topological Graph Construction**: Builds the dependency DAG and determines parallelizable execution groups.
6. **Cost & Fingerprint Computation**: Evaluates compute cost, startup overhead, memory classification, and content fingerprints.

```text
Canonical VideoDocument
       │
       ▼
 ┌───────────────┐
 │ RenderPlanner │ ──> Queries RendererRegistry (Capabilities & Availability)
 └───────┬───────┘
         │
         ▼
    RenderPlan (Deterministic DAG + ExecutionGroups + Cost Profile)
```

---

## 2. Work Decomposition Model

The `RenderPlanner` avoids excessive, gratuitous partitioning while providing fine-grained decomposition suitable for multi-engine dispatch:

### 2.1 Scene-Level Decomposition
Each canonical scene $S_i$ in `document.scenes` becomes an independent visual node:
- **Scope**: `{ type: "scene", id: scene.scene_id, sceneIndex: i }`
- **Time Range**: Start frame computed contiguously; duration matches scene canonical duration.
- **Fragment Document**: An isolated sub-document containing only this scene, starting at relative frame 0.
- **Capabilities**: Exact capabilities required by scene content, media kind, layers, keyframes, transitions, and templates.

### 2.2 Master Compositor Stage
A final assembly node (`node_master_compositor`) is placed at the root of the DAG:
- **Scope**: `{ type: "compositor", id: "master" }`
- **Dependencies**: Depends on all scene render nodes and audio stem nodes.
- **Artifact**: Ingests `IntermediateArtifact`s produced upstream and invokes `MasterCompositor.composite()` to assemble the normalized final video.

---

## 3. Deterministic Planning Guarantees

Identical inputs produce identical RenderPlans down to the SHA-256 plan fingerprint:

$$\text{Canonical Document} + \text{RendererRegistry State} + \text{PlanningPolicy} \implies \text{Deterministic RenderPlan}$$

### Tie-Breaking Rules:
1. **Scene Order**: Preserves explicit canonical scene index order ($0, 1, 2, \dots$).
2. **Node ID Stability**: Structured stable naming (`node_scene_${sceneId}`, `node_master_compositor`).
3. **Renderer Ranking Tie-Breakers**:
   - Relative compute cost ascending (cheaper engine first).
   - Adapter priority descending.
   - Number of supported capabilities descending.
   - Adapter ID lexicographical ascending.
4. **Adjacency Sorting**: Adjacency lists and Kahn queues are strictly sorted prior to topological level computation.

---

## 4. Separation of Powers

The architecture enforces strict separation of concerns across the pipeline:

| Subsystem | Authority & Responsibility | Forbidden Actions |
| :--- | :--- | :--- |
| **Canonical VideoDocument** | Sole authority for video structure, semantics, and timing. | Cannot import planner or engine code. |
| **RendererRegistry** | Sole authority for registering engines and declaring capabilities. | Cannot contain planning policies or graph logic. |
| **RenderPlanner** | Sole authority for decomposing work and building the RenderPlan. | CANNOT render frames, execute FFmpeg, or mutate documents. |
| **RenderGraphExecutor** | Subordinated local runner executing nodes and tracking progress. | CANNOT alter plan topology or mutate canonical documents. |
| **MasterCompositor** | Subordinated assembly orchestrator normalizing and stitching clips. | CANNOT select renderers or make planning decisions. |
