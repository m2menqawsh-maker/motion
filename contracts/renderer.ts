/**
 * contracts/renderer.ts — Canonical Renderer Contracts, Capability Model & Engine Registry.
 * S28-R08: Authoritative renderer abstraction decoupling canonical video documents from rendering engines.
 * 
 * Flow:
 * Canonical VideoDocument -> Render Request -> Renderer Registry -> Renderer Selection -> Renderer Adapter -> Render Result
 * 
 * Enforces:
 *   - Strict engine-neutrality: ZERO React, Remotion, FFmpeg, Canvas, DOM or WebGL dependencies
 *   - Explicit structured capability taxonomy (visual, temporal, advanced graphics, audio subsystem)
 *   - Fail-closed deterministic renderer selection (NO silent fallbacks)
 *   - Single Renderer Authority via Canonical Renderer Registry
 *   - R05 engine-backed templates and R07 audio subsystem capability derivation
 */

import { z } from "zod";
import type { BlueprintV2, BlueprintScene } from "./blueprint";
import { getSemanticTemplateSpec } from "../registry/semantic-registry";

// ────────────────────────────────────────────────────────────────────────────
// 1. Authoritative Capability Taxonomy
// ────────────────────────────────────────────────────────────────────────────

export const CANONICAL_CAPABILITIES = [
  // Core Visual Primitives
  "text",
  "image",
  "video",
  "audio",
  "shapes",
  "groups",
  // Temporal & Motion
  "keyframes",
  "transitions",
  "alpha",
  // Advanced & Hardware-accelerated graphics
  "webgl",
  "3d",
  "particles",
  "map",
  "custom_shaders",
  // Audio Subsystem (R07 Integration)
  "audio_voiceover",
  "audio_music",
  "audio_sfx",
  "audio_mixing",
  "audio_ducking",
  "audio_timing",
  // Render Targets / Pipeline Modes
  "frame_rendering",
  "sequence_rendering",
  "export_video",
  "live_preview",
] as const;

export type CanonicalRendererCapability = (typeof CANONICAL_CAPABILITIES)[number];

export const RendererCapabilitySchema = z.enum(CANONICAL_CAPABILITIES);

export const CAPABILITY_ALIASES: Record<string, CanonicalRendererCapability> = {
  // Shaders
  "custom shaders": "custom_shaders",
  "custom_shader": "custom_shaders",
  "shaders": "custom_shaders",
  "shader": "custom_shaders",
  // Audio Subsystem Aliases
  "mixing": "audio_mixing",
  "audio mixing": "audio_mixing",
  "ducking": "audio_ducking",
  "audio ducking": "audio_ducking",
  "timing": "audio_timing",
  "audio timing": "audio_timing",
  "voiceover": "audio_voiceover",
  "audio voiceover": "audio_voiceover",
  "music": "audio_music",
  "audio music": "audio_music",
  "sfx": "audio_sfx",
  "audio sfx": "audio_sfx",
  // Engine-backed Template Requirements
  "maplibre-gl": "map",
  "maplibre": "map",
  "three": "3d",
  "three.js": "3d",
  "webgl_3d": "3d",
  "remotion-bits": "particles",
  "particle_simulation": "particles",
};

/**
 * Normalizes any recognized capability identifier or alias into its canonical form.
 */
export function normalizeCapability(cap: string): CanonicalRendererCapability {
  if (!cap || typeof cap !== "string") {
    throw new Error(`Invalid capability format: expected non-empty string, received ${typeof cap}`);
  }
  const clean = cap.trim().toLowerCase();
  if (clean in CAPABILITY_ALIASES) {
    return CAPABILITY_ALIASES[clean];
  }
  if ((CANONICAL_CAPABILITIES as readonly string[]).includes(clean)) {
    return clean as CanonicalRendererCapability;
  }
  // Replace space with underscore or vice-versa
  const under = clean.replace(/\s+/g, "_");
  if (under in CAPABILITY_ALIASES) {
    return CAPABILITY_ALIASES[under];
  }
  if ((CANONICAL_CAPABILITIES as readonly string[]).includes(under)) {
    return under as CanonicalRendererCapability;
  }
  return clean as CanonicalRendererCapability;
}

export type RendererCapability = CanonicalRendererCapability | keyof typeof CAPABILITY_ALIASES | string;

// ────────────────────────────────────────────────────────────────────────────
// 2. Structured Renderer Error Taxonomy
// ────────────────────────────────────────────────────────────────────────────

