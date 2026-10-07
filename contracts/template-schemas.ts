import { z } from "zod";
import {
  HexColorSchema,
  FontKeySchema,
  AnimationIdSchema,
  StyleOverrideSchema,
  PositionSchema,
  GradientSchema,
  SceneContentSchema,
} from "./blueprint";
export type SchemaFieldType =
  | "text"
  | "number"
  | "color"
  | "select"
  | "range"
  | "fontKey"
  | "animation"
  | "anchor"
  | "boolean"
  | "logo";

export interface SchemaField {
  type: SchemaFieldType;
  label: { ar: string; en: string };
  min?: number;
  max?: number;
  step?: number;
  options?: string[];
  default?: any;
  placeholder?: string;
}

// ─── 1. Error Definition ──────────────────────────────────────────────────────

export class InvalidTemplatePayloadError extends Error {
  public readonly code = "INVALID_TEMPLATE_PAYLOAD";
  public readonly templateId: string;
  public readonly sceneId: string;
  public readonly fieldPath: string;
  public readonly reason: string;
  public readonly details: Record<string, any>;

  constructor(options: {
    templateId: string;
    sceneId: string;
    fieldPath: string;
    reason: string;
    details?: Record<string, any>;
  }) {
    const msg = `INVALID_TEMPLATE_PAYLOAD: Template '${options.templateId}' in scene '${options.sceneId}' failed validation at '${options.fieldPath}': ${options.reason}`;
    super(msg);
    this.name = "InvalidTemplatePayloadError";
    this.templateId = options.templateId;
    this.sceneId = options.sceneId;
    this.fieldPath = options.fieldPath;
    this.reason = options.reason;
    this.details = options.details || {};
  }
}

// ─── 2. Strict Surface Schema (Trust Boundary - S16 LED-045) ─────────────────
// Does NOT use .passthrough() to prevent leaking arbitrary unvalidated keys to template mount

export const StrictStyleSurfaceSchema = z.object({
  text: z.string().optional(),
  subtext: z.string().optional(),
  emphasis: z.string().optional(),
  fontSize: z.number().min(8).max(400).optional(),
  fontWeight: z.union([z.number(), z.string()]).optional(),
  fontFamily: FontKeySchema.optional(),
  letterSpacing: z.string().optional(),
  textAlign: z.enum(["right", "center", "left", "start", "end"]).optional(),
  lineHeight: z.number().min(0.5).max(4).optional(),
  color: HexColorSchema.optional(),
  background: HexColorSchema.optional(),
  gradient: GradientSchema.optional(),
  opacity: z.number().min(0).max(1).optional(),
  position: PositionSchema.optional(),
  scale: z.number().min(0.1).max(10).optional(),
  rotation: z.number().min(-360).max(360).optional(),
  width: z.number().min(1).optional(),
  height: z.number().min(1).optional(),
  animation: AnimationIdSchema.optional(),
  speed: z.number().min(0.1).max(5).optional(),
  delay: z.number().min(0).optional(),
  mode: z.enum(["light", "dark"]).optional(),
  logoSrc: z.string().optional(),
  brandName: z.string().optional(),
  styleOverride: StyleOverrideSchema.optional(),
  coverage_pct: z.number().min(0).max(100).optional(),
  layer: z.number().min(1).max(5).optional(),
});
export type StrictStyleSurface = z.infer<typeof StrictStyleSurfaceSchema>;

// Set of recognized style surface keys for clean property separation
export const SURFACE_FIELD_KEYS = new Set(Object.keys(StrictStyleSurfaceSchema.shape));

// ─── 3. Template Family Schemas ──────────────────────────────────────────────

// DataStory Family (rui-data-story, DataStoryWrapper)
export const ChartDatumSchema = z.object({
  label: z.string(),
  value: z.number(),
  color: z.string().optional(),
  delta: z.string().optional(),
});

export const MetricTickerItemSchema = z.object({
  label: z.string(),
  value: z.number(),
  from: z.number().optional(),
  suffix: z.string().optional(),
  prefix: z.string().optional(),
  delta: z.string().optional(),
  trend: z.array(z.number()).optional(),
  color: z.string().optional(),
});

