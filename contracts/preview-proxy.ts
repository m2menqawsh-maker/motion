/**
 * contracts/preview-proxy.ts — Canonical Preview Proxy Request & Artifact Contracts.
 * S28-R07B: Authoritative contracts for generating, storing, and consuming low-resolution
 * preview proxies via the Canonical Renderer Registry.
 * 
 * Strict Architectural Invariants:
 *   - ZERO concrete renderer references (no Remotion, Canvas, React imports).
 *   - Deterministic content fingerprinting.
 *   - Explicit resolution, quality, and capability policies.
 */

import * as crypto from "crypto";
import { z } from "zod";
import type { BlueprintV2 } from "./blueprint";
import {
  type CanonicalRendererCapability,
  type RenderContext,
} from "./renderer";

// ────────────────────────────────────────────────────────────────────────────
// 1. Proxy Quality Policy & Presets
// ────────────────────────────────────────────────────────────────────────────

export const ProxyFormatSchema = z.enum(["png", "jpeg", "webp", "mp4"]);
export type ProxyFormat = z.infer<typeof ProxyFormatSchema>;

export interface ProxyQualityPolicy {
  name: string;
  resolutionScale: number; // 0.1 to 1.0
  targetFps: number;
  quality: number; // 1 to 100
  format: ProxyFormat;
  maxDimension?: { width: number; height: number };
}

export const PREVIEW_PROXY_QUALITY_PRESETS: Record<string, ProxyQualityPolicy> = {
  low: {
    name: "low",
    resolutionScale: 0.25,
    targetFps: 15,
    quality: 40,
    format: "jpeg",
    maxDimension: { width: 480, height: 270 },
  },
  balanced: {
    name: "balanced",
    resolutionScale: 0.5,
    targetFps: 30,
    quality: 65,
    format: "png",
    maxDimension: { width: 960, height: 540 },
  },
  high: {
    name: "high",
    resolutionScale: 0.75,
    targetFps: 30,
    quality: 85,
    format: "png",
    maxDimension: { width: 1440, height: 810 },
  },
};

export const DEFAULT_PROXY_QUALITY_POLICY: ProxyQualityPolicy = PREVIEW_PROXY_QUALITY_PRESETS.balanced;

/**
 * Calculates scaled pixel dimensions respecting aspect ratio and ensuring even integers.
 */
export function resolveProxyDimensions(
  base: { width: number; height: number },
  policy: ProxyQualityPolicy = DEFAULT_PROXY_QUALITY_POLICY
): { width: number; height: number } {
  let targetW = Math.round(base.width * policy.resolutionScale);
  let targetH = Math.round(base.height * policy.resolutionScale);

  if (policy.maxDimension) {
    if (targetW > policy.maxDimension.width) {
      const scale = policy.maxDimension.width / targetW;
      targetW = policy.maxDimension.width;
      targetH = Math.round(targetH * scale);
    }
    if (targetH > policy.maxDimension.height) {
      const scale = policy.maxDimension.height / targetH;
      targetH = policy.maxDimension.height;
      targetW = Math.round(targetW * scale);
    }
  }

  // Ensure even dimensions (required for many video/image encoders)
  targetW = Math.max(2, Math.floor(targetW / 2) * 2);
  targetH = Math.max(2, Math.floor(targetH / 2) * 2);

  return { width: targetW, height: targetH };
}

// ────────────────────────────────────────────────────────────────────────────
// 2. Canonical Content Fingerprinting
// ────────────────────────────────────────────────────────────────────────────

/**
 * Deterministically computes a SHA-256 fingerprint of any canonical fragment or object.
 */
export function computeFragmentFingerprint(fragment: unknown): string {
  const normalizedJson = JSON.stringify(fragment, (_key, val) => {
    // Sort object keys for strict determinism
    if (val && typeof val === "object" && !Array.isArray(val)) {
      return Object.keys(val)
        .sort()
        .reduce((sorted: Record<string, unknown>, k) => {
          sorted[k] = val[k];
          return sorted;
        }, {});
    }
    return val;
  });

  return crypto.createHash("sha256").update(normalizedJson || "").digest("hex").slice(0, 32);
}

// ────────────────────────────────────────────────────────────────────────────
// 3. Preview Proxy Request Contract
// ────────────────────────────────────────────────────────────────────────────

export interface PreviewProxyEntity {
  type: "scene" | "layer" | "fragment" | "document";
  sceneId?: string;
  layerId?: string;
  templateId?: string;
}

export interface PreviewProxyRequest {
  id: string;
  project_id: string;
  canonical_revision: number;
  entity: PreviewProxyEntity;
  timeRange: {
    startFrame: number;
    endFrame: number;
  };
  requiredCapabilities: CanonicalRendererCapability[];
  width: number;
  height: number;
  fps: number;
  quality: number;
  format: ProxyFormat;
  contentFingerprint: string;
  schemaVersion: string;
  context?: RenderContext;
  metadata?: Record<string, unknown>;
}

export const PROXY_SCHEMA_VERSION = "2.0.0";

export function createPreviewProxyRequest(params: {
  id?: string;
  project_id: string;
  canonical_revision: number;
  entity: PreviewProxyEntity;
  timeRange?: { startFrame: number; endFrame: number };
  requiredCapabilities: CanonicalRendererCapability[];
  baseDimensions?: { width: number; height: number };
  policy?: ProxyQualityPolicy;
  contentFragment: unknown;
  context?: RenderContext;
  metadata?: Record<string, unknown>;
}): PreviewProxyRequest {
  const policy = params.policy ?? DEFAULT_PROXY_QUALITY_POLICY;
  const baseDim = params.baseDimensions ?? { width: 1920, height: 1080 };
  const scaledDim = resolveProxyDimensions(baseDim, policy);
  const timeRange = params.timeRange ?? { startFrame: 0, endFrame: 0 };
  const fingerprint = computeFragmentFingerprint(params.contentFragment);

  const reqId =
    params.id ??
    `proxy-req-${params.project_id}-rev${params.canonical_revision}-${fingerprint.slice(0, 8)}`;

  return {
    id: reqId,
    project_id: params.project_id,
    canonical_revision: params.canonical_revision,
    entity: params.entity,
    timeRange,
    requiredCapabilities: params.requiredCapabilities,
    width: scaledDim.width,
    height: scaledDim.height,
    fps: policy.targetFps,
    quality: policy.quality,
    format: policy.format,
    contentFingerprint: fingerprint,
    schemaVersion: PROXY_SCHEMA_VERSION,
    context: params.context,
    metadata: params.metadata,
  };
}

// ────────────────────────────────────────────────────────────────────────────
// 4. Preview Proxy Artifact Contract
// ────────────────────────────────────────────────────────────────────────────

export interface PreviewProxyArtifactOutput {
  filePath?: string;
  dataUrl?: string;
  buffer?: Uint8Array;
  mimeType?: string;
}

export interface PreviewProxyArtifact {
  id: string;
  requestId: string;
  cacheKey: string;
  project_id: string;
  canonical_revision: number;
  entity: PreviewProxyEntity;
  timeRange: {
    startFrame: number;
    endFrame: number;
  };
  width: number;
  height: number;
  fps: number;
  format: ProxyFormat;
  rendererId: string;
  output: PreviewProxyArtifactOutput;
  createdAt: number;
  sizeBytes: number;
  stale?: boolean;
  metadata?: Record<string, unknown>;
}
