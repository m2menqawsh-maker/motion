import { EFFECT_COMPONENTS } from "../templates/effects/engine-bridge";

export type EffectKind = "wrapper" | "overlay" | "behavior" | "unbridged" | "primitive";

export interface EffectRuntimeEntry {
  id: string;
  kind: EffectKind;
  paramsSchema: any;
  component?: React.ComponentType<any>;
  sourcePath?: string;
  reason?: string;
}

export const EFFECTS_RUNTIME: Record<string, EffectRuntimeEntry> = {
  "AppFromDescriptor": {
    id: "AppFromDescriptor",
    kind: "unbridged",
    paramsSchema: {},
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/AppFromDescriptor.tsx",
    reason: "Transitive dependency error"
  },
  "AppShell": {
    id: "AppShell",
    kind: "unbridged",
    paramsSchema: {},
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/AppShell.tsx",
    reason: "Transitive dependency error"
  },
  "AudioManager": {
    id: "AudioManager",
    kind: "primitive",
    paramsSchema: {},
    component: EFFECT_COMPONENTS["AudioManager"]
  },
  "AutoZoom": {
    id: "AutoZoom",
    kind: "unbridged",
    paramsSchema: {},
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/camera/AutoZoom.tsx",
    reason: "Invalid relative import to ../../tokens"
  },
  "Avatar": {
    id: "Avatar",
    kind: "unbridged",
    paramsSchema: {},
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/Avatar.tsx",
    reason: "Transitive dependency error"
  },
  "Badge": {
    id: "Badge",
    kind: "unbridged",
    paramsSchema: {},
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/Badge.tsx",
    reason: "Transitive dependency error"
  },
  "Button": {
    id: "Button",
    kind: "unbridged",
    paramsSchema: {},
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/Button.tsx",
    reason: "Cannot find module '../../engine/ui-state'"
  },
  "CameraRig": {
    id: "CameraRig",
    kind: "primitive",
    paramsSchema: {},
    component: EFFECT_COMPONENTS["CameraRig"]
  },
  "ChaosDesktop": {
    id: "ChaosDesktop",
    kind: "unbridged",
    paramsSchema: {},
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/scenes/ChaosDesktop.tsx",
    reason: "Cannot find module '../engine'"
  },
  "Closer": {
    id: "Closer",
    kind: "unbridged",
    paramsSchema: {},
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/scenes/Closer.tsx",
    reason: "Cannot find module '../content'"
  },
  "CountUp": {
    id: "CountUp",
    kind: "primitive",
    paramsSchema: {},
    component: EFFECT_COMPONENTS["CountUp"]
  },
  "Cursor": {
    id: "Cursor",
    kind: "unbridged",
    paramsSchema: {},
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/cursor/Cursor.tsx",
    reason: "Cannot find module '../../CursorInteractionContext'"
  },
  "CursorSprite": {
    id: "CursorSprite",
    kind: "unbridged",
    paramsSchema: {},
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/cursor/CursorSprite.tsx",
    reason: "Cannot find module '../../tokens'"
  },
  "DataTable": {
    id: "DataTable",
    kind: "unbridged",
    paramsSchema: {},
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/DataTable.tsx",
    reason: "Cannot find module '../../engine/ui-state'"
  },
  "DynamicWindows": {
    id: "DynamicWindows",
    kind: "unbridged",
    paramsSchema: {},
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/scenes/DynamicWindows.tsx",
    reason: "Cannot find module '../engine'"
  },
  "EndCard": {
    id: "EndCard",
    kind: "unbridged",
    paramsSchema: {},
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/EndCard.tsx",
    reason: "Cannot find module '../editor'"
  },
  "Enter": {
    id: "Enter",
    kind: "primitive",
    paramsSchema: {},
    component: EFFECT_COMPONENTS["Enter"]
  },
  "Exit": {
    id: "Exit",
    kind: "primitive",
    paramsSchema: {},
    component: EFFECT_COMPONENTS["Exit"]
  },
  "FeatureShowcase": {
    id: "FeatureShowcase",
    kind: "unbridged",
    paramsSchema: {},
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/scenes/FeatureShowcase.tsx",
    reason: "Cannot find module '../engine'"
  },
  "Headline": {
    id: "Headline",
    kind: "unbridged",
    paramsSchema: {},
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/Headline.tsx",
    reason: "Cannot find module '../editor'"
  },
  "HeadlineResolution": {
    id: "HeadlineResolution",
    kind: "unbridged",
    paramsSchema: {},
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/scenes/HeadlineResolution.tsx",
    reason: "Cannot find module '../content'"
  },
  "Highlight": {
    id: "Highlight",
    kind: "primitive",
    paramsSchema: {},
    component: EFFECT_COMPONENTS["Highlight"]
  },
  "LayoutContext": {
    id: "LayoutContext",
    kind: "unbridged",
    paramsSchema: {},
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/layout/LayoutContext.tsx",
    reason: "Module has no exported member 'LayoutContext'"
  },
  "LayoutWindow": {
    id: "LayoutWindow",
    kind: "unbridged",
    paramsSchema: {},
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/layout/LayoutWindow.tsx",
    reason: "Transitive dependency error"
  },
  "ListItems": {
    id: "ListItems",
    kind: "unbridged",
    paramsSchema: {},
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/ListItems.tsx",
    reason: "Transitive dependency error"
  },
  "MessageList": {
    id: "MessageList",
    kind: "unbridged",
    paramsSchema: {},
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/MessageList.tsx",
    reason: "Cannot find module '../../engine/ui-state'"
  },
  "NotificationToast": {
    id: "NotificationToast",
    kind: "unbridged",
    paramsSchema: {},
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/NotificationToast.tsx",
    reason: "Cannot find module '../../engine/ui-state'"
  },
  "Panel": {
    id: "Panel",
    kind: "unbridged",
    paramsSchema: {},
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/Panel.tsx",
    reason: "Cannot find module '../../engine/ui-state'"
  },
  "PanelGrid": {
    id: "PanelGrid",
    kind: "unbridged",
    paramsSchema: {},
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/PanelGrid.tsx",
    reason: "Transitive dependency error"
  },
  "Placeholder": {
    id: "Placeholder",
    kind: "unbridged",
    paramsSchema: {},
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/Placeholder.tsx",
    reason: "Transitive dependency error"
  },
  "ProductReveal": {
    id: "ProductReveal",
    kind: "unbridged",
    paramsSchema: {},
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/scenes/ProductReveal.tsx",
    reason: "Cannot find module '../engine'"
  },
  "Pulse": {
    id: "Pulse",
    kind: "primitive",
    paramsSchema: {},
    component: EFFECT_COMPONENTS["Pulse"]
  },
  "ScenePush": {
    id: "ScenePush",
    kind: "unbridged",
    paramsSchema: {},
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/ScenePush.tsx",
    reason: "Cannot find module '../engine/types'"
  },
  "SearchBar": {
    id: "SearchBar",
    kind: "unbridged",
    paramsSchema: {},
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/SearchBar.tsx",
    reason: "Cannot find module '../../engine/ui-state'"
  },
  "SidebarNav": {
    id: "SidebarNav",
    kind: "unbridged",
    paramsSchema: {},
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/SidebarNav.tsx",
    reason: "Cannot find module '../../engine/ui-state'"
  },
  "Stagger": {
    id: "Stagger",
    kind: "primitive",
    paramsSchema: {},
    component: EFFECT_COMPONENTS["Stagger"]
  },
  "StatCard": {
    id: "StatCard",
    kind: "unbridged",
    paramsSchema: {},
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/StatCard.tsx",
    reason: "Transitive dependency error"
  },
  "TabBar": {
    id: "TabBar",
    kind: "unbridged",
    paramsSchema: {},
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/TabBar.tsx",
    reason: "Cannot find module '../../engine/ui-state'"
  },
  "TopNav": {
    id: "TopNav",
    kind: "unbridged",
    paramsSchema: {},
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/TopNav.tsx",
    reason: "Transitive dependency error"
  },
  "TrafficLights": {
    id: "TrafficLights",
    kind: "primitive",
    paramsSchema: {},
    component: EFFECT_COMPONENTS["TrafficLights"]
  },
  "TypeWriter": {
    id: "TypeWriter",
    kind: "unbridged",
    paramsSchema: {},
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/TypeWriter.tsx",
    reason: "Transitive dependency error"
  },
  "UIStateProvider": {
    id: "UIStateProvider",
    kind: "unbridged",
    paramsSchema: {},
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/ui-state/UIStateProvider.tsx",
    reason: "Transitive dependency error"
  },
  "Wallpaper": {
    id: "Wallpaper",
    kind: "primitive",
    paramsSchema: {},
    component: EFFECT_COMPONENTS["Wallpaper"]
  },
  "Window": {
    id: "Window",
    kind: "unbridged",
    paramsSchema: {},
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/Window.tsx",
    reason: "Cannot find module '../VideoPropsContext'"
  },
  "camera-shake": {
    id: "camera-shake",
    kind: "wrapper",
    paramsSchema: {},
    component: EFFECT_COMPONENTS["camera-shake"]
  }
};
