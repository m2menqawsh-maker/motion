# S28-R02 Milestone Report: Canonical Editable Video Contract & Core Normalizer Extraction

**Milestone**: S28-R02  
**Parent Initiative**: S28-R — Renderer Independence & Live Editor Core  
**Git Baseline Audited SHA**: `69b8798b2e2296bc5a24af411ac44133c072a029`  
**Execution Date**: 2026-10-06  
**Final Status**: **PASS (100% Verified)**  

---

## 1. Executive Summary

Milestone **S28-R02** successfully transformed the video contract from an engine-coupled specification into a **pure data contract and normalizer**, completely free of React, Remotion, and runtime UI dependencies. 

Prior to S28-R02, importing video contracts or validating video inputs transitively dragged React, Remotion, and all 105 TSX template component wrappers into memory. S28-R02 eliminates this inversion while maintaining **ONE SINGLE CANONICAL VIDEO AUTHORITY** (`BlueprintV2` evolved and purified), preserving 100% backwards compatibility for the existing Remotion rendering pipeline, and enforcing strict fail-closed validation.

### Key Milestones Achieved:
1. **Single Canonical Authority**: Unified all video project parsing, validation, and normalization under `contracts/canonical-video.ts` and `contracts/blueprint.ts`. No conflicting secondary persistent document was created.
2. **Zero Framework Pollution**: Eradicated all React and Remotion imports from the contracts layer (`contracts/*.ts`), dropping framework dependencies in contracts to exactly **0**.
3. **Core Normalizer Extracted**: Separated pure domain normalization (`contracts/normalization.ts`) from engine preparation (`remotion-app/src/merge.ts`).
4. **Decoupled Semantic Registries**: Created pure machine-readable template registry (`registry/semantic-registry.ts`) and semantic effects catalog (`contracts/effects.ts`), eliminating the need to compile 105 TSX templates during validation.
5. **Runtime Compatibility Preserved**: Existing Remotion consumers (`parseRenderInput`, `mergeProject`, `Root.tsx`, `render_project.py`, `probe_qc.py`, `final_qc.py`) execute without breaking changes.
6. **Automated Architecture Guards**: Added dual TypeScript Vitest and Python Pytest guard suites (including an isolated subprocess execution test) preventing regressions.

---

## 2. Target vs Actual Assessment

| Architectural Objective | Target Standard | Actual Achieved State | Verdict |
| :--- | :--- | :--- | :--- |
| **Video Authority Model** | Single Canonical Authority (No dual truth) | Evolved `BlueprintV2` via `contracts/canonical-video.ts` | **PASS** |
| **Contracts Framework Coupling** | 0 imports from `react` or `remotion` in `contracts/` | Exactly **0** imports across all `contracts/*.ts` files | **PASS** |
| **Core Normalizer** | Pure domain normalizer outside `remotion-app` | Extracted to `contracts/normalization.ts` | **PASS** |
| **Animation Contract** | Pure declarative specs without Remotion math | `contracts/animations.ts` purified; math in `remotion-app/src/animations.ts` | **PASS** |
| **Effects Contract** | Semantic catalog separated from TSX bridge | 45 semantic effects in `contracts/effects.ts`; TSX bridge in `registry/effects-runtime.ts` | **PASS** |
| **Render Input Gate** | `parseRenderInput` behavior strictly preserved | 100% pass across all existing conformance & parity tests | **PASS** |
| **Validation Strictness** | Fail-closed validation; no weakened rules | Unknown effects, aspect ratios, and scenes fail-closed | **PASS** |
| **Subprocess Isolation** | Parser & normalizer execute with React/Remotion blocked | Verified via Node subprocess test (`AG-05`) | **PASS** |

---

## 3. Detailed Architectural Remediation

### 3.1 Eliminating the Effects Transitive Leak (CPL-002 & CPL-021)
- **Problem**: `contracts/blueprint.ts` imported `registry/effects-runtime.ts` to validate effects. `effects-runtime.ts` imported `engine-bridge.tsx`, which imported Remotion and React UI components.
- **Solution**:
  - Created `contracts/effects.ts` containing the complete 45-effect catalog as pure metadata (`SemanticEffectDefinition`).
  - Added pure `EffectRefSchema`, `isKnownEffect()`, and `isExecutableEffect()`.
  - Refactored `registry/effects-runtime.ts` to consume `contracts/effects.ts` and attach concrete React component bindings.

