# S28-R05 Milestone Evidence Report: Engine-Neutral TemplateSpec & Migration

**Milestone**: S28-R05  
**Parent Initiative**: S28-R — Renderer Independence & Live Editor Core  
**Git Baseline Audited SHA**: `69b8798b2e2296bc5a24af411ac44133c072a029`  
**Branch**: `feature/s27-ai-platform`  
**Execution Date**: 2026-10-06  
**Final Status**: **PASS (100% Verified)**  

---

## 1. Executive Result

Milestone **S28-R05** has transformed the concept of "Template" from a concrete Remotion/React TSX component implementation into an **engine-neutral, declarative semantic data contract (`TemplateSpec`)**. 

A template is no longer defined by a TSX filename, a React functional component, or a Remotion composition. Instead, a template is a **reusable semantic fragment of the Canonical VideoDocument**, complete with a typed parameter schema, content slots, duration/aspect constraints, capability requirements, and declarative layer synthesis.

Key accomplishments:
1. **Engine-Neutral Specification**: Created `contracts/template-spec.ts` with pure Zod data contracts, containing **zero imports from React, Remotion, Canvas, DOM, or UI libraries**.
2. **Canonical Instantiation Service**: Implemented `contracts/template-instantiator.ts` (`TemplateInstantiator`), enabling direct conversion from `TemplateSpec + inputs + context` into a valid, deterministic Canonical VideoDocument fragment (`BlueprintScene` + `CanonicalLayer[]`).
3. **Single Template Authority Preserved**: Upgraded the authoritative registry (`registry/template-registry-data.json` & `registry/semantic-registry.ts`) to serve both legacy Remotion consumers and new `TemplateSpec` consumers without creating conflicting parallel registries.
4. **Complete 105-Template Inventory & Classification**: Every single canonical template (105 total) has been cataloged and classified into `NATIVE` (29), `HYBRID` (14), `ENGINE_BACKED` (3), or `LEGACY_COMPATIBILITY` (59). Exactly **0 templates remain UNKNOWN**.
5. **Representative End-to-End Migrations**: Migrated 10 representative templates covering simple cards, text-heavy typography, media framing, multi-layer overlays, numeric statistics, full scenes, standard transitions, and bento layouts.
6. **Subprocess Isolation Verified**: Proved that native templates instantiate, normalize, and evaluate in an isolated Node child process where `react`, `react-dom`, `remotion`, and `@remotion/*` are completely blocked at module loader level.
7. **100% Legacy Compatibility**: Preserved all existing Remotion TSX implementations and mappings (`getRegistryEntry()`), keeping the current Remotion production rendering pipeline 100% green.

---

## 2. Repository Baseline

- **Repository Root**: `/home/eng_Momen/Projects/المشروع الحالي/Video maker`
- **Git Branch**: `feature/s27-ai-platform`
- **Git SHA Baseline**: `69b8798b2e2296bc5a24af411ac44133c072a029`
- **Runtime Toolchains**:
  - Node.js: `v26.7.0`
  - npm: `11.19.0`
  - Python: `3.14.7`
  - Vitest: `5.0.0`
  - pytest: `9.1.1`

---

## 3. Preconditions Verification

| Precondition | Evidence Path | Target Standard | Status |
| :--- | :--- | :--- | :--- |
| **S28-R01** | `documentation/s28r/evidence/S28-R01_REPORT.md` | Audit baseline, Remotion coupling inventory | **PASS** |
| **S28-R02** | `documentation/s28r/evidence/S28-R02_REPORT.md` | Canonical Blueprint V2, pure contracts layer, normalization | **PASS** |
| **S28-R03** | `documentation/s28r/evidence/S28-R03_REPORT.md` | Timeline timebase, CanonicalLayer taxonomy, keyframe math, evaluator | **PASS** |
| **S28-R04** | `documentation/s28r/evidence/S28-R04_REPORT.md` | Canonical mutation core, editor session, OCC, bijective undo/redo | **PASS** |

All four prerequisite milestones are verified present, passing, and fully authoritative.

