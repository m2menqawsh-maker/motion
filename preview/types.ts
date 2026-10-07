/**
 * preview/types.ts — Browser Live Preview Runtime Type Contracts.
 * S28-R06: Engine-independent preview data structures, visual node tree,
 * playback state, and diagnostic event definitions.
 * ZERO Remotion runtime, TSX, or React authority dependencies.
 */
import type { EvaluatedTransform, EvaluatedFrameState } from "../contracts/evaluator";
import type { ChangeSet } from "../contracts/mutations";
import type { PreviewQualityLevel, PreviewCapabilityAssessment } from "../contracts/preview-fidelity";

export type PreviewPlaybackState = "idle" | "playing" | "paused";

export interface CanvasDimensions {
  width: number;
  height: number;
}

export type AspectRatioString = "16:9" | "9:16" | "1:1" | "4:5" | string;

export type VisualNodeType = "text" | "image" | "shape" | "group";

export interface VisualNode {
  id: string;
  kind: VisualNodeType;
  zIndex: number;
  visible: boolean;
  opacity: number;
  localFrame: number;
  transform: EvaluatedTransform;
  computedStyles: Record<string, string | number>;
  // Layer-specific data
  text?: string;
  assetRef?: string;
  objectFit?: "contain" | "cover" | "fill" | "none";
  crop?: { x: number; y: number; width: number; height: number };
  shapeType?: "rectangle" | "ellipse" | "path";
  shapeFill?: string;
  shapeStroke?: string;
  shapeStrokeWidth?: number;
  shapeBorderRadius?: number;
  pathData?: string;
  children?: VisualNode[];
  attributes?: Record<string, string>;
  previewQuality?: PreviewQualityLevel;
  proxyArtifactId?: string;
  approximationDetails?: { isApproximated: boolean; originalFeature: string; reason: string };
}

export interface TransitionProgression {
  type: string;
  progress: number; // 0.0 to 1.0
  durationFrames: number;
  fromSceneId: string;
  toSceneId: string;
  outgoingOpacity: number;
  incomingOpacity: number;
  outgoingTranslateX: number;
  incomingTranslateX: number;
}

export interface UnsupportedCapabilityDetail {
  entityId: string;
  entityType: "template" | "layer" | "transition" | "effect";
  classification: string;
  reason: string;
  requiredCapabilities: string[];
}

export interface UnsupportedCapabilityReport {
  isSupported: boolean;
  unsupportedEntities: UnsupportedCapabilityDetail[];
  missingCapabilities: string[];
}

export interface VisualFrame {
  frame: number;
  fps: number;
  timeMs: number;
  durationFrames: number;
  durationMs: number;
  dimensions: CanvasDimensions;
  aspectRatio: string;
  activeScenes: string[];
  nodes: VisualNode[];
  transition?: TransitionProgression;
  unsupportedReport?: UnsupportedCapabilityReport;
  previewQuality?: PreviewQualityLevel;
  fidelityAssessment?: PreviewCapabilityAssessment;
}

export interface PreviewRuntimeConfig {
  autoplay?: boolean;
  loop?: boolean;
  playbackRate?: number;
  failClosedOnUnsupported?: boolean;
  clockMode?: "requestAnimationFrame" | "timer" | "manual";
  defaultDimensions?: CanvasDimensions;
  enableAudio?: boolean;
  audioRuntime?: any;
  proxyCoordinator?: any;
}

export interface PreviewEventMap {
  frame: (frame: number, timeMs: number, visualFrame: VisualFrame) => void;
  play: () => void;
  pause: () => void;
  seek: (frame: number) => void;
  ended: () => void;
  resize: (dimensions: CanvasDimensions, aspectRatio: string) => void;
  documentChange: (revision: number, changeSet?: ChangeSet) => void;
  unsupportedCapability: (report: UnsupportedCapabilityReport) => void;
  proxyApplied: (artifactId: string, sceneId?: string, layerId?: string) => void;
  proxyInvalidated: (count: number) => void;
  error: (err: Error) => void;
}
