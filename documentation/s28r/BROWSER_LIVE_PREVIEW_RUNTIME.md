# Browser Live Preview Runtime Architecture

**Initiative**: S28-R — Renderer Independence & Live Editor Core  
**Milestone**: S28-R06  
**Governing Modules**: `preview/preview-runtime.ts`, `preview/visual-frame.ts`, `preview/dom-driver.ts`, `preview/capabilities.ts`, `preview/components/LivePreviewPlayer.tsx`

---

## 1. Architectural Mission

Milestone **S28-R06** establishes an engine-independent, high-performance **Browser Live Preview Runtime** capable of directly previewing the `Canonical VideoDocument` (`BlueprintV2` and `NormalizedVideo`) without relying on Remotion as the preview authority.

### The Canonical Preview Path

```text
       Canonical VideoDocument (BlueprintV2 / NormalizedVideo)
                             │
                             ▼
                  evaluateVideoAtFrame()
                 (contracts/evaluator.ts)
                             │
                             ▼
                   buildVisualFrame()
                (preview/visual-frame.ts)
                             │
                             ▼
                  DOMPreviewDriver / Canvas
                 (preview/dom-driver.ts)
                             │
                             ▼
                        Visual Frame
```

---

## 2. Fundamental Invariants

1. **Canonical VideoDocument Remains Authority**: The preview runtime holds no private document format, no `PreviewDocumentSchema`, and no independent document state. It reads and reflects `BlueprintV2` or `NormalizedVideo`.
2. **Zero Secondary Timeline or Animation Math**: Timeline durations (`calculateCanonicalDuration`), timebase conversions (`frameToMs`, `msToFrame`), easing curves (`solveCubicBezier`), and spring physics (`evaluateSpring`) are strictly delegated to `contracts/timeline.ts`, `contracts/keyframes.ts`, and `contracts/evaluator.ts`.
3. **Engine-Free Runtime Core**: The core modules (`preview/types.ts`, `preview/capabilities.ts`, `preview/visual-frame.ts`, `preview/dom-driver.ts`, `preview/preview-runtime.ts`) have **0 imports from React, Remotion, or `@remotion/*`**.
4. **Decoupled React Shell**: React exists solely as an optional consumer wrapper (`LivePreviewPlayer.tsx`) for embedding in web applications. All canonical semantics remain 100% outside React.
5. **Explicit Capabilities**: Features requiring external runtime engines (`ENGINE_BACKED`), custom WebGL shaders (`HYBRID`), or legacy TSX components (`LEGACY_COMPATIBILITY`) are explicitly diagnosed and handled fail-closed.

---

## 3. Playback State Machine & Controls

The `BrowserPreviewRuntime` class implements a complete temporal controller:

| Control / State | Mechanism | Invariant Enforced |
| :--- | :--- | :--- |
| **`play()`** | Clock / RAF Loop | Advances frames according to canonical fps and playback rate. |
| **`pause()`** | Halts Clock | Freezes current playhead deterministically at frame $N$. |
| **`seek(frame)`** | Clamp & Re-evaluate | Clamps $0 \le \text{frame} \le \text{duration} - 1$; generates frame in $< 0.05$ ms. |
| **`seekToMs(ms)`** | `msToFrame()` Conversion | Uses canonical rounding policy from `contracts/timeline.ts`. |
| **`stepForward(n)`** | Integer frame increment | Steps $N$ frames forward with upper bound clamping. |
| **`stepBackward(n)`**| Integer frame decrement | Steps $N$ frames backward with lower bound clamping ($0$). |
| **`setPlaybackRate()`**| Time dilation multiplier | Modulates frame accumulation interval. |
| **`setAspectRatio()`** | Dimension resolution | Resizes canvas to 16:9, 9:16, 1:1, or custom aspect ratio. |
| **`setDimensions()`** | Pixel dimensions | Re-computes viewport scale and aspect-fit transformation. |

---