export const RendererErrorCodeSchema = z.enum([
  "RENDERER_NOT_FOUND",
  "NO_COMPATIBLE_RENDERER",
  "UNSUPPORTED_CAPABILITY",
  "INVALID_RENDER_REQUEST",
  "RENDER_FAILED",
  "DUPLICATE_RENDERER_ID",
]);
export type RendererErrorCode = z.infer<typeof RendererErrorCodeSchema>;

export class RendererError extends Error {
  public readonly code: RendererErrorCode;
  public readonly details: Record<string, unknown>;

  constructor(message: string, code: RendererErrorCode, details: Record<string, unknown> = {}) {
    super(`[${code}] ${message}`);
    this.name = "RendererError";
    this.code = code;
    this.details = details;
  }
}

export class RendererNotFoundError extends RendererError {
  constructor(message: string, details: Record<string, unknown> = {}) {
    super(message, "RENDERER_NOT_FOUND", details);
    this.name = "RendererNotFoundError";
  }
}

export class NoCompatibleRendererError extends RendererError {
  constructor(message: string, details: Record<string, unknown> = {}) {
    super(message, "NO_COMPATIBLE_RENDERER", details);
    this.name = "NoCompatibleRendererError";
  }
}

export class UnsupportedCapabilityError extends RendererError {
  constructor(message: string, details: Record<string, unknown> = {}) {
    super(message, "UNSUPPORTED_CAPABILITY", details);
    this.name = "UnsupportedCapabilityError";
  }
}

export class InvalidRenderRequestError extends RendererError {
  constructor(message: string, details: Record<string, unknown> = {}) {
    super(message, "INVALID_RENDER_REQUEST", details);
    this.name = "InvalidRenderRequestError";
  }
}

export class RenderFailedError extends RendererError {
  constructor(message: string, details: Record<string, unknown> = {}) {
    super(message, "RENDER_FAILED", details);
    this.name = "RenderFailedError";
  }
}

export class DuplicateRendererError extends RendererError {
  constructor(message: string, details: Record<string, unknown> = {}) {
    super(message, "DUPLICATE_RENDERER_ID", details);
    this.name = "DuplicateRendererError";
  }
}

// ────────────────────────────────────────────────────────────────────────────
// 3. Renderer Capabilities Model
// ────────────────────────────────────────────────────────────────────────────

export interface RendererCapabilitiesInit {
  supported: Iterable<string>;
  maxResolution?: { width: number; height: number };
  supportedFormats?: string[];
  supportedCodecs?: string[];
  maxFps?: number;
  metadata?: Record<string, unknown>;
}

export class RendererCapabilities {
  private readonly _supported: Set<CanonicalRendererCapability>;
  public readonly maxResolution?: { width: number; height: number };
  public readonly supportedFormats: readonly string[];
  public readonly supportedCodecs: readonly string[];
  public readonly maxFps?: number;
  public readonly metadata: Readonly<Record<string, unknown>>;

  constructor(init: RendererCapabilitiesInit) {
    this._supported = new Set();
    for (const cap of init.supported) {
      this._supported.add(normalizeCapability(cap));
    }
    this.maxResolution = init.maxResolution;
    this.supportedFormats = Object.freeze([...(init.supportedFormats ?? [])]);
    this.supportedCodecs = Object.freeze([...(init.supportedCodecs ?? [])]);
    this.maxFps = init.maxFps;
    this.metadata = Object.freeze({ ...(init.metadata ?? {}) });
  }

  get supported(): ReadonlySet<CanonicalRendererCapability> {
    return this._supported;
  }

  has(capability: string): boolean {
    const normalized = normalizeCapability(capability);
    return this._supported.has(normalized);
  }

  hasAll(capabilities: Iterable<string>): boolean {
    for (const cap of capabilities) {
      if (!this.has(cap)) return false;
    }
    return true;
  }

  getMissing(required: Iterable<string>): CanonicalRendererCapability[] {
    const missing: CanonicalRendererCapability[] = [];
    for (const cap of required) {
      const norm = normalizeCapability(cap);
      if (!this._supported.has(norm)) {
        if (!missing.includes(norm)) {
          missing.push(norm);
        }
      }
    }
    return missing;
  }

  toArray(): CanonicalRendererCapability[] {
    return Array.from(this._supported);
  }
}

export function createRendererCapabilities(init: RendererCapabilitiesInit): RendererCapabilities {
  return new RendererCapabilities(init);
}

// ────────────────────────────────────────────────────────────────────────────
// 4. Render Request & Render Result Contracts
// ────────────────────────────────────────────────────────────────────────────

export const RenderRequestTypeSchema = z.enum(["frame", "sequence", "export"]);
export type RenderRequestType = z.infer<typeof RenderRequestTypeSchema>;

