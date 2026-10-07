# S28-R05 Architecture Specification: Engine-Neutral TemplateSpec & Migration

**Parent Initiative**: S28-R — Renderer Independence & Live Editor Core  
**Milestone**: S28-R05  
**Status**: ACTIVE & VERIFIED  
**Authority**: `contracts/template-spec.ts`, `contracts/template-instantiator.ts`, `registry/semantic-registry.ts`

---

## 1. Core Architectural Separation

Prior to Milestone S28-R05, a video template was conflated with a React component wrapper and a Remotion composition. S28-R05 establishes the formal separation of authoring asset semantics from execution runtime:

```text
BEFORE (Coupled Implementation Model):
Template = Registry ID → TSX / React Component / Remotion Runtime

AFTER (Semantic Data Contract Model):
Canonical Template Registry
         │
         ├──► TemplateSpec (Pure Engine-Neutral Data Contract)
         │           │
         │           ▼
         │    TemplateInstantiator
         │           │
         │           ▼
         │    Canonical VideoDocument Fragment (BlueprintScene + CanonicalLayer[])
         │           │
         │           ▼
         │    Canonical Document Validator
         │           │
         │           ├──► Live Preview (R06)
         │           └──► Multi-Renderer Dispatch (R08)
         │
         └──► Legacy Implementation Metadata (Preserved Compatibility)
                     │
                     ▼
              Remotion Path (Preserved for R09 wrapping)
```

### Definitions:
- **`TemplateSpec`**: Reusable semantic authoring asset defining parameter contracts, content slots, duration/aspect constraints, capabilities requirements, and declarative fragment layer synthesis.
- **`Canonical VideoDocument`**: The single executable, editable source of truth (`BlueprintV2` and `NormalizedVideo`).
- **`Remotion Implementation`**: A preserved compatibility runtime wrapper, NOT the canonical identity of the template.
- **`Template Registry`**: The single authority for reusable templates (`registry/template-registry-data.json`, `registry/template-specs-data.json`, `registry/semantic-registry.ts`).
- **`Renderer`**: A downstream execution concern (governed in R08+), not a template authority.

---

## 2. Template Classification Taxonomy

Every template in the registry is explicitly classified into one of four mutually exclusive, fail-closed categories:

| Classification | Meaning | Instantiation Behavior |
| :--- | :--- | :--- |
| **`NATIVE`** | Fully representable by R02/R03 canonical primitives (layers, typography, transforms, standard transitions, keyframes). | Instantiates directly into canonical `BlueprintScene` + `CanonicalLayer[]` with zero framework dependencies. |
| **`ENGINE_BACKED`** | Inherently requires specialized runtime engines not present in core video documents (e.g. MapLibre GL for geospatial flight, Three.js for 3D perspective scenes, particle simulation). | Throws `EngineBackedTemplateError` with structured diagnostic of required capabilities; no silent mock. |
| **`HYBRID`** | Semantic layout combined with specialized visual shader or runtime effect (e.g. GL transitions, continuous momentum scrollers, canvas rain). | Native layers are synthesized alongside explicit engine metadata. |
| **`LEGACY_COMPATIBILITY`** | Legacy Remotion TSX implementation preserved for rendering pipeline compatibility pending declarative migration in R08/R09. | Retains complete legacy compatibility; documented with explicit reason, remaining gap, and migration owner. |

### Classification Distribution (Total: 105 Templates)
- **`NATIVE`**: 29 templates (27.6%)
- **`HYBRID`**: 14 templates (13.3%)
- **`ENGINE_BACKED`**: 3 templates (2.9%)
- **`LEGACY_COMPATIBILITY`**: 59 templates (56.2%)
- **`UNKNOWN`**: **0 templates (0.0%)**

---

## 3. Template Lifecycle & Instantiation Pipeline

```text
Template Inputs + Instantiation Context
                   │
                   ▼
       1. Resolve Canonical ID & Alias
          (Fail-closed via SEMANTIC_TEMPLATE_REGISTRY)
                   │
                   ▼
       2. Classification Gate
          (ENGINE_BACKED throws EngineBackedTemplateError)
                   │
                   ▼
       3. Parameter & Slot Validation
          (Fail-closed against typed parameter definitions)
                   │
                   ▼
       4. Constraints Check
          (Duration bounds [minFrames, maxFrames], aspect ratio)
                   │
                   ▼
       5. Deterministic Token & Default Resolution
          (Resolve brand tokens, apply defaults)
                   │
                   ▼
       6. Stable ID Generation
          (Deterministic prefix: scene_${tplId}_${startFrame})
                   │
                   ▼
       7. Canonical Layer Synthesis & Binding
          (Clone default_layers, bind params, set TimeRange)
                   │
                   ▼
       8. Contract Validation Gate
          (validateLayerHierarchy + BlueprintSceneSchema)
                   │
                   ▼
       Canonical VideoDocument Fragment
```

---

## 4. Architectural Guards & Invariants

The architecture enforces the following invariants:
1. **Zero Framework Pollution**: `contracts/template-spec.ts` and `contracts/template-instantiator.ts` have **0 imports** from `react`, `react-dom`, `remotion`, `@remotion/*`.
2. **Zero Code Containers**: `TemplateSpec` is a pure data contract containing **0 function pointers**, **0 TSX references**, **0 ReactNode symbols**, and **0 frame hooks**.
3. **Subprocess Isolation**: Verified in an isolated Node process where `react` and `remotion` are forcibly blocked at the module loader level (`R05-ISO-01`).
4. **Single Authority Rule**: No secondary or parallel template registries (`template-registry-v2`, `editor-template-registry`) are permitted.
5. **No Silent Fallback**: If a template is `ENGINE_BACKED` or unknown, it throws structured errors immediately rather than silently executing TSX.