## 4. Layer Taxonomy & Visual Representation

The `buildVisualFrame()` pure assembler maps discrete layer states into `VisualNode` structures:

### Supported Canonical Layers:
1. **`TextLayer`**:
   - Typography: `fontFamily`, `fontSize`, `fontWeight`, `fontStyle`, `fillColor`, `strokeColor`, `strokeWidth`, `lineHeight`, `textAlign`.
   - Text content dynamically bound from template parameters or surface overrides.
2. **`ImageLayer`**:
   - Resolves `asset_ref` to local or remote image asset.
   - Sizing: `fit` modes (`contain`, `cover`, `fill`).
   - Crop rectangle support (`x`, `y`, `width`, `height`).
3. **`ShapeLayer`**:
   - Geometries: `rectangle`, `ellipse`, `path` (SVG vector path).
   - Styling: `fillColor`, `strokeColor`, `strokeWidth`, `borderRadius`.
4. **`GroupLayer`**:
   - Hierarchical container with nested `children` nodes.
   - Composed transforms: $\mathbf{T}_{\text{child}} = \mathbf{T}_{\text{parent}} \circ \mathbf{T}_{\text{child}}$ (composed position, scale, rotation, and opacity).
5. **Basic Transitions**:
   - `fade`: Blends outgoing scene opacity ($1 - t$) and incoming scene opacity ($t$).
   - `slide`: Offsets outgoing scene coordinates ($-W \cdot t$) and incoming scene ($W \cdot (1 - t)$).
   - `wipe`: Discrete boundary switch.
6. **Keyframe Animations**:
   - Evaluates channel tracks (`TRANSFORM_X`, `TRANSFORM_Y`, `SCALE`, `SCALE_X`, `SCALE_Y`, `ROTATION`, `OPACITY`) via pure R03 keyframe mathematics.

---

## 5. Live Mutation & Invalidation Integration

The preview runtime subscribes directly to changes emitted by R04 mutations or `EditorSession`:

```typescript
runtime.updateDocument(mutatedBlueprint, changeSet);
```

### Invalidation Granularity:
- **`requires_timeline_rebuild`**: Re-computes canonical duration via `calculateCanonicalDuration(scenes)` and clamps the current playhead if duration shortened.
- **`requires_layout`**: Re-computes aspect ratio, dimensions, and viewport scale.
- **`requires_render`**: Re-evaluates active layers and redraws DOM/Canvas stage.
- **`affected_scene_ids` / `affected_layer_ids`**: Enables targeted entity caching and minimal DOM updates.

### Transient Interaction Support:
- In drag gestures (e.g. bounding box repositioning at 60fps), `EditorSession.applyTransientMutation()` feeds directly into `runtime.updateDocument()`.
- The live preview updates instantaneously ($< 1.5$ ms) without committing to the undo stack.
- Calling `session.undo()` or `session.redo()` immediately restores prior preview state.

---

## 6. Capability Detection & Fail-Closed Boundary

To prevent silent failures or disguised compatibility:

| Classification | Behavior in Preview Runtime | Example Templates |
| :--- | :--- | :--- |
| **`NATIVE`** | Fully rendered directly in browser stage | `rui-title-card`, `rui-quote-card`, `rui-media-frame`, `rui-lower-third`, `rui-stat-card`, `rui-intro`, `rui-bento-pan` |
| **`ENGINE_BACKED`** | Explicit diagnostic error; throws if `failClosed: true`; renders warning badge | `rui-map-flight` (MapLibre WebGL), `scene3d-element` (3D Mesh), `particlesystem-element` (Physics spawner) |
| **`HYBRID`** | Explicit shader warning; fallback badge | WebGL GL transitions (`film-burn`, `ripple`, `crosswarp`) |
| **`LEGACY_COMPATIBILITY`** | Explicit legacy notification; deferred to R08/R09 renderer dispatch | `rui-browser-flow`, `rui-data-story`, `rui-hero-device-assemble` |