export const RenderOutputConfigSchema = z.object({
  format: z.string().optional(),
  path: z.string().optional(),
  width: z.number().int().positive().optional(),
  height: z.number().int().positive().optional(),
  fps: z.number().int().positive().optional(),
  quality: z.number().min(0).max(100).optional(),
  includeAudio: z.boolean().default(true),
});
export type RenderOutputConfig = z.infer<typeof RenderOutputConfigSchema>;

export interface RenderLogger {
  info(msg: string, ...args: any[]): void;
  warn(msg: string, ...args: any[]): void;
  error(msg: string, ...args: any[]): void;
}

export interface RenderContext {
  projectId: string;
  signal?: AbortSignal;
  logger?: RenderLogger;
  tempDir?: string;
  assetsDir?: string;
  resolveAsset?: (assetRef: string) => Promise<string> | string;
  timeBudgetMs?: number;
  metadata?: Record<string, unknown>;
}

export interface RenderRequest {
  id: string;
  document: BlueprintV2;
  type: RenderRequestType;
  frame?: number;
  timeRange?: {
    startFrame: number;
    endFrame: number;
  };
  output?: RenderOutputConfig;
  requiredCapabilities?: CanonicalRendererCapability[];
  preferredRendererId?: string;
  context?: RenderContext;
  metadata?: Record<string, unknown>;
}

export interface RenderOutput {
  buffer?: Uint8Array;
  dataUrl?: string;
  filePath?: string;
  mimeType?: string;
  frameCount?: number;
  durationMs?: number;
  width?: number;
  height?: number;
  data?: unknown;
}

export interface RenderMetrics {
  renderTimeMs: number;
  evaluatedFrames?: number;
  peakMemoryBytes?: number;
}

export interface RenderResult {
  ok: boolean;
  requestId: string;
  rendererId: string;
  type: RenderRequestType;
  output?: RenderOutput;
  metrics?: RenderMetrics;
  error?: {
    code: RendererErrorCode;
    message: string;
    details?: Record<string, unknown>;
  };
}

/**
 * Validates a RenderRequest fail-closed.
 */
export function validateRenderRequest(request: unknown): RenderRequest {
  if (!request || typeof request !== "object") {
    throw new InvalidRenderRequestError("RenderRequest must be a non-null object", { received: request });
  }

  const r = request as Partial<RenderRequest>;
  if (!r.id || typeof r.id !== "string") {
    throw new InvalidRenderRequestError("RenderRequest missing required non-empty string 'id'", { request });
  }

  if (!r.type || !["frame", "sequence", "export"].includes(r.type)) {
    throw new InvalidRenderRequestError(`RenderRequest 'type' must be 'frame', 'sequence', or 'export'. Received '${r.type}'`, { request });
  }

  if (!r.document || typeof r.document !== "object") {
    throw new InvalidRenderRequestError("RenderRequest missing canonical 'document'", { request });
  }

  if (!r.document.project_id || !r.document.fps || !Array.isArray(r.document.scenes)) {
    throw new InvalidRenderRequestError("RenderRequest document does not conform to BlueprintV2 structure", { request });
  }

  if (r.type === "frame") {
    if (r.frame === undefined || typeof r.frame !== "number" || !Number.isInteger(r.frame) || r.frame < 0) {
      throw new InvalidRenderRequestError(`Frame render request must specify a non-negative integer 'frame'. Received '${r.frame}'`, { request });
    }
  }

  if (r.type === "sequence") {
    if (!r.timeRange || typeof r.timeRange.startFrame !== "number" || typeof r.timeRange.endFrame !== "number") {
      throw new InvalidRenderRequestError("Sequence render request must specify 'timeRange' with startFrame and endFrame", { request });
    }
    if (r.timeRange.startFrame < 0 || r.timeRange.endFrame < r.timeRange.startFrame) {
      throw new InvalidRenderRequestError(
        `Sequence render request invalid timeRange: startFrame (${r.timeRange.startFrame}) must be >= 0 and <= endFrame (${r.timeRange.endFrame})`,
        { request }
      );
    }
  }

  return r as RenderRequest;
}

// ────────────────────────────────────────────────────────────────────────────
// 5. Capability Derivation Engine (R05 Templates & R07 Audio Integration)
// ────────────────────────────────────────────────────────────────────────────

const GL_TRANSITION_TYPES = new Set([
  "book-flip",
  "clock-wipe",
  "crosswarp",
  "dreamy-zoom",
  "film-burn",
  "linear-blur",
  "ripple",
  "zoom-blur",
]);