---

## 4. Legacy Template Inventory

An automated reality audit (`documentation/s28r/TEMPLATE_INVENTORY_S28_R05.json`) mapped all 105 templates registered in `registry/template-registry-data.json`:

### By Category/Family:
- **`composition`**: 80 templates (high-level scene layouts and animated structures)
- **`effect`**: 18 templates (transitions)
- **`overlay`**: 3 templates (`particlesystem-element`, `scrollingimages-element`, `staggeredmotion-element`)
- **`text`**: 2 templates (`animatedtext-element`, `typewriter-element`)
- **`ui-block`**: 2 templates (`codeblock-element`, `matrixrain-element`)

### By Implementation & Dependencies:
- **React / TSX wrapper files**: 105 files in `templates/`
- **Direct Remotion imports in wrapper**: 20 files
- **Specialized external libraries**:
  - `maplibre-gl`: 1 (`rui-map-flight`)
  - `remotion-bits`: 8 (`animatedtext-element`, `animatedcounter-element`, `codeblock-element`, `matrixrain-element`, `particlesystem-element`, `scrollingimages-element`, `staggeredmotion-element`, `gradient-element`)
  - 3D Mockup engine: 1 (`scene3d-element`)
  - GL Transitions: 12 transition templates

---

## 5. Migration Classification Breakdown

All 105 templates are classified into formal enums:

```text
┌────────────────────────────────────────────────────────┐
│  TOTAL REGISTERED TEMPLATES: 105                       │
├─────────────────────────┬──────────────┬───────────────┤
│ Classification          │ Count        │ Percentage    │
├─────────────────────────┼──────────────┼───────────────┤
│ NATIVE                  │ 29           │ 27.6%         │
│ HYBRID                  │ 14           │ 13.3%         │
│ ENGINE_BACKED           │ 3            │ 2.9%          │
│ LEGACY_COMPATIBILITY    │ 59           │ 56.2%         │
│ UNKNOWN                 │ 0            │ 0.0%          │
└─────────────────────────┴──────────────┴───────────────┘
```

### Definitions:
1. **`NATIVE` (29 templates)**: Fully expressible using pure R02/R03 canonical primitives (`TextLayer`, `ImageLayer`, `ShapeLayer`, `GroupLayer`, standard transitions, keyframe animation channels). Can be instantiated without Remotion or React loaded in memory.
2. **`ENGINE_BACKED` (3 templates)**:
   - `rui-map-flight`: Requires MapLibre GL map engine & WebGL context.
   - `scene3d-element`: Requires 3D device mockup camera rig & WebGL.
   - `particlesystem-element`: Requires particle physics spawner simulation.
3. **`HYBRID` (14 templates)**:
   - 12 GL Transitions (`book-flip`, `clock-wipe`, `cross-zoom`, `crosswarp`, `dreamy-zoom`, `film-burn`, `iris`, `linear-blur`, `push-cut`, `ripple`, `zoom-blur`, `zoom-in-out`).
   - `matrixrain-element`: Standard text layer + Matrix rain canvas generator.
   - `scrollingimages-element`: Media stack + continuous infinite momentum scroller.
4. **`LEGACY_COMPATIBILITY` (59 templates)**: Complex multi-element scene templates preserved for backward compatibility until R08/R09. All gaps, reasons, and migration owners are machine-documented.

---

## 6. Canonical TemplateSpec Design

Defined in `contracts/template-spec.ts`:

```typescript
export interface TemplateSpec {
  template_id: string; // Lowercase kebab-case canonical ID
  version: string; // Semantic version (e.g., "2.0.0")
  status: "experimental" | "verified" | "production";
  classification: "NATIVE" | "ENGINE_BACKED" | "HYBRID" | "LEGACY_COMPATIBILITY";
  metadata: {
    display_name: { ar: string; en: string };
    description: { ar: string; en: string };
    category: string;
    family?: string;
    tags: string[];
  };
  supported_document_version: string;
  parameters: Record<string, TemplateParameter>;
  slots: Record<string, TemplateSlot>;
  requirements: TemplateRequirements;
  constraints: TemplateConstraints;
  fragment?: TemplateFragment;
  compatibility: TemplateCompatibility;
  provenance: TemplateProvenance;
}
```

