import React from "react";
import { TemplateMeta } from "./types";
import catalogJson from "../../../../ground-truth/template_catalog.json";

// Raw catalog metadata discovered dynamically from SSOT
export const CATALOG_METADATA: TemplateMeta[] = (catalogJson as any[]).map((item) => ({
  ...item,
  quality: item.quality || "B",
}));

// Filter ONLY visual templates (exclude pure .ts backend types/math utilities)
export const VISUAL_TEMPLATES = CATALOG_METADATA.filter(
  (t) => !t.path.endsWith(".ts")
);

export const SCENE_TEMPLATES = VISUAL_TEMPLATES.filter(
  (t) => t.type === "scene" || (t.type === "engine" && t.family === "scenes")
);

export const ELEMENT_TEMPLATES = VISUAL_TEMPLATES.filter(
  (t) => t.type === "element"
);

export const EFFECT_TEMPLATES = VISUAL_TEMPLATES.filter(
  (t) => t.type === "effect" && t.family !== "transitions"
);

export const TRANSITION_TEMPLATES = VISUAL_TEMPLATES.filter(
  (t) => t.family === "transitions"
);

export const ENGINE_TEMPLATES = VISUAL_TEMPLATES.filter(
  (t) => t.type === "engine" && t.family !== "scenes"
);

export const TYPOGRAPHY_TEMPLATES = VISUAL_TEMPLATES.filter(
  (t) => t.family === "typography" || t.family === "captions"
);

export const TOTAL_TEMPLATES_COUNT = CATALOG_METADATA.length;
export const TOTAL_VISUAL_COUNT = VISUAL_TEMPLATES.length;