/**
 * Derives the exact set of canonical capabilities required to render a document.
 * Maps R05 engine-backed templates, transitions, layers, and R07 audio plans into formal requirements.
 */
export function deriveRequiredCapabilities(
  doc: BlueprintV2,
  requestType?: RenderRequestType
): CanonicalRendererCapability[] {
  const caps = new Set<CanonicalRendererCapability>();

  // 1. Pipeline execution mode
  if (requestType === "frame") {
    caps.add("frame_rendering");
  } else if (requestType === "sequence") {
    caps.add("sequence_rendering");
  } else if (requestType === "export") {
    caps.add("export_video");
  }

  const scenes: BlueprintScene[] = doc.scenes ?? [];

  // 2. Scenes & Visual Hierarchy
  for (const scene of scenes) {
    // Check template and engine-backed requirements (R05)
    if (scene.template) {
      const templateId = scene.template;
      if (templateId === "rui-map-flight") {
        caps.add("map");
        caps.add("webgl");
      } else if (templateId === "scene3d-element") {
        caps.add("3d");
        caps.add("webgl");
      } else if (templateId === "particlesystem-element") {
        caps.add("particles");
      }

      // Check TemplateSpec requirements in canonical registry
      const spec = getSemanticTemplateSpec(templateId);
      if (spec) {
        if (spec.classification === "ENGINE_BACKED" || spec.classification === "HYBRID") {
          const reqCaps = spec.requirements?.capabilities ?? [];
          for (const c of reqCaps) {
            const norm = normalizeCapability(c);
            caps.add(norm);
            if (norm === "map" || norm === "3d") {
              caps.add("webgl");
            }
          }
        }
      }
    }

    // Check transitions
    if (scene.transition) {
      caps.add("transitions");
      if (GL_TRANSITION_TYPES.has(scene.transition.type)) {
        caps.add("custom_shaders");
        caps.add("webgl");
      }
    }

    // Check surfaces / shapes
    if (scene.surface) {
      caps.add("shapes");
    }

    // Check content primitives
    if (scene.content) {
      if (scene.content.title || scene.content.subtitle || scene.content.body) {
        caps.add("text");
      }
      if (scene.content.media?.kind === "image") {
        caps.add("image");
      }
      if (scene.content.media?.kind === "video") {
        caps.add("video");
      }
    }

    // Check canonical layers
    if (Array.isArray(scene.layers)) {
      for (const layer of scene.layers) {
        if (layer.kind === "text") caps.add("text");
        if (layer.kind === "image") caps.add("image");
        if (layer.kind === "video") caps.add("video");
        if (layer.kind === "shape") caps.add("shapes");
        if (layer.kind === "group" || layer.parent_id) caps.add("groups");

        // Keyframe animations
        if (Array.isArray(layer.channels) && layer.channels.length > 0) {
          const hasKf = layer.channels.some((ch) => ch.keyframes && ch.keyframes.length > 0);
          if (hasKf) caps.add("keyframes");
        }

        // Alpha transparency
        if (layer.opacity !== undefined && layer.opacity < 1.0) {
          caps.add("alpha");
        }
        if (layer.transform?.opacity !== undefined && layer.transform.opacity < 1.0) {
          caps.add("alpha");
        }
      }
    }
  }

  // 3. Audio Subsystem Capabilities (R07 Integration)
  let audioStreamCount = 0;
  const audio = doc.audio;

  if (audio?.voiceover && (audio.voiceover.asset_ref || (audio.voiceover as any).file)) {
    caps.add("audio");
    caps.add("audio_voiceover");
    caps.add("audio_timing");
    audioStreamCount++;
  }

  if (audio?.music && (audio.music.asset_ref || (audio.music as any).file)) {
    caps.add("audio");
    caps.add("audio_music");
    caps.add("audio_timing");
    audioStreamCount++;

    // Audio ducking
    if (audio.music.ducking && audio.music.ducking.enabled !== false) {
      caps.add("audio_ducking");
      caps.add("audio_mixing");
    }
  }

  if (audio?.global_sfx && Array.isArray(audio.global_sfx) && audio.global_sfx.length > 0) {
    caps.add("audio");
    caps.add("audio_sfx");
    caps.add("audio_timing");
    audioStreamCount += audio.global_sfx.length;
  }

  // Scene audio layers
  for (const scene of scenes) {
    if (Array.isArray(scene.layers)) {
      for (const layer of scene.layers) {
        if (layer.kind === "audio") {
          caps.add("audio");
          caps.add("audio_timing");
          audioStreamCount++;
        }
      }
    }
  }

  // If multiple audio streams coexist, audio mixing capability is required
  if (audioStreamCount >= 2) {
    caps.add("audio_mixing");
  }

  return Array.from(caps);
}

