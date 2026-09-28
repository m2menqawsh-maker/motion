/**
 * contracts/asset-resolver.ts — Canonical AssetRef Discovery & Fail-Closed Resolution Authority (S14).
 * TypeScript Implementation matching scripts/core/asset_resolution.py.
 */
import { z } from "zod";

function getBasename(p: string): string {
  const parts = p.replace(/\\/g, "/").split("/").filter(Boolean);
  return parts.length > 0 ? parts[parts.length - 1] : p;
}

function joinPath(dir: string, file: string): string {
  return dir.replace(/[\\/]+$/, "") + "/" + file.replace(/^[\\/]+/, "");
}

export const ASSET_ID_REGEX = /^[a-zA-Z0-9_\-\.]+$/;

// ─── 1. Error Taxonomy ────────────────────────────────────────────────────────

export class AssetResolutionError extends Error {
  public readonly code: string;
  public readonly details: Record<string, any>;

  constructor(message: string, code = "ASSET_RESOLUTION_ERROR", details: Record<string, any> = {}) {
    super(`${code}: ${message}`);
    this.name = "AssetResolutionError";
    this.code = code;
    this.details = details;
  }
}

export class UnknownAssetReferenceError extends AssetResolutionError {
  public readonly assetId: string;
  public readonly fieldPath?: string;
  public readonly sceneId?: string;
  public readonly projectId?: string;

  constructor(options: {
    assetId: string;
    fieldPath?: string;
    sceneId?: string;
    projectId?: string;
    message?: string;
  }) {
    const loc = options.sceneId
      ? `scene='${options.sceneId}' field='${options.fieldPath || "unknown"}'`
      : `field='${options.fieldPath || "unknown"}'`;
    const proj = options.projectId ? ` project='${options.projectId}'` : "";
    const msg = options.message || `Logical asset '${options.assetId}' not found in media_map (${loc}${proj})`;
    super(msg, "UNKNOWN_ASSET_REFERENCE", {
      assetId: options.assetId,
      fieldPath: options.fieldPath,
      sceneId: options.sceneId,
      projectId: options.projectId,
    });
    this.name = "UnknownAssetReferenceError";
    this.assetId = options.assetId;
    this.fieldPath = options.fieldPath;
    this.sceneId = options.sceneId;
    this.projectId = options.projectId;
  }
}

export class MalformedAssetRefError extends AssetResolutionError {
  public readonly rawRef: any;
  public readonly reason: string;

  constructor(options: {
    rawRef: any;
    reason: string;
    fieldPath?: string;
    sceneId?: string;
  }) {
    const loc = options.sceneId ? ` in scene '${options.sceneId}'` : "";
    const atField = options.fieldPath ? ` at '${options.fieldPath}'` : "";
    const msg = `Malformed asset reference '${JSON.stringify(options.rawRef)}'${loc}${atField}: ${options.reason}`;
    super(msg, "MALFORMED_ASSET_REF", options);
    this.name = "MalformedAssetRefError";
    this.rawRef = options.rawRef;
    this.reason = options.reason;
  }
}

export class RequiredArtifactMissingError extends AssetResolutionError {
  public readonly artifactName: string;
  public readonly projectDir: string;

  constructor(artifactName: string, projectDir: string, lifecycleState?: string) {
    const stateStr = lifecycleState ? ` for lifecycle state '${lifecycleState}'` : "";
    const msg = `Mandatory artifact '${artifactName}' is missing in project '${getBasename(projectDir)}'${stateStr}.`;
    super(msg, "REQUIRED_ARTIFACT_MISSING", { artifactName, projectDir, lifecycleState });
    this.name = "RequiredArtifactMissingError";
    this.artifactName = artifactName;
    this.projectDir = projectDir;
  }
}

export class ArtifactCorruptedError extends AssetResolutionError {
  public readonly artifactName: string;
  public readonly reason: string;

