/**
 * preview/proxy/proxy-cache.ts — Bounded Preview Proxy Cache & Selective Invalidation Engine.
 * S28-R07B: In-memory LRU cache storing low-resolution preview proxy artifacts.
 * 
 * Invariants:
 *   - Strictly bounded by maxEntries (count) and maxBytes (memory size).
 *   - Deterministic cache key based on revision, fingerprint, entity, resolution, capabilities.
 *   - Fine-grained dependency tracking (sceneIds, layerIds, assetIds, timeRange).
 *   - Selective ChangeSet invalidation: mutating Scene A does NOT invalidate Scene B proxies.
 *   - Zero mutation of canonical video documents.
 */

import type { ChangeSet } from "../../contracts/mutations";
import type {
  PreviewProxyArtifact,
  PreviewProxyEntity,
} from "../../contracts/preview-proxy";
import type { CanonicalRendererCapability } from "../../contracts/renderer";

export interface ProxyDependencyInfo {
  projectId: string;
  canonicalRevision: number;
  contentFingerprint: string;
  sceneIds: string[];
  layerIds: string[];
  assetIds: string[];
  timeRange: { startFrame: number; endFrame: number };
  requiredCapabilities: CanonicalRendererCapability[];
}

export interface CacheKeyParams {
  projectId: string;
  canonicalRevision: number;
  contentFingerprint: string;
  entity: PreviewProxyEntity;
  timeRange: { startFrame: number; endFrame: number };
  requiredCapabilities: CanonicalRendererCapability[];
  width: number;
  height: number;
  quality: number;
  schemaVersion?: string;
}

/**
 * Computes a deterministic cache key for a proxy request.
 */
export function computeProxyCacheKey(params: CacheKeyParams): string {
  const entityKey = params.entity.sceneId
    ? `scene:${params.entity.sceneId}`
    : params.entity.layerId
    ? `layer:${params.entity.layerId}`
    : `${params.entity.type}:${params.entity.templateId || "root"}`;

  const capsKey = [...params.requiredCapabilities].sort().join(",");
  const timeKey = `${params.timeRange.startFrame}-${params.timeRange.endFrame}`;
  const resKey = `${params.width}x${params.height}@q${params.quality}`;
  const vKey = params.schemaVersion ? `v${params.schemaVersion}` : "v2";

  return `proxy:${params.projectId}:r${params.canonicalRevision}:${entityKey}:${timeKey}:${resKey}:caps[${capsKey}]:fp[${params.contentFingerprint}]:${vKey}`;
}

export interface PreviewProxyCacheOptions {
  maxEntries?: number;
  maxBytes?: number; // total output buffer / string size limit
}

export interface CacheStats {
  hits: number;
  misses: number;
  entries: number;
  totalBytes: number;
  evictions: number;
  invalidations: number;
}

interface CacheNode {
  key: string;
  artifact: PreviewProxyArtifact;
  dependencies: ProxyDependencyInfo;
  sizeBytes: number;
}

export class PreviewProxyCache {
  private readonly maxEntries: number;
  private readonly maxBytes: number;

  // Map preserving LRU insertion order (re-insert on access moves to most-recent)
  private readonly store = new Map<string, CacheNode>();

  private stats: CacheStats = {
    hits: 0,
    misses: 0,
    entries: 0,
    totalBytes: 0,
    evictions: 0,
    invalidations: 0,
  };

  constructor(options?: PreviewProxyCacheOptions) {
    this.maxEntries = options?.maxEntries ?? 100;
    this.maxBytes = options?.maxBytes ?? 50 * 1024 * 1024; // 50MB default
  }

  /**
   * Retrieves a cached proxy artifact by key, promoting it in LRU order.
   */
  public get(key: string): PreviewProxyArtifact | undefined {
    const node = this.store.get(key);
    if (!node) {
      this.stats.misses++;
      return undefined;
    }

    if (node.artifact.stale) {
      // Discard stale entry
      this.delete(key);
      this.stats.misses++;
      return undefined;
    }

    // Refresh LRU order: delete and re-insert at end
    this.store.delete(key);
    this.store.set(key, node);

    this.stats.hits++;
    return node.artifact;
  }

  /**
   * Stores a proxy artifact and its dependencies into cache, evicting oldest entries if limits reached.
   */
  public set(
    key: string,
    artifact: PreviewProxyArtifact,
    dependencies: ProxyDependencyInfo
  ): void {
    if (this.store.has(key)) {
      this.delete(key);
    }

    const sizeBytes = artifact.sizeBytes > 0
      ? artifact.sizeBytes
      : artifact.output.buffer?.byteLength ?? (artifact.output.dataUrl?.length ?? 1024);

    // Evict entries if capacity exceeded
    while (
      (this.store.size >= this.maxEntries ||
        (this.stats.totalBytes + sizeBytes > this.maxBytes && this.store.size > 0)) &&
      this.store.size > 0
    ) {
      this.evictOldest();
    }

    const node: CacheNode = {
      key,
      artifact: { ...artifact, cacheKey: key },
      dependencies,
      sizeBytes,
    };

    this.store.set(key, node);
    this.stats.entries = this.store.size;
    this.stats.totalBytes += sizeBytes;
  }

  public has(key: string): boolean {
    const node = this.store.get(key);
    return !!node && !node.artifact.stale;
  }