// ────────────────────────────────────────────────────────────────────────────
// 6. Renderer Adapter Interface Contract
// ────────────────────────────────────────────────────────────────────────────

export interface RendererCanRenderResult {
  canRender: boolean;
  missingCapabilities: CanonicalRendererCapability[];
  reason?: string;
}

export interface RendererAdapter {
  readonly id: string;
  readonly name: string;
  readonly version: string;
  readonly priority?: number;

  /**
   * Returns the complete declared capabilities of this renderer.
   */
  capabilities(): RendererCapabilities;

  /**
   * Inspects whether this renderer can satisfy the given render request without silent fallbacks.
   */
  canRender(request: RenderRequest): RendererCanRenderResult;

  /**
   * Renders a single discrete frame.
   */
  renderFrame(request: RenderRequest, context?: RenderContext): Promise<RenderResult>;

  /**
   * Renders a sequence of discrete frames.
   */
  renderSequence(request: RenderRequest, context?: RenderContext): Promise<RenderResult>;

  /**
   * Exports a complete standalone video file.
   */
  exportVideo(request: RenderRequest, context?: RenderContext): Promise<RenderResult>;
}

// ────────────────────────────────────────────────────────────────────────────
// 7. Authoritative Renderer Registry & Selection Engine
// ────────────────────────────────────────────────────────────────────────────

export interface RendererSelectionOptions {
  preferredRendererId?: string;
  strictExplicitOnly?: boolean;
}

export class RendererRegistry {
  private readonly _adapters = new Map<string, RendererAdapter>();

  /**
   * Registers a renderer adapter into the registry.
   * Fails closed if adapter is invalid or if adapter with same ID is already registered.
   */
  register(adapter: RendererAdapter): void {
    if (!adapter || typeof adapter !== "object" || !adapter.id) {
      throw new InvalidRenderRequestError("Cannot register an invalid renderer adapter: missing ID or object");
    }
    if (this._adapters.has(adapter.id)) {
      throw new DuplicateRendererError(
        `Renderer with ID '${adapter.id}' is already registered. Duplicate renderer IDs are forbidden.`,
        { rendererId: adapter.id }
      );
    }
    this._adapters.set(adapter.id, adapter);
  }

  /**
   * Unregisters an adapter from the registry by ID.
   */
  unregister(id: string): boolean {
    return this._adapters.delete(id);
  }

  /**
   * Checks whether an adapter ID is registered.
   */
  has(id: string): boolean {
    return this._adapters.has(id);
  }

  /**
   * Looks up an adapter by ID. Returns undefined if not found.
   */
  get(id: string): RendererAdapter | undefined {
    return this._adapters.get(id);
  }

  /**
   * Alias for get().
   */
  lookup(id: string): RendererAdapter | undefined {
    return this.get(id);
  }

  /**
   * Requires a renderer adapter by ID, failing closed if not found.
   */
  requireRenderer(id: string): RendererAdapter {
    const adapter = this.get(id);
    if (!adapter) {
      throw new RendererNotFoundError(`Renderer with ID '${id}' is not registered in the Renderer Registry.`, {
        requestedId: id,
        availableRendererIds: this.listRendererIds(),
      });
    }
    return adapter;
  }

  /**
   * Lists all registered renderer adapters.
   */
  list(): RendererAdapter[] {
    return Array.from(this._adapters.values());
  }

  /**
   * Lists all registered renderer IDs.
   */
  listRendererIds(): string[] {
    return Array.from(this._adapters.keys());
  }

  /**
   * Lists capabilities across all renderers, or for a specific renderer.
   */
  listCapabilities(rendererId?: string): CanonicalRendererCapability[] {
    if (rendererId) {
      const adapter = this.requireRenderer(rendererId);
      return adapter.capabilities().toArray();
    }
    const all = new Set<CanonicalRendererCapability>();
    for (const adapter of this._adapters.values()) {
      for (const cap of adapter.capabilities().toArray()) {
        all.add(cap);
      }
    }
    return Array.from(all);
  }

  /**
   * Clears all registered adapters (primarily for test resets).
   */
  clear(): void {
    this._adapters.clear();
  }

