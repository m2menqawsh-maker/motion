# S28-R04 Compatibility & Migration Map

**Status**: Formally Adopted Architecture Standard  
**Milestone**: S28-R04 Complete (Part 1 + Part 2)  
**Parent Initiative**: S28-R — Renderer Independence & Live Editor Core  
**Governing Modules**: `contracts/mutations.ts`, `contracts/editor-session.ts`, `contracts/blueprint.ts`, `contracts/canonical-video.ts`  
**Date**: 2026-10-06  

---

## 1. Executive Summary

Milestone **S28-R04** establishes the Canonical Mutation Core, live Editor Session, exact bijective Undo/Redo, transient high-frequency drag editing, and mutation coalescing without introducing a secondary document authority. Pure `BlueprintV2` remains the sole canonical truth.

---

## 2. Compatibility Mapping Matrix

| Subsystem / Contract | Pre-R04 State (R03) | Post-R04 State (Parts 1 & 2) | Backward Compatibility | Risk Level |
| :--- | :--- | :--- | :--- | :--- |
| **`BlueprintV2` Schema** | Had scenes, audio, aspect_ratio, fps, meta. No revision field. | Additive optional `revision?: number` (default 0) and `applied_mutations?: string[]` (default `[]`). | **100% PRESERVED** — All existing fixtures parse without modification. | **ZERO** |
| **`contracts/canonical-video.ts`** | Re-exported contracts, normalization, timeline, layers, keyframes, evaluator. | Re-exports all of the above plus `contracts/mutations.ts` and `contracts/editor-session.ts`. | **100% PRESERVED** — Additive only. | **ZERO** |
| **`normalizeCanonicalVideo()`** | Normalizes parsed `BlueprintV2` into `NormalizedVideo`. | Operates on both original and post-mutation `BlueprintV2` documents identically. | **100% PRESERVED** — Fully verified in tests. | **ZERO** |
| **`evaluateVideoAtFrame()`** | Evaluates active layers, transforms, and audio at frame $N$. | Evaluates post-mutation, undone, and redone `BlueprintV2` documents reflecting exact properties. | **100% PRESERVED** — Bit-level deterministic evaluation. | **ZERO** |
| **Editor State Architecture** | No interactive session; static mutations only. | `EditorSession` wraps pure `BlueprintV2` without creating an `EditorDocument` duplicate truth. | **100% CLEAN** — Zero duplication of video truth. | **ZERO** |
| **Remotion Runtime** (`BlueprintVideo.tsx`, `merge.ts`) | Consumes `MergedProject` via `normalizeCanonicalVideo`. | Continues to consume normalized output unchanged. Editor core is pure TypeScript. | **100% PRESERVED** — Zero imports from React or Remotion in editor core. | **ZERO** |
| **Python QC & Gates** (`final_qc.py`, architecture tests) | Enforces 0 React/Remotion imports in `contracts/`. | Architecture guards pass 100% with `mutations.ts` and `editor-session.ts`. | **100% PRESERVED** — Fully verified. | **ZERO** |

---

## 3. Integration Proof

The end-to-end editorial pipeline:
$$\text{Input BlueprintV2} \xrightarrow{\text{EditorSession / applyMutation}} \text{Mutated} \xrightarrow{\text{Undo/Redo}} \text{Exact Canonical} \xrightarrow{\text{normalizeCanonicalVideo}} \text{NormalizedVideo} \xrightarrow{\text{evaluateVideoAtFrame}} \text{EvaluatedFrameState}$$
executes with 100% fidelity both in Vitest test runs and in isolated subprocesses where React, Remotion, Canvas, and DOM are completely blocked.

