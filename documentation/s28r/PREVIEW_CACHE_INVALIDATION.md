# Preview Proxy Cache & Invalidation Architecture

**Status**: Verified Reality Specification  
**Milestone**: S28-R07B (Preview Fidelity, Cache & Proxy System)  
**Contract Source**: [`preview/proxy/proxy-cache.ts`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/preview/proxy/proxy-cache.ts)  

---

## 1. Overview & Problem Definition

In interactive video editing, proxy generation is an asynchronous, computationally intensive process. Without fine-grained cache invalidation:
1. Every small edit (e.g. typing a letter in Scene 1) would wipe out all generated proxies across the entire timeline, forcing costly re-renders of Scene 2, 3, etc.
2. In-flight render jobs initiated on an older document revision might complete and overwrite a newer document state, causing visual regressions (stale overwrites).

To solve both problems, [`PreviewProxyCache`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/preview/proxy/proxy-cache.ts) implements deterministic cache keys, dependency tracking, selective [`ChangeSet`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/contracts/mutations.ts) invalidation, and strict stale revision protection.

---

## 2. Deterministic Cache Keys

Every cache key is deterministically generated from the immutable characteristics of the requested fragment:

```typescript
export function computeProxyCacheKey(params: {
  projectId: string;
  canonicalRevision: number;
  contentFingerprint: string;
  sceneId?: string;
  layerId?: string;
  timeRange?: TimeRange;
  requiredCapabilities: readonly string[];
  width: number;
  height: number;
  quality: string;
  format: string;
}): string;
```

### Key Components:
- **`projectId` & `canonicalRevision`**: Scope to document lifecycle.
- **`contentFingerprint`**: SHA-256 hash of the canonical JSON fragment (scenes, layers, keyframes, typography).
- **`sceneId` / `layerId`**: Granular entity scoping.
- **`timeRange`**: `[startFrame, endFrame]` temporal boundary.
- **`requiredCapabilities`**: Sorted capability requirements.
- **`width`, `height`, `quality`, `format`**: Render resolution and encoding profile.
- **`schemaVersion`**: Invalidates cache automatically across schema breaking changes.

---

## 3. Dependency Tracking & Bounded LRU Storage

### 3.1 Dependency Metadata
Each cached proxy artifact records its exact dependency graph:

```typescript
export interface ProxyDependencies {
  readonly sceneIds: readonly string[];
  readonly layerIds: readonly string[];
  readonly assetIds: readonly string[];
  readonly timeRange?: TimeRange;
  readonly canonicalRevision: number;
  readonly requiredCapabilities: readonly string[];
}
```

### 3.2 Bounded Eviction Policy
To prevent memory leaks and uncontrolled disk usage, the cache enforces strict bounds:
- **`maxEntries`** (default: 100 entries)
- **`maxSizeBytes`** (default: 50 MB)
- **Policy**: Least Recently Used (LRU).
  - Every `get()` updates `lastAccessedAt`.
  - When either entry count or byte size exceeds limits, the oldest unaccessed entries are evicted and discarded.

---

## 4. Selective `ChangeSet` Invalidation

When an editor mutation occurs, [`EditorSession`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/contracts/editor-session.ts) produces a canonical [`ChangeSet`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/contracts/mutations.ts) detailing modified scenes, layers, assets, and temporal ranges.

```text
Editor Mutation (e.g. UPDATE_LAYER in Scene A)
                    │
                    ▼
          ChangeSet Generated
   scenesUpdated: ["scene_a"]
   layersUpdated: ["layer_text_1"]
                    │
                    ▼
     invalidateByChangeSet(changeSet)
                    │
       ┌────────────┴────────────┐
       ▼                         ▼
   Proxy for Scene A         Proxy for Scene B
   (Matches scene_a)         (Unrelated to scene_a)
       │                         │
       ▼                         ▼
   [EVICTED]                 [PRESERVED]
```

### Invalidation Logic:
A cached entry is invalidated if and only if:
1. `entry.dependencies.sceneIds` intersects `changeSet.scenesUpdated` or `changeSet.scenesRemoved`.
2. `entry.dependencies.layerIds` intersects `changeSet.layersUpdated` or `changeSet.layersRemoved`.
3. `entry.dependencies.assetIds` intersects `changeSet.assetsUpdated` or `changeSet.assetsRemoved`.
4. `entry.dependencies.timeRange` overlaps with `changeSet.affectedTimeRange`.

All other unaffected proxies remain intact and instantly valid.

---

## 5. Stale Result Protection

### The Race Condition:
1. User is on Revision $R_{20}$.
2. A proxy job $J_1$ is queued for an engine-backed element at $R_{20}$.
3. User types a change or moves a playhead property, advancing document to Revision $R_{21}$.
4. Job $J_1$ finishes execution.
5. **DANGER**: If $J_1$ installs its rendered artifact into the preview player, it would overwrite Revision $R_{21}$ with the obsolete appearance of Revision $R_{20}$.

### Fail-Closed Resolution:
1. **Revision Tracking**: [`PreviewProxyCoordinator`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/preview/proxy/proxy-coordinator.ts) maintains `currentRevision`.
2. **Pre-Dispatch & Post-Render Guard**:
   - When a job completes, the coordinator checks:
     ```typescript
     if (this.currentRevision > job.request.canonicalRevision) {
       job.status = "stale";
       throw new Error(`STALE_RESULT: Proxy rendered for revision ${job.request.canonicalRevision} but document is at revision ${this.currentRevision}`);
     }
     ```
3. **Runtime Invalidation Guard**:
   - [`BrowserPreviewRuntime`](file:///home/eng_Momen/Projects/المشروع%20الحالي/Video%20maker/preview/preview-runtime.ts) rejects artifacts where `artifact.canonicalRevision < this.document.revision`.
4. **Cancellation**:
   - Calling `coordinator.updateCurrentRevision(nextRevision)` automatically aborts active in-flight jobs matching older revisions, preventing wasted CPU cycles.