  /**
   * Selects a compatible renderer adapter for the given render request.
   * Fails closed (throws NO_COMPATIBLE_RENDERER) if no registered renderer can satisfy all required capabilities.
   * Selection is 100% deterministic:
   * 1. If preferred renderer ID specified: checks compatibility strictly. Fails closed if incompatible (no silent fallback).
   * 2. Automatically filters candidate adapters satisfying canRender(request).
   * 3. Breaks ties deterministically: priority desc -> capability count desc -> adapter.id asc (lexicographical).
   */
  selectRenderer(request: RenderRequest, options?: RendererSelectionOptions): RendererAdapter {
    validateRenderRequest(request);

    // Derive or ensure required capabilities are present
    const required =
      request.requiredCapabilities && request.requiredCapabilities.length > 0
        ? request.requiredCapabilities.map(normalizeCapability)
        : deriveRequiredCapabilities(request.document, request.type);

    const effectiveRequest: RenderRequest = {
      ...request,
      requiredCapabilities: required,
    };

    const targetPreferred = options?.preferredRendererId ?? request.preferredRendererId;
    if (targetPreferred) {
      const preferred = this.requireRenderer(targetPreferred);
      const canRenderRes = preferred.canRender(effectiveRequest);
      if (!canRenderRes.canRender) {
        throw new UnsupportedCapabilityError(
          `Preferred renderer '${targetPreferred}' cannot fulfill render request: missing capabilities [${canRenderRes.missingCapabilities.join(", ")}]. Silent fallback is forbidden.`,
          {
            requestedRendererId: targetPreferred,
            missingCapabilities: canRenderRes.missingCapabilities,
            requiredCapabilities: required,
            reason: canRenderRes.reason,
          }
        );
      }
      return preferred;
    }

    if (this._adapters.size === 0) {
      throw new NoCompatibleRendererError(
        `NO_COMPATIBLE_RENDERER: No renderers are registered in the Renderer Registry. Required capabilities: [${required.join(", ")}]`,
        {
          requiredCapabilities: required,
          availableRendererIds: [],
          candidateRejections: [],
        }
      );
    }

    const compatible: RendererAdapter[] = [];
    const rejections: Array<{
      rendererId: string;
      missingCapabilities: CanonicalRendererCapability[];
      reason?: string;
    }> = [];

    for (const adapter of this._adapters.values()) {
      const check = adapter.canRender(effectiveRequest);
      if (check.canRender) {
        compatible.push(adapter);
      } else {
        rejections.push({
          rendererId: adapter.id,
          missingCapabilities: check.missingCapabilities,
          reason: check.reason,
        });
      }
    }

    if (compatible.length === 0) {
      throw new NoCompatibleRendererError(
        `NO_COMPATIBLE_RENDERER: None of the ${this._adapters.size} registered renderers can fulfill the request. Required capabilities: [${required.join(", ")}].`,
        {
          requiredCapabilities: required,
          availableRendererIds: this.listRendererIds(),
          candidateRejections: rejections,
        }
      );
    }

    // Deterministic selection tie-breaking:
    // 1. priority descending
    // 2. number of supported capabilities descending
    // 3. ID lexicographical ascending
    compatible.sort((a, b) => {
      const prioA = a.priority ?? 0;
      const prioB = b.priority ?? 0;
      if (prioA !== prioB) return prioB - prioA;

      const capsA = a.capabilities().toArray().length;
      const capsB = b.capabilities().toArray().length;
      if (capsA !== capsB) return capsB - capsA;

      return a.id.localeCompare(b.id);
    });

    return compatible[0];
  }
}

/**
 * Authoritative Canonical Global Renderer Registry instance.
 * Single Authority for renderer registration and selection.
 */
export const CANONICAL_RENDERER_REGISTRY = new RendererRegistry();

// ────────────────────────────────────────────────────────────────────────────
// 8. Test, Preview & Remotion Adapter Implementations / Stubs
// ────────────────────────────────────────────────────────────────────────────

export interface MockAdapterOptions {
  id: string;
  name?: string;
  version?: string;
  priority?: number;
  capabilities: Iterable<string>;
  onRenderFrame?: (req: RenderRequest, ctx?: RenderContext) => Promise<RenderResult>;
  onExportVideo?: (req: RenderRequest, ctx?: RenderContext) => Promise<RenderResult>;
}

/**
 * Creates an in-memory deterministic Mock Renderer Adapter for testing the abstraction.
 */