### 3.2 Purifying Animations from Remotion (CPL-001)
- **Problem**: `contracts/animations.ts` imported `interpolate` and `spring` directly from `remotion`.
- **Solution**:
  - Purified `contracts/animations.ts` to declare 13 named `AnimationSpec` definitions, easing enums, and pure TypeScript types (`AnimationContext`, `AnimationResult`).
  - Created `remotion-app/src/animations.ts` containing the runtime execution logic (`applyAnimation`, Remotion `interpolate`, and Remotion `spring`).

### 3.3 Relocating `SceneOverride` (CPL-003)
- **Problem**: `contracts/render-input.ts` imported `SceneOverride` from `remotion-app/src/merge.ts`, inverting dependency direction.
- **Solution**:
  - Defined canonical `SceneOverrideSchema` and `OverridesSchema` directly inside `contracts/blueprint.ts`.
  - Re-exported them with explicit TypeScript types from `contracts/index.ts`.
  - `contracts/render-input.ts` and `remotion-app/src/merge.ts` now import `SceneOverride` from `contracts/blueprint.ts`.

### 3.4 Decoupling from 105 TSX Templates (CPL-004)
- **Problem**: `contracts/render-input.ts` imported `getRegistryEntry` from `registry/template-registry.tsx`, forcing Node and Vitest to transpile 105 TSX template files during every contract check. This frequently caused test runner timeouts (>5,000ms).
- **Solution**:
  - Created `registry/semantic-registry.ts` which loads directly from `registry/template-registry-data.json` with zero React or TSX imports.
  - `contracts/render-input.ts` now calls `getSemanticTemplateEntry()` for fail-closed template verification.
  - **Performance Impact**: Contract test execution dropped from >5,000ms (timeout) to **238ms** (a 20x speedup).

### 3.5 Extracting the Core Normalizer (CPL-008)
- **Problem**: Project normalization (`mergeProject`, `resolveTokensDeep`, `normalizeScene`) was trapped inside `remotion-app/src/merge.ts`.
- **Solution**:
  - Created `contracts/normalization.ts` as a pure, deterministic, framework-agnostic normalizer.
  - Converted `remotion-app/src/merge.ts` into a thin compatibility adapter that imports and delegates to `contracts/normalization.ts`.

### 3.6 Resolving Hidden Framework Leaks
- **`contracts/brand.ts`**: Removed React `createContext` and `BrandProvider`. Moved React context to `remotion-app/src/BrandContext.tsx`.
- **`contracts/positions.ts`**: Replaced React `CSSProperties` with pure `PositionStyle = Record<string, string | number>`.
- **`contracts/fonts.ts`**: Removed 9 `@remotion/google-fonts/*` package imports; moved loader to `remotion-app/src/fonts.ts`.
- **`registry/types.ts`**: Removed `import type { ComponentType } from "react"`.

---

## 4. Test Verification & Conformance Evidence

### 4.1 Vitest S28-R02 Suite
```text
✓ tests/remotion/s28_r02_red_tests.test.ts (7 tests) [238ms]
    ✓ RED-01: contracts/blueprint.ts has ZERO imports from remotion or react
    ✓ RED-02: contracts/animations.ts has ZERO imports from remotion
    ✓ RED-03: contracts/render-input.ts does not import from remotion-app/src/merge
    ✓ RED-04: contracts/render-input.ts does not import from registry/template-registry.tsx
    ✓ RED-05: contracts/normalization.ts exists and provides pure normalizeCanonicalVideo
    ✓ RED-06: remotion-app/src/merge.ts delegates to pure contracts/normalization.ts
    ✓ RED-07: parseRenderInput() continues to pass all valid inputs fail-closed

✓ tests/architecture/test_s28_r02_architecture_guards.test.ts (5 tests) [2484ms]
    ✓ AG-01: Zero Remotion/React imports in contracts layer
    ✓ AG-02: Zero upward imports from contracts to remotion-app
    ✓ AG-03: Pure Semantic Effects Catalog integrity (45 effects)
    ✓ AG-04: Pure Semantic Template Registry integrity (105 templates)
    ✓ AG-05: Isolated process verification with React/Remotion blocked

✓ tests/remotion/s28_r02_canonical_parity.test.ts (11 tests) [28ms]
    ✓ Deterministic normalization across all 8 canonical fixtures
    ✓ Idempotency invariant verified
    ✓ Frame/millisecond mathematical precision verified

✓ tests/remotion/s28_06_render_smoke.test.ts (6 tests) [158ms]
    ✓ Full Remotion render smoke tests pass
```

### 4.2 Vitest Full Test Suite
```text
Test Files  13 passed (13)
Tests       153 passed (153)
Duration    6.59s
```

