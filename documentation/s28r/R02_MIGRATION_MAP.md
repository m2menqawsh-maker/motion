# Remotion Coupling Migration Map (S28-R02 Baseline Update)

**Status**: Verified Migration Tracking  
**Milestone**: S28-R02  
**Parent Initiative**: S28-R — Renderer Independence & Live Editor Core  
**Audited Baseline SHA**: `69b8798b2e2296bc5a24af411ac44133c072a029`  
**Updated Date**: 2026-10-06  

---

## 1. Executive Summary

In milestone **S28-R01**, an exhaustive audit of the video platform identified **21 coupling points** between domain contracts, registries, runtime components, and the Remotion framework (5 CRITICAL, 8 HIGH, 6 MEDIUM, 2 LOW).

Milestone **S28-R02** targeted the highest-risk couplings in the contract and normalization layers:
- **Couplings Resolved in R02**: 6 major inventory items (CPL-001, CPL-002, CPL-003, CPL-004 [contract side], CPL-005 [catalog side], CPL-008).
- **Additional Hidden Leaks Discovered & Resolved in R02**: 4 items (`contracts/brand.ts`, `contracts/positions.ts`, `contracts/fonts.ts`, `registry/types.ts`).
- **Remoting Import Reductions**: **100% of React and Remotion imports eradicated from `contracts/`**.
- **All Existing Runtime Consumers Preserved**: 0 breaking changes to `parseRenderInput()`, `Root.tsx`, `render_project.py`, or `final_qc.py`.

---

## 2. Detailed 21-Coupling Status Matrix

| ID | Severity | Category | Description | S28-R01 State | S28-R02 Action & Status | Target Milestone |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **CPL-001** | **CRITICAL** | Contracts | `contracts/animations.ts` imported `interpolate`, `spring` from `remotion` | Direct coupling | **RESOLVED**: Purified into pure declarative specs (`AnimationSpec`). Remotion math moved to `remotion-app/src/animations.ts`. | **R02 (Done)** |
| **CPL-002** | **CRITICAL** | Contracts | `contracts/blueprint.ts` imported `registry/effects-runtime.ts` $\to$ React/Remotion bridge | Transitive leak | **RESOLVED**: Extracted pure `contracts/effects.ts` metadata catalog (45 effects). Schema validates semantically without loading TSX. | **R02 (Done)** |
| **CPL-003** | **MEDIUM** | Contracts | `contracts/render-input.ts` imported `SceneOverride` from `remotion-app/src/merge.ts` | Upward inversion | **RESOLVED**: Moved `SceneOverride` into `contracts/blueprint.ts`. All consumers import from contracts. | **R02 (Done)** |
| **CPL-004** | **CRITICAL** | Registry | `contracts/render-input.ts` imported `registry/template-registry.tsx` (105 TSX templates drag) | Heavy React import | **RESOLVED (Contract Boundary)**: Created `registry/semantic-registry.ts` from JSON data. `render-input.ts` imports zero TSX. Runtime component binding deferred to R04/R05. | **R02 (Boundary) / R04 (Full)** |
| **CPL-005** | **HIGH** | Registry | `registry/effects-runtime.ts` bundled catalog metadata with broken TSX bridge imports | Mixed concern | **PARTIALLY RESOLVED**: Separated pure metadata catalog into `contracts/effects.ts`. `effects-runtime.ts` remains a runtime consumer. Full adapter in R04. | **R02 (Metadata) / R04 (Adapter)** |
| **CPL-006** | **HIGH** | Runtime | `remotion-app/src/BlueprintVideo.tsx` Remotion composition logic | Runtime component | **PRESERVED**: Legitimate Remotion engine implementation. Will be encapsulated behind `RemotionRendererAdapter`. | **R05** |
| **CPL-007** | **HIGH** | Runtime | `remotion-app/src/Root.tsx` Remotion compositions & `calculateMetadata` | Entrypoint | **PRESERVED**: Remotion composition entrypoint. Will delegate metadata to core planner in R05. | **R05** |
| **CPL-008** | **HIGH** | Domain | `remotion-app/src/merge.ts` domain normalization inside Remotion app dir | Misplaced domain logic | **RESOLVED**: Extracted core normalization to `contracts/normalization.ts`. `remotion-app/src/merge.ts` converted into a thin backward-compatible adapter. | **R02 (Done)** |
| **CPL-009** | **MEDIUM** | Build | `remotion-app/remotion.config.ts` Webpack & Chromium flags | Build config | **PRESERVED**: Remotion-specific build config. To be isolated to Remotion renderer package. | **R05** |
| **CPL-010** | **HIGH** | Templates | 105 TSX templates use `@remotion/transitions`, `spring()`, `useCurrentFrame()` | Deep runtime coupling | **PRESERVED (Planned R04)**: Templates will receive an abstraction facade (`useTimelineFrame()`, declarative transitions) in R04. | **R04** |
| **CPL-011** | **MEDIUM** | Scripts | `scripts/render_project.py` invokes `npx remotion render` directly | Dispatcher coupling | **PRESERVED**: CLI runner. Will be migrated to call `RenderPipelineGateway` in R08. | **R08** |
| **CPL-012** | **MEDIUM** | Scripts | `scripts/open_studio.py` launches Remotion Studio UI | Dev tooling | **PRESERVED**: Preview runner. Live Editor core will be introduced in R06. | **R06** |
| **CPL-013** | **MEDIUM** | Scripts | `scripts/gates/probe_qc.py` renders preview stills via Remotion CLI | Headless QC | **PRESERVED**: Preview capture. Will use `RendererAdapter.captureFrame()` in R08. | **R08** |
| **CPL-014** | **LOW** | Docker | `docker/Dockerfile.video-builder` installs Remotion CLI & Chrome | Builder container | **PRESERVED**: Standard builder image. | **R09** |
| **CPL-015** | **MEDIUM** | QC | `scripts/gates/final_qc.py` checks duration against Blueprint vs Remotion transition drift | Authority drift | **MONITORED**: Duration semantics documented in R02. Mathematical alignment planned in R03. | **R03** |
| **CPL-016** | **HIGH** | Audio | Remotion `<Audio>` component handles mixing and ducking at runtime | Engine audio mixing | **PRESERVED**: Declarative audio plan purified in R02; engine-neutral audio export planned in R07. | **R07** |
| **CPL-017** | **HIGH** | Assets | Hardcoded `/projects/{id}/media` filesystem path in render inputs | Path coupling | **NEUTRALIZED IN CONTRACTS**: Canonical contract uses `AssetRef` logical IDs only. Materializer resolves physical files. | **R02 (Contract) / R07 (Engine)** |
| **CPL-018** | **MEDIUM** | Fonts | Google font loaders in runtime | Font engine | **RESOLVED IN CONTRACTS**: Extracted 9 `@remotion/google-fonts/*` packages out of `contracts/fonts.ts` into `remotion-app/src/fonts.ts`. | **R02 (Done)** |
| **CPL-019** | **MEDIUM** | Brand | Brand context and styling resolution | React context coupling | **RESOLVED**: Purified `contracts/brand.ts`. React context moved to `remotion-app/src/BrandContext.tsx`. | **R02 (Done)** |
| **CPL-020** | **LOW** | Layout | Screen coordinate math and positions | CSSProperties import | **RESOLVED**: Replaced React `CSSProperties` with pure `PositionStyle` in `contracts/positions.ts`. | **R02 (Done)** |
| **CPL-021** | **CRITICAL** | Engine | Effects bridge component (`engine-bridge.tsx`) imports Remotion | Direct engine bridge | **ISOLATED**: Bridge is now strictly Layer 4; no contract or schema imports it. Full renderer adapter in R05. | **R02 (Isolated) / R05 (Adapter)** |

