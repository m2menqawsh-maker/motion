# Remotion Lock-In Scorecard: Subsystem Vulnerability Audit

**Status**: Verified Reality Assessment  
**Milestone**: S28-R01  
**Audited SHA**: `69b8798b2e2296bc5a24af411ac44133c072a029`  

---

## 1. Executive Scorecard Summary

This scorecard rates the level of **lock-in** (coupling to Remotion, React, and TSX runtime semantics) across all 14 major system dimensions.

```text
CRITICAL LOCK-IN :  3 Subsystems (Templates, Animations, CREATE Flow)
HIGH LOCK-IN     :  4 Subsystems (Preview, Editor Model, Render Execution, Probe)
MEDIUM LOCK-IN   :  3 Subsystems (Canonical Contracts, Asset Storage, Tests)
LOW LOCK-IN      :  1 Subsystem  (API)
ZERO LOCK-IN     :  3 Subsystems (AI Authoring, Final QC, Workers)
```

---

## 2. Dimension Breakdown Matrix

| Subsystem Dimension | Lock-In Score | Rationale & Code Evidence | Decoupling Difficulty |
| :--- | :---: | :--- | :---: |
| **1. Canonical Contracts** | `MEDIUM` | `contracts/blueprint.ts` and `contracts/animations.ts` leak imports to Remotion/React via `registry/effects-runtime` and `interpolate/spring`. However, `BlueprintV2` data schema itself is mostly engine-neutral. | **LOW** (Clean imports, replace math) |
| **2. Templates** | `CRITICAL` | All 105 templates are implemented as React TSX components importing Remotion hooks (`useCurrentFrame`, `useVideoConfig`, `AbsoluteFill`). `registry/template-registry.tsx` crashes fail-closed if any TSX component is missing. | **HIGH** (Requires Template abstraction) |
| **3. Animations** | `CRITICAL` | 100% of complex scene motion is hardcoded procedural TypeScript (`interpolate(frame, ...)`). Zero declarative keyframe/curve format exists. Impossible to inspect or render outside Remotion runtime today. | **HIGH** (Requires portable animation model) |
| **4. Preview Model** | `HIGH` | Only preview available is `remotion studio` running a full Webpack dev server on port 3000. It requires building `render_props.json` and passing mechanical `.studio_unlocked` checks. | **MEDIUM** (Build client preview canvas) |
| **5. Editor Model** | `HIGH` | Currently `NOT_IMPLEMENTED`. The existing system has no live editing capability; all edits require rewriting JSON files on disk and re-triggering the pipeline. | **HIGH** (Primary goal of S28-R) |
| **6. Render Execution** | `HIGH` | `scripts/render_project.py` directly executes `npx remotion render`. Docker container `clean-video-builder` is tailored specifically for Node/Remotion Chrome rendering. | **MEDIUM** (Introduce `RendererAdapter`) |
| **7. Public / Product API** | `LOW` | REST API (`api/`) exposes durable Run records, Blueprint mutations, and lifecycle gates. Only minor leakage exists in `health_service.py` (`_probe_remotion`). | **LOW** (Minor cleanup) |
| **8. AI Authoring** | `NONE` | `CreativePlanner` and `BlueprintCompiler` operate completely on high-level creative concepts (`CreativePlan`, `NarrativeBeat`, `SceneIntent`) and compile to canonical JSON without touching Remotion. | **NONE** (Already decoupled) |
| **9. CREATE Flow** | `CRITICAL` | When creating new templates, AI generates React TSX. Candidate validation runner (`candidate_runtime_runner.py`) synthesizes `CandidateHarness.tsx` importing `registerRoot` from Remotion. | **HIGH** (Multi-target compiler needed) |
| **10. Probe Gates** | `HIGH` | `scripts/gates/probe_qc.py` invokes `npx remotion still` to capture frames and build the contact sheet. Probe qualification depends on Remotion CLI availability. | **MEDIUM** (Wrap `render_still`) |
| **11. Final QC** | `NONE` | `scripts/gates/final_qc.py` inspects the produced MP4 container via `ffprobe` and `ffmpeg.probe`. Zero Remotion dependencies exist. Pure engine-neutral artifact testing. | **NONE** (Already decoupled) |
| **12. Asset Storage** | `MEDIUM` | Assets must be physically copied into `remotion-app/public/` so Remotion's `staticFile()` can locate them. StorageService itself is neutral, but materializer is coupled. | **LOW** (Decouple staging path) |
| **13. Workers & Queuing** | `NONE` | `scripts/core/worker.py` manages leases, atomic CAS claims, and executes the pipeline as an isolated subprocess. Completely engine-agnostic. | **NONE** (Already decoupled) |
| **14. Tests** | `MEDIUM` | Vitest suites (`tests/remotion/`) mock Remotion or test Remotion component mounting via `@testing-library/react`. Zero non-Remotion execution fixtures exist today. | **MEDIUM** (Add engine-neutral fixtures) |

---

## 3. Lock-In Risk Assessment for S28-R Roadmap

- **The Easy Decoupling (R02 - R03)**:
  Purifying `contracts/` and moving `merge.ts` out of `remotion-app` can be accomplished rapidly with near-zero risk, eliminating the top-level contract leaks immediately.
- **The Moderate Decoupling (R06 - R09)**:
  Wrapping `render_project.py` and `probe_qc.py` behind a unified `VideoRenderer` interface, and decoupling asset materialization from `remotion-app/public`.
- **The Complex Decoupling (R04, R11 - R13)**:
  Decoupling the 105 Template implementations from React component identity, and building the Live Editor Preview Canvas. Because existing template motion is hardcoded TypeScript, Remotion must be preserved as the first `RemotionRendererAdapter` to maintain 100% visual parity while the new engine-neutral video document is introduced.
