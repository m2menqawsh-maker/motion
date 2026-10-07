# Pure Deterministic Frame Evaluation Specification

**Status**: Formally Adopted Architecture Standard  
**Milestone**: S28-R03  
**Parent Initiative**: S28-R — Renderer Independence & Live Editor Core  
**Governing Module**: `contracts/evaluator.ts`  
**Date**: 2026-10-06  

---

## 1. Executive Summary

The **Frame Evaluation Engine** is a pure, framework-agnostic mathematical evaluator that calculates the visual and audible state of any video project at any given frame $N$.

### Critical Invariants:
1. **Engine Neutrality**: Zero imports from React, Remotion, Canvas, DOM, WebGL, or OS display servers.
2. **Deterministic Output**: Given identical inputs $(V, N)$, the evaluated state $E(V, N)$ is bit-identical across runs, platforms, and Node/Bun processes.
3. **Zero Wall-Clock Dependency**: Absolutely zero calls to `Date.now()`, `performance.now()`, or `Math.random()`.
4. **Sub-millisecond Latency**: Average frame evaluation executes in $< 0.1$ ms, establishing the real-time foundation for the future Live Editor and Preview Runtime (S28-R06).

---

## 2. Evaluation Pipeline & Algorithm

```mermaid
flowchart TD
    Input[Canonical Project V + Frame N] --> ActiveScenes[Filter Active Scenes: frame in [startFrame, endFrame)]
    Input --> ActiveAudio[Evaluate AudioPlan: Vo, BGM, SFX at frame N]
    ActiveScenes --> SceneLayers[Extract / Synthesize Canonical Layers]
    SceneLayers --> ZSort[Sort Layers by z_index & Track Order]
    ZSort --> LoopLayers[Iterate Layers]
    LoopLayers --> ChannelEval[Evaluate Layer Channels at localFrame]
    ChannelEval --> HierCompose[Compose Parent Hierarchical Transforms]
    HierCompose --> OutputLayer[Construct EvaluatedLayerState]
    OutputLayer --> FinalState[Assemble EvaluatedFrameState: active scenes, layers, audio]
```

---

## 3. Evaluated State Structure (`EvaluatedFrameState`)

The output of `evaluateVideoAtFrame()` is an ephemeral, in-memory data snapshot:

```typescript
export interface EvaluatedFrameState {
  frame: number;
  fps: number;
  timeMs: number;
  active_scenes: string[];
  layers: EvaluatedLayerState[];
  audio: EvaluatedAudioState;
}

export interface EvaluatedLayerState {
  layer_id: string;
  kind: string;
  visible: boolean;
  localFrame: number;
  transform: {
    x: number;
    y: number;
    scaleX: number;
    scaleY: number;
    rotation: number;
    opacity: number;
  };
  opacity: number;
  properties: Record<string, any>;
}
```

---

## 4. Subprocess Isolation Proof

To decisively prove that frame evaluation functions without rendering engines, the test suite executes an isolated Node subprocess with custom module interceptors blocking `react`, `remotion`, and all `@remotion/*` packages. The evaluator loads the canonical blueprint, resolves timeline tracks, steps through discrete frames, and outputs exact evaluated layer transforms and opacities with exit code 0.
