# Template Runtime Matrix: Reality Audit & Contract Analysis

**Status**: Verified Reality Specification  
**Milestone**: S28-R01  
**Audited SHA**: `69b8798b2e2296bc5a24af411ac44133c072a029`  

---

## 1. Template Identity Dual Reality

The repository currently exhibits a **split personality** regarding what constitutes a "Template":

```text
+-----------------------------------------------------------------------------------+
| 1. SEMANTIC TEMPLATE IDENTITY (Declarative Domain Contract)                       |
| - Defined in registry/template-registry-data.json                                 |
| - Properties: canonical_id, label, description, category, schema, defaults,       |
|   default_duration_frames, consumes, supported_aspects                            |
| - Consumed by: AI Planner, BlueprintCompiler, contracts/template-schemas.ts       |
+-----------------------------------------------------------------------------------+
                                         |
                                         | FORCED BINDING (Coupling Point)
                                         v
+-----------------------------------------------------------------------------------+
| 2. RUNTIME COMPONENT IDENTITY (Remotion React Implementation)                     |
| - Defined in templates/<category>/<Wrapper>.tsx                                   |
| - Backed by remotion-app/src/compositions/ or remotion-app/src/remotion/scenes/   |
| - Bound in registry/template-registry.tsx: COMPONENT_BINDINGS[component_name]     |
| - FAILS CLOSED: Throws fatal error if physical .tsx component is missing          |
+-----------------------------------------------------------------------------------+
```

### Specific Coupling Points Where Template == TSX:
1. **Registry Registration**: `registry/template-registry.tsx` line 235:
   ```ts
   const comp = COMPONENT_BINDINGS[t.component_name];
   if (!comp) {
     throw new Error(`Template component binding missing for '${t.canonical_id}' (${t.component_name})`);
   }
   ```
   A semantic template cannot even be loaded into memory without an existing, compiled React component.
2. **Pre-Mount Render Gate**: `contracts/render-input.ts` lines 266-269:
   `UnknownTemplateError` is raised if `scene.template` does not resolve to an entry in `TEMPLATE_REGISTRY`, which in turn requires `component` to be present.
3. **Template Capability Lock**: Template visual animations (staggers, keyframes, spring bounces, SVG morphs) exist **only** as internal TypeScript code inside `remotion-app/src/` components. They are not represented in any declarative AST or schema.

---

## 2. Template Families Runtime Matrix

The 105 registered templates group into distinct functional families with specific runtime characteristics:

| Template Family | Representative Templates | Source Wrapper Path | Backing Remotion Implementation | Animation Authority | Asset Dependencies | Remotion Primitives Used |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Scene / Narrative** | `intro`, `showcase`, `creator-reel`, `deploy-reveal` | `templates/scenes/*Wrapper.tsx` | `remotion-app/src/compositions/*` | Component-internal TSX code (`RAIL_AT`, `FADE_AT`) | Media refs, logo, audio tracks | `useCurrentFrame`, `useVideoConfig`, `interpolate`, `spring`, `Sequence`, `AbsoluteFill` |
| **Data & Metrics** | `animated-bar-chart`, `stat-card`, `metric-ticker`, `data-story` | `templates/elements/*Wrapper.tsx`, `templates/scenes/DataStoryWrapper.tsx` | `remotion-app/src/remotion/scenes/*` | Component-internal math + `spring()` interpolation | Numerical data, labels, delta indicators | `useCurrentFrame`, `spring`, `interpolate`, `AbsoluteFill` |
| **Code & Technical** | `code-block`, `terminal-simulator`, `code-reveal`, `code-diff-wipe` | `templates/elements/*Wrapper.tsx` | `remotion-app/src/remotion/scenes/*` | Character typing loops, line reveals | Code snippets, syntax tokens | `useCurrentFrame`, `interpolate`, `AbsoluteFill` |
| **Social & Content** | `social-clip`, `podcast-clip`, `audiogram-scene`, `caption-scene` | `templates/scenes/*Wrapper.tsx`, `templates/elements/*Wrapper.tsx` | `remotion-app/src/remotion/scenes/*` | Audio spectrum sync, caption word timestamps | Audio files, spectrum JSON, avatar images | `useCurrentFrame`, `Audio`, `staticFile`, `AbsoluteFill`, `delayRender`, `continueRender` |
| **UI & Product** | `bento-pan`, `dashboard-populate`, `browser-flow`, `device-mockup-zoom` | `templates/scenes/*Wrapper.tsx`, `templates/elements/*Wrapper.tsx` | `remotion-app/src/compositions/*` | Virtual camera panning, window assembly | Screenshot images, screen refs | `useCurrentFrame`, `useVideoConfig`, `interpolate`, `spring`, `AbsoluteFill` |
| **Text & Typography** | `animated-text`, `title-card`, `typewriter`, `auto-fit-title` | `templates/elements/*Wrapper.tsx` | `remotion-app/src/remotion/scenes/*` | Surface animation (`contracts/animations.ts`) | Google Web Fonts (`contracts/fonts.ts`) | `useCurrentFrame`, `interpolate`, `spring`, `AbsoluteFill` |
| **Geographic / Map** | `map-flight` | `templates/elements/MapFlightWrapper.tsx` | `remotion-app/src/remotion/scenes/map-flight/` | MapLibre camera interpolation, marker triggers | Map styles, geojson paths, marker icons | `useCurrentFrame`, `delayRender`, `continueRender`, `MapLibre GL` |
| **Transitions & Effects**| `fade`, `slide`, `wipe`, `flip`, `dissolve`, `camera-shake` | `templates/effects/*Transition.tsx` | `@remotion/transitions`, `remotion-app/src/engine/` | Remotion presentation timing (`linearTiming`) | None | `TransitionSeries`, `fade`, `slide`, `CameraRig` |

---

## 3. Discovered Source Code Divergence (Drift Alert)

During file-level diffing between the root `templates/` tree and `remotion-app/src/templates/`, an active file drift was discovered:

```diff
--- templates/scenes/SplitScreenWrapper.tsx
+++ remotion-app/src/templates/scenes/SplitScreenWrapper.tsx
@@ -2,18 +2,11 @@
 import { SplitScreen } from "@/remotion/scenes/split-screen";
 import type { TemplateProps } from "@registry/types";
 
-const DEFAULT_PANEL = {
-  src: "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxIiBoZWlnaHQ9IjEiPjwvc3ZnPg==",
-  label: "",
-};
-
 export const SplitScreenWrapper = ({ surface, content, ...rest }: any) => {
   const template_props = rest.template_props || {};
-  const left = template_props.left || DEFAULT_PANEL;
-  const right = template_props.right || DEFAULT_PANEL;
   return (
     <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
-      <SplitScreen left={left} right={right} {...template_props} title={content?.text || undefined} />
-    </div>
+    <SplitScreen  {...template_props} title={content?.text || undefined} />
+  </div>
   );
 };
```

**Architectural Assessment**:
- `templates/scenes/SplitScreenWrapper.tsx` contains fallback data URL panel definitions preventing crashes on missing media.
- `remotion-app/src/templates/scenes/SplitScreenWrapper.tsx` is an older version lacking these guards.
- Because `tsconfig.json` at root references `templates/` and `remotion-app/tsconfig.json` references `src/templates`, different execution tools may resolve different wrapper implementations!
- In accordance with S28-R01 rules: **Flagged as drift; not modified in this audit.**

---

## 4. Path to Template Independence

To achieve the future S28-R goal:
1. **R04**: Decouple `TemplateEntry` from `React.ComponentType`.
2. **R04**: Move `COMPONENT_BINDINGS` inside `RemotionRendererAdapter`.
3. **R04**: Establish a renderer-neutral `TemplateDefinition` where template capabilities, parameters, and layout regions are expressed declaratively.
4. **R05**: Preserve existing TSX wrappers as the Remotion implementation of those templates.
