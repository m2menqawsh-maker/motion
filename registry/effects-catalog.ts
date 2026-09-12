export interface EffectEntry {
  id: string;
  sourcePath: string;
  kind: string;
  tier: string;
  description: string;
}

export const EFFECTS_CATALOG: EffectEntry[] = [
  {
    id: "AppFromDescriptor",
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/AppFromDescriptor.tsx",
    kind: "primitive",
    tier: "unknown",
    description: "Engine primitive: AppFromDescriptor"
  },
  {
    id: "AppShell",
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/AppShell.tsx",
    kind: "primitive",
    tier: "unknown",
    description: "Engine primitive: AppShell"
  },
  {
    id: "AudioManager",
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/audio/AudioManager.tsx",
    kind: "primitive",
    tier: "unknown",
    description: "Engine primitive: AudioManager"
  },
  {
    id: "AutoZoom",
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/camera/AutoZoom.tsx",
    kind: "primitive",
    tier: "unknown",
    description: "Engine primitive: AutoZoom"
  },
  {
    id: "Avatar",
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/Avatar.tsx",
    kind: "primitive",
    tier: "unknown",
    description: "Engine primitive: Avatar"
  },
  {
    id: "Badge",
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/Badge.tsx",
    kind: "primitive",
    tier: "unknown",
    description: "Engine primitive: Badge"
  },
  {
    id: "Button",
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/Button.tsx",
    kind: "primitive",
    tier: "unknown",
    description: "Engine primitive: Button"
  },
  {
    id: "CameraRig",
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/camera/CameraRig.tsx",
    kind: "primitive",
    tier: "unknown",
    description: "Engine primitive: CameraRig"
  },
  {
    id: "ChaosDesktop",
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/scenes/ChaosDesktop.tsx",
    kind: "primitive",
    tier: "unknown",
    description: "Engine primitive: ChaosDesktop"
  },
  {
    id: "Closer",
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/scenes/Closer.tsx",
    kind: "primitive",
    tier: "unknown",
    description: "Engine primitive: Closer"
  },
  {
    id: "CountUp",
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/CountUp.tsx",
    kind: "primitive",
    tier: "unknown",
    description: "Engine primitive: CountUp"
  },
  {
    id: "Cursor",
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/cursor/Cursor.tsx",
    kind: "primitive",
    tier: "unknown",
    description: "Engine primitive: Cursor"
  },
  {
    id: "CursorSprite",
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/cursor/CursorSprite.tsx",
    kind: "primitive",
    tier: "unknown",
    description: "Engine primitive: CursorSprite"
  },
  {
    id: "DataTable",
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/DataTable.tsx",
    kind: "primitive",
    tier: "unknown",
    description: "Engine primitive: DataTable"
  },
  {
    id: "DynamicWindows",
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/scenes/DynamicWindows.tsx",
    kind: "primitive",
    tier: "unknown",
    description: "Engine primitive: DynamicWindows"
  },
  {
    id: "EndCard",
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/EndCard.tsx",
    kind: "primitive",
    tier: "unknown",
    description: "Engine primitive: EndCard"
  },
  {
    id: "Enter",
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/Enter.tsx",
    kind: "primitive",
    tier: "unknown",
    description: "Engine primitive: Enter"
  },
  {
    id: "Exit",
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/Exit.tsx",
    kind: "primitive",
    tier: "unknown",
    description: "Engine primitive: Exit"
  },
  {
    id: "FeatureShowcase",
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/scenes/FeatureShowcase.tsx",
    kind: "primitive",
    tier: "unknown",
    description: "Engine primitive: FeatureShowcase"
  },
  {
    id: "Headline",
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/Headline.tsx",
    kind: "primitive",
    tier: "unknown",
    description: "Engine primitive: Headline"
  },
  {
    id: "HeadlineResolution",
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/scenes/HeadlineResolution.tsx",
    kind: "primitive",
    tier: "unknown",
    description: "Engine primitive: HeadlineResolution"
  },
  {
    id: "Highlight",
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/Highlight.tsx",
    kind: "primitive",
    tier: "unknown",
    description: "Engine primitive: Highlight"
  },
  {
    id: "LayoutContext",
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/layout/LayoutContext.tsx",
    kind: "primitive",
    tier: "unknown",
    description: "Engine primitive: LayoutContext"
  },
  {
    id: "LayoutWindow",
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/layout/LayoutWindow.tsx",
    kind: "primitive",
    tier: "unknown",
    description: "Engine primitive: LayoutWindow"
  },
  {
    id: "ListItems",
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/ListItems.tsx",
    kind: "primitive",
    tier: "unknown",
    description: "Engine primitive: ListItems"
  },
  {
    id: "MessageList",
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/MessageList.tsx",
    kind: "primitive",
    tier: "unknown",
    description: "Engine primitive: MessageList"
  },
  {
    id: "NotificationToast",
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/NotificationToast.tsx",
    kind: "primitive",
    tier: "unknown",
    description: "Engine primitive: NotificationToast"
  },
  {
    id: "Panel",
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/Panel.tsx",
    kind: "primitive",
    tier: "unknown",
    description: "Engine primitive: Panel"
  },
  {
    id: "PanelGrid",
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/PanelGrid.tsx",
    kind: "primitive",
    tier: "unknown",
    description: "Engine primitive: PanelGrid"
  },
  {
    id: "Placeholder",
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/Placeholder.tsx",
    kind: "primitive",
    tier: "unknown",
    description: "Engine primitive: Placeholder"
  },
  {
    id: "ProductReveal",
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/scenes/ProductReveal.tsx",
    kind: "primitive",
    tier: "unknown",
    description: "Engine primitive: ProductReveal"
  },
  {
    id: "Pulse",
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/Pulse.tsx",
    kind: "primitive",
    tier: "unknown",
    description: "Engine primitive: Pulse"
  },
  {
    id: "ScenePush",
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/ScenePush.tsx",
    kind: "primitive",
    tier: "unknown",
    description: "Engine primitive: ScenePush"
  },
  {
    id: "SearchBar",
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/SearchBar.tsx",
    kind: "primitive",
    tier: "unknown",
    description: "Engine primitive: SearchBar"
  },
  {
    id: "SidebarNav",
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/SidebarNav.tsx",
    kind: "primitive",
    tier: "unknown",
    description: "Engine primitive: SidebarNav"
  },
  {
    id: "Stagger",
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/Stagger.tsx",
    kind: "primitive",
    tier: "unknown",
    description: "Engine primitive: Stagger"
  },
  {
    id: "StatCard",
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/StatCard.tsx",
    kind: "primitive",
    tier: "unknown",
    description: "Engine primitive: StatCard"
  },
  {
    id: "TabBar",
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/TabBar.tsx",
    kind: "primitive",
    tier: "unknown",
    description: "Engine primitive: TabBar"
  },
  {
    id: "TopNav",
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/app-ui/TopNav.tsx",
    kind: "primitive",
    tier: "unknown",
    description: "Engine primitive: TopNav"
  },
  {
    id: "TrafficLights",
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/TrafficLights.tsx",
    kind: "primitive",
    tier: "unknown",
    description: "Engine primitive: TrafficLights"
  },
  {
    id: "TypeWriter",
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/TypeWriter.tsx",
    kind: "primitive",
    tier: "unknown",
    description: "Engine primitive: TypeWriter"
  },
  {
    id: "UIStateProvider",
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/ui-state/UIStateProvider.tsx",
    kind: "primitive",
    tier: "unknown",
    description: "Engine primitive: UIStateProvider"
  },
  {
    id: "Wallpaper",
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/Wallpaper.tsx",
    kind: "primitive",
    tier: "unknown",
    description: "Engine primitive: Wallpaper"
  },
  {
    id: "Window",
    sourcePath: ".agents/plugins/super-video-maker-plugin/engine/primitives/Window.tsx",
    kind: "primitive",
    tier: "unknown",
    description: "Engine primitive: Window"
  },
];
