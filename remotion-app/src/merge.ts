/**
 * remotion-app/src/merge.ts — Remotion Compatibility Layer for Video Normalization.
 * S28-R02: Delegates domain normalization to the pure contracts/normalization.ts core normalizer.
 * Preserves 100% backward compatibility for all existing Remotion consumers.
 */
import { BrandKit } from "../../contracts/brand";
import {
  BlueprintScene,
  SceneOverride,
  TransitionRef,
} from "../../contracts/blueprint";
import { SceneContent } from "../../contracts/SceneContent";
import { StyleSurface } from "../../contracts/StyleSurface";
import { TemplateEntry } from "../../registry/types";
import {
  NormalizedScene,
  NormalizedVideo,
  CanonicalVideoInput,
  normalizeScene as coreNormalizeScene,
  normalizeCanonicalVideo as coreNormalizeCanonicalVideo,
} from "../../contracts/normalization";

export type { BlueprintScene, SceneOverride } from "../../contracts/blueprint";
export type { NormalizedScene, NormalizedVideo } from "../../contracts/normalization";

export type MergedScene = NormalizedScene;
export type MergedProject = NormalizedVideo;

export interface ProjectData {
  project: { title: string; fps?: number; [key: string]: any };
  blueprint: { fps?: number; aspect_ratio?: string; scenes: BlueprintScene[]; [key: string]: any };
  brand: BrandKit;
  overrides?: { scenes: Record<string, SceneOverride> };
  asset_manifest?: any;
  media_map?: Record<string, string>;
}

/**
 * Merge and normalize a single scene.
 * Delegates to the pure core normalizer in contracts/normalization.ts.
 */
export function mergeScene(
  scene: BlueprintScene,
  registryEntry: TemplateEntry,
  brand: BrandKit,
  override?: SceneOverride,
  mediaMap?: Record<string, string>,
  projectId?: string
): MergedScene {
  return coreNormalizeScene(scene, registryEntry, brand, override, mediaMap, projectId);
}

/**
 * Merge and normalize a full project.
 * Delegates to the pure core normalizer in contracts/normalization.ts.
 */
export function mergeProject(
  data: ProjectData,
  getRegistryEntry: (template: string) => TemplateEntry | undefined
): MergedProject {
  return coreNormalizeCanonicalVideo(data, {
    getTemplateEntry: getRegistryEntry as any,
    mediaMap: data.media_map,
    defaultBrand: data.brand,
  });
}
