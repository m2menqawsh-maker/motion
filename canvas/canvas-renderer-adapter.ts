/**
 * canvas/canvas-renderer-adapter.ts
 * Production Headless Canvas 2D Renderer Adapter implementing S28-R08/R10 Renderer Contracts.
 * 
 * Pipeline:
 * Canonical VideoDocument -> RenderRequest -> RendererRegistry -> CanvasRendererAdapter -> 2D Canvas Surface / FFmpeg -> RenderResult
 * 
 * Enforces:
 *   - Canonical VideoDocument and evaluateVideoAtFrame are the sole video authorities
 *   - Zero mutation of canonical video documents
 *   - Pure 2D Canvas vector scene generation (text, image, shapes, groups, alpha, keyframes, transitions)
 *   - Sub-second headless rasterization and video export via system FFmpeg/librsvg
 *   - Accurate declared capabilities (strictly excludes map, 3d, particles, custom_shaders, video)
 *   - Fail-closed capability rejection with UNSUPPORTED_CAPABILITY / NO_COMPATIBLE_RENDERER
 *   - Structured RenderResult output with metrics and abort signal cancellation
 */

import * as fs from "fs";
import * as path from "path";
import * as os from "os";
import { execFileSync, spawn } from "child_process";

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
  CANVAS_RENDERER_ID,
  CANONICAL_RENDERER_REGISTRY,
  RendererRegistry,
  type CanonicalRendererCapability,
} from "../contracts/renderer";
import type { BlueprintV2 } from "../contracts/blueprint";
import {
  evaluateVideoAtFrame,
  type EvaluatedFrameState,
  type EvaluatedLayerState,
} from "../contracts/evaluator";
import {
  calculateCanonicalDuration,
  frameToMs,
} from "../contracts/timeline";

/**
 * Declared capabilities for Headless Canvas 2D Production Engine.
 * Note: video, map, 3d, particles, custom_shaders, live_preview are explicitly omitted
 * to maintain strict fail-closed boundaries.
 */
export const CANVAS_SUPPORTED_CAPABILITIES: readonly CanonicalRendererCapability[] = [
  // Visual Primitives
  "text",
  "image",
  "shapes",
  "groups",
  // Temporal & Motion
  "keyframes",
  "transitions",
  "alpha",
  // Execution Targets
  "frame_rendering",
  "sequence_rendering",
  "export_video",
];

export interface CanvasAdapterOptions {
  ffmpegPath?: string;
  priority?: number;
  defaultBgColor?: string;
}

/**
 * Helper to escape XML/SVG special characters.
 */
