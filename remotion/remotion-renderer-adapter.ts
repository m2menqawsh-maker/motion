/**
 * remotion/remotion-renderer-adapter.ts
 * Production Remotion Renderer Adapter implementing S28-R08 Renderer Contracts.
 * 
 * Pipeline:
 * Canonical VideoDocument -> RenderRequest -> RendererRegistry -> RemotionRendererAdapter -> @remotion/renderer -> RenderResult
 * 
 * Enforces:
 *   - Remotion is strictly a rendering engine; canonical document is the sole authority
 *   - Zero mutation of canonical video document
 *   - Accurate declared capabilities (no claiming map/3d/particles/shaders)
 *   - Fail-closed capability rejection with UNSUPPORTED_CAPABILITY / NO_COMPATIBLE_RENDERER
 *   - Audio ducking, mixing, timing parity matching canonical evaluator
 *   - Structured RenderResult output
 *   - Cancellation and progress signal integration via RenderContext
 */

import * as fs from "fs";
import * as path from "path";
import * as os from "os";
import { bundle } from "@remotion/bundler";
import {
  renderStill,
  renderMedia,
  selectComposition,
  makeCancelSignal,
  type VideoConfig,
} from "@remotion/renderer";

import {
  type RendererAdapter,
  type RenderRequest,
  type RenderResult,
  type RenderContext,
  type RendererCanRenderResult,
  RendererCapabilities,
  createRendererCapabilities,
  deriveRequiredCapabilities,
  validateRenderRequest,
  UnsupportedCapabilityError,
  RenderFailedError,
  InvalidRenderRequestError,
  REMOTION_RENDERER_ID,
  CANONICAL_RENDERER_REGISTRY,
  RendererRegistry,
  type CanonicalRendererCapability,
} from "../contracts/renderer";
import type { BlueprintV2 } from "../contracts/blueprint";

/**
 * Declared capabilities for Remotion Production Engine.
 * Note: map, 3d, particles, custom_shaders, live_preview are explicitly omitted
 * to maintain strict fail-closed boundary unless specialized engines are registered.
 */
export const REMOTION_SUPPORTED_CAPABILITIES: readonly CanonicalRendererCapability[] = [
  // Visual Primitives
  "text",
  "image",
  "video",
  "shapes",
  "groups",
  // Temporal & Motion
  "keyframes",
  "transitions",
  "alpha",
  // Audio Subsystem (Full R07 Parity)
  "audio",
  "audio_voiceover",
  "audio_music",
  "audio_sfx",
  "audio_mixing",
  "audio_ducking",
  "audio_timing",
  // Execution Targets
  "frame_rendering",
  "sequence_rendering",
  "export_video",
];

export interface RemotionAdapterOptions {
  bundleLocation?: string;
  appDir?: string;
  concurrency?: number;
  priority?: number;
}

// Global bundle caching to avoid re-bundling webpack on every render call
let globalCachedBundlePath: string | null = null;
let globalBundlePromise: Promise<string> | null = null;

const BUNDLE_CACHE_FILE = path.join(os.tmpdir(), "clean-video-remotion-bundle-path.txt");

