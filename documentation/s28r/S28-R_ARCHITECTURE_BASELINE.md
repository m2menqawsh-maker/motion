# S28-R Architecture Baseline: Reality Audit & Remotion Coupling

**Status**: Verified Reality Audit Baseline  
**Scope**: S28-R01  
**Repository Branch**: `feature/s27-ai-platform`  
**Git Commit SHA**: `69b8798b2e2296bc5a24af411ac44133c072a029`  
**Working Tree**: Active feature development with untracked/unstaged S28-M modernization files  
**Auditor**: Antigravity S28-R Reality Auditor  
**Date**: October 2026  

---

## 1. Executive Summary & Audit Mandate

The overarching goal of the **S28-R** track (*Renderer Independence & Live Editor Core*) is to transform the `motion / clean-video-workspace` repository into an engine-neutral video platform where:
```text
Remotion ≠ System Core
Remotion = One Replaceable Rendering Implementation
```

This document establishes the authoritative **Reality Baseline** for S28-R. In accordance with S28-R01 rules:
- **Audit Only**: No code migration, no deletions, no rewrites, and no premature renderer abstractions have been created in this milestone.
- **Code Over Documentation**: Where architectural documentation drifts from actual source code, the physical source code is taken as authoritative ground truth.
- **Zero Breakage**: The existing Remotion runtime (`remotion-app/`) remains 100% operational throughout this audit.

---

## 2. Environment & Toolchain Baseline

The actual runtime environment hosting this repository has been inspected and confirmed as follows:

| Toolchain / Runtime | Version Verified | Role / Scope |
| :--- | :--- | :--- |
| **Operating System** | Linux (Kernel 6.x, x86_64) | Development and containerized execution host |
| **Python** | `3.14.7` | Pipeline orchestration, gates, AI planning, API, workers |
| **Node.js** | `v26.7.0` | Remotion CLI, studio, bundler, vitest test runner |
| **npm** | `11.19.0` | Package manager for root and remotion-app |
| **uv** | `0.12.17` | High-performance Python package management & runner |
| **FFmpeg** | `8.1.3` | Video decoding, stream probing, audio normalization, QC |
| **FFprobe** | `8.1.3` | Structural video inspection, stream analysis, AV sync QC |
| **Docker** | `5.8.7` | Containerized headless rendering (`clean-video-builder`) |

---

## 3. High-Level Architectural Reality: Core vs Implementation

The current repository already exhibits strong separation of concerns across multiple layers, but suffers from acute **leaks and coupling points** where Remotion assumptions have crossed architectural boundaries into contracts, assets, and validation gates.

```mermaid
flowchart TD
    subgraph Creative_AI_Core ["Creative & AI Intelligence (100% Engine Neutral)"]
        CP[CreativePlanner] --> NC[Narrative & Taste]
        NC --> BC[BlueprintCompiler]
    end

    subgraph Canonical_Contracts ["Contracts & Domain Layer (Leaked Coupling)"]
        BC --> BP[05_blueprint.json / BlueprintV2]
        BP -.->|LEAK: imports EFFECTS_RUNTIME| ER[registry/effects-runtime.ts]
        BP -.->|LEAK: imports remotion spring/interpolate| AN[contracts/animations.ts]
        BP --> RI[contracts/render-input.ts]
        RI -.->|LEAK: imports SceneOverride| MP[remotion-app/src/merge.ts]
    end

    subgraph Asset_Pipeline ["Asset Pipeline (Materializer Coupling)"]
        MAT[scripts/core/materializer.py] -->|COUPLED: writes to| PUB[remotion-app/public/projects/...]
        PUB --> SF[Remotion staticFile()]
    end

    subgraph Preview_And_QC ["Preview, Probes & Quality Gates"]
        RI --> PRB[gates/probe_qc.py]
        PRB -->|COUPLED: calls| REM_STILL[remotion still CLI]
        REM_STILL --> CS[contact_sheet.png]
        RI --> STU[scripts/open_studio.py]
        STU -->|COUPLED: runs| REM_STUDIO[remotion studio CLI]
    end

    subgraph Render_Execution ["Render Execution (Local / Docker)"]
        CS -->|Human Approval Gate| RP[scripts/render_project.py]
        RP -->|Executes| REM_RENDER[remotion render CLI]
        REM_RENDER --> OUT[out.mp4]
    end

    subgraph Final_QC_And_Storage ["Post-Render QC & Storage (100% Engine Neutral)"]
        OUT --> FQC[gates/final_qc.py via ffprobe]
        FQC --> WRK[worker.py / StorageService]
    end

    classDef neutral fill:#1b4d3e,stroke:#2ecc71,stroke-width:2px,color:#fff;
    classDef leaked fill:#8b5a00,stroke:#f39c12,stroke-width:2px,color:#fff;
    classDef coupled fill:#78281f,stroke:#e74c3c,stroke-width:2px,color:#fff;

    class CP,NC,BC,FQC,WRK neutral;
    class BP,AN,RI leaked;
    class MAT,PUB,SF,PRB,REM_STILL,STU,REM_STUDIO,RP,REM_RENDER coupled;
```