  constructor(artifactName: string, reason: string, projectDir?: string) {
    const projStr = projectDir ? ` in project '${getBasename(projectDir)}'` : "";
    const msg = `Artifact '${artifactName}'${projStr} is corrupted: ${reason}`;
    super(msg, "ARTIFACT_CORRUPTED", { artifactName, reason, projectDir });
    this.name = "ArtifactCorruptedError";
    this.artifactName = artifactName;
    this.reason = reason;
  }
}

// ─── 2. Canonical AssetRef Schemas ───────────────────────────────────────────

export const TaggedAssetRefSchema = z.discriminatedUnion("kind", [
  z.object({
    kind: z.literal("asset"),
    asset_id: z.string().min(1).regex(ASSET_ID_REGEX, "Invalid asset_id format"),
  }),
  z.object({
    kind: z.literal("url"),
    url: z.string().url("Invalid URL format").refine(u => u.startsWith("http://") || u.startsWith("https://"), {
      message: "External URL must start with http:// or https://",
    }),
  }),
]);
export type TaggedAssetRef = z.infer<typeof TaggedAssetRefSchema>;

export const AssetRefSchema = z.union([
  z.string().min(1, "Asset reference cannot be empty").refine(s => {
    return !s.startsWith("http://") && !s.startsWith("https://") && !s.startsWith("/") && !s.startsWith("./") && !s.includes("\\");
  }, {
    message: "String asset reference must be a logical asset ID, not a raw URL or path. Use tagged ref { kind: 'url', url: '...' } for external URLs.",
  }).refine(s => ASSET_ID_REGEX.test(s), {
    message: "String asset reference must match ^[a-zA-Z0-9_\\-\\.]+$",
  }),
  TaggedAssetRefSchema,
]);
export type AssetRef = z.infer<typeof AssetRefSchema>;

export interface ParsedAssetRef {
  refKind: "asset" | "url";
  assetId: string | null;
  url: string | null;
  rawRef: any;
  isLogical: boolean;
  isUrl: boolean;
}