export async function getOrCreateRemotionBundle(options?: {
  appDir?: string;
  bundleLocation?: string;
  forceFresh?: boolean;
}): Promise<string> {
  if (options?.bundleLocation && fs.existsSync(options.bundleLocation)) {
    return options.bundleLocation;
  }

  // Check in-memory cache
  if (globalCachedBundlePath && !options?.forceFresh && fs.existsSync(globalCachedBundlePath)) {
    return globalCachedBundlePath;
  }

  // Check persistent tempfile cache across Node processes
  if (!options?.forceFresh && fs.existsSync(BUNDLE_CACHE_FILE)) {
    try {
      const persisted = fs.readFileSync(BUNDLE_CACHE_FILE, "utf-8").trim();
      if (persisted && fs.existsSync(persisted)) {
        globalCachedBundlePath = persisted;
        return persisted;
      }
    } catch {}
  }

  if (globalBundlePromise && !options?.forceFresh) {
    return globalBundlePromise;
  }

  globalBundlePromise = (async () => {
    const rootDir = process.cwd();
    const appDir = options?.appDir || path.resolve(rootDir, "remotion-app");
    const entryPoint = path.resolve(appDir, "src/index.ts");

    if (!fs.existsSync(entryPoint)) {
      throw new Error(`Remotion entrypoint not found at ${entryPoint}`);
    }

    const bundleResult = await bundle({
      entryPoint,
      publicDir: path.resolve(appDir, "public"),
      webpackOverride: (config) => ({
        ...config,
        resolve: {
          ...config.resolve,
          modules: [
            path.resolve(appDir, "node_modules"),
            path.resolve(rootDir, "node_modules"),
            ...(config.resolve?.modules || ["node_modules"]),
          ],
          alias: {
            ...(config.resolve?.alias ?? {}),
            "@": path.resolve(appDir, "src"),
            "@registry": path.resolve(rootDir, "registry"),
            "@contracts": path.resolve(rootDir, "contracts"),
            react: path.resolve(appDir, "node_modules", "react"),
            "react-dom": path.resolve(appDir, "node_modules", "react-dom"),
          },
        },
      }),
    });

    globalCachedBundlePath = bundleResult;
    try {
      fs.writeFileSync(BUNDLE_CACHE_FILE, bundleResult, "utf-8");
    } catch {}
    return bundleResult;
  })();

  return globalBundlePromise;
}

export function resetRemotionBundleCache(): void {
  globalCachedBundlePath = null;
  globalBundlePromise = null;
}

export class RemotionRendererAdapter implements RendererAdapter {
  public readonly id = REMOTION_RENDERER_ID;
  public readonly name = "Remotion Production Engine Adapter";
  public readonly version = "4.0.525";
  public readonly priority: number;

  private readonly _capabilities: RendererCapabilities;
  private readonly _options: RemotionAdapterOptions;

  constructor(options: RemotionAdapterOptions = {}) {
    this._options = options;
    this.priority = options.priority ?? 100;
    this._capabilities = createRendererCapabilities({
      supported: REMOTION_SUPPORTED_CAPABILITIES,
      supportedFormats: ["mp4", "webm", "png", "jpeg"],
      supportedCodecs: ["h264", "vp8", "vp9"],
      maxResolution: { width: 3840, height: 2160 },
      maxFps: 60,
      metadata: {
        engine: "remotion",
        version: this.version,
        compositionId: "CanonicalVideo",
      },
    });
  }

  capabilities(): RendererCapabilities {
    return this._capabilities;
  }

  canRender(request: RenderRequest): RendererCanRenderResult {
    const required =
      request.requiredCapabilities && request.requiredCapabilities.length > 0
        ? request.requiredCapabilities
        : deriveRequiredCapabilities(request.document, request.type);

    const missing = this._capabilities.getMissing(required);
    return {
      canRender: missing.length === 0,
      missingCapabilities: missing,
      reason:
        missing.length > 0
          ? `Remotion adapter cannot fulfill request: missing capabilities [${missing.join(", ")}]`
          : undefined,
    };
  }

  private async getBundleLocation(): Promise<string> {
    return getOrCreateRemotionBundle({
      bundleLocation: this._options.bundleLocation,
      appDir: this._options.appDir,
    });
  }

  private async resolveComposition(
    serveUrl: string,
    document: BlueprintV2,
    context?: RenderContext
  ): Promise<{ composition: VideoConfig; id: string; inputProps: Record<string, unknown> }> {
    const brand = (context?.metadata as any)?.brand;

    // Prefer CanonicalVideo composition
    try {
      const inputProps = { document, brand };
      const comp = await selectComposition({
        serveUrl,
        id: "CanonicalVideo",
        inputProps,
      });
      return { composition: comp, id: "CanonicalVideo", inputProps };
    } catch {
      // Fallback bridge for legacy BlueprintVideo composition
      const inputProps = {
        projectData: {
          project: { title: document.project_id || "Video" },
          blueprint: document,
          brand,
        },
      };
      const comp = await selectComposition({
        serveUrl,
        id: "BlueprintVideo",
        inputProps,
      });
      return { composition: comp, id: "BlueprintVideo", inputProps };
    }
  }

