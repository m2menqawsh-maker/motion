/**
 * preview/visual-frame.ts — Evaluated Frame to Visual Tree Assembler.
 * S28-R06: Converts deterministic EvaluatedFrameState into engine-neutral
 * VisualNode hierarchy with CSS styles, bounding boxes, and transition blending.
 * ZERO React or Remotion runtime dependencies.
 */
import {
  evaluateVideoAtFrame,
  type EvaluatedFrameState,
  type EvaluatedLayerState,
  type EvaluatedTransform,
} from "../contracts/evaluator";
import {
  calculateCanonicalDuration,
  frameToMs,
} from "../contracts/timeline";
import type { BlueprintV2, BlueprintScene } from "../contracts/blueprint";
import type { NormalizedVideo, NormalizedScene } from "../contracts/normalization";
import { inspectDocumentCapabilities } from "./capabilities";
import { resolvePreviewFidelity, APPROXIMATABLE_TRANSITIONS } from "../contracts/preview-fidelity";
import type { PreviewProxyArtifact } from "../contracts/preview-proxy";
import { getSemanticTemplateSpec } from "../registry/semantic-registry";
import type {
  VisualFrame,
  VisualNode,
  CanvasDimensions,
  TransitionProgression,
  AspectRatioString,
} from "./types";

/**
 * Resolves default canvas pixel dimensions from canonical aspect ratio string.
 */