export function parseAssetRef(
  val: any,
  fieldPath = "",
  sceneId?: string
): ParsedAssetRef {
  if (val === null || val === undefined) {
    throw new MalformedAssetRefError({ rawRef: val, reason: "Reference cannot be null or undefined", fieldPath, sceneId });
  }

  // 1. Plain String
  if (typeof val === "string") {
    const cleaned = val.trim();
    if (!cleaned) {
      throw new MalformedAssetRefError({ rawRef: val, reason: "Asset reference string cannot be empty", fieldPath, sceneId });
    }

    if (cleaned.startsWith("http://") || cleaned.startsWith("https://")) {
      throw new MalformedAssetRefError({
        rawRef: val,
        reason: "String reference looks like a URL. External URLs must use tagged format: { kind: 'url', url: '...' }",
        fieldPath,
        sceneId,
      });
    }

    if (cleaned.startsWith("/") || cleaned.startsWith("./") || cleaned.startsWith("../") || cleaned.includes("\\")) {
      throw new MalformedAssetRefError({
        rawRef: val,
        reason: "String reference looks like a filesystem path. Logical references must be asset IDs, not local paths",
        fieldPath,
        sceneId,
      });
    }

    if (!ASSET_ID_REGEX.test(cleaned)) {
      throw new MalformedAssetRefError({
        rawRef: val,
        reason: `Asset ID '${cleaned}' contains invalid characters (must match ^[a-zA-Z0-9_\\-\\.]+$)`,
        fieldPath,
        sceneId,
      });
    }

    return {
      refKind: "asset",
      assetId: cleaned,
      url: null,
      rawRef: val,
      isLogical: true,
      isUrl: false,
    };
  }

  // 2. Tagged Object
  if (typeof val === "object" && val !== null) {
    const kind = val.kind;
    if (!kind) {
      throw new MalformedAssetRefError({
        rawRef: val,
        reason: "Missing required 'kind' property in tagged asset reference",
        fieldPath,
        sceneId,
      });
    }

    if (kind === "asset") {
      const aid = val.asset_id;
      if (typeof aid !== "string" || !aid.trim()) {
        throw new MalformedAssetRefError({
          rawRef: val,
          reason: "Tagged asset reference must contain non-empty string 'asset_id'",
          fieldPath,
          sceneId,
        });
      }
      const aidClean = aid.trim();
      if (!ASSET_ID_REGEX.test(aidClean)) {
        throw new MalformedAssetRefError({
          rawRef: val,
          reason: `asset_id '${aidClean}' contains invalid characters`,
          fieldPath,
          sceneId,
        });
      }
      return {
        refKind: "asset",
        assetId: aidClean,
        url: null,
        rawRef: val,
        isLogical: true,
        isUrl: false,
      };
    }

    if (kind === "url") {
      const urlVal = val.url;
      if (typeof urlVal !== "string" || !urlVal.trim()) {
        throw new MalformedAssetRefError({
          rawRef: val,
          reason: "Tagged url reference must contain non-empty string 'url'",
          fieldPath,
          sceneId,
        });
      }
      const urlClean = urlVal.trim();
      try {
        const parsed = new URL(urlClean);
        if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
          throw new Error("Protocol must be http: or https:");
        }
      } catch (err: any) {
        throw new MalformedAssetRefError({
          rawRef: val,
          reason: `Invalid external URL '${urlClean}': ${err.message}`,
          fieldPath,
          sceneId,
        });
      }
      return {
        refKind: "url",
        assetId: null,
        url: urlClean,
        rawRef: val,
        isLogical: false,
        isUrl: true,
      };
    }

    throw new MalformedAssetRefError({
      rawRef: val,
      reason: `Unsupported asset reference kind: '${kind}'. Expected 'asset' or 'url'`,
      fieldPath,
      sceneId,
    });
  }

  throw new MalformedAssetRefError({
    rawRef: val,
    reason: `Unsupported asset reference type: ${typeof val}`,
    fieldPath,
    sceneId,
  });
}

// ─── 3. Declarative Media Discovery (ASSET-005) ──────────────────────────────

export interface AssetReferenceOccurrence {
  rawRef: any;
  parsed: ParsedAssetRef;
  fieldPath: string;
  slot: string;
  sceneId?: string;
  expectedKinds?: string[];
}