### Key Architectural Invariants:
- **Zero Framework Types**: Absolutely no `ReactNode`, `React.ComponentType`, `JSX.Element`, `AbsoluteFill`, `Sequence`, `useCurrentFrame`, `interpolate`, `spring`.
- **Pure Data Contract**: Instantiation logic is strictly decoupled from the specification data.

---

## 7. Files Added & Modified

### Added:
1. `contracts/template-spec.ts`: Pure Zod schemas, types, and validator for `TemplateSpec`.
2. `contracts/template-instantiator.ts`: Deterministic canonical instantiation engine (`TemplateInstantiator`).
3. `registry/template-specs-data.json`: Machine-readable catalog containing all 105 authoritative `TemplateSpec` objects.
4. `registry/template-migration-manifest.json`: Machine-readable migration manifest with classification, parity status, and remaining gaps.
5. `documentation/s28r/TEMPLATE_INVENTORY_S28_R05.json`: Comprehensive reality inventory of all 105 legacy templates.
6. `documentation/s28r/ENGINE_NEUTRAL_TEMPLATE_ARCHITECTURE.md`: Formal architectural documentation and sequence diagrams.
7. `tests/remotion/s28_r05_red_tests.test.ts`: Initial RED invariant test suite (11 tests).
8. `tests/remotion/s28_r05_template_spec.test.ts`: Contract, parameter, slot, and constraints unit test suite (15 tests).
9. `tests/remotion/s28_r05_template_migration.test.ts`: Migration and semantic parity test suite across 10 representative templates (11 tests).
10. `tests/remotion/s28_r05_subprocess_isolation.test.ts`: Subprocess isolation test executing with React/Remotion blocked (1 test).
11. `tests/architecture/test_s28_r05_architecture_guards.test.ts`: Architectural boundary guard suite (7 tests).
12. `documentation/s28r/evidence/S28-R05_REPORT.md`: This comprehensive gate report.

### Modified:
1. `registry/semantic-registry.ts`: Integrated `TemplateSpec` loader, proxied alias resolution (`getSemanticTemplateSpec()`), preserving single authority.
2. `contracts/index.ts`: Re-exported `template-spec` and `template-instantiator`.

---

## 8. Registry Migration Approach

Single authority was strictly preserved without creating parallel competing registries:
1. `registry/template-registry-data.json` remains the authoritative origin for all template identity, labels, categories, and aliases.
2. `registry/template-specs-data.json` expands this truth with engine-neutral `TemplateSpec` structures.
3. `registry/semantic-registry.ts` exposes `getSemanticTemplateSpec(idOrAlias)` alongside existing `getSemanticTemplateEntry(idOrAlias)`.
4. `registry/template-registry.tsx` remains untouched as the preserved Remotion compatibility layer for existing renderers.

---

## 9. Representative Migrations

Ten representative templates were migrated and verified with semantic parity:

| # | Representative Scope | Canonical Template ID | Classification | Synthesized Canonical Layers |
| :--- | :--- | :--- | :--- | :--- |
| **1** | Simple Title Card | `rui-title-card` | `NATIVE` | Shape (bg) + Text (title) + Text (sub) + Shape (accent) |
| **2** | Text-Heavy Typography | `rui-quote-card` | `NATIVE` | Shape (bg) + Text (italic quote) + Text (author) |
| **3** | Image/Video Media Frame | `rui-media-frame` | `NATIVE` | Shape (bg) + Image (asset_ref, contain) + Text (caption) |
| **4** | Multi-Layer Overlay | `rui-lower-third` | `NATIVE` | Shape (plate) + Text (name) + Text (role) |
| **5** | Numeric / Statistics | `rui-stat-card` | `NATIVE` | Shape (bg) + Text (value) + Text (label) |
| **6** | Scene Presentation | `rui-intro` | `NATIVE` | Shape (bg) + Text (title, 72pt) + Text (tagline) |
| **7** | Standard Transitions | `fade-transition`, `slide-transition` | `NATIVE` | Canonical `TransitionRef` ("fade" / "slide", 15f overlap) |
| **8** | Bento Grid Panels | `rui-bento-pan` | `NATIVE` | Shape (bg) + Text (title) + Shape (panel 1) + Shape (panel 2) |
| **9** | Aliased Template | `BentoPanWrapper` $\to$ `rui-bento-pan` | `NATIVE` | Identical canonical spec & fragment produced via alias |
| **10**| Active Production Pipeline | `rui-title-card` | `NATIVE` | Passes R02 Normalizer & R03 Evaluator with exact values |