  public delete(key: string): boolean {
    const node = this.store.get(key);
    if (!node) return false;

    this.store.delete(key);
    this.stats.entries = this.store.size;
    this.stats.totalBytes = Math.max(0, this.stats.totalBytes - node.sizeBytes);
    return true;
  }

  public clear(): void {
    this.store.clear();
    this.stats.entries = 0;
    this.stats.totalBytes = 0;
  }

  public getStats(): Readonly<CacheStats> {
    return { ...this.stats };
  }

  public size(): number {
    return this.store.size;
  }

  public getDependencies(key: string): ProxyDependencyInfo | undefined {
    return this.store.get(key)?.dependencies;
  }

  // ────────────────────────────────────────────────────────────────────────────
  // Selective Invalidation Engine (R04 ChangeSet Integration)
  // ────────────────────────────────────────────────────────────────────────────

  /**
   * Selectively invalidates cached entries affected by an R04 ChangeSet.
   * Modifying Scene A will NOT invalidate proxies for Scene B.
   */
  public invalidateByChangeSet(changeSet: ChangeSet, currentRevision?: number): number {
    let invalidatedCount = 0;
    const affectedScenes = new Set(changeSet.affected_scene_ids || []);
    const affectedLayers = new Set(changeSet.affected_layer_ids || []);
    const timeRange = changeSet.time_range;
    const requiresTimelineRebuild = changeSet.invalidation?.requires_timeline_rebuild;

    const keysToInvalidate: string[] = [];

    for (const [key, node] of this.store.entries()) {
      const deps = node.dependencies;

      // 1. Revision mismatch check
      if (currentRevision !== undefined && deps.canonicalRevision < currentRevision) {
        // If the document advanced, check if this specific entity was affected
        // or if it requires rebuild
      }

      // 2. Timeline rebuild invalidates all temporal sequences
      if (requiresTimelineRebuild) {
        keysToInvalidate.push(key);
        continue;
      }

      // 3. Scene match
      const sceneMatches = deps.sceneIds.some((sId) => affectedScenes.has(sId));
      if (sceneMatches) {
        keysToInvalidate.push(key);
        continue;
      }

      // 4. Layer match
      const layerMatches = deps.layerIds.some((lId) => affectedLayers.has(lId));
      if (layerMatches) {
        keysToInvalidate.push(key);
        continue;
      }

      // 5. Time range overlap check (if time range defined)
      if (timeRange && deps.timeRange) {
        const hasTimeOverlap =
          deps.timeRange.startFrame <= timeRange.endFrame &&
          deps.timeRange.endFrame >= timeRange.startFrame;
        // Only invalidate if there is also an affected entity or layout change
        if (hasTimeOverlap && (changeSet.invalidation?.requires_render || changeSet.invalidation?.requires_layout)) {
          // If no specific entity targeted but time overlaps
          if (affectedScenes.size === 0 && affectedLayers.size === 0) {
            keysToInvalidate.push(key);
            continue;
          }
        }
      }
    }

    for (const key of keysToInvalidate) {
      this.delete(key);
      invalidatedCount++;
    }

    this.stats.invalidations += invalidatedCount;
    return invalidatedCount;
  }

  /**
   * Invalidates all proxies depending on a specific scene ID.
   */
  public invalidateBySceneId(sceneId: string): number {
    let count = 0;
    const keys: string[] = [];
    for (const [key, node] of this.store.entries()) {
      if (node.dependencies.sceneIds.includes(sceneId)) {
        keys.push(key);
      }
    }
    for (const k of keys) {
      this.delete(k);
      count++;
    }
    this.stats.invalidations += count;
    return count;
  }

  /**
   * Invalidates all proxies depending on a specific layer ID.
   */
  public invalidateByLayerId(layerId: string): number {
    let count = 0;
    const keys: string[] = [];
    for (const [key, node] of this.store.entries()) {
      if (node.dependencies.layerIds.includes(layerId)) {
        keys.push(key);
      }
    }
    for (const k of keys) {
      this.delete(k);
      count++;
    }
    this.stats.invalidations += count;
    return count;
  }

  /**
   * Invalidates all proxies depending on a specific asset ID.
   */
  public invalidateByAssetId(assetId: string): number {
    let count = 0;
    const keys: string[] = [];
    for (const [key, node] of this.store.entries()) {
      if (node.dependencies.assetIds.includes(assetId)) {
        keys.push(key);
      }
    }
    for (const k of keys) {
      this.delete(k);
      count++;
    }
    this.stats.invalidations += count;
    return count;
  }

  /**
   * Invalidates all proxies overlapping a frame/time range.
   */
  public invalidateByTimeRange(range: { startFrame: number; endFrame: number }): number {
    let count = 0;
    const keys: string[] = [];
    for (const [key, node] of this.store.entries()) {
      const tr = node.dependencies.timeRange;
      if (tr.startFrame <= range.endFrame && tr.endFrame >= range.startFrame) {
        keys.push(key);
      }
    }
    for (const k of keys) {
      this.delete(k);
      count++;
    }
    this.stats.invalidations += count;
    return count;
  }

  private evictOldest(): void {
    const oldestKey = this.store.keys().next().value;
    if (oldestKey) {
      const node = this.store.get(oldestKey);
      if (node) {
        this.store.delete(oldestKey);
        this.stats.entries = this.store.size;
        this.stats.totalBytes = Math.max(0, this.stats.totalBytes - node.sizeBytes);
        this.stats.evictions++;
      }
    }
  }
}