export const TimelineStepSchema = z.object({
  title: z.string(),
  description: z.string().optional(),
});

export const DataStoryPropsSchema = z.object({
  title: z.string().optional(),
  subtitle: z.string().optional(),
  barData: z.array(ChartDatumSchema).optional(),
  metrics: z.array(MetricTickerItemSchema).optional(),
  steps: z.array(TimelineStepSchema).optional(),
  chartTitle: z.string().optional(),
  metricsTitle: z.string().optional(),
  timelineTitle: z.string().optional(),
  insight: z.string().optional(),
  endMessage: z.string().optional(),
  ctaLabel: z.string().optional(),
}).strict();

// AnimatedText Family (animatedtext-element, typewriter-element)
export const AnimatedTextPropsSchema = z.object({
  transition: z.object({
    split: z.enum(["none", "word", "character", "line"]).or(z.string()).optional(),
    splitStagger: z.number().optional(),
    glitch: z.any().optional(),
    cycle: z.object({
      texts: z.array(z.string()),
      itemDuration: z.number().min(1),
    }).optional(),
  }).strict().optional(),
  style: z.record(z.string(), z.any()).optional(),
  className: z.string().optional(),
}).strict();

// AnimatedCounter Family (animatedcounter-element)
export const AnimatedCounterPropsSchema = z.object({
  from: z.number().optional(),
  to: z.number().optional(),
  prefix: z.string().optional(),
  suffix: z.string().optional(),
  style: z.record(z.string(), z.any()).optional(),
}).strict();

// CodeBlock Family (codeblock-element)
export const CodeBlockPropsSchema = z.object({
  language: z.string().optional(),
  fontSize: z.number().optional(),
  theme: z.string().optional(),
  highlightLines: z.array(z.number()).optional(),
  style: z.record(z.string(), z.any()).optional(),
}).strict();

// ─── 4. Dynamic Schema Builder for Declared Schema Fields ────────────────────

export function buildPropsSchemaFromFields(schemaFields: Record<string, SchemaField>): z.ZodType<any> {
  const shape: Record<string, z.ZodType<any>> = {};
  
  for (const [fieldName, fieldDef] of Object.entries(schemaFields)) {
    const fieldType = fieldDef.type;
    if (fieldType === "number") {
      shape[fieldName] = z.number().optional();
    } else if (fieldType === "color") {
      shape[fieldName] = HexColorSchema.optional();
    } else if (fieldType === "fontKey") {
      shape[fieldName] = FontKeySchema.optional();
    } else if (fieldType === "animation") {
      shape[fieldName] = AnimationIdSchema.optional();
    } else if (fieldType === "boolean") {
      shape[fieldName] = z.boolean().optional();
    } else if (fieldType === "select" && Array.isArray(fieldDef.options) && fieldDef.options.length > 0) {
      shape[fieldName] = z.enum(fieldDef.options as [string, ...string[]]).optional();
    } else {
      shape[fieldName] = z.string().optional();
    }
  }

  return z.object(shape).strict();
}

// ─── 5. Resolve Schemas for a Template Entry ─────────────────────────────────

export interface TemplateSchemas {
  contentSchema: z.ZodTypeAny;
  propsSchema: z.ZodTypeAny;
  surfaceSchema: z.ZodTypeAny;
}