  async renderFrame(request: RenderRequest, context?: RenderContext): Promise<RenderResult> {
    const startTime = Date.now();
    validateRenderRequest(request);

    const check = this.canRender(request);
    if (!check.canRender) {
      throw new UnsupportedCapabilityError(
        `RemotionRendererAdapter cannot render frame: missing capabilities [${check.missingCapabilities.join(
          ", "
        )}]`,
        {
          rendererId: this.id,
          requestId: request.id,
          missingCapabilities: check.missingCapabilities,
          requiredCapabilities: request.requiredCapabilities,
        }
      );
    }

    const frame = request.frame ?? 0;
    const tempDir = context?.tempDir || os.tmpdir();
    const format =
      request.output?.format === "jpeg" || request.output?.format === "jpg"
        ? "jpeg"
        : "png";
    const ext = format === "jpeg" ? "jpg" : "png";
    const outPath =
      request.output?.path ||
      path.join(tempDir, `remotion_frame_${request.id}_${frame}.${ext}`);

    try {
      const serveUrl = await this.getBundleLocation();
      const { composition, inputProps } = await this.resolveComposition(
        serveUrl,
        request.document,
        context
      );

      await renderStill({
        composition,
        serveUrl,
        output: outPath,
        frame,
        inputProps,
        imageFormat: format,
      });

      const fileBuf = fs.existsSync(outPath) ? fs.readFileSync(outPath) : undefined;
      const durationMs = Date.now() - startTime;

      if (context?.logger) {
        context.logger.info(`Rendered frame ${frame} to ${outPath} in ${durationMs}ms`);
      }

      return {
        ok: true,
        requestId: request.id,
        rendererId: this.id,
        type: "frame",
        output: {
          filePath: outPath,
          buffer: fileBuf ? new Uint8Array(fileBuf) : undefined,
          mimeType: format === "jpeg" ? "image/jpeg" : "image/png",
          frameCount: 1,
          width: request.output?.width || composition.width,
          height: request.output?.height || composition.height,
        },
        metrics: {
          renderTimeMs: durationMs,
          evaluatedFrames: 1,
        },
      };
    } catch (err: any) {
      if (err instanceof UnsupportedCapabilityError) throw err;
      const durationMs = Date.now() - startTime;
      throw new RenderFailedError(
        `Remotion frame render failed: ${err?.message || String(err)}`,
        {
          requestId: request.id,
          frame,
          durationMs,
          error: String(err),
        }
      );
    }
  }

  async renderSequence(request: RenderRequest, context?: RenderContext): Promise<RenderResult> {
    const startTime = Date.now();
    validateRenderRequest(request);

    const check = this.canRender(request);
    if (!check.canRender) {
      throw new UnsupportedCapabilityError(
        `RemotionRendererAdapter cannot render sequence: missing capabilities [${check.missingCapabilities.join(
          ", "
        )}]`,
        {
          rendererId: this.id,
          requestId: request.id,
          missingCapabilities: check.missingCapabilities,
          requiredCapabilities: request.requiredCapabilities,
        }
      );
    }

    const startFrame = request.timeRange?.startFrame ?? 0;
    const endFrame = request.timeRange?.endFrame ?? 0;
    const frameCount = endFrame - startFrame + 1;

    const tempDir = context?.tempDir || os.tmpdir();
    const outDir =
      request.output?.path || path.join(tempDir, `remotion_seq_${request.id}`);
    fs.mkdirSync(outDir, { recursive: true });

    const format =
      request.output?.format === "jpeg" || request.output?.format === "jpg"
        ? "jpeg"
        : "png";
    const ext = format === "jpeg" ? "jpg" : "png";

    try {
      const serveUrl = await this.getBundleLocation();
      const { composition, inputProps } = await this.resolveComposition(
        serveUrl,
        request.document,
        context
      );

      for (let f = startFrame; f <= endFrame; f++) {
        if (context?.signal?.aborted) {
          throw new Error("Render sequence aborted via AbortSignal");
        }
        const framePath = path.join(
          outDir,
          `frame_${String(f).padStart(6, "0")}.${ext}`
        );
        await renderStill({
          composition,
          serveUrl,
          output: framePath,
          frame: f,
          inputProps,
          imageFormat: format,
        });
      }

      const durationMs = Date.now() - startTime;
      if (context?.logger) {
        context.logger.info(`Rendered sequence of ${frameCount} frames in ${durationMs}ms`);
      }

      return {
        ok: true,
        requestId: request.id,
        rendererId: this.id,
        type: "sequence",
        output: {
          filePath: outDir,
          frameCount,
          mimeType: `image/${format}`,
          width: request.output?.width || composition.width,
          height: request.output?.height || composition.height,
        },
        metrics: {
          renderTimeMs: durationMs,
          evaluatedFrames: frameCount,
        },
      };
    } catch (err: any) {
      if (err instanceof UnsupportedCapabilityError) throw err;
      const durationMs = Date.now() - startTime;
      throw new RenderFailedError(
        `Remotion sequence render failed: ${err?.message || String(err)}`,
        {
          requestId: request.id,
          timeRange: request.timeRange,
          durationMs,
        }
      );
    }
  }

