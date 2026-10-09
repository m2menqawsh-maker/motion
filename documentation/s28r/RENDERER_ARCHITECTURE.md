# Renderer Architecture & Engine Decoupling Specification (S28-R08)

## 1. Executive Summary

Milestone **S28-R08** establishes the formal rendering abstraction layer for the video platform. It breaks the historical tight coupling between the canonical data model (`BlueprintV2` / `NormalizedVideo`) and specific rendering runtimes (such as Remotion or headless Chromium).

The architecture introduces a unidirectional rendering pipeline governed by a single authoritative registry:

```text
Canonical VideoDocument
           ↓
     RenderRequest
           ↓
   Renderer Registry
           ↓
   Renderer Selection  (Fail-Closed / Deterministic)
           ↓
    Renderer Adapter
           ↓
      RenderResult
```

---

## 2. Architectural Boundaries & Invariants

### 2.1 Engine Independence Invariant
The canonical core (`contracts/`) remains 100% agnostic to any concrete rendering framework.
- **Forbidden in `contracts/`**: `remotion`, `@remotion/*`, `react`, `react-dom`, `fluent-ffmpeg`, `@ffmpeg/*`, `canvas`, `jsdom`, `webgl`, `three`, `maplibre-gl`.
- **Allowed in `contracts/renderer.ts`**: Pure TypeScript contracts, Zod schemas, numeric algorithms, canonical capability derivation, error taxonomy, and registry dispatch logic.

### 2.2 Single Authority Invariant
There is exactly one authoritative entity responsible for registering, discovering, and selecting rendering engines:
- `CANONICAL_RENDERER_REGISTRY` (an instance of `RendererRegistry`).
- Individual tools, CLI scripts, and UI components MUST NOT instantiate private competing registries or hard-code renderer selection hacks.

### 2.3 Strict Fail-Closed Execution
- When a document requires capabilities (e.g. `map`, `webgl`, `particles`, `audio_ducking`) that no registered renderer supports, the system MUST throw `NoCompatibleRendererError` (`NO_COMPATIBLE_RENDERER`).
- **Zero Silent Fallback**: The system is strictly forbidden from falling back to an incomplete renderer that silently ignores unsupported layers, effects, or audio ducking plans.

---

## 3. Core Contract Specifications

### 3.1 `RendererCapabilities`
An immutable, queryable container representing the capabilities declared by a renderer adapter:
- `has(capability: string): boolean`
- `hasAll(capabilities: Iterable<string>): boolean`
- `getMissing(required: Iterable<string>): CanonicalRendererCapability[]`
- `toArray(): CanonicalRendererCapability[]`

### 3.2 `RenderRequest`
A strongly validated request structure encapsulating:
- `id`: Unique request trace identifier.
- `document`: Canonical `BlueprintV2` video document.
- `type`: `"frame"` | `"sequence"` | `"export"`.
- `frame` / `timeRange`: Target frame or discrete frame boundary.
- `output`: Dimensions, format, path, and quality configurations.
- `requiredCapabilities`: Explicit or auto-derived list of needed engine capabilities.
- `preferredRendererId`: Optional explicit renderer request (validated strictly).
- `context`: Operational execution context (logger, abort signal, temp storage).

### 3.3 `RendererAdapter`
The standardized contract implemented by concrete rendering engines:
```typescript
export interface RendererAdapter {
  readonly id: string;
  readonly name: string;
  readonly version: string;
  readonly priority?: number;

  capabilities(): RendererCapabilities;
  canRender(request: RenderRequest): RendererCanRenderResult;
  renderFrame(request: RenderRequest, context?: RenderContext): Promise<RenderResult>;
  renderSequence(request: RenderRequest, context?: RenderContext): Promise<RenderResult>;
  exportVideo(request: RenderRequest, context?: RenderContext): Promise<RenderResult>;
}
```

### 3.4 `RenderResult`
The unified response structure:
- `ok`: Boolean indicating successful completion.
- `requestId`: Matching request identifier.
- `rendererId`: Identifier of the executing adapter.
- `type`: Execution mode.
- `output`: Generated buffer, data URL, file path, or dimensions.
- `metrics`: Render time in milliseconds, peak memory, and evaluated frame count.
- `error`: Structured `RendererError` details if `ok` is false.

---

## 4. Engine Relationships

### 4.1 Remotion Architecture Placement
- **Role**: Remotion is an external rendering engine that provides high-throughput video encoding (`exportVideo`), sequence rendering (`renderSequence`), and still frame capture (`renderFrame`).
- **Decoupling**: Remotion does NOT govern canonical document schemas, editor session state, mutations, timeline math, or waveform calculations.
- **Production Implementation (S28-R09)**: `RemotionRendererAdapter` replaces `RemotionRendererAdapterStub`. It consumes canonical documents via `CanonicalVideo.tsx` using `evaluateVideoAtFrame()` to evaluate all layer types, keyframes, transitions, and dynamic audio ducking. It declares production capabilities strictly (`REMOTION_SUPPORTED_CAPABILITIES`) and fails closed on unsupported engine capabilities.

### 4.3 Canvas Headless Renderer Adapter (S28-R10)
- **Role**: Lightweight, high-speed 2D vector canvas engine (`CanvasRendererAdapter`).
- **Use Case**: Sub-second frame previews, discrete sequence captures, and lightweight video exports.
- **Capabilities**: Full 2D visual primitives (`text`, `image`, `shapes`, `groups`, `alpha`, `keyframes`, `transitions`), frame rendering, sequence rendering, video export.
- **Exclusions**: Strictly excludes `video`, `map`, `3d`, `particles`, `custom_shaders`.
- **Authority**: Subordinated entirely to canonical `BlueprintV2` and `evaluateVideoAtFrame()`.

### 4.4 Multi-Renderer Selection & Deterministic Dispatch (S28-R10)
When multiple real rendering engines are registered in `CANONICAL_RENDERER_REGISTRY`, selection is deterministic and capability-driven:
1. `canRender()` filters out all adapters that lack required capabilities.
2. If multiple adapters qualify, tie-breaking sorts by:
   - Priority descending (`CanvasRendererAdapter` = 110, `RemotionRendererAdapter` = 100).
   - Supported capability count descending.
   - Renderer ID lexicographical ascending.
3. If no registered renderer satisfies all requirements, throws `NoCompatibleRendererError` (`NO_COMPATIBLE_RENDERER`).
4. Silent degradation or engine branching outside `RendererRegistry` is strictly prohibited.

---

## 5. Structured Error Taxonomy

| Error Code | Class | Semantics |
| :--- | :--- | :--- |
| `RENDERER_NOT_FOUND` | `RendererNotFoundError` | An explicitly requested renderer ID does not exist in the registry. |
| `NO_COMPATIBLE_RENDERER` | `NoCompatibleRendererError` | No registered renderer satisfies all required capabilities of the request. |
| `UNSUPPORTED_CAPABILITY` | `UnsupportedCapabilityError` | A specific renderer was invoked but lacks one or more required capabilities. |
| `INVALID_RENDER_REQUEST` | `InvalidRenderRequestError` | The render request failed schema validation or parameter invariants. |
| `RENDER_FAILED` | `RenderFailedError` | Runtime failure during render execution within the adapter. |
| `DUPLICATE_RENDERER_ID` | `DuplicateRendererError` | Attempted to register two adapters sharing the same ID. |