export function createMockRendererAdapter(options: MockAdapterOptions): RendererAdapter {
  const caps = createRendererCapabilities({
    supported: options.capabilities,
  });

  return {
    id: options.id,
    name: options.name ?? `Mock Renderer (${options.id})`,
    version: options.version ?? "1.0.0",
    priority: options.priority ?? 0,

    capabilities() {
      return caps;
    },

    canRender(request: RenderRequest): RendererCanRenderResult {
      const required =
        request.requiredCapabilities && request.requiredCapabilities.length > 0
          ? request.requiredCapabilities
          : deriveRequiredCapabilities(request.document, request.type);

      const missing = caps.getMissing(required);
      return {
        canRender: missing.length === 0,
        missingCapabilities: missing,
        reason: missing.length > 0 ? `Missing capabilities: ${missing.join(", ")}` : undefined,
      };
    },

    async renderFrame(request: RenderRequest, context?: RenderContext): Promise<RenderResult> {
      const check = this.canRender(request);
      if (!check.canRender) {
        throw new UnsupportedCapabilityError(
          `Mock renderer '${this.id}' cannot render frame: missing [${check.missingCapabilities.join(", ")}]`,
          { missingCapabilities: check.missingCapabilities }
        );
      }
      if (options.onRenderFrame) {
        return options.onRenderFrame(request, context);
      }
      return {
        ok: true,
        requestId: request.id,
        rendererId: this.id,
        type: "frame",
        output: {
          mimeType: "image/png",
          frameCount: 1,
          width: request.output?.width ?? 1920,
          height: request.output?.height ?? 1080,
        },
        metrics: {
          renderTimeMs: 12,
          evaluatedFrames: 1,
        },
      };
    },

    async renderSequence(request: RenderRequest, context?: RenderContext): Promise<RenderResult> {
      const check = this.canRender(request);
      if (!check.canRender) {
        throw new UnsupportedCapabilityError(
          `Mock renderer '${this.id}' cannot render sequence: missing [${check.missingCapabilities.join(", ")}]`,
          { missingCapabilities: check.missingCapabilities }
        );
      }
      const start = request.timeRange?.startFrame ?? 0;
      const end = request.timeRange?.endFrame ?? 30;
      const count = end - start + 1;
      return {
        ok: true,
        requestId: request.id,
        rendererId: this.id,
        type: "sequence",
        output: {
          frameCount: count,
          width: request.output?.width ?? 1920,
          height: request.output?.height ?? 1080,
        },
        metrics: {
          renderTimeMs: count * 5,
          evaluatedFrames: count,
        },
      };
    },

    async exportVideo(request: RenderRequest, context?: RenderContext): Promise<RenderResult> {
      const check = this.canRender(request);
      if (!check.canRender) {
        throw new UnsupportedCapabilityError(
          `Mock renderer '${this.id}' cannot export video: missing [${check.missingCapabilities.join(", ")}]`,
          { missingCapabilities: check.missingCapabilities }
        );
      }
      if (options.onExportVideo) {
        return options.onExportVideo(request, context);
      }
      return {
        ok: true,
        requestId: request.id,
        rendererId: this.id,
        type: "export",
        output: {
          filePath: request.output?.path ?? "/tmp/mock_export.mp4",
          mimeType: "video/mp4",
          durationMs: 5000,
          frameCount: 150,
        },
        metrics: {
          renderTimeMs: 150,
          evaluatedFrames: 150,
        },
      };
    },
  };
}

/**
 * REMOTION ARCHITECTURE PLACEMENT (S28-R08):
 * Remotion is an external video rendering engine wrapped behind a RendererAdapter.
 * It is NOT the canonical authority.
 * Full execution adapter is implemented in S28-R09.
 */
export const REMOTION_RENDERER_ID = "remotion-engine-adapter";

/**
 * CANVAS ARCHITECTURE PLACEMENT (S28-R10):
 * Lightweight Headless Canvas 2D Renderer wrapped behind a RendererAdapter.
 * Full execution adapter is implemented in S28-R10 (canvas/canvas-renderer-adapter.ts).
 */
export const CANVAS_RENDERER_ID = "canvas-renderer-adapter";

export const REMOTION_DECLARED_CAPABILITIES: readonly CanonicalRendererCapability[] = [
  "text",
  "image",
  "video",
  "audio",
  "shapes",
  "groups",
  "keyframes",
  "transitions",
  "alpha",
  "audio_voiceover",
  "audio_music",
  "audio_sfx",
  "audio_mixing",
  "audio_ducking",
  "audio_timing",
  "frame_rendering",
  "sequence_rendering",
  "export_video",
];