### 3.1 What is Genuine Domain/Core Concept?
1. **Canonical Blueprint (`BlueprintV2`)**: Video metadata (`fps`, `aspect_ratio`, `project_id`), scene sequence (`startFrame`, `durationFrames`), scene content (`lines`, `words` with millisecond timings, logical media asset references), style surface descriptions, and audio track plans.
2. **Deterministic Compiler (`BlueprintCompiler`)**: Translates high-level creative proposals (`CreativePlan`) into validatable, reproducible timeline contracts.
3. **Asset Manifest & Resolver (`ManifestV2`, `asset-resolver.ts`)**: Content-addressed asset metadata, kind checking, and logical ID mapping.
4. **Final QC Engine (`final_qc.py`)**: Pure artifact validation via `ffprobe` verifying duration, dimensions, framerate, freeze frames, and AV sync on the output container.
5. **Worker Daemon & Storage Service (`worker.py`, `storage_service.py`)**: Asynchronous job leasing, CAS state locking, idempotency control, and S3-compatible cloud object persistence.

### 3.2 What is Merely Remotion Implementation Detail?
1. **React TSX Template Components**: The 105 implementations under `templates/` and `remotion-app/src/compositions/` that call `useCurrentFrame()`, `useVideoConfig()`, and `AbsoluteFill`.
2. **Remotion Webpack Public Folder Requirement**: The convention where Python scripts must stage media into `remotion-app/public/` so that `staticFile()` can locate assets.
3. **Transition Overlap Behavior**: The `TransitionSeries` semantics where transitions reduce overall timeline duration rather than executing as explicit scene-level timing offsets.
4. **Probe Still Rendering via CLI**: Calling `npx remotion still` to generate probe frames and contact sheets.
5. **Remotion Studio Web Server**: Running `npx remotion studio` on port 3000 to preview the project.
6. **Mechanical `.studio_unlocked` Webpack Guard**: Code embedded in `remotion-app/remotion.config.ts` enforcing probe-qc passes before Remotion Webpack compiles.

---

## 4. Key Architectural Findings & Deficiencies

### Finding 1: Upstream Contract Leaks to React / Remotion
- `contracts/blueprint.ts` lines 8 & 180 import `isExecutableEffect` and `EFFECTS_RUNTIME` from `registry/effects-runtime.ts`.
- `registry/effects-runtime.ts` imports `EFFECT_COMPONENTS` from `templates/effects/engine-bridge.tsx`.
- `templates/effects/engine-bridge.tsx` imports concrete React components from `remotion-app/src/engine/`.
- **Result**: Importing the Zod schema for Blueprint (`contracts/blueprint.ts`) transitively loads React, JSX, and Remotion engine components into any Node/TS runtime.

### Finding 2: Direct Remotion Imports in Contracts
- `contracts/animations.ts` line 6 explicitly imports `{ interpolate, spring } from "remotion"`.
- `ANIMATION_REGISTRY` contains runtime functions that execute Remotion's `interpolate` and `spring` at the contracts level.

