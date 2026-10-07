/**
 * contracts/effects.ts — Authoritative Canonical Semantic Effects Contract.
 * S28-R02: Pure declarative effect definitions, schemas, and semantic validation.
 * ZERO React or Remotion dependencies.
 */
import { z } from "zod";

export type EffectKind = "wrapper" | "overlay" | "behavior" | "unbridged" | "primitive";

export interface EffectSemanticDefinition {
  id: string;
  kind: EffectKind;
  paramsSchema: Record<string, any>;
  executable: boolean;
  version?: string;
  category?: string;
  semantic_behavior?: string;
  required_capabilities?: string[];
  sourcePath?: string;
  reason?: string;
}

export const SEMANTIC_EFFECTS_CATALOG: Record<string, EffectSemanticDefinition> = {
  "AppFromDescriptor": {
    id: "AppFromDescriptor",
    kind: "unbridged",
    paramsSchema: {},
    executable: false,
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/AppFromDescriptor.tsx",
    reason: "Transitive dependency error"
  },
  "AppShell": {
    id: "AppShell",
    kind: "unbridged",
    paramsSchema: {},
    executable: false,
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/AppShell.tsx",
    reason: "Transitive dependency error"
  },
  "AudioManager": {
    id: "AudioManager",
    kind: "primitive",
    paramsSchema: {},
    executable: true,
    category: "audio",
    semantic_behavior: "Background audio management and ducking coordination"
  },
  "AutoZoom": {
    id: "AutoZoom",
    kind: "unbridged",
    paramsSchema: {},
    executable: false,
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/camera/AutoZoom.tsx",
    reason: "Invalid relative import to ../../tokens"
  },
  "Avatar": {
    id: "Avatar",
    kind: "unbridged",
    paramsSchema: {},
    executable: false,
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/Avatar.tsx",
    reason: "Transitive dependency error"
  },
  "Badge": {
    id: "Badge",
    kind: "unbridged",
    paramsSchema: {},
    executable: false,
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/Badge.tsx",
    reason: "Transitive dependency error"
  },
  "Button": {
    id: "Button",
    kind: "unbridged",
    paramsSchema: {},
    executable: false,
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/Button.tsx",
    reason: "Cannot find module '../../engine/ui-state'"
  },
  "CameraRig": {
    id: "CameraRig",
    kind: "primitive",
    paramsSchema: {},
    executable: true,
    category: "camera",
    semantic_behavior: "Camera pan, tilt, zoom and transform viewport coordination"
  },
  "ChaosDesktop": {
    id: "ChaosDesktop",
    kind: "unbridged",
    paramsSchema: {},
    executable: false,
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/scenes/ChaosDesktop.tsx",
    reason: "Cannot find module '../engine'"
  },
  "Closer": {
    id: "Closer",
    kind: "unbridged",
    paramsSchema: {},
    executable: false,
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/scenes/Closer.tsx",
    reason: "Cannot find module '../content'"
  },
  "CountUp": {
    id: "CountUp",
    kind: "primitive",
    paramsSchema: {},
    executable: true,
    category: "data",
    semantic_behavior: "Numerical increment counter presentation"
  },
  "Cursor": {
    id: "Cursor",
    kind: "unbridged",
    paramsSchema: {},
    executable: false,
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/cursor/Cursor.tsx",
    reason: "Cannot find module '../../CursorInteractionContext'"
  },
  "CursorSprite": {
    id: "CursorSprite",
    kind: "unbridged",
    paramsSchema: {},
    executable: false,
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/cursor/CursorSprite.tsx",
    reason: "Cannot find module '../../tokens'"
  },
  "DataTable": {
    id: "DataTable",
    kind: "unbridged",
    paramsSchema: {},
    executable: false,
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/DataTable.tsx",
    reason: "Cannot find module '../../engine/ui-state'"
  },
  "DynamicWindows": {
    id: "DynamicWindows",
    kind: "unbridged",
    paramsSchema: {},
    executable: false,
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/scenes/DynamicWindows.tsx",
    reason: "Cannot find module '../engine'"
  },
  "EndCard": {
    id: "EndCard",
    kind: "unbridged",
    paramsSchema: {},
    executable: false,
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/EndCard.tsx",
    reason: "Cannot find module '../editor'"
  },
  "Enter": {
    id: "Enter",
    kind: "primitive",
    paramsSchema: {},
    executable: true,
    category: "transition",
    semantic_behavior: "Entrance animation primitive"
  },
  "Exit": {
    id: "Exit",
    kind: "primitive",
    paramsSchema: {},
    executable: true,
    category: "transition",
    semantic_behavior: "Exit animation primitive"
  },
  "FeatureShowcase": {
    id: "FeatureShowcase",
    kind: "unbridged",
    paramsSchema: {},
    executable: false,
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/scenes/FeatureShowcase.tsx",
    reason: "Cannot find module '../engine'"
  },
  "Headline": {
    id: "Headline",
    kind: "unbridged",
    paramsSchema: {},
    executable: false,
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/Headline.tsx",
    reason: "Cannot find module '../editor'"
  },
  "HeadlineResolution": {
    id: "HeadlineResolution",
    kind: "unbridged",
    paramsSchema: {},
    executable: false,
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/scenes/HeadlineResolution.tsx",
    reason: "Cannot find module '../content'"
  },
  "Highlight": {
    id: "Highlight",
    kind: "primitive",
    paramsSchema: {},
    executable: true,
    category: "overlay",
    semantic_behavior: "Visual callout highlighting"
  },
  "LayoutContext": {
    id: "LayoutContext",
    kind: "unbridged",
    paramsSchema: {},
    executable: false,
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/layout/LayoutContext.tsx",
    reason: "Module has no exported member 'LayoutContext'"
  },
  "LayoutWindow": {
    id: "LayoutWindow",
    kind: "unbridged",
    paramsSchema: {},
    executable: false,
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/layout/LayoutWindow.tsx",
    reason: "Transitive dependency error"
  },
  "ListItems": {
    id: "ListItems",
    kind: "unbridged",
    paramsSchema: {},
    executable: false,
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/ListItems.tsx",
    reason: "Transitive dependency error"
  },
  "MessageList": {
    id: "MessageList",
    kind: "unbridged",
    paramsSchema: {},
    executable: false,
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/MessageList.tsx",
    reason: "Cannot find module '../../engine/ui-state'"
  },
  "NotificationToast": {
    id: "NotificationToast",
    kind: "unbridged",
    paramsSchema: {},
    executable: false,
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/NotificationToast.tsx",
    reason: "Cannot find module '../../engine/ui-state'"
  },
  "Panel": {
    id: "Panel",
    kind: "unbridged",
    paramsSchema: {},
    executable: false,
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/Panel.tsx",
    reason: "Cannot find module '../../engine/ui-state'"
  },
  "PanelGrid": {
    id: "PanelGrid",
    kind: "unbridged",
    paramsSchema: {},
    executable: false,
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/PanelGrid.tsx",
    reason: "Transitive dependency error"
  },
  "Placeholder": {
    id: "Placeholder",
    kind: "unbridged",
    paramsSchema: {},
    executable: false,
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/Placeholder.tsx",
    reason: "Transitive dependency error"
  },
  "ProductReveal": {
    id: "ProductReveal",
    kind: "unbridged",
    paramsSchema: {},
    executable: false,
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/scenes/ProductReveal.tsx",
    reason: "Cannot find module '../engine'"
  },
  "Pulse": {
    id: "Pulse",
    kind: "primitive",
    paramsSchema: {},
    executable: true,
    category: "behavior",
    semantic_behavior: "Scale/opacity pulse periodic effect"
  },
  "ScenePush": {
    id: "ScenePush",
    kind: "unbridged",
    paramsSchema: {},
    executable: false,
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/ScenePush.tsx",
    reason: "Cannot find module '../engine/types'"
  },
  "SearchBar": {
    id: "SearchBar",
    kind: "unbridged",
    paramsSchema: {},
    executable: false,
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/SearchBar.tsx",
    reason: "Cannot find module '../../engine/ui-state'"
  },
  "SidebarNav": {
    id: "SidebarNav",
    kind: "unbridged",
    paramsSchema: {},
    executable: false,
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/SidebarNav.tsx",
    reason: "Cannot find module '../../engine/ui-state'"
  },
  "Stagger": {
    id: "Stagger",
    kind: "primitive",
    paramsSchema: {},
    executable: true,
    category: "behavior",
    semantic_behavior: "Staggered sequential reveal of child elements"
  },
  "StatCard": {
    id: "StatCard",
    kind: "unbridged",
    paramsSchema: {},
    executable: false,
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/StatCard.tsx",
    reason: "Transitive dependency error"
  },
  "TabBar": {
    id: "TabBar",
    kind: "unbridged",
    paramsSchema: {},
    executable: false,
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/TabBar.tsx",
    reason: "Cannot find module '../../engine/ui-state'"
  },
  "TopNav": {
    id: "TopNav",
    kind: "unbridged",
    paramsSchema: {},
    executable: false,
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/TopNav.tsx",
    reason: "Transitive dependency error"
  },
  "TrafficLights": {
    id: "TrafficLights",
    kind: "primitive",
    paramsSchema: {},
    executable: true,
    category: "overlay",
    semantic_behavior: "OS-style window control buttons decoration"
  },
  "TypeWriter": {
    id: "TypeWriter",
    kind: "unbridged",
    paramsSchema: {},
    executable: false,
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/TypeWriter.tsx",
    reason: "Transitive dependency error"
  },
  "UIStateProvider": {
    id: "UIStateProvider",
    kind: "unbridged",
    paramsSchema: {},
    executable: false,
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/ui-state/UIStateProvider.tsx",
    reason: "Transitive dependency error"
  },
  "Wallpaper": {
    id: "Wallpaper",
    kind: "primitive",
    paramsSchema: {},
    executable: true,
    category: "overlay",
    semantic_behavior: "Background wallpaper texture overlay"
  },
  "Window": {
    id: "Window",
    kind: "unbridged",
    paramsSchema: {},
    executable: false,
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/Window.tsx",
    reason: "Cannot find module '../VideoPropsContext'"
  },
  "camera-shake": {
    id: "camera-shake",
    kind: "wrapper",
    paramsSchema: {},
    executable: true,
    category: "camera",
    semantic_behavior: "Perlin-noise or spring-based procedural camera shaking"
  }
};

