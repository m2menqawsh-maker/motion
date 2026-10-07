# S28-R03 Compatibility & Migration Map

**Status**: Formally Adopted Architecture Standard  
**Milestone**: S28-R03  
**Parent Initiative**: S28-R — Renderer Independence & Live Editor Core  
**Date**: 2026-10-06  

---

## 1. Executive Summary

Milestone **S28-R03** introduces the canonical timeline, layers, keyframes, and frame evaluation engine without regressing existing rendering consumers (`parseRenderInput`, `mergeProject`, `Root.tsx`, `render_project.py`, `probe_qc.py`, `final_qc.py`).

---

## 2. Compatibility Mapping Matrix

| Legacy / R02 Concept | New Canonical Concept (R03) | Migration / Projection Strategy | Behavior Preserved? | Renderer Dependency? | Target Milestone for Full Adapter |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`BlueprintScene` (Template-only)** | `BlueprintScene` + `layers?: CanonicalLayer[]` | Additive extension. If `layers` is omitted, `contracts/normalization.ts` deterministically synthesizes canonical layers from template defaults & surface. | **100% PRESERVED** | ZERO (Pure contracts) | R04 (Template Abstraction) |
| **`remotion-app/src/animations.ts` (Remotion runtime)** | `contracts/keyframes.ts` (Pure reference math) + `remotion-app/src/animations.ts` | Pure spring & easing engine lives in `contracts/keyframes.ts`. Remotion runtime continues to use `remotion-app/src/animations.ts` with verified numeric parity ($< 10^{-9}$). | **100% PRESERVED** | Remotion isolated to runtime | R05 (Remotion Renderer Adapter) |
| **`TransitionRef` (Implicit overlap)** | `CanonicalTransitionSpec` (`contracts/timeline.ts`) | Additive `overlap_semantics: "overlap" \| "insert"`. Defaults to `"overlap"` preserving existing Remotion `TransitionSeries` duration. | **100% PRESERVED** | ZERO (Pure contracts) | R05 |
| **`AudioPlan` (Authoritative Audio)** | `AudioPlan` + Derived `CanonicalTrack` (kind: "audio") | Single persistent truth retained in `AudioPlan`. Normalization projects voiceover, music, and SFX into timeline audio tracks. | **100% PRESERVED** | ZERO | R07 (Audio Pipeline) |
| **`mergeProject()` (`remotion-app/src/merge.ts`)** | `normalizeCanonicalVideo()` (`contracts/normalization.ts`) | `merge.ts` delegates directly to pure `normalizeCanonicalVideo`. Type aliases `MergedProject` and `MergedScene` preserved. | **100% PRESERVED** | ZERO in contracts; wrapper in remotion-app | R05 |
| **Duration Calculation** | `calculateCanonicalDuration()` (`contracts/timeline.ts`) | Pure duration calculation accounts for overlap vs insert transitions deterministically. | **100% PRESERVED** | ZERO | Production Gate |
