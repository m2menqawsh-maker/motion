# S28-R12 Compatibility Map

**Milestone**: S28-R12 (Multi-Engine RenderGraph & Render Planner)  
**Status**: VERIFIED PASS  
**Audited SHA**: `69b8798b2e2296bc5a24af411ac44133c072a029`  

---

## 1. Upstream & Downstream Subsystem Parity

This matrix records the exact architectural compatibility between the Render Planner & RenderGraph subsystem and all upstream and downstream modules in the clean-video-workspace codebase:

| Subsystem | Compatibility Status | Interface & Boundary Contract | Invariants Enforced |
| :--- | :--- | :--- | :--- |
| **Canonical VideoDocument (`contracts/blueprint.ts`)** | **COMPATIBLE** | Ingested via `request.document` (`BlueprintV2`). Sole source of truth for scenes and timing. | Zero mutation of documents. Planner strictly derives DAG from canonical scenes. |
| **Frame Evaluator (`contracts/evaluator.ts`)** | **COMPATIBLE** | Evaluator frame states consumed indirectly by renderer adapters during scene rendering. | Evaluator remains the single deterministic frame state authority. |
| **Timeline Authority (`contracts/timeline.ts`)** | **COMPATIBLE** | `calculateCanonicalDuration(scenes)` and `frameToSeconds` provide canonical timing math. | Overlaps and start frames strictly conform to canonical timing. |
| **Editor Session & Mutations (`contracts/mutations.ts`)** | **COMPATIBLE** | Zero imports from mutations or editor sessions in contracts or planner. | Planner cannot trigger mutations or alter change history. |
| **Template Spec (`contracts/template-spec.ts`)** | **COMPATIBLE** | `deriveSceneRequiredCapabilities` queries `getSemanticTemplateSpec()` for engine requirements. | Zero coupling between TemplateSpec and concrete rendering engines. |
| **Renderer Registry (`contracts/renderer.ts`)** | **COMPATIBLE** | `resolveCompatibleRenderer()` queries `RendererRegistry.list()` for capability satisfaction. | Registry contains zero planning policies. Planner queries capabilities dynamically. |
| **Remotion Adapter (`remotion/`)** | **COMPATIBLE** | Assigned to heavy video/typography scenes based on declared capabilities. | Produces `IntermediateArtifact` with explicit provenance. |
| **Canvas Adapter (`canvas/`)** | **COMPATIBLE** | Assigned to lightweight 2D scenes based on declared capabilities and lower compute cost. | Produces `IntermediateArtifact` with explicit provenance. |
| **Preview Proxy System (`contracts/preview-fidelity.ts`)** | **COMPATIBLE** | Shared capability taxonomy and approximation models without unifying authority. | `PreviewProxyCoordinator ≠ RenderPlanner` strictly enforced. |
| **Master Compositor (`compositor/master-compositor.ts`)** | **COMPATIBLE** | Ingests planned `IntermediateArtifact`s produced across engines and normalizes final video. | Master Compositor never selects renderers (R12 boundary honored). |
| **Quality Control Gate (`scripts/gates/final_qc.py`)** | **COMPATIBLE** | Final MP4 output from multi-engine plan passes ffprobe inspection. | Resolution, aspect ratio, and framerate match OutputProfile. |

---

## 2. Multi-Engine Planning & Composition Flow

The Multi-Engine Planner successfully orchestrated the end-to-end execution of a mixed project:

```text
Project: multi_engine_critical
 ├── Scene A (2D native)       ──> CanvasRendererAdapter   ──> IntermediateArtifact A (1.0s, 30f)
 ├── Scene B (video content)   ──> RemotionRendererAdapter ──> IntermediateArtifact B (1.0s, 30f)
 └── Scene C (2D native)       ──> CanvasRendererAdapter   ──> IntermediateArtifact C (1.0s, 30f)
                                                                       │
                                                                       ▼
                                                              MasterCompositor
                                                                       │
                                                                       ▼
                                                       Final MP4 (1080p@30fps, 3.0s)
```

- Verified in `tests/remotion/s28_r12_render_planner.test.ts` (test suite `R12-04`).
- Result: **PASS** (Zero engine conflicts, perfect timeline alignment, duration $3.0\text{ s}$).