export const EFFECT_IDS = Object.keys(SEMANTIC_EFFECTS_CATALOG) as string[];

export function isKnownEffect(effectId: string): boolean {
  if (typeof effectId !== "string" || !effectId) return false;
  return Boolean(SEMANTIC_EFFECTS_CATALOG[effectId]);
}

export function isExecutableEffect(effectId: string): boolean {
  if (typeof effectId !== "string" || !effectId) return false;
  const entry = SEMANTIC_EFFECTS_CATALOG[effectId];
  return Boolean(entry && entry.executable);
}

export function getExecutableEffectIds(): string[] {
  return EFFECT_IDS.filter((id) => Boolean(SEMANTIC_EFFECTS_CATALOG[id]?.executable));
}

// ─── Semantic Effect Reference Schema (Pure Fail-Closed Validation) ───────────

export const EffectRefSchema = z.object({
  effect: z.string().min(1).superRefine((val: string, ctx: z.RefinementCtx) => {
    if (!isExecutableEffect(val)) {
      const entry = SEMANTIC_EFFECTS_CATALOG[val];
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: entry
          ? `Unsupported effect '${val}' (kind: '${entry.kind}'). Cannot render unbridged effect without runtime component.`
          : `Unknown effect '${val}'. Must be registered in EFFECTS_RUNTIME with an executable component.`,
      });
    }
  }),
  apply: z.enum(["scene", "overlay"]).optional().default("scene"),
  params: z.record(z.string(), z.any()).optional().default({}),
});
export type EffectRef = z.infer<typeof EffectRefSchema>;