### Finding 3: Template Registry Dual Identity
- `registry/template-registry-data.json` holds semantic metadata (canonical ID, category, schema, defaults, default duration).
- `registry/template-registry.tsx` binds this metadata directly to `COMPONENT_BINDINGS[t.component_name]`.
- Line 237 of `registry/template-registry.tsx` throws: `Error: Template component binding missing for '<canonical_id>'`.
- **Result**: A template cannot exist in the registry without an existing, compiled React TSX implementation.

### Finding 4: Asset Staging Tied to Remotion Public Folder
- Remotion's `staticFile()` utility resolves assets relative to `remotion-app/public`.
- Consequently, `scripts/core/materializer.py` stages project assets into `remotion-app/public/projects/<project_id>/generations/<gen_id>/` and writes relative paths into `media_map.json`.
- `remotion-app/remotion.config.ts` documents this as an immutable rule: `Python tools generating assets for Remotion MUST output them to remotion-app/public/ so staticFile() works natively.`

### Finding 5: Timing Model Discrepancy (TransitionSeries Overlap)
- Blueprint V2, `merge.ts`, `probe_planner.py`, and `final_qc.py` calculate total video duration as:
  $$\text{Total Duration} = \max(\text{startFrame} + \text{durationFrames})$$
- However, `remotion-app/src/BlueprintVideo.tsx` wraps scenes in `<TransitionSeries>`.
- In Remotion `TransitionSeries`, each transition overlaps the preceding and subsequent scenes by `transition.durationFrames`.
- This creates an inherent timeline authority drift between Blueprint declarative timings and actual Remotion frame playback.

### Finding 6: Template Candidate CREATE Flow Hardcoded to Remotion
- When generating candidate templates, `scripts/validators/candidate_runtime_runner.py` writes a temporary `CandidateHarness.tsx` using `Composition` and `registerRoot` from `remotion`.
- It executes `npx remotion still CandidateHarness ...` to evaluate whether the candidate passes static and smoke gates.
- Candidate validity is thus equated with Remotion mountability.

---

## 5. Architectural Drift Log (Code vs Existing Documentation)

| Documented Architecture | Current Code Reality | Impact / Drift Severity |
| :--- | :--- | :--- |
| **"Pure Engine-Neutral Contracts"** (`contracts/`) | `contracts/blueprint.ts` and `contracts/animations.ts` import React & Remotion | **CRITICAL**: Leaks engine dependencies into contract definitions |
| **"Semantic Template Catalog"** (`ground-truth/`) | Registry requires concrete TSX `COMPONENT_BINDINGS` or crashes fail-closed | **HIGH**: Template identity is coupled to React component existence |
| **"Canonical Timeline Duration"** | `merge.ts` uses $\max(\text{start} + \text{dur})$; Remotion `TransitionSeries` shortens timeline | **HIGH**: Potential freeze/black frame pad or AV-sync mismatch in QC |
| **"SplitScreenWrapper" Parity** | `templates/scenes/SplitScreenWrapper.tsx` has `DEFAULT_PANEL`; `remotion-app/.../SplitScreenWrapper.tsx` lacks it | **MEDIUM**: File divergence between root `templates/` and `remotion-app/src/templates/` |
| **"Independent Asset Storage"** | Assets must physically be copied into `remotion-app/public/` for rendering | **HIGH**: Tight coupling between storage layout and Remotion Webpack dev server |

---

## 6. Audit Conclusion & Baseline Sign-Off

The repository contains an advanced, robust, and highly resilient domain architecture:
- Deterministic AI compilers, strict schema gates, cryptographic evidence seals, durable state machines, and thorough QC analyzers.
- However, Remotion is currently entangled across 4 critical junctures: **Contract Imports**, **Template Registry Component Bindings**, **Asset Public Folder Staging**, and **Probe Frame Rendering**.

S28-R01 establishes this verified baseline so that subsequent phases (S28-R02 through S28-R15) can systematically isolate Remotion behind a clean `RemotionRendererAdapter` without destabilizing current production workflows.
