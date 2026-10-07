# Proposed Future Architecture Guards (S28-R Governance)

**Status**: Proposed Architecture Invariants (Audit Specification)  
**Milestone Target**: S28-R02 through S28-R15  
**Enforcement Policy**: Strict Fail-Closed (Automated via Pytest & Vitest Architecture Guards)  

---

## 1. Overview & Policy Rationale

To ensure that the S28-R migration permanently decouples the video system core from any specific rendering engine, the following structural rules must be codified into automated test guards starting in S28-R02.

**Rule of Thumb**:
```text
Contracts & Core Domains NEVER import Render Engines.
Render Engines ALWAYS adapt to Contracts.
```

---

## 2. Guard Specifications

### Guard 1: Contract Layer Purity
- **Rule**: No file within `contracts/` or `schemas/` may import from `remotion`, `@remotion/*`, or `react`.
- **Target Invariant**:
  ```text
  contracts/**/* ↛ remotion
  contracts/**/* ↛ @remotion/*
  contracts/**/* ↛ react
  contracts/**/* ↛ remotion-app/**/*
  ```
- **Current Violations to Fix in R02/R03**:
  - `contracts/animations.ts` (imports `interpolate`, `spring` from `remotion`).
  - `contracts/blueprint.ts` (indirectly imports `EFFECTS_RUNTIME` $\to$ `engine-bridge.tsx` $\to$ React).
  - `contracts/render-input.ts` (imports `SceneOverride` from `remotion-app/src/merge.ts`).

---

### Guard 2: AI Creative Intent Decoupling
- **Rule**: No file within `ai/planning/` or `ai/contracts/` may produce, validate, or reference React JSX, Remotion primitives, or physical `.tsx` component paths.
- **Target Invariant**:
  ```text
  ai/planning/**/* ↛ remotion
  ai/planning/**/* ↛ react
  CreativePlan ↛ ComponentType
  ```
- **Status Today**: **PASS**. `CreativePlanner` and `BlueprintCompiler` already comply 100%.

---

### Guard 3: Semantic Template Independence
- **Rule**: A Template's semantic identity (`canonical_id`, `schema`, `category`, `defaults`) must be valid, queryable, and testable without requiring the presence or import of a concrete React TSX component.
- **Target Invariant**:
  ```text
  registry/types.ts: TemplateEntry.component MUST be optional or separated into RendererBindings
  registry/template-registry.tsx: Missing TSX component MUST NOT crash the semantic registry
  ```
- **Current Violations to Fix in R04**:
  - `registry/types.ts` imports `ComponentType` from `react`.
  - `registry/template-registry.tsx` line 237 throws fatal error if component binding is missing.

---

### Guard 4: Asset Staging Neutrality
- **Rule**: Core asset materialization and storage services must not assume or hardcode a specific renderer's public directory structure.
- **Target Invariant**:
  ```text
  scripts/core/materializer.py ↛ remotion-app/public
  media_map.json entries MUST NOT require relative paths to remotion-app/public
  ```
- **Current Violations to Fix in R06**:
  - `materializer.py` stages files into `remotion-app/public/projects/...`.

---

### Guard 5: Quality Control (QC) Isolation
- **Rule**: Quality Control gates must evaluate output containers (`out.mp4`), audio streams, and still images neutrally without depending on internal renderer component trees.
- **Target Invariant**:
  ```text
  scripts/gates/final_qc.py ↛ remotion (Currently 100% compliant)
  scripts/gates/probe_qc.py MUST delegate still rendering via abstract VideoRenderer interface
  ```
- **Current Violations to Fix in R07**:
  - `probe_qc.py` invokes `npx remotion still` directly via subprocess.

---

### Guard 6: Public API Confinement
- **Rule**: Public API contracts (`api/schemas/`, `api/routers/`) must never expose internal renderer composition IDs, TSX file paths, or engine-specific error classes to client consumers.
- **Target Invariant**:
  ```text
  api/schemas/**/* ↛ composition_id
  api/schemas/**/* ↛ *.tsx
  api/services/health_service.py: Replace _probe_remotion with RendererRegistry.health()
  ```

---

## 3. Enforcement Implementation Plan (R02+)

1. **Python Guard**: Create `tests/architecture/test_renderer_independence_guards.py` using Python AST analysis to fail any PR introducing forbidden imports in `contracts/`, `ai/`, or `api/`.
2. **TypeScript Guard**: Create `tests/architecture/contracts_boundary.test.ts` scanning `contracts/**/*.ts` using `ts-morph` to assert zero imports from `remotion` or `react`.