  async exportVideo(request: RenderRequest, context?: RenderContext): Promise<RenderResult> {
    const startTime = Date.now();
    validateRenderRequest(request);

    const check = this.canRender(request);
    if (!check.canRender) {
      throw new UnsupportedCapabilityError(
        `RemotionRendererAdapter cannot export video: missing capabilities [${check.missingCapabilities.join(
          ", "
        )}]`,
        {
          rendererId: this.id,
          requestId: request.id,
          missingCapabilities: check.missingCapabilities,
          requiredCapabilities: request.requiredCapabilities,
        }
      );
    }

    const tempDir = context?.tempDir || os.tmpdir();
    const outPath =
      request.output?.path || path.join(tempDir, `remotion_export_${request.id}.mp4`);
    fs.mkdirSync(path.dirname(outPath), { recursive: true });

    try {
      const serveUrl = await this.getBundleLocation();
      const { composition, inputProps } = await this.resolveComposition(
        serveUrl,
        request.document,
        context
      );

      const { cancelSignal, cancel } = makeCancelSignal();
      if (context?.signal) {
        context.signal.addEventListener("abort", () => {
          cancel();
        });
      }

      await renderMedia({
        composition,
        serveUrl,
        outputLocation: outPath,
        inputProps,
        codec: "h264",
        imageFormat: "jpeg",
        cancelSignal,
        enforceAudioTrack: request.output?.includeAudio !== false,
        onProgress: ({ progress, renderedFrames }) => {
          if (context?.logger) {
            context.logger.info(
              `Export progress: ${Math.round(progress * 100)}% (${renderedFrames} frames)`
            );
          }
        },
      });

      const durationMs = Date.now() - startTime;
      const totalFrames = composition.durationInFrames;
      const fps = composition.fps;

      return {
        ok: true,
        requestId: request.id,
        rendererId: this.id,
        type: "export",
        output: {
          filePath: outPath,
          mimeType: "video/mp4",
          frameCount: totalFrames,
          durationMs: Math.round((totalFrames / fps) * 1000),
          width: composition.width,
          height: composition.height,
        },
        metrics: {
          renderTimeMs: durationMs,
          evaluatedFrames: totalFrames,
        },
      };
    } catch (err: any) {
      if (err instanceof UnsupportedCapabilityError) throw err;
      const durationMs = Date.now() - startTime;
      throw new RenderFailedError(
        `Remotion video export failed: ${err?.message || String(err)}`,
        {
          requestId: request.id,
          durationMs,
        }
      );
    }
  }
}

/**
 * Factory helper to construct RemotionRendererAdapter.
 */
export function createRemotionRendererAdapter(
  options?: RemotionAdapterOptions
): RemotionRendererAdapter {
  return new RemotionRendererAdapter(options);
}

/**
 * Registers RemotionRendererAdapter into canonical registry, replacing any stub.
 */
export function registerRemotionRenderer(
  registry: RendererRegistry = CANONICAL_RENDERER_REGISTRY,
  options?: RemotionAdapterOptions
): RemotionRendererAdapter {
  if (registry.has(REMOTION_RENDERER_ID)) {
    registry.unregister(REMOTION_RENDERER_ID);
  }
  const adapter = createRemotionRendererAdapter(options);
  registry.register(adapter);
  return adapter;
}
