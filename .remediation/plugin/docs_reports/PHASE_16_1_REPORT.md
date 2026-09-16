# Phase 16.1 — Specialized Template Family Mining & Adapter Compression

## 1. Executive Summary

In Phase 15.1, we structurally decoupled execution eligibility from runtime verification, resulting in 104 `FULLY_SUPPORTED` templates out of a catalog of 153 processed physical template files. This left exactly **49 templates** blocked in the `CATALOG_ONLY` and `BROKEN` queues.

The objective of Phase 16.1 was to perform a rigorous structural analysis of these 49 templates and determine the smallest set of reusable adapter families and generic fixes needed to unlock them. 

The analysis reveals that the vast majority of blocked templates **do not require specialized adapter families**. Instead, they are blocked by scalar prop mapping gaps or missing proven defaults. Only **8 templates** possess complex structural props (e.g., arrays or objects) that genuinely demand adapter intervention.

## 2. Blocker Distribution

A precise inventory of the 49 blocked templates shows the following true blockers:

- **MISSING_DEFAULT_OR_MAPPING**: 45 templates
- **MISSING_MEDIA_MAPPING**: 3 templates
- **MISSING_DEPENDENCIES**: 1 template

*(Note: In previous phases, templates lacking semantic roles were temporarily grouped manually. However, the Phase 15 semantic engine successfully assigned baseline roles (e.g., `generic_component`) to all templates, shifting their core execution barrier to the unmapped props stage.)*

## 3. Physical Prop Clusters

By extracting the physical signature (required and optional props lacking proven defaults) of every template directly from TypeScript interfaces and Zod schemas, we categorized the 49 templates into:

- **Structural Templates (8)**: Templates containing `array` or `object` props that cannot be natively resolved by a scalar mapping.
- **Scalar/Generic Templates (40)**: Templates whose unmapped props are purely scalar (strings, numbers, booleans) or simple media references.
- **Dependency/Source Broken (1)**: Templates with fundamentally broken source code or missing assets.

## 4. Proposed Adapter Families

By clustering the 8 structural templates by their precise structural prop signatures, we identified **1 reusable adapter family**.

### `family_v1_1` (Social Captions)
- **Members**: 2 (`scenes/social/social-clip/index`, `scenes/social/SocialClip`)
- **Physical Signature**: `captions: array`
- **Semantic Role**: `explainer_text`
- **Complexity**: MEDIUM
- **Confidence**: MEDIUM
- **Required Adaption**: Injecting the parsed word-level captions array from `CreativeSpec` into the template's `captions` prop structure.

## 5. Compression Analysis

- **`family_v1_1` Compression Ratio**: 2x (2 templates unlocked for 1 adapter).

While the number of families is low, this is a highly positive architectural signal. It means we avoided creating unnecessary "mega-adapters" for templates that only require standard configuration.

## 6. Generic Fix Opportunities

A massive **40 templates** can be unlocked entirely through generic engine improvements rather than template-specific adapters:

- **Default Fix Candidates (37)**: These templates (such as `primitives/TrafficLights`, `orphan/Glow`, `cursor/CursorSprite`) are blocked solely because they define many optional styling props (e.g., `color`, `size`, `scale`) that lack proven defaults in the schema. Solving the generic default injection pipeline (or defining a semantic schema for fallback values) will unlock all 37 immediately.
- **Generic Mapping Candidates (3)**: Templates blocked by `MISSING_MEDIA_MAPPING` without complex structural needs. Enhancing the `SemanticContentResolver` to map primary scene media to these components will unlock them.

## 7. Singleton Candidates

**6 templates** have completely unique structural contracts and cannot be clustered:

1. `audio/AudioManager`: Requires complex audio object mappings.
2. `camera/AutoZoom`: Unique structural bounding configs.
3. `camera/CameraRig`: Specialized camera configuration object.
4. `cursor/Cursor`: Requires an `actions: array` and `getRect: string` configuration block.
5. `layout/LayoutWindow`: Specialized recursive or nested configuration.
6. `primitives/Stagger`: Requires specialized children/timing arrays.

These must be treated as `SINGLETON_ADAPTER`s if execution is desired.

## 8. Dependency/Source Blockers

**1 template** is blocked by non-adapter physical issues:
- `scenes/ChaosDesktop`: `MISSING_DEPENDENCIES`
  - **Issue**: Requires repairing the physical assets and dependency imports. This cannot be solved via an adapter.

## 9. False Families

- **Cursor vs CursorSprite**: `Cursor` requires a complex `actions` array to drive motion, while `CursorSprite` is a purely scalar UI component (`size`, `color`). Grouping them into a single "Cursor" family was rejected because their execution contracts are structurally incompatible.
- **Generic UI Primitives**: Grouping components like `TrafficLights`, `Placeholder`, and `TopNav` into a "UI Toolkit" family was rejected. They all require unique scalar defaults, not a shared structural adapter. Grouping them would create an untyped mega-adapter rather than a deterministic pipeline.

## 10. Recommended Phase 16.2 Order

1. **Generic Default Fallbacks**: Solve the 37 scalar `defaultFixCandidates` first. This requires zero new adapters and yields the highest coverage gain.
2. **Generic Media Mapping**: Solve the 3 `genericMappingCandidates`.
3. **`family_v1_1`**: Implement the Social Captions adapter (unlocks 2 templates).
4. **High-Priority Singletons**: Address `cursor/Cursor` (1 template) if highly requested.
5. **Dependency Fixes**: Repair `scenes/ChaosDesktop` source files.

## 11. Expected Coverage

**Current Verified State:**
104 / 153 processed (68%)

**Potential Coverage Expansion:**
- After generic default fixes: 141 / 153 (92%)
- After generic media mapping: 144 / 153 (94%)
- After adapter `family_v1_1`: 146 / 153 (95%)
- After Singletons: 152 / 153 (99%)

*(Note: This represents potential eligibility coverage, assuming the engine successfully maps the props. Full verification requires progression to `COHORT_RENDER_VERIFIED` in a later phase.)*

---

# PHASE 16.1 DECISION GATE

Blocked templates: 49
Templates requiring no specialized adapter: 40
Potentially unlockable by generic mapping/defaults: 40
Family adapter candidates: 2 templates (1 family)
Singleton adapter candidates: 6 templates
Dependency/source blockers: 1 template
Unresolved: 0
Minimum practical new adapters: 1 (excluding singletons)
Potential coverage gain: +42 templates (Generic Fixes + Family 1)
Projected coverage: 146 / 153

Highest-leverage fix: Generic Default Pipeline (+37)
Second-highest: Generic Media Mapping (+3)
Third-highest: `family_v1_1` (+2)

Recommended Phase 16.2: Proceed with generic scalar default pipeline before implementing structural adapters.