export function createRemotionAdapterStub(): RendererAdapter {
  const caps = createRendererCapabilities({
    supported: REMOTION_DECLARED_CAPABILITIES,
    supportedFormats: ["mp4", "webm", "png", "jpeg"],
    maxResolution: { width: 3840, height: 2160 },
    metadata: {
      engine: "remotion",
      version: "4.0.525",
      implementationMilestone: "S28-R09",
    },
  });

  return {
    id: REMOTION_RENDERER_ID,
    name: "Remotion Production Engine Adapter (Stub)",
    version: "4.0.525-stub",
    priority: 100,

    capabilities() {
      return caps;
    },

    canRender(request: RenderRequest): RendererCanRenderResult {
      const required =
        request.requiredCapabilities && request.requiredCapabilities.length > 0
          ? request.requiredCapabilities
          : deriveRequiredCapabilities(request.document, request.type);

      const missing = caps.getMissing(required);
      return {
        canRender: missing.length === 0,
        missingCapabilities: missing,
        reason: missing.length > 0 ? `Remotion adapter stub missing capabilities: ${missing.join(", ")}` : undefined,
      };
    },

    async renderFrame(request: RenderRequest): Promise<RenderResult> {
      throw new RenderFailedError(
        "RemotionRendererAdapter execution is reserved for S28-R09. Canonical contracts are verified.",
        { rendererId: REMOTION_RENDERER_ID, requestId: request.id }
      );
    },

    async renderSequence(request: RenderRequest): Promise<RenderResult> {
      throw new RenderFailedError(
        "RemotionRendererAdapter execution is reserved for S28-R09. Canonical contracts are verified.",
        { rendererId: REMOTION_RENDERER_ID, requestId: request.id }
      );
    },

    async exportVideo(request: RenderRequest): Promise<RenderResult> {
      throw new RenderFailedError(
        "RemotionRendererAdapter execution is reserved for S28-R09. Canonical contracts are verified.",
        { rendererId: REMOTION_RENDERER_ID, requestId: request.id }
      );
    },
  };
}

/**
 * PREVIEW RELATIONSHIP (S28-R08):
 * R06/R07 BrowserPreviewRuntime is NOT a renderer authority.
 * It can be registered as a preview-capable adapter for frame rendering without altering its authority.
 */
export const BROWSER_PREVIEW_RENDERER_ID = "browser-preview-adapter";

export const BROWSER_PREVIEW_CAPABILITIES: readonly CanonicalRendererCapability[] = [
  "frame_rendering",
  "live_preview",
  "text",
  "image",
  "shapes",
  "groups",
  "keyframes",
  "alpha",
  "audio",
  "audio_voiceover",
  "audio_music",
  "audio_sfx",
  "audio_timing",
];

export function createBrowserPreviewAdapter(): RendererAdapter {
  const caps = createRendererCapabilities({
    supported: BROWSER_PREVIEW_CAPABILITIES,
    supportedFormats: ["canvas", "dom"],
    metadata: {
      sourceRuntime: "BrowserPreviewRuntime (R06/R07)",
      authority: "Subordinated to Canonical Contracts",
    },
  });

  return {
    id: BROWSER_PREVIEW_RENDERER_ID,
    name: "Browser Live Preview Adapter",
    version: "2.0.0",
    priority: 50,

    capabilities() {
      return caps;
    },

    canRender(request: RenderRequest): RendererCanRenderResult {
      const required =
        request.requiredCapabilities && request.requiredCapabilities.length > 0
          ? request.requiredCapabilities
          : deriveRequiredCapabilities(request.document, request.type);

      const missing = caps.getMissing(required);
      return {
        canRender: missing.length === 0,
        missingCapabilities: missing,
        reason: missing.length > 0 ? `Browser preview adapter cannot satisfy: ${missing.join(", ")}` : undefined,
      };
    },

    async renderFrame(request: RenderRequest): Promise<RenderResult> {
      const check = this.canRender(request);
      if (!check.canRender) {
        throw new UnsupportedCapabilityError(
          `Browser preview adapter cannot render frame: missing [${check.missingCapabilities.join(", ")}]`,
          { missingCapabilities: check.missingCapabilities }
        );
      }
      return {
        ok: true,
        requestId: request.id,
        rendererId: BROWSER_PREVIEW_RENDERER_ID,
        type: "frame",
        output: {
          mimeType: "image/canvas-state",
          frameCount: 1,
        },
        metrics: {
          renderTimeMs: 2,
          evaluatedFrames: 1,
        },
      };
    },

    async renderSequence(): Promise<RenderResult> {
      throw new UnsupportedCapabilityError(
        "Browser preview adapter does not support offline sequence rendering",
        { rendererId: BROWSER_PREVIEW_RENDERER_ID, missingCapabilities: ["sequence_rendering"] }
      );
    },

    async exportVideo(): Promise<RenderResult> {
      throw new UnsupportedCapabilityError(
        "Browser preview adapter does not support video file export. Requires export_video capability.",
        { rendererId: BROWSER_PREVIEW_RENDERER_ID, missingCapabilities: ["export_video"] }
      );
    },
  };
}
