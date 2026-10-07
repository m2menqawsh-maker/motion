# Contract Dependency & Layering Rules

**Status**: Formally Adopted Architecture Standard  
**Milestone**: S28-R02  
**Parent Initiative**: S28-R — Renderer Independence & Live Editor Core  
**Governing Automated Tests**:
- Vitest: `tests/architecture/test_s28_r02_architecture_guards.test.ts`
- Pytest: `tests/architecture/test_s28_r02_architecture_guards.py`  
**Implementation Date**: 2026-10-06  

---

## 1. Executive Summary & Principles

The architectural integrity of the video platform depends on strict dependency direction. Core contracts and domain normalizers must be completely decoupled from rendering frameworks, UI component libraries, and concrete runtime environments.

### The Golden Rule of Video Contracts:
> **Contracts define reality. Engines consume reality.**  
> Under no circumstances may a contract module import, reference, or depend upon the engine that renders it.

---

## 2. System Layering Model

The codebase is organized into five strictly bounded layers with strictly unidirectional dependency flow:

```mermaid
flowchart TD
    subgraph Layer 0: Pure Contracts [contracts/*]
        L0_1[contracts/canonical-video.ts]
        L0_2[contracts/blueprint.ts]
        L0_3[contracts/effects.ts]
        L0_4[contracts/animations.ts]
        L0_5[contracts/brand.ts]
        L0_6[contracts/positions.ts]
        L0_7[contracts/fonts.ts]
    end

    subgraph Layer 1: Core Domain Normalization [contracts/normalization.ts]
        L1_1[normalizeCanonicalVideo]
        L1_2[normalizeScene]
        L1_3[resolveTokensDeep]
    end

    subgraph Layer 2: Semantic Metadata Registries [registry/semantic-registry.ts]
        L2_1[template-registry-data.json]
        L2_2[getSemanticTemplateEntry]
        L2_3[listSemanticTemplates]
    end

    subgraph Layer 3: Compatibility & Validation Gates [contracts/render-input.ts & remotion-app/src/merge.ts]
        L3_1[parseRenderInput Gate]
        L3_2[mergeProject Adapter]
    end

    subgraph Layer 4: Concrete Render Runtime [remotion-app/* & registry/*.tsx]
        L4_1[remotion-app/src/Root.tsx]
        L4_2[remotion-app/src/BlueprintVideo.tsx]
        L4_3[registry/template-registry.tsx - 105 TSX Templates]
        L4_4[registry/effects-runtime.ts - Concrete React Effects]
        L4_5[remotion-app/src/animations.ts - Remotion interpolate/spring]
        L4_6[remotion-app/src/BrandContext.tsx - React Context]
    end

    Layer 0 --> Layer 1
    Layer 0 --> Layer 2
    Layer 1 --> Layer 3
    Layer 2 --> Layer 3
    Layer 3 --> Layer 4
```

### Dependency Rules:
- **Layer 0 (Pure Contracts)**:
  - May ONLY import standard libraries (e.g., `zod`, Node utilities).
  - May import other Layer 0 contracts.
  - **CANNOT** import Layer 1, 2, 3, or 4.
  - **CANNOT** import `react`, `react-dom`, `remotion`, `@remotion/*`.
- **Layer 1 (Core Normalization)**:
  - May import Layer 0.
  - **CANNOT** import Layer 2, 3, or 4.
  - Zero framework dependencies.
- **Layer 2 (Semantic Registries)**:
  - May import Layer 0.
  - Pure JSON data lookups.
  - **CANNOT** import TSX components or React libraries.
- **Layer 3 (Compatibility Gates)**:
  - May import Layer 0, 1, 2.
  - Provides backwards compatibility for existing render callers.
- **Layer 4 (Concrete Runtimes)**:
  - May import any lower layer (Layer 0 through 3).
  - Remotion, React, and browser/Node canvas APIs are strictly confined to this layer.

---

## 3. Explicit Forbidden Import Catalog

The automated architecture guards enforce the following prohibitions:

| Forbidden Pattern in `contracts/` | Violation Severity | Rationale | Resolution |
| :--- | :--- | :--- | :--- |
| `import ... from "react"` | **CRITICAL (FAIL-CLOSED)** | Couples data contracts to React UI framework | Use pure TypeScript types or custom interfaces (e.g. `PositionStyle` instead of `CSSProperties`) |
| `import ... from "remotion"` | **CRITICAL (FAIL-CLOSED)** | Couples contracts to Remotion engine | Move runtime math to `remotion-app/src/animations.ts` |
| `import ... from "@remotion/*"` | **CRITICAL (FAIL-CLOSED)** | Couples contracts to Remotion packages | Move font loaders to `remotion-app/src/fonts.ts` |
| `import ... from "../remotion-app/*"` | **CRITICAL (FAIL-CLOSED)** | Upward dependency inversion into concrete app | Relocate shared types/models into `contracts/` |
| `import ... from "../templates/*"` | **HIGH (FAIL-CLOSED)** | Pulls TSX components into data parsing | Decouple semantic schema from component implementation |
| `import ... from "./BrandContext"` | **HIGH (FAIL-CLOSED)** | React Context inside brand tokens | Keep token data pure in `contracts/brand.ts`; context in `remotion-app/src/BrandContext.tsx` |

---

## 4. Automated Architecture Guards

S28-R02 introduced two independent automated guard suites (TypeScript Vitest and Python Pytest) to guarantee zero regression:

### 4.1 TypeScript Guard Suite (`tests/architecture/test_s28_r02_architecture_guards.test.ts`)
1. **AG-01: Zero React/Remotion in `contracts/`**:
   Scans every `.ts` file in `contracts/` using AST/regex, asserting 0 imports from `react`, `remotion`, or `@remotion/*`.
2. **AG-02: Zero Inversion into `remotion-app/`**:
   Ensures no contract file imports from `../remotion-app/*` or `remotion-app/*`.
3. **AG-03: Semantic Effects Catalog Purity**:
   Validates `contracts/effects.ts` contains all 45 semantic definitions without importing any `.tsx` or React component bridges.
4. **AG-04: Semantic Template Registry Decoupling**:
   Validates `registry/semantic-registry.ts` loads purely from `template-registry-data.json` without loading any of the 105 TSX templates.
5. **AG-05: Subprocess Isolation Execution**:
   Executes a fresh Node subprocess running `parseCanonicalVideo()` and `normalizeCanonicalVideo()` with a custom module loader hook that throws fatal errors if `react` or `remotion` are ever required. Asserts exit code 0.

### 4.2 Python Guard Suite (`tests/architecture/test_s28_r02_architecture_guards.py`)
1. **`test_contracts_layer_has_zero_react_or_remotion_imports`**:
   Scans `contracts/*.ts` from Python, asserting zero framework imports.
2. **`test_contracts_layer_has_no_remotion_app_imports`**:
   Verifies zero upward imports from `contracts/` into `remotion-app/`.
3. **`test_pure_normalization_module_exists_and_is_clean`**:
   Verifies `contracts/normalization.ts` is pure and unpolluted.
4. **`test_semantic_effects_catalog_is_pure_and_complete`**:
   Verifies `contracts/effects.ts` contains the complete 45-effect catalog.

---

## 5. Maintenance Guidelines for Developers

1. **Adding a New Field to Blueprint**:
   Add the field directly in `contracts/blueprint.ts` with pure Zod validation. If default values are needed, handle them in `contracts/normalization.ts`.
2. **Adding a New Template**:
   Register metadata in `registry/template-registry-data.json`. The template becomes semantically valid immediately without requiring a TSX wrapper.
3. **Adding a New Effect**:
   Define the semantic schema in `contracts/effects.ts`. If an implementation exists in Remotion, wire it inside `registry/effects-runtime.ts`.
4. **Pre-commit Verification**:
   Always run:
   ```bash
   npx vitest run tests/architecture/test_s28_r02_architecture_guards.test.ts
   uv run pytest tests/architecture/test_s28_r02_architecture_guards.py
   ```