function escapeXml(unsafe: string): string {
  return unsafe
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

/**
 * Resolves canvas pixel dimensions from document aspect ratio or explicit output dimensions.
 */
export function resolveCanvasDimensions(
  doc: BlueprintV2,
  outputConfig?: { width?: number; height?: number }
): { width: number; height: number } {
  if (outputConfig?.width && outputConfig?.height) {
    return { width: outputConfig.width, height: outputConfig.height };
  }

  const ratio = doc.aspect_ratio || "16:9";
  switch (ratio) {
    case "9:16":
      return { width: 1080, height: 1920 };
    case "1:1":
      return { width: 1080, height: 1080 };
    case "4:5":
      return { width: 1080, height: 1350 };
    case "16:9":
    default:
      return { width: 1920, height: 1080 };
  }
}

/**
 * Assembles pure SVG markup representing the evaluated canvas frame.
 * Center-based coordinate system matching canonical evaluator mathematics.
 */
export function assembleCanvasSvg(
  evaluated: EvaluatedFrameState,
  width: number,
  height: number,
  options?: { bgColor?: string }
): string {
  const bgColor = options?.bgColor || "#000000";
  const layers = evaluated.layers;

  const elements: string[] = [];

  // Background canvas rectangle
  elements.push(
    `<rect x="0" y="0" width="${width}" height="${height}" fill="${bgColor}" />`
  );

  const centerX = width / 2;
  const centerY = height / 2;

  for (const layer of layers) {
    if (!layer.visible || layer.opacity <= 0) {
      continue;
    }

    const t = layer.transform;
    const netOpacity = Math.max(0, Math.min(1, layer.opacity));
    const posX = centerX + t.x;
    const posY = centerY + t.y;

    const transformAttr = `transform="translate(${posX}, ${posY}) rotate(${t.rotation}) scale(${t.scaleX}, ${t.scaleY})"`;
    const opacityAttr = `opacity="${netOpacity.toFixed(4)}"`;
    const props = layer.properties || {};

    let innerContent = "";

    if (layer.kind === "text") {
      const textVal = props.text !== undefined ? String(props.text) : "";
      const typo = props.typography || {};
      const fontFamily = typo.fontFamily || props.fontFamily || "Cairo, sans-serif";
      const fontSize = typo.fontSize || props.fontSize || 48;
      const fillColor = typo.fillColor || typo.color || props.fillColor || "#ffffff";
      const fontWeight = typo.fontWeight || props.fontWeight || "normal";
      const textAnchor = "middle";
      const dominantBaseline = "central";

      innerContent = `<text text-anchor="${textAnchor}" dominant-baseline="${dominantBaseline}" font-family="${escapeXml(
        fontFamily
      )}" font-size="${fontSize}" font-weight="${fontWeight}" fill="${fillColor}">${escapeXml(
        textVal
      )}</text>`;
    } else if (layer.kind === "shape") {
      const shapeType = props.shape_type || "rectangle";
      const size = props.size || { width: 200, height: 200 };
      const w = typeof size === "number" ? size : (size.width ?? 200);
      const h = typeof size === "number" ? size : (size.height ?? 200);
      const fill = props.fillColor || props.color || "#3b82f6";
      const stroke = props.strokeColor || "none";
      const strokeWidth = props.strokeWidth || 0;
      const strokeAttr = stroke !== "none" && strokeWidth > 0 ? ` stroke="${stroke}" stroke-width="${strokeWidth}"` : "";

      if (shapeType === "circle") {
        const r = props.radius || Math.min(w, h) / 2;
        innerContent = `<circle cx="0" cy="0" r="${r}" fill="${fill}"${strokeAttr} />`;
      } else if (shapeType === "line") {
        innerContent = `<line x1="${-w / 2}" y1="0" x2="${w / 2}" y2="0" stroke="${fill}" stroke-width="${strokeWidth || 4}" />`;
      } else if (shapeType === "path" && props.pathData) {
        innerContent = `<path d="${escapeXml(props.pathData)}" fill="${fill}"${strokeAttr} />`;
      } else {
        // rectangle default
        const rx = props.borderRadius ? ` rx="${props.borderRadius}" ry="${props.borderRadius}"` : "";
        innerContent = `<rect x="${-w / 2}" y="${-h / 2}" width="${w}" height="${h}"${rx} fill="${fill}"${strokeAttr} />`;
      }
    } else if (layer.kind === "image") {
      const assetRef = props.asset_ref || "";
      const size = props.size || { width: 400, height: 300 };
      const w = size.width || 400;
      const h = size.height || 300;
      if (assetRef) {
        innerContent = `<image href="${escapeXml(
          assetRef
        )}" x="${-w / 2}" y="${-h / 2}" width="${w}" height="${h}" preserveAspectRatio="xMidYMid slice" />`;
      }
    } else if (layer.kind === "group") {
      // Group container; child elements are flattened or rendered hierarchically
      innerContent = `<g id="group_${layer.layer_id}"></g>`;
    }

    if (innerContent) {
      elements.push(
        `<g id="layer_${layer.layer_id}" ${transformAttr} ${opacityAttr}>${innerContent}</g>`
      );
    }
  }

  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
${elements.join("\n")}
</svg>`;
}

export class CanvasRendererAdapter implements RendererAdapter {
  public readonly id = CANVAS_RENDERER_ID;
  public readonly name = "Canvas Headless 2D Renderer Adapter";
  public readonly version = "1.0.0";
  public readonly priority: number;

  private readonly _capabilities: RendererCapabilities;
  private readonly _ffmpegPath: string;
  private readonly _defaultBgColor: string;

  constructor(options: CanvasAdapterOptions = {}) {
    this.priority = options.priority ?? 110;
    this._ffmpegPath = options.ffmpegPath || "ffmpeg";
    this._defaultBgColor = options.defaultBgColor || "#000000";

    this._capabilities = createRendererCapabilities({
      supported: CANVAS_SUPPORTED_CAPABILITIES,
      supportedFormats: ["png", "jpeg", "svg", "mp4"],
      supportedCodecs: ["libx264"],
      maxResolution: { width: 3840, height: 2160 },
      maxFps: 60,
      metadata: {
        engine: "canvas",
        backend: "headless-vector-surface",
        rasterizer: "ffmpeg-librsvg",
        milestone: "S28-R10",
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
          ? `CanvasRendererAdapter cannot fulfill request: missing capabilities [${missing.join(", ")}]`
          : undefined,
    };
  }

  /**
   * Rasterizes an SVG string to an image file (PNG / JPEG) using FFmpeg librsvg.
   */
  private rasterizeSvg(
    svgContent: string,
    outPath: string,
    format: "png" | "jpeg",
    width: number,
    height: number
  ): void {
    const tmpSvg = path.join(
      os.tmpdir(),
      `cv_render_${Date.now()}_${Math.random().toString(36).substring(2, 9)}.svg`
    );

    try {
      fs.writeFileSync(tmpSvg, svgContent, "utf-8");
      fs.mkdirSync(path.dirname(outPath), { recursive: true });

      const args = [
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        tmpSvg,
        "-update",
        "1",
        "-frames:v",
        "1",
        "-s",
        `${width}x${height}`,
        outPath,
      ];

      execFileSync(this._ffmpegPath, args, { stdio: "pipe" });
    } catch (err: any) {
      throw new RenderFailedError(
        `Failed to rasterize canvas frame via FFmpeg: ${err?.message || String(err)}`,
        { outPath, error: String(err) }
      );
    } finally {
      try {
        if (fs.existsSync(tmpSvg)) fs.unlinkSync(tmpSvg);
      } catch {}
    }
  }

  async renderFrame(request: RenderRequest, context?: RenderContext): Promise<RenderResult> {
    const startTime = Date.now();
    validateRenderRequest(request);

    const check = this.canRender(request);
    if (!check.canRender) {
      throw new UnsupportedCapabilityError(
        `CanvasRendererAdapter cannot render frame: missing capabilities [${check.missingCapabilities.join(
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
    const dimensions = resolveCanvasDimensions(request.document, request.output);
    const { width, height } = dimensions;

    const tempDir = context?.tempDir || os.tmpdir();
    const format =
      request.output?.format === "jpeg" || request.output?.format === "jpg"
        ? "jpeg"
        : request.output?.format === "svg"
        ? "svg"
        : "png";

    const ext = format === "jpeg" ? "jpg" : format === "svg" ? "svg" : "png";
    const outPath =
      request.output?.path ||
      path.join(tempDir, `canvas_frame_${request.id}_${frame}.${ext}`);

    try {
      // 1. Evaluate discrete frame strictly via Canonical Evaluator
      const evaluated = evaluateVideoAtFrame(request.document, frame);

      // 2. Assemble vector surface SVG
      const svg = assembleCanvasSvg(evaluated, width, height, {
        bgColor: this._defaultBgColor,
      });

      let fileBuf: Buffer;

      if (format === "svg") {
        fs.mkdirSync(path.dirname(outPath), { recursive: true });
        fs.writeFileSync(outPath, svg, "utf-8");
        fileBuf = Buffer.from(svg, "utf-8");
      } else {
        // 3. Rasterize to image
        this.rasterizeSvg(svg, outPath, format, width, height);
        fileBuf = fs.readFileSync(outPath);
      }

      const durationMs = Date.now() - startTime;
      if (context?.logger) {
        context.logger.info(`CanvasRendererAdapter rendered frame ${frame} in ${durationMs}ms`);
      }

      return {
        ok: true,
        requestId: request.id,
        rendererId: this.id,
        type: "frame",
        output: {
          filePath: outPath,
          buffer: new Uint8Array(fileBuf),
          mimeType: format === "jpeg" ? "image/jpeg" : format === "svg" ? "image/svg+xml" : "image/png",
          frameCount: 1,
          width,
          height,
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
        `Canvas frame render failed: ${err?.message || String(err)}`,
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
        `CanvasRendererAdapter cannot render sequence: missing capabilities [${check.missingCapabilities.join(
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

    const dimensions = resolveCanvasDimensions(request.document, request.output);
    const { width, height } = dimensions;

    const tempDir = context?.tempDir || os.tmpdir();
    const outDir =
      request.output?.path || path.join(tempDir, `canvas_seq_${request.id}`);
    fs.mkdirSync(outDir, { recursive: true });

    const format =
      request.output?.format === "jpeg" || request.output?.format === "jpg"
        ? "jpeg"
        : "png";
    const ext = format === "jpeg" ? "jpg" : "png";

    try {
      for (let f = startFrame; f <= endFrame; f++) {
        if (context?.signal?.aborted) {
          throw new Error("Render sequence aborted via AbortSignal");
        }

        const evaluated = evaluateVideoAtFrame(request.document, f);
        const svg = assembleCanvasSvg(evaluated, width, height, {
          bgColor: this._defaultBgColor,
        });

        const framePath = path.join(
          outDir,
          `frame_${String(f).padStart(6, "0")}.${ext}`
        );

        this.rasterizeSvg(svg, framePath, format, width, height);
      }

      const durationMs = Date.now() - startTime;
      if (context?.logger) {
        context.logger.info(
          `CanvasRendererAdapter rendered sequence of ${frameCount} frames in ${durationMs}ms`
        );
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
          width,
          height,
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
        `Canvas sequence render failed: ${err?.message || String(err)}`,
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
        `CanvasRendererAdapter cannot export video: missing capabilities [${check.missingCapabilities.join(
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

    const fps = request.document.fps || 30;
    const totalFrames =
      request.document.totalDurationFrames ??
      calculateCanonicalDuration(request.document);

    const dimensions = resolveCanvasDimensions(request.document, request.output);
    const { width, height } = dimensions;

    const tempDir = context?.tempDir || os.tmpdir();
    const workDir = path.join(
      tempDir,
      `canvas_export_work_${request.id}_${Date.now()}`
    );
    fs.mkdirSync(workDir, { recursive: true });

    const outPath =
      request.output?.path || path.join(tempDir, `canvas_export_${request.id}.mp4`);
    fs.mkdirSync(path.dirname(outPath), { recursive: true });

    try {
      // 1. Render all frames sequentially into temp workDir
      for (let f = 0; f < totalFrames; f++) {
        if (context?.signal?.aborted) {
          throw new Error("Video export aborted via AbortSignal");
        }

        const evaluated = evaluateVideoAtFrame(request.document, f);
        const svg = assembleCanvasSvg(evaluated, width, height, {
          bgColor: this._defaultBgColor,
        });

        const framePath = path.join(
          workDir,
          `frame_${String(f).padStart(6, "0")}.png`
        );
        this.rasterizeSvg(svg, framePath, "png", width, height);

        if (context?.logger && f % 15 === 0) {
          context.logger.info(`Canvas export progress: ${Math.round((f / totalFrames) * 100)}%`);
        }
      }

      if (context?.signal?.aborted) {
        throw new Error("Video export aborted via AbortSignal");
      }

      // 2. Encode to MP4 with FFmpeg
      const inputPattern = path.join(workDir, "frame_%06d.png");
      const ffmpegArgs = [
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-framerate",
        String(fps),
        "-i",
        inputPattern,
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        outPath,
      ];

      execFileSync(this._ffmpegPath, ffmpegArgs, { stdio: "pipe" });

      const durationMs = Date.now() - startTime;
      if (context?.logger) {
        context.logger.info(`Exported video ${outPath} (${totalFrames} frames) in ${durationMs}ms`);
      }

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
          width,
          height,
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
        `Canvas video export failed: ${err?.message || String(err)}`,
        {
          requestId: request.id,
          durationMs,
          error: String(err),
        }
      );
    } finally {
      // Clean up temp frames directory
      try {
        if (fs.existsSync(workDir)) {
          fs.rmSync(workDir, { recursive: true, force: true });
        }
      } catch {}
    }
  }
}

/**
 * Factory helper to construct CanvasRendererAdapter.
 */
export function createCanvasRendererAdapter(
  options?: CanvasAdapterOptions
): CanvasRendererAdapter {
  return new CanvasRendererAdapter(options);
}

/**
 * Registers CanvasRendererAdapter into canonical registry.
 */
export function registerCanvasRenderer(
  registry: RendererRegistry = CANONICAL_RENDERER_REGISTRY,
  options?: CanvasAdapterOptions
): CanvasRendererAdapter {
  if (registry.has(CANVAS_RENDERER_ID)) {
    registry.unregister(CANVAS_RENDERER_ID);
  }
  const adapter = createCanvasRendererAdapter(options);
  registry.register(adapter);
  return adapter;
}