### 4.3 Python Test Suite
```text
tests/architecture/test_s28_r02_architecture_guards.py .... [4/4 passed]
tests/core/test_s17_render_input.py ...........             [11/11 passed]
============================== 15 passed in 2.96s ==============================
```

---

## 5. Subprocess Isolation Proof (AG-05)

To decisively prove that the canonical contract and normalizer can execute in an environment where React and Remotion do not exist, test `AG-05` launches a dedicated Node child process executing the following script:

```typescript
// Monkey-patch module loader to throw on react or remotion
const Module = require('module');
const origRequire = Module.prototype.require;
Module.prototype.require = function(path) {
  if (path.includes('react') || path.includes('remotion')) {
    throw new Error('FORBIDDEN_FRAMEWORK_LOAD: ' + path);
  }
  return origRequire.apply(this, arguments);
};

// Import and execute canonical video parser and normalizer
const { parseCanonicalVideo } = require('./contracts/canonical-video');
const { normalizeCanonicalVideo } = require('./contracts/normalization');

const parsed = parseCanonicalVideo(fixture);
const normalized = normalizeCanonicalVideo(parsed);
assert(normalized.scenes.length === 2);
```

**Result**: Process exited with code `0`. Total execution time: 2.4s.

---

## 6. Inventory of Modified and Created Artifacts

### Files Created:
1. `contracts/effects.ts`: Semantic effect definitions, schemas, and catalog.
2. `contracts/normalization.ts`: Pure domain normalizer, token resolver, timing calculators.
3. `contracts/canonical-video.ts`: Canonical video parsing and normalization API.
4. `contracts/index.ts`: Unified contracts entrypoint.
5. `registry/semantic-registry.ts`: Pure JSON-based template registry.
6. `remotion-app/src/animations.ts`: Runtime animation execution adapter.
7. `remotion-app/src/BrandContext.tsx`: Runtime React Brand context provider.
8. `remotion-app/src/fonts.ts`: Runtime Remotion Google Fonts loader.
9. `tests/fixtures/canonical/*`: 8 canonical video test fixtures.
10. `tests/remotion/s28_r02_red_tests.test.ts`: Vitest RED test suite.
11. `tests/remotion/s28_r02_canonical_parity.test.ts`: Parity and deterministic invariants test suite.
12. `tests/architecture/test_s28_r02_architecture_guards.test.ts`: TypeScript architecture guard suite.
13. `tests/architecture/test_s28_r02_architecture_guards.py`: Python architecture guard suite.
14. `documentation/s28r/CANONICAL_VIDEO_CONTRACT.md`: Architecture specification.
15. `documentation/s28r/CANONICAL_NORMALIZATION.md`: Architecture specification.
16. `documentation/s28r/CONTRACT_DEPENDENCY_RULES.md`: Architecture specification.
17. `documentation/s28r/R02_MIGRATION_MAP.md`: Coupling tracking map.
18. `documentation/s28r/evidence/S28-R02_REPORT.md`: This milestone closure report.

### Files Refactored:
1. `contracts/animations.ts`: Eradicated Remotion imports; purified to declarative specs.
2. `contracts/blueprint.ts`: Removed `registry/effects-runtime.ts` leak; imported pure `contracts/effects.ts`.
3. `contracts/brand.ts`: Removed React context; preserved pure token resolution.
4. `contracts/positions.ts`: Removed React `CSSProperties`; replaced with `PositionStyle`.
5. `contracts/fonts.ts`: Removed 9 `@remotion/google-fonts/*` package imports.
6. `contracts/render-input.ts`: Decoupled from `template-registry.tsx` and `remotion-app/src/merge.ts`.
7. `contracts/template-schemas.ts`: Inlined schema types; decoupled from `registry/types.ts`.
8. `registry/types.ts`: Removed React `ComponentType` import.
9. `registry/effects-runtime.ts`: Converted to consumer of `contracts/effects.ts`.
10. `remotion-app/src/merge.ts`: Converted to thin compatibility wrapper over `contracts/normalization.ts`.

---

## 7. Recommendations & Handoff for S28-R03

Milestone **S28-R03** will introduce:
- Pure Timeline, Tracks, Clips, and Layers abstraction models.
- Keyframes and interpolation mathematical engines.
- Mutation and undo/redo architecture foundation.

### Directives for R03:
- Build strictly upon `contracts/canonical-video.ts` and `contracts/normalization.ts`.
- Maintain the zero-framework invariant established in `CONTRACT_DEPENDENCY_RULES.md`.
- Keep the timeline model engine-agnostic so that both Remotion and future canvas/WebCodecs engines can consume it.