export function resolveDimensionsFromAspectRatio(ratio?: AspectRatioString): CanvasDimensions {
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
 * Computes active basic transition between scenes if the playhead falls
 * within an overlapping scene boundary.
 */
function computeActiveTransition(
  scenes: Array<BlueprintScene | NormalizedScene>,
  frame: number,
  dimensions: CanvasDimensions
): { transition?: TransitionProgression; sceneMultipliers: Map<string, { opacity: number; offsetX: number }> } {
  const sceneMultipliers = new Map<string, { opacity: number; offsetX: number }>();
  let activeTransition: TransitionProgression | undefined;

  for (let i = 0; i < scenes.length; i++) {
    const curr = scenes[i];
    const next = scenes[i + 1];
    if (!next || !curr.transition || (curr.transition.durationFrames ?? 0) <= 0) {
      continue;
    }

    const trans = curr.transition;
    const dur = trans.durationFrames;
    const currStart = curr.startFrame ?? 0;
    const currDur = curr.durationFrames ?? 1;
    const currEnd = currStart + currDur;

    // Transition window is located around currEnd
    const transStart = currEnd - dur;
    const transEnd = currEnd;

    if (frame >= transStart && frame < transEnd && dur > 0) {
      const progress = Math.max(0, Math.min(1, (frame - transStart) / dur));
      const transType = trans.type || "fade";

      let outgoingOpacity = 1.0;
      let incomingOpacity = 1.0;
      let outgoingTranslateX = 0;
      let incomingTranslateX = 0;

      if (transType === "fade" || transType === "dissolve") {
        outgoingOpacity = 1.0 - progress;
        incomingOpacity = progress;
      } else if (transType === "slide") {
        outgoingTranslateX = -dimensions.width * progress;
        incomingTranslateX = dimensions.width * (1.0 - progress);
      } else if (transType === "wipe") {
        outgoingOpacity = progress >= 0.5 ? 0 : 1;
        incomingOpacity = progress >= 0.5 ? 1 : 0;
      } else if (APPROXIMATABLE_TRANSITIONS.has(transType)) {
        outgoingOpacity = 1.0 - progress;
        incomingOpacity = progress;
      }

      activeTransition = {
        type: transType,
        progress,
        durationFrames: dur,
        fromSceneId: curr.scene_id,
        toSceneId: next.scene_id,
        outgoingOpacity,
        incomingOpacity,
        outgoingTranslateX,
        incomingTranslateX,
      };

      sceneMultipliers.set(curr.scene_id, { opacity: outgoingOpacity, offsetX: outgoingTranslateX });
      sceneMultipliers.set(next.scene_id, { opacity: incomingOpacity, offsetX: incomingTranslateX });
      break;
    }
  }

  return { transition: activeTransition, sceneMultipliers };
}

/**
 * Builds computed CSS style dictionary from an evaluated layer transform and properties.
 */
function buildComputedStyles(
  layer: EvaluatedLayerState,
  transitionMultiplier: { opacity: number; offsetX: number },
  canvasDimensions: CanvasDimensions
): Record<string, string | number> {
  const t = layer.transform;
  const netOpacity = Math.max(0, Math.min(1, layer.opacity * transitionMultiplier.opacity));
  const netX = t.x + transitionMultiplier.offsetX;
  const netY = t.y;

  // Center-based coordinate system
  const centerX = canvasDimensions.width / 2 + netX;
  const centerY = canvasDimensions.height / 2 + netY;

  const transformCss = `translate(-50%, -50%) rotate(${t.rotation}deg) scale(${t.scaleX}, ${t.scaleY})`;

  const styles: Record<string, string | number> = {
    position: "absolute",
    left: `${centerX}px`,
    top: `${centerY}px`,
    transform: transformCss,
    transformOrigin: "center center",
    opacity: netOpacity,
    display: layer.visible && netOpacity > 0 ? "block" : "none",
    pointerEvents: "none",
    boxSizing: "border-box",
  };

  const props = layer.properties ?? {};

  if (layer.kind === "text") {
    const typo = props.typography ?? {};
    styles.fontFamily = typo.fontFamily || props.fontFamily || "Cairo, sans-serif";
    styles.fontSize = `${typo.fontSize || props.fontSize || 48}px`;
    styles.color = typo.fillColor || typo.color || "#FFFFFF";
    styles.textAlign = typo.textAlign || "center";
    if (typo.fontWeight) styles.fontWeight = typo.fontWeight;
    if (typo.fontStyle) styles.fontStyle = typo.fontStyle;
    if (typo.lineHeight) styles.lineHeight = typo.lineHeight;
    if (typo.letterSpacing) styles.letterSpacing = typo.letterSpacing;
    if (typo.strokeWidth && typo.strokeColor) {
      styles.WebkitTextStroke = `${typo.strokeWidth}px ${typo.strokeColor}`;
    }
    styles.whiteSpace = "pre-wrap";
    styles.userSelect = "none";
  } else if (layer.kind === "shape") {
    const size = props.size ?? { width: 200, height: 100 };
    styles.width = `${size.width}px`;
    styles.height = `${size.height}px`;

    if (props.fillColor) {
      styles.backgroundColor = props.fillColor;
    }
    if (props.borderRadius) {
      styles.borderRadius = `${props.borderRadius}px`;
    }
    if (props.shape_type === "ellipse") {
      styles.borderRadius = "50%";
    }
    if (props.strokeWidth && props.strokeColor) {
      styles.border = `${props.strokeWidth}px solid ${props.strokeColor}`;
    }
  } else if (layer.kind === "image" || layer.kind === "video") {
    styles.objectFit = props.fit || "contain";
  }

  return styles;
}

/**
 * Pure function: Assembles a VisualFrame representing the exact visual preview
 * of the canonical video document at frame N.
 */
export function buildVisualFrame(
  doc: BlueprintV2 | NormalizedVideo | any,
  frame: number,
  overrideDimensions?: CanvasDimensions,
  activeProxies?: Map<string, PreviewProxyArtifact> | Record<string, PreviewProxyArtifact>
): VisualFrame {
  const fps = doc.fps ?? 30;
  const scenes: Array<BlueprintScene | NormalizedScene> = doc.scenes ?? [];
  const durationFrames = calculateCanonicalDuration(scenes);
  const timeMs = frameToMs(frame, fps);
  const durationMs = frameToMs(durationFrames, fps);

  const aspectRatio: AspectRatioString = doc.aspect_ratio || "16:9";
  const dimensions = overrideDimensions || resolveDimensionsFromAspectRatio(aspectRatio);

  const getProxy = (id: string): PreviewProxyArtifact | undefined => {
    if (!activeProxies) return undefined;
    if (activeProxies instanceof Map) return activeProxies.get(id);
    return (activeProxies as Record<string, PreviewProxyArtifact>)[id];
  };

  // 1. Evaluate discrete frame state using pure R03 evaluator
  const evalState: EvaluatedFrameState = evaluateVideoAtFrame(doc, frame);

  // 2. Check for active transitions between scenes
  const { transition, sceneMultipliers } = computeActiveTransition(scenes, frame, dimensions);

  // 3. Capability & Fidelity detection
  const unsupportedReport = inspectDocumentCapabilities(doc);
  const fidelityAssessment = resolvePreviewFidelity(doc);
  let overallQuality = fidelityAssessment.quality_level;

  // 4. Transform evaluated layers into visual node tree
  const visualNodes: VisualNode[] = [];
  const nodeMap = new Map<string, VisualNode>();

  for (let i = 0; i < evalState.layers.length; i++) {
    const layer = evalState.layers[i];
    if (!layer.visible) continue;

    const props = layer.properties ?? {};

    // Match transition multiplier by exact scene_id
    let transitionMult = { opacity: 1.0, offsetX: 0 };
    if (layer.scene_id && sceneMultipliers.has(layer.scene_id)) {
      transitionMult = sceneMultipliers.get(layer.scene_id)!;
    }

    const computedStyles = buildComputedStyles(layer, transitionMult, dimensions);
    const zIndex = (layer as any).z_index ?? i;

    // Check if layer has active proxy
    const layerProxy = getProxy(layer.layer_id);

    const node: VisualNode = {
      id: layer.layer_id,
      kind: layerProxy ? "image" : (layer.kind as any),
      zIndex,
      visible: layer.visible,
      opacity: layer.opacity * transitionMult.opacity,
      localFrame: layer.localFrame,
      transform: layer.transform,
      computedStyles,
      previewQuality: layerProxy ? "proxy" : "native",
      proxyArtifactId: layerProxy?.id,
    };

    if (layerProxy) {
      node.assetRef = layerProxy.output.dataUrl || layerProxy.output.filePath;
      node.objectFit = "contain";
    } else if (layer.kind === "text") {
      node.text = props.text ?? "";
    } else if (layer.kind === "image" || layer.kind === "video") {
      node.assetRef = props.asset_ref;
      node.objectFit = props.fit ?? "contain";
      if (props.crop) node.crop = props.crop;
    } else if (layer.kind === "shape") {
      node.shapeType = props.shape_type ?? "rectangle";
      node.shapeFill = props.fillColor;
      node.shapeStroke = props.strokeColor;
      node.shapeStrokeWidth = props.strokeWidth;
      node.shapeBorderRadius = props.borderRadius;
      node.pathData = props.pathData;
    } else if (layer.kind === "group") {
      node.children = [];
    }

    nodeMap.set(layer.layer_id, node);
    visualNodes.push(node);
  }

  // Check active scenes for ENGINE_BACKED or HYBRID templates needing scene-level proxy
  for (const sceneId of evalState.active_scenes) {
    const scene = scenes.find((s) => s.scene_id === sceneId);
    if (!scene || !scene.template) continue;

    const spec = getSemanticTemplateSpec(scene.template);
    if (spec && (spec.classification === "ENGINE_BACKED" || spec.classification === "LEGACY_COMPATIBILITY")) {
      const sceneProxy = getProxy(scene.scene_id) || getProxy(scene.template);
      if (sceneProxy) {
        const proxyNode: VisualNode = {
          id: `proxy-scene-${scene.scene_id}`,
          kind: "image",
          zIndex: -1,
          visible: true,
          opacity: 1.0,
          localFrame: frame - (scene.startFrame ?? 0),
          transform: { x: 0, y: 0, scaleX: 1, scaleY: 1, rotation: 0, opacity: 1 },
          computedStyles: {
            position: "absolute",
            left: `${dimensions.width / 2}px`,
            top: `${dimensions.height / 2}px`,
            width: `${dimensions.width}px`,
            height: `${dimensions.height}px`,
            transform: "translate(-50%, -50%)",
            objectFit: "contain",
            pointerEvents: "none",
          },
          assetRef: sceneProxy.output.dataUrl || sceneProxy.output.filePath,
          previewQuality: "proxy",
          proxyArtifactId: sceneProxy.id,
        };
        visualNodes.unshift(proxyNode);
        overallQuality = "proxy";
      } else {
        const placeholderNode: VisualNode = {
          id: `placeholder-scene-${scene.scene_id}`,
          kind: "shape",
          zIndex: -1,
          visible: true,
          opacity: 0.9,
          localFrame: frame - (scene.startFrame ?? 0),
          transform: { x: 0, y: 0, scaleX: 1, scaleY: 1, rotation: 0, opacity: 1 },
          computedStyles: {
            position: "absolute",
            left: `${dimensions.width / 2}px`,
            top: `${dimensions.height / 2}px`,
            width: `${dimensions.width}px`,
            height: `${dimensions.height}px`,
            transform: "translate(-50%, -50%)",
            backgroundColor: "#1e1e24",
            border: "2px dashed #6366f1",
            boxSizing: "border-box",
            pointerEvents: "none",
          },
          shapeType: "rectangle",
          text: `[Proxy Required: ${scene.template} (rendering...)]`,
          previewQuality: "proxy",
          attributes: { "data-proxy-pending": "true" },
        };
        visualNodes.unshift(placeholderNode);
      }
    }
  }

  // Handle parent-child relationships for group layers
  const rootNodes: VisualNode[] = [];
  for (const node of visualNodes) {
    const originalLayer = evalState.layers.find((l) => l.layer_id === node.id);
    const parentId = originalLayer?.parent_id;

    if (parentId && nodeMap.has(parentId)) {
      const parentNode = nodeMap.get(parentId)!;
      if (!parentNode.children) parentNode.children = [];
      parentNode.children.push(node);
    } else {
      rootNodes.push(node);
    }
  }

  // Sort nodes by zIndex ascending
  rootNodes.sort((a, b) => a.zIndex - b.zIndex);

  return {
    frame,
    fps,
    timeMs,
    durationFrames,
    durationMs,
    dimensions,
    aspectRatio,
    activeScenes: evalState.active_scenes,
    nodes: rootNodes,
    transition,
    unsupportedReport,
    previewQuality: overallQuality,
    fidelityAssessment,
  };
}