export function collectAssetReferences(blueprint: any): AssetReferenceOccurrence[] {
  if (!blueprint || typeof blueprint !== "object") return [];

  const occurrences: AssetReferenceOccurrence[] = [];

  // 1. AudioPlan tracks
  const audio = blueprint.audio;
  if (audio && typeof audio === "object") {
    // Voiceover
    if (audio.voiceover?.asset_ref) {
      const p = parseAssetRef(audio.voiceover.asset_ref, "audio.voiceover.asset_ref");
      occurrences.push({
        rawRef: audio.voiceover.asset_ref,
        parsed: p,
        fieldPath: "audio.voiceover.asset_ref",
        slot: "audio.voiceover",
        expectedKinds: ["vo", "audio"],
      });
    }

    // Music
    if (audio.music?.asset_ref) {
      const p = parseAssetRef(audio.music.asset_ref, "audio.music.asset_ref");
      occurrences.push({
        rawRef: audio.music.asset_ref,
        parsed: p,
        fieldPath: "audio.music.asset_ref",
        slot: "audio.music",
        expectedKinds: ["music", "audio"],
      });
    }

    // Global SFX
    if (Array.isArray(audio.global_sfx)) {
      audio.global_sfx.forEach((sfx: any, idx: number) => {
        if (sfx?.asset_ref) {
          const pathStr = `audio.global_sfx[${idx}].asset_ref`;
          const p = parseAssetRef(sfx.asset_ref, pathStr);
          occurrences.push({
            rawRef: sfx.asset_ref,
            parsed: p,
            fieldPath: pathStr,
            slot: "audio.global_sfx",
            expectedKinds: ["sfx", "audio"],
          });
        }
      });
    }
  }

  // 2. Scenes
  const scenes = blueprint.scenes;
  if (Array.isArray(scenes)) {
    scenes.forEach((scene: any, sIdx: number) => {
      if (!scene || typeof scene !== "object") return;
      const sceneId = scene.scene_id || `scene_${sIdx}`;

      // media_refs
      if (Array.isArray(scene.media_refs)) {
        scene.media_refs.forEach((mRef: any, mIdx: number) => {
          if (mRef !== null && mRef !== undefined) {
            const pathStr = `scenes[${sIdx}].media_refs[${mIdx}]`;
            const p = parseAssetRef(mRef, pathStr, sceneId);
            occurrences.push({
              rawRef: mRef,
              parsed: p,
              fieldPath: pathStr,
              slot: "scenes.media_refs",
              sceneId,
              expectedKinds: ["image", "video"],
            });
          }
        });
      }

      // sfx_ref
      if (scene.sfx_ref) {
        const pathStr = `scenes[${sIdx}].sfx_ref`;
        const p = parseAssetRef(scene.sfx_ref, pathStr, sceneId);
        occurrences.push({
          rawRef: scene.sfx_ref,
          parsed: p,
          fieldPath: pathStr,
          slot: "scenes.sfx_ref",
          sceneId,
          expectedKinds: ["sfx", "audio"],
        });
      }

      // captions_ref
      if (scene.captions_ref) {
        const pathStr = `scenes[${sIdx}].captions_ref`;
        const p = parseAssetRef(scene.captions_ref, pathStr, sceneId);
        occurrences.push({
          rawRef: scene.captions_ref,
          parsed: p,
          fieldPath: pathStr,
          slot: "scenes.captions_ref",
          sceneId,
          expectedKinds: ["json", "other"],
        });
      }

      // surface.logoSrc
      if (scene.surface?.logoSrc) {
        const pathStr = `scenes[${sIdx}].surface.logoSrc`;
        const p = parseAssetRef(scene.surface.logoSrc, pathStr, sceneId);
        occurrences.push({
          rawRef: scene.surface.logoSrc,
          parsed: p,
          fieldPath: pathStr,
          slot: "scenes.surface.logoSrc",
          sceneId,
          expectedKinds: ["logo", "image"],
        });
      }

      // content
      const content = scene.content;
      if (content && typeof content === "object") {
        // content.images
        if (Array.isArray(content.images)) {
          content.images.forEach((imgRef: any, imgIdx: number) => {
            if (imgRef !== null && imgRef !== undefined) {
              const pathStr = `scenes[${sIdx}].content.images[${imgIdx}]`;
              const p = parseAssetRef(imgRef, pathStr, sceneId);
              occurrences.push({
                rawRef: imgRef,
                parsed: p,
                fieldPath: pathStr,
                slot: "scenes.content.images",
                sceneId,
                expectedKinds: ["image"],
              });
            }
          });
        }

        // content.screen
        if (content.screen) {
          const pathStr = `scenes[${sIdx}].content.screen`;
          const p = parseAssetRef(content.screen, pathStr, sceneId);
          occurrences.push({
            rawRef: content.screen,
            parsed: p,
            fieldPath: pathStr,
            slot: "scenes.content.screen",
            sceneId,
            expectedKinds: ["image", "video"],
          });
        }

        // content.icons
        if (Array.isArray(content.icons)) {
          content.icons.forEach((iconRef: any, iconIdx: number) => {
            if (iconRef !== null && iconRef !== undefined) {
              const pathStr = `scenes[${sIdx}].content.icons[${iconIdx}]`;
              const p = parseAssetRef(iconRef, pathStr, sceneId);
              occurrences.push({
                rawRef: iconRef,
                parsed: p,
                fieldPath: pathStr,
                slot: "scenes.content.icons",
                sceneId,
                expectedKinds: ["icon", "image"],
              });
            }
          });
        }

        // content.audioRef
        if (content.audioRef) {
          const pathStr = `scenes[${sIdx}].content.audioRef`;
          const p = parseAssetRef(content.audioRef, pathStr, sceneId);
          occurrences.push({
            rawRef: content.audioRef,
            parsed: p,
            fieldPath: pathStr,
            slot: "scenes.content.audioRef",
            sceneId,
            expectedKinds: ["audio", "vo", "music", "sfx"],
          });
        }

        // content.path
        if (content.path && typeof content.path === "string" && !content.path.startsWith("M") && !content.path.startsWith("m")) {
          if (ASSET_ID_REGEX.test(content.path)) {
            const pathStr = `scenes[${sIdx}].content.path`;
            const p = parseAssetRef(content.path, pathStr, sceneId);
            occurrences.push({
              rawRef: content.path,
              parsed: p,
              fieldPath: pathStr,
              slot: "scenes.content.path",
              sceneId,
              expectedKinds: ["image", "video", "other"],
            });
          }
        }
      }
    });
  }

  return occurrences;
}