---

## 10. Legacy Remotion Preservation

- **Zero deleted TSX templates**: All 105 TSX wrapper components in `templates/` remain intact.
- **Zero breaking changes in render pipeline**: `npm test` continues to pass 100% of its 153 tests.
- **Backwards compatibility preserved**: `getRegistryEntry()` and `COMPONENT_BINDINGS` in `registry/template-registry.tsx` remain available for Remotion rendering until R08/R09.

---

## 11. Test Verification & Results

```text
===================================================================================
COMPREHENSIVE TEST SUITE EXECUTION SUMMARY
===================================================================================

1. S28-R05 Vitest Suite (New in R05):
   ✓ tests/remotion/s28_r05_red_tests.test.ts                     (11 tests) [PASS]
   ✓ tests/remotion/s28_r05_template_spec.test.ts                 (15 tests) [PASS]
   ✓ tests/remotion/s28_r05_template_migration.test.ts            (11 tests) [PASS]
   ✓ tests/remotion/s28_r05_subprocess_isolation.test.ts          ( 1 test ) [PASS]
   ✓ tests/architecture/test_s28_r05_architecture_guards.test.ts  ( 7 tests) [PASS]
   Subtotal S28-R05: 45 passed (45)

2. Complete S28 Vitest Regression Suite (R02, R03, R04, R05):
   ✓ tests/remotion/s28_r02_red_tests.test.ts                     ( 7 tests) [PASS]
   ✓ tests/remotion/s28_r02_canonical_parity.test.ts              (11 tests) [PASS]
   ✓ tests/architecture/test_s28_r02_architecture_guards.test.ts  ( 5 tests) [PASS]
   ✓ tests/remotion/s28_r03_red_tests.test.ts                     (12 tests) [PASS]
   ✓ tests/remotion/s28_r03_canonical_parity.test.ts              ( 8 tests) [PASS]
   ✓ tests/architecture/test_s28_r03_architecture_guards.test.ts  ( 4 tests) [PASS]
   ✓ tests/remotion/s28_r04_mutations_core.test.ts                (15 tests) [PASS]
   ✓ tests/remotion/s28_r04_editor_session.test.ts                (13 tests) [PASS]
   ✓ tests/remotion/s28_r04_editor_performance.test.ts            ( 1 test ) [PASS]
   ✓ tests/remotion/s28_r04_subprocess_isolation.test.ts          ( 2 tests) [PASS]
   ✓ tests/architecture/test_s28_r04_architecture_guards.test.ts  ( 5 tests) [PASS]
   ✓ tests/remotion/s28_06_render_smoke.test.ts                   ( 6 tests) [PASS]
   Subtotal S28 Combined: 134 passed (134)

3. Standard Remotion Test Suite (`npm test`):
   ✓ 13 test files                                               (153 tests) [PASS]

4. Python Architecture & Core Suites (`pytest`):
   ✓ tests/architecture/ (24 test files)                         (105 tests) [PASS]
   ✓ tests/core/test_template_contract.py                        ( 14 tests) [PASS]
   ✓ tests/validators/test_template_registry_consistency.py       (  4 tests) [PASS]

TOTAL TESTS VERIFIED: 410 PASSED / 0 FAILED (100% GREEN)
```

---

## 12. Architecture Guards Enforcement

