# S28-R11 Compatibility Map

**Milestone**: S28-R11 (Master Compositor & Output Normalization)  
**Status**: VERIFIED PASS  
**Audited SHA**: `69b8798b2e2296bc5a24af411ac44133c072a029`  

---

## 1. Upstream & Downstream Subsystem Parity

This matrix records the exact architectural compatibility between the Master Compositor subsystem and all upstream and downstream modules in the video maker codebase:

| Subsystem | Compatibility Status | Interface & Boundary Contract | Invariants Enforced |
| :--- | :--- | :--- | :--- |
| **Canonical VideoDocument (`contracts/blueprint.ts`)** | **COMPATIBLE** | Consumed via `request.document` (`BlueprintV2`). Sole source of timing and scene order. | Zero mutation of documents. Compositor never invents an independent timeline clock. |
| **Frame Evaluator (`contracts/evaluator.ts`)** | **COMPATIBLE** | Consumed indirectly via renderer adapters and audio track evaluations. | Parity with evaluator frame timing and ducking volume model. |
| **Timeline Authority (`contracts/timeline.ts`)** | **COMPATIBLE** | `calculateCanonicalDuration(scenes)` and `frameToSeconds` provide canonical timing math. | Overlaps from transitions correctly subtracted from total runtime. |
| **Editor Session & Mutations (`contracts/mutations.ts`)** | **COMPATIBLE** | Zero imports from mutations or editor sessions. | Master Compositor cannot trigger mutations or alter change history. |
| **Template Spec (`contracts/template-spec.ts`)** | **COMPATIBLE** | Engine-neutral templates render through adapters prior to composition. | Zero coupling between TemplateSpec and composition filtergraphs. |
| **Renderer Registry (`contracts/renderer.ts`)** | **COMPATIBLE** | Renderers register capabilities independently. | Registry contains zero composition logic. Compositor does NOT select renderers. |
| **Remotion Adapter (`remotion/`)** | **COMPATIBLE** | Outputs consumed as `IntermediateArtifact` with `sourceRendererId: "remotion-engine-adapter"`. | Remotion produces scene clips without needing to assemble full external videos. |
| **Canvas Adapter (`canvas/`)** | **COMPATIBLE** | Outputs consumed as `IntermediateArtifact` with `sourceRendererId: "canvas-renderer-adapter"`. | Canvas produces sub-second 2D clips without needing complex audio muxers. |
| **Audio Preview Runtime (`preview/audio/`)** | **COMPATIBLE** | Canonical AudioPlan semantics match between preview runtime and master compositor. | Dynamic voiceover ducking yields exact volume curves in final MP4. |
| **Quality Control Gate (`scripts/gates/final_qc.py`)** | **COMPATIBLE** | Integrated via `compositor/qc-adapter.ts` (`runQcForCompositorResult`). | Output MP4 conforms to ffprobe inspection, strict aspect ratio, and AV sync gates. |

---

## 2. Multi-Engine Assembly Compatibility

The Master Compositor verified mixed-engine composition:

```text
Scene 1 (2D Title Card) ──> CanvasRendererAdapter ──> Intermediate Artifact A (PNG sequence / MP4)
                                                                 │
                                                                 ▼
Scene 2 (Stat Card)     ──> RemotionRendererAdapter ──> Intermediate Artifact B (1080p MP4)
                                                                 │
                                                                 ▼
                                                        MasterCompositor
                                                                 │
                                                                 ▼
                                                   Final Normalized MP4 (1080p, 30fps)
```

- Verified in `tests/remotion/s28_r11_master_compositor.test.ts` (test suite `R11-04`).
- Result: **PASS** (Zero engine conflicts, perfect timeline alignment).
