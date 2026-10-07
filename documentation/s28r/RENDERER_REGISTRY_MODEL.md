# Renderer Registry & Selection Model Specification (S28-R08)

## 1. Registry Architecture

The `RendererRegistry` is the authoritative subsystem responsible for managing renderer adapters and matching render requests to compatible execution engines.

### 1.1 Structural Invariants
1. **Zero Execution Logic**: The registry does NOT render pixels, spawn worker threads, or transcode streams. Rendering logic remains strictly encapsulated inside individual `RendererAdapter` implementations.
2. **Zero Mutation Logic**: The registry treats incoming canonical documents as immutable read-only state.
3. **Single Authority**: `CANONICAL_RENDERER_REGISTRY` in `contracts/renderer.ts` is the single system authority.

---

## 2. Registry API & Lifecycle

```typescript
class RendererRegistry {
  register(adapter: RendererAdapter): void;
  unregister(id: string): boolean;
  has(id: string): boolean;
  get(id: string): RendererAdapter | undefined;
  lookup(id: string): RendererAdapter | undefined;
  requireRenderer(id: string): RendererAdapter;
  list(): RendererAdapter[];
  listRendererIds(): string[];
  listCapabilities(rendererId?: string): CanonicalRendererCapability[];
  clear(): void;

  selectRenderer(request: RenderRequest, options?: RendererSelectionOptions): RendererAdapter;
}
```

### 2.1 Registration Invariants
- **Validation**: Rejects invalid, null, or malformed adapter objects with `InvalidRenderRequestError`.
- **Unique Identifiers**: Registering two adapters with identical `id` fields immediately throws `DuplicateRendererError` (`DUPLICATE_RENDERER_ID`). Silent overwrites are forbidden.

---

## 3. Deterministic Selection Policy

The selection algorithm guarantees 100% reproducible results given identical registry states and render requests:

```text
Incoming RenderRequest
          │
          ▼
Derive or Inspect Required Capabilities
          │
          ▼
Target Preferred Renderer specified?
 ├─ YES ──► Lookup Preferred Adapter
 │           ├─ Compatible? ────────► Select & Return Preferred Adapter
 │           └─ Incompatible? ──────► THROW UnsupportedCapabilityError (Fail-Closed)
 │
 └─ NO ───► Filter All Registered Adapters where canRender(req) == TRUE
             │
             ├─ Matching Adapters Count == 0?
             │   └─► THROW NoCompatibleRendererError (NO_COMPATIBLE_RENDERER)
             │
             └─ Matching Adapters Count > 0?
                 │
                 ▼
                 Deterministic Tie-Breaking Sort:
                 1. adapter.priority (DESC)
                 2. adapter.capabilities().count (DESC)
                 3. adapter.id (ASC, lexicographical)
                 │
                 ▼
                 Select & Return Top Adapter
```

---

## 4. Rejection Diagnostics & Structured Failures

When selection fails, the registry constructs structured diagnostic metadata to facilitate debugging without guesswork:

```json
{
  "code": "NO_COMPATIBLE_RENDERER",
  "details": {
    "requiredCapabilities": ["text", "map", "webgl", "frame_rendering"],
    "availableRendererIds": ["canvas-2d-renderer"],
    "candidateRejections": [
      {
        "rendererId": "canvas-2d-renderer",
        "missingCapabilities": ["map", "webgl"],
        "reason": "Missing capabilities: map, webgl"
      }
    ]
  }
}
```