export function resolveTemplateSchemas(
  canonicalId: string,
  schemaFields: Record<string, SchemaField>,
  defaults: Record<string, any>
): TemplateSchemas {
  // 1. DataStory Family
  if (canonicalId === "rui-data-story" || canonicalId === "DataStoryWrapper") {
    return {
      contentSchema: SceneContentSchema,
      propsSchema: DataStoryPropsSchema,
      surfaceSchema: StrictStyleSurfaceSchema,
    };
  }

  // 2. AnimatedText Family
  if (canonicalId === "animatedtext-element" || canonicalId === "typewriter-element") {
    return {
      contentSchema: SceneContentSchema,
      propsSchema: AnimatedTextPropsSchema,
      surfaceSchema: StrictStyleSurfaceSchema,
    };
  }

  // 3. AnimatedCounter Family
  if (canonicalId === "animatedcounter-element") {
    return {
      contentSchema: SceneContentSchema,
      propsSchema: AnimatedCounterPropsSchema,
      surfaceSchema: StrictStyleSurfaceSchema,
    };
  }

  // 4. CodeBlock Family
  if (canonicalId === "codeblock-element") {
    return {
      contentSchema: SceneContentSchema,
      propsSchema: CodeBlockPropsSchema,
      surfaceSchema: StrictStyleSurfaceSchema,
    };
  }

  // 5. Default/Generic Registry Templates (deriving typed schema from declared schema fields)
  return {
    contentSchema: SceneContentSchema,
    propsSchema: buildPropsSchemaFromFields(schemaFields),
    surfaceSchema: StrictStyleSurfaceSchema,
  };
}

// ─── 6. Validate Template Payload Fail-Closed ─────────────────────────────────

export function validateTemplatePayload(
  entry: {
    id: string;
    schema?: Record<string, any>;
    contentSchema?: any;
    propsSchema?: any;
    surfaceSchema?: any;
    [key: string]: any;
  },
  scene: {
    scene_id: string;
    template: string;
    surface?: any;
    content?: any;
    template_props?: any;
  },
  fieldPathPrefix = `scenes[${scene.scene_id}]`
): void {
  const schemas: TemplateSchemas = {
    contentSchema: entry.contentSchema || SceneContentSchema,
    propsSchema: entry.propsSchema || buildPropsSchemaFromFields(entry.schema || {}),
    surfaceSchema: entry.surfaceSchema || StrictStyleSurfaceSchema,
  };

  // 1. Validate template_props
  if (scene.template_props !== undefined && scene.template_props !== null) {
    const propsRes = schemas.propsSchema.safeParse(scene.template_props);
    if (!propsRes.success) {
      const issue = propsRes.error.issues[0];
      const issuePath = issue ? issue.path.join(".") : "";
      const fullPath = issuePath ? `${fieldPathPrefix}.template_props.${issuePath}` : `${fieldPathPrefix}.template_props`;
      throw new InvalidTemplatePayloadError({
        templateId: entry.id,
        sceneId: scene.scene_id,
        fieldPath: fullPath,
        reason: issue?.message || "Invalid template_props",
        details: { issues: propsRes.error.issues },
      });
    }
  }

  // 2. Validate surface (if explicitly supplied)
  if (scene.surface !== undefined && scene.surface !== null) {
    const surfaceRes = schemas.surfaceSchema.safeParse(scene.surface);
    if (!surfaceRes.success) {
      const issue = surfaceRes.error.issues[0];
      const issuePath = issue ? issue.path.join(".") : "";
      const fullPath = issuePath ? `${fieldPathPrefix}.surface.${issuePath}` : `${fieldPathPrefix}.surface`;
      throw new InvalidTemplatePayloadError({
        templateId: entry.id,
        sceneId: scene.scene_id,
        fieldPath: fullPath,
        reason: issue?.message || "Invalid surface properties",
        details: { issues: surfaceRes.error.issues },
      });
    }
  }

  // 3. Validate content (if explicitly supplied)
  if (scene.content !== undefined && scene.content !== null) {
    const contentRes = schemas.contentSchema.safeParse(scene.content);
    if (!contentRes.success) {
      const issue = contentRes.error.issues[0];
      const issuePath = issue ? issue.path.join(".") : "";
      const fullPath = issuePath ? `${fieldPathPrefix}.content.${issuePath}` : `${fieldPathPrefix}.content`;
      throw new InvalidTemplatePayloadError({
        templateId: entry.id,
        sceneId: scene.scene_id,
        fieldPath: fullPath,
        reason: issue?.message || "Invalid content properties",
        details: { issues: contentRes.error.issues },
      });
    }
  }
}