| Guard Identifier | Invariant Enforced | Status |
| :--- | :--- | :--- |
| **`R05-AG-01`** | `contracts/template-spec.ts` & `template-instantiator.ts` have 0 imports from React or Remotion | **PASS** |
| **`R05-AG-02`** | `TemplateSpec` data contracts contain 0 TSX references, code containers, or frame hooks | **PASS** |
| **`R05-AG-03`** | `TemplateInstantiator` cannot call renderer, spawn subprocesses, or perform network/fs I/O | **PASS** |
| **`R05-AG-04`** | Single Canonical Template Registry authority strictly preserved (no second registry created) | **PASS** |
| **`R05-AG-05`** | Machine-readable migration manifest has exactly 105 templates, 0 unknown | **PASS** |
| **`R05-AG-06`** | Fail-closed gate: `ENGINE_BACKED` and unknown templates throw without silent TSX fallback | **PASS** |
| **`R05-AG-07`** | All 105 `TemplateSpec` entries pass strict structural and purity validation | **PASS** |
| **`R05-ISO-01`** | Isolated Node process executes native instantiation with React/Remotion blocked | **PASS** |

---

## 13. Known Unsupported Semantic Features

The following capabilities are explicitly documented as unsupported by the pure canonical layer document and are categorized under `ENGINE_BACKED` or `HYBRID`:
- **MapLibre GL Vector Map Rendering**: Requires WebGL context and dynamic tile fetching (`rui-map-flight`).
- **3D Perspective Camera Rigs**: Requires 3D rendering engine and mesh projection (`scene3d-element`).
- **Physics Particle Simulation**: Requires runtime physics step and particle spawner (`particlesystem-element`).
- **Non-Standard GL Shaders**: Shader-based transition presentations (`ripple`, `film-burn`, `dreamy-zoom`, etc.) are retained as `HYBRID`.

---

## 14. Remaining Compatibility-Only Templates

59 templates are classified as `LEGACY_COMPATIBILITY`. These represent complex multi-scene templates (e.g. `rui-browser-flow`, `rui-data-story`, `rui-hero-device-assemble`) whose Remotion TSX implementation is preserved for rendering pipeline compatibility until R08/R09 renderer wrapping.

---

## 15. Scope Explicitly Deferred

In strict adherence to the milestone boundaries:
- **`R06` (Browser Live Preview Runtime)**: NOT implemented (canvas, DOM renderer, play/pause/seek controls).
- **`R07` (Audio Preview & Waveform)**: NOT implemented.
- **`R08` (Multi-Renderer Dispatch & Registry)**: NOT implemented.
- **`R09` (Remotion Renderer Adapter)**: NOT implemented.

---

## 16. Final Gate Assessment

```text
Canonical Template Registry remains single authority          ✅ PASS
Template identity is no longer inherently TSX/Remotion        ✅ PASS
TemplateSpec contract is engine-neutral                       ✅ PASS
Native fragment contains no Remotion/React/TSX types          ✅ PASS
Template parameters are typed and validated                   ✅ PASS
Template constraints/requirements are explicit                ✅ PASS
TemplateInstantiator exists as one canonical path              ✅ PASS
Representative native templates instantiate successfully      ✅ PASS
At least one real current template is migrated end-to-end      ✅ PASS
Native template instantiation works with Remotion disabled     ✅ PASS
Same inputs produce deterministic semantic structure           ✅ PASS
Aliases/canonical IDs remain safe                              ✅ PASS
Legacy Remotion implementations are preserved                  ✅ PASS
No silent fallback from semantic failure to TSX                ✅ PASS
Every canonical template has migration classification          ✅ PASS
No critical template remains UNKNOWN                           ✅ PASS
Engine-backed templates are explicit, not disguised native     ✅ PASS
Architecture guards prevent engine leakage                     ✅ PASS
Existing legacy regression suite remains green                 ✅ PASS
R06 preview runtime has not been implemented prematurely       ✅ PASS
R08 renderer architecture has not been implemented prematurely ✅ PASS
```

### FINAL GATE DECISION:
# **`S28-R05 PASS`**
