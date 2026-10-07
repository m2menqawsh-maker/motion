# Timebase, Range Invariants & Canonical Duration Semantics

**Status**: Formally Adopted Architecture Standard  
**Milestone**: S28-R03  
**Parent Initiative**: S28-R — Renderer Independence & Live Editor Core  
**Governing Module**: `contracts/timeline.ts`  
**Date**: 2026-10-06  

---

## 1. Executive Summary

A major finding of S28-R01 was the subtle divergence between Blueprint nominal scene durations and Remotion's runtime `TransitionSeries` duration when overlapping transitions exist (CPL-015).

Milestone **S28-R03** establishes:
1. Pure timebase primitives and mathematical rounding policies.
2. Explicit $[startFrame, endFrame)$ half-open interval semantics.
3. Declarative transition overlap semantics (`overlap` vs `insert`).
4. A single pure function (`calculateCanonicalDuration`) serving as the universal duration authority.

---

## 2. Canonical Time Primitives & Interval Semantics

All temporal entities adhere to the following invariants:

1. **`FrameNumber`**: Integer $\ge 0$.
2. **`FrameDuration`**: Integer $\ge 1$.
3. **`TimeRange`**: Half-open interval $[startFrame, endFrame)$:
   - `startFrame` is **inclusive** (element is active at `startFrame`).
   - `endFrame` is **exclusive** (element is inactive at `endFrame`).
   - **Invariant**: $endFrame = startFrame + durationFrames$.

---

## 3. Timebase Conversion & Rounding Policies

Conversions between discrete frames and continuous physical time are governed by pure mathematical functions accepting explicit `RoundingPolicy`:

| Policy | Behavior | Formula |
| :--- | :--- | :--- |
| `ROUND` (Default) | Standard nearest-integer rounding | $\operatorname{round}\left(\frac{\text{frame} \times 1000}{\text{fps}}\right)$ |
| `FLOOR` | Conservative downward rounding | $\lfloor \frac{\text{frame} \times 1000}{\text{fps}} \rfloor$ |
| `CEIL` | Conservative upward rounding | $\lceil \frac{\text{frame} \times 1000}{\text{fps}} \rceil$ |
| `EXACT_WHERE_POSSIBLE` | Floating-point exact representation | $\frac{\text{frame} \times 1000}{\text{fps}}$ |

### Supported Frame Rates
Standard video project frame rates: `24`, `25`, `30`, `60` fps. Fractional frame rates (such as 29.97 or 59.94) are intentionally excluded from the default schema to prevent floating-point frame drift in headless pipelines.

---

## 4. Transition Overlap Semantics & Project Duration Calculation

Transitions between scenes support explicit semantic modes:
- **`overlap` (Default)**: Adjacent scenes overlap temporally during the transition window. The outgoing scene fades/slides out while the incoming scene simultaneously animates in.
  $$\text{Total Duration} = \sum_{i=1}^N \text{scene}_i.\text{durationFrames} - \sum_{j=1}^{N-1} \text{transition}_j.\text{durationFrames}$$
- **`insert`**: The transition acts as an independent bridge node inserted between the two scenes.
  $$\text{Total Duration} = \sum_{i=1}^N \text{scene}_i.\text{durationFrames} + \sum_{j=1}^{N-1} \text{transition}_j.\text{durationFrames}$$

### Universal Duration Function: `calculateCanonicalDuration()`
Located in `contracts/timeline.ts`, this pure function accepts the scenes and transition list, returning the exact authoritative duration in frames for the entire video.