---

## 3. Discovered & Remediated Leaks Beyond Initial Inventory

During the execution of S28-R02, comprehensive AST scans revealed four additional subtle coupling points that were not fully cataloged in R01:

1. **`contracts/brand.ts` (React Context Leak)**:
   - *Problem*: Contained `createContext<BrandContextValue | null>(null)` and `BrandProvider`.
   - *Fix*: Purified `contracts/brand.ts` to pure TypeScript data interfaces and token resolution functions. Moved React Context to `remotion-app/src/BrandContext.tsx`.
2. **`contracts/positions.ts` (React Types Leak)**:
   - *Problem*: Imported `CSSProperties` from `react`.
   - *Fix*: Replaced with engine-neutral `PositionStyle = Record<string, string | number>`.
3. **`contracts/fonts.ts` (Remotion Packages Leak)**:
   - *Problem*: Imported 9 font packages from `@remotion/google-fonts/*`.
   - *Fix*: Retained pure typography metadata and RTL helpers in `contracts/fonts.ts`. Moved `@remotion/google-fonts` loader to `remotion-app/src/fonts.ts`.
4. **`registry/types.ts` (React Types Leak)**:
   - *Problem*: Imported `ComponentType` from `react`.
   - *Fix*: Removed `ComponentType` import and typed component bindings neutrally.

---

## 4. Roadmap & Milestone Handoff

```text
S28-R01 [DONE] ──> Reality Audit & Coupling Inventory
                    │
S28-R02 [DONE] ──> Pure Canonical Video Contract & Core Normalizer Extraction
                    │
S28-R03 [NEXT] ──> Timeline, Tracks, Clips, Layers, Keyframes & Animation Model
                    │
S28-R04        ──> Template Contract & Rendering Abstraction
                    │
S28-R05        ──> Remotion Renderer Adapter & Runtime Decoupling
                    │
S28-R06        ──> Live Editor Core & Interaction State Machine
                    │
S28-R07        ──> Audio & Asset Composition Pipeline
                    │
S28-R08        ──> Multi-Engine Render Orchestration & Dispatcher
                    │
S28-R09        ──> Verification, Stress & Cross-Engine Parity
                    │
S28-R10        ──> Final Reality Gate & Production Sign-off
```

### Guidance for S28-R03:
- S28-R03 must build directly on the purified `contracts/canonical-video.ts` and `contracts/normalization.ts`.
- All Timeline, Track, Clip, and Layer abstractions must adhere to the layering rules in `CONTRACT_DEPENDENCY_RULES.md` (zero framework imports in contracts).
- Mathematical animation easing models will expand `contracts/animations.ts` while maintaining runtime execution isolation.