// ─── 4. Fail-Closed Resolver Authority (ASSET-012) ───────────────────────────

export function resolveAssetReference(
  ref: any,
  mediaMap: Record<string, string> | undefined | null,
  options?: {
    fieldPath?: string;
    sceneId?: string;
    projectId?: string;
  }
): string {
  if (ref === null || ref === undefined) {
    throw new MalformedAssetRefError({
      rawRef: ref,
      reason: "Asset reference cannot be null or undefined",
      fieldPath: options?.fieldPath,
      sceneId: options?.sceneId,
    });
  }

  const parsed = parseAssetRef(ref, options?.fieldPath, options?.sceneId);

  if (parsed.isUrl) {
    return parsed.url!;
  }

  const aid = parsed.assetId!;

  if (!mediaMap) {
    throw new UnknownAssetReferenceError({
      assetId: aid,
      fieldPath: options?.fieldPath,
      sceneId: options?.sceneId,
      projectId: options?.projectId,
      message: `UNKNOWN_ASSET_REFERENCE: Logical asset '${aid}' cannot be resolved because media_map is missing or empty`,
    });
  }

  if (Object.prototype.hasOwnProperty.call(mediaMap, aid)) {
    return mediaMap[aid];
  }

  throw new UnknownAssetReferenceError({
    assetId: aid,
    fieldPath: options?.fieldPath,
    sceneId: options?.sceneId,
    projectId: options?.projectId,
  });
}

// ─── 5. Media Map Loader (LED-033) ───────────────────────────────────────────

export function loadRequiredMediaMap(
  projectDir: string,
  options?: { isMandatory?: boolean; state?: string }
): Record<string, string> {
  let fsModule: any = null;
  try {
    if (typeof process !== "undefined" && process?.versions?.node) {
      fsModule = eval("require")("fs");
    }
  } catch {
    fsModule = null;
  }
  if (!fsModule) return {};

  const mapPath = joinPath(projectDir, "media_map.json");
  const isMandatory = options?.isMandatory !== undefined ? options.isMandatory : true;

  if (!fsModule.existsSync(mapPath)) {
    if (isMandatory) {
      throw new RequiredArtifactMissingError("media_map.json", projectDir, options?.state);
    }
    return {};
  }

  let parsed: any;
  try {
    const raw = fsModule.readFileSync(mapPath, "utf-8");
    parsed = JSON.parse(raw);
  } catch (err: any) {
    throw new ArtifactCorruptedError("media_map.json", `Malformed JSON: ${err.message}`, projectDir);
  }

  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
    throw new ArtifactCorruptedError("media_map.json", `media_map must be a JSON object, got ${typeof parsed}`, projectDir);
  }

  return parsed as Record<string, string>;
}
