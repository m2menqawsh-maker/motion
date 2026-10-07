/**
 * remotion-app/src/CanonicalVideo.tsx
 * Canonical VideoDocument Renderer for Remotion Engine (S28-R09).
 * 
 * Strict architectural boundary:
 *   - Canonical VideoDocument is the sole semantic authority.
 *   - Frame evaluation is driven exclusively by evaluateVideoAtFrame() from contracts/evaluator.ts.
 *   - Audio ducking, mixing, and timing strictly mirror contracts/evaluator.ts.
 *   - Remotion acts strictly as a rendering engine (render tree).
 */
import React, { useEffect, useState, useMemo } from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  Audio,
  Sequence,
  Img,
  delayRender,
  continueRender,
  staticFile,
} from "remotion";
import type { BlueprintV2, BlueprintScene } from "../../contracts/blueprint";
import {
  evaluateVideoAtFrame,
  type EvaluatedFrameState,
  type EvaluatedLayerState,
} from "../../contracts/evaluator";
import type { BrandKit } from "../../contracts/brand";
import { BrandProvider } from "./BrandContext";
import { loadFont, type FontKey } from "./fonts";
import { TEMPLATE_REGISTRY } from "../../registry/template-registry";

export interface CanonicalVideoProps {
  document: BlueprintV2;
  brand?: BrandKit;
}

const DEFAULT_BRAND_KIT: BrandKit = {
  brandName: "Default",
  logoSrc: null,
  colors: {
    primary: "#00F5FF",
    accent: "#FFD700",
    background: "#1a2238",
    text: "#FFFFFF",
  },
  fonts: {
    display: "Cairo",
    body: "IBMPlexSansArabic",
  },
};

/**
 * Resolves a media or audio asset reference into a URL suitable for Remotion.
 */
export function resolveMediaSrc(ref?: any): string {
  if (!ref) return "";
  let resolvedRef = "";
  if (typeof ref === "string") {
    resolvedRef = ref;
  } else if (typeof ref === "object") {
    if (ref.url) return ref.url;
    if (ref.asset_id) resolvedRef = ref.asset_id;
    else return "";
  } else {
    return "";
  }
  if (
    resolvedRef.startsWith("data:") ||
    resolvedRef.startsWith("http://") ||
    resolvedRef.startsWith("https://") ||
    resolvedRef.startsWith("blob:")
  ) {
    return resolvedRef;
  }
  // If logical asset ID without file extension, provide safe SVG data URI
  const hasExtension = /\.[a-zA-Z0-9]+$/.test(resolvedRef);
  if (!hasExtension) {
    return `data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600"><rect width="100%" height="100%" fill="%231a2238"/><text x="50%" y="50%" fill="%23ffffff" font-family="sans-serif" font-size="28" dominant-baseline="middle" text-anchor="middle">${encodeURIComponent(resolvedRef)}</text></svg>`;
  }
  try {
    return staticFile(resolvedRef);
  } catch {
    return `data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600"><rect width="100%" height="100%" fill="%231a2238"/><text x="50%" y="50%" fill="%23ffffff" font-family="sans-serif" font-size="28" dominant-baseline="middle" text-anchor="middle">${encodeURIComponent(resolvedRef)}</text></svg>`;
  }
}

/**
 * Computes transition multipliers for scenes when in transition boundary (parity with preview/visual-frame.ts).
 */
function computeTransitionEffect(
  scenes: BlueprintScene[],
  frame: number,
  canvasWidth: number
): Map<string, { opacity: number; offsetX: number }> {
  const multipliers = new Map<string, { opacity: number; offsetX: number }>();
  if (!Array.isArray(scenes) || scenes.length === 0) return multipliers;

  for (let i = 0; i < scenes.length; i++) {
    const curr = scenes[i];
    const next = scenes[i + 1];
    if (!next || !curr.transition || (curr.transition.durationFrames ?? 0) <= 0) continue;

    const dur = curr.transition.durationFrames ?? 15;
    const currStart = curr.startFrame ?? 0;
    const currDur = curr.durationFrames ?? 1;
    const currEnd = currStart + currDur;

    const transStart = currEnd - dur;
    const transEnd = currEnd;

    if (frame >= transStart && frame < transEnd && dur > 0) {
      const progress = Math.max(0, Math.min(1, (frame - transStart) / dur));
      const transType = curr.transition.type || "fade";

      let outgoingOpacity = 1.0;
      let incomingOpacity = 1.0;
      let outgoingOffsetX = 0;
      let incomingOffsetX = 0;

      if (transType === "fade" || transType === "dissolve") {
        outgoingOpacity = 1.0 - progress;
        incomingOpacity = progress;
      } else if (transType === "slide") {
        outgoingOffsetX = -canvasWidth * progress;
        incomingOffsetX = canvasWidth * (1.0 - progress);
      } else if (transType === "wipe") {
        outgoingOpacity = progress >= 0.5 ? 0 : 1;
        incomingOpacity = progress >= 0.5 ? 1 : 0;
      }

      multipliers.set(curr.scene_id, { opacity: outgoingOpacity, offsetX: outgoingOffsetX });
      multipliers.set(next.scene_id, { opacity: incomingOpacity, offsetX: incomingOffsetX });
    }
  }

  return multipliers;
}

export const CanonicalVideo: React.FC<CanonicalVideoProps> = ({
  document,
  brand = DEFAULT_BRAND_KIT,
}) => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();

  const [handle] = useState(() => delayRender("CanonicalVideo.fonts"));
  const [fontsLoaded, setFontsLoaded] = useState(false);

  // Pre-load required fonts
  useEffect(() => {
    const fontsToLoad = new Set<string>();
    if (brand.fonts?.display) fontsToLoad.add(brand.fonts.display);
    if (brand.fonts?.body) fontsToLoad.add(brand.fonts.body);

    if (Array.isArray(document.scenes)) {
      for (const scene of document.scenes) {
        if ((scene as any)?.surface?.fontFamily) {
          fontsToLoad.add((scene as any).surface.fontFamily);
        }
        if (Array.isArray(scene.layers)) {
          for (const l of scene.layers) {
            if (l.kind === "text" && (l as any).typography?.fontFamily) {
              fontsToLoad.add((l as any).typography.fontFamily);
            }
          }
        }
      }
    }

    if (fontsToLoad.size === 0) {
      fontsToLoad.add("Cairo");
    }

    Promise.all(
      Array.from(fontsToLoad).map((f) => loadFont(f as FontKey).catch(() => {}))
    )
      .catch((err) => console.warn("Failed loading fonts for CanonicalVideo", err))
      .finally(() => {
        setFontsLoaded(true);
        continueRender(handle);
      });
  }, [brand, document, handle]);

  // Evaluate canonical video state at current frame (sole authority)
  const evalState: EvaluatedFrameState = useMemo(() => {
    return evaluateVideoAtFrame(document, frame);
  }, [document, frame]);

  const transitionMap = useMemo(() => {
    return computeTransitionEffect(document.scenes ?? [], frame, width);
  }, [document.scenes, frame, width]);

  if (!fontsLoaded) {
    return null;
  }

  const bgColor = brand.colors?.background || "#1a2238";
  const scenes = document.scenes ?? [];
  const totalFrames =
    (document as any).totalDurationFrames ||
    scenes.reduce(
      (acc: number, s: any) =>
        Math.max(acc, (s.startFrame ?? 0) + (s.durationFrames ?? 0)),
      0
    ) ||
    300;

  return (
    <BrandProvider brand={brand}>
      <AbsoluteFill style={{ backgroundColor: bgColor, overflow: "hidden" }}>
        {/* ─── 1. Canonical Layer Hierarchy ─────────────────────────────────── */}
        {evalState.layers.map((layer, index) => {
          if (!layer.visible) return null;

          const t = layer.transform;
          const sceneMulti = layer.scene_id ? transitionMap.get(layer.scene_id) : undefined;
          const effectiveOpacity = Math.max(
            0,
            Math.min(1, layer.opacity * (sceneMulti ? sceneMulti.opacity : 1.0))
          );
          if (effectiveOpacity <= 0) return null;

          const offsetX = (t.x || 0) + (sceneMulti ? sceneMulti.offsetX : 0);
          const offsetY = t.y || 0;
          const transformStyle = `translate(-50%, -50%) translate(${offsetX}px, ${offsetY}px) rotate(${t.rotation || 0}deg) scale(${t.scaleX || 1}, ${t.scaleY || 1})`;

          const baseStyle: React.CSSProperties = {
            position: "absolute",
            left: "50%",
            top: "50%",
            transform: transformStyle,
            opacity: effectiveOpacity,
            zIndex: index,
            pointerEvents: "none",
          };

          if (layer.kind === "text") {
            const typo = layer.properties.typography || {};
            const fontFamily = typo.fontFamily || brand.fonts?.display || "Cairo";
            const fontSize = typo.fontSize || 48;
            const color = typo.fillColor || brand.colors?.text || "#FFFFFF";
            const textAlign = typo.textAlign || "center";

            return (
              <div
                key={layer.layer_id}
                style={{
                  ...baseStyle,
                  fontFamily,
                  fontSize,
                  color,
                  textAlign,
                  fontWeight: typo.fontWeight || "normal",
                  letterSpacing: typo.letterSpacing ? `${typo.letterSpacing}px` : undefined,
                  lineHeight: typo.lineHeight || 1.2,
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-word",
                  maxWidth: width * 0.9,
                }}
              >
                {layer.properties.text ?? ""}
              </div>
            );
          }

          if (layer.kind === "image") {
            const assetRef = layer.properties.asset_ref;
            const fit = layer.properties.fit || "contain";
            const src = resolveMediaSrc(assetRef);
            if (!src) return null;

            return (
              <div key={layer.layer_id} style={baseStyle}>
                <Img
                  src={src}
                  style={{
                    objectFit: fit,
                    maxWidth: width,
                    maxHeight: height,
                  }}
                />
              </div>
            );
          }

          if (layer.kind === "video") {
            const assetRef = layer.properties.asset_ref;
            const fit = layer.properties.fit || "contain";
            const src = resolveMediaSrc(assetRef);
            if (!src) return null;

            return (
              <div key={layer.layer_id} style={baseStyle}>
                <video
                  src={src}
                  style={{
                    objectFit: fit,
                    maxWidth: width,
                    maxHeight: height,
                  }}
                />
              </div>
            );
          }

          if (layer.kind === "shape") {
            const size = layer.properties.size || { width, height };
            const fillColor = layer.properties.fillColor || "transparent";
            const strokeColor = layer.properties.strokeColor || "transparent";
            const strokeWidth = layer.properties.strokeWidth || 0;
            const borderRadius =
              layer.properties.shape_type === "circle" ? "50%" : layer.properties.borderRadius || 0;

            return (
              <div
                key={layer.layer_id}
                style={{
                  ...baseStyle,
                  width: size.width,
                  height: size.height,
                  backgroundColor: fillColor,
                  borderColor: strokeColor,
                  borderWidth: strokeWidth,
                  borderStyle: strokeWidth > 0 ? "solid" : "none",
                  borderRadius,
                  boxSizing: "border-box",
                  overflow: "hidden",
                }}
              >
                {layer.properties.pathData && (
                  <svg width="100%" height="100%">
                    <path
                      d={layer.properties.pathData}
                      fill={fillColor}
                      stroke={strokeColor}
                      strokeWidth={strokeWidth}
                    />
                  </svg>
                )}
              </div>
            );
          }

          if (layer.kind === "group") {
            return <div key={layer.layer_id} style={baseStyle} />;
          }

          return null;
        })}

        {/* ─── 2. Legacy Template Compatibility Bridge ──────────────────────── */}
        {/* If an active scene has no explicit canonical layers, mount legacy template */}
        {evalState.active_scenes.map((sceneId) => {
          const scene = scenes.find((s) => s.scene_id === sceneId);
          if (!scene) return null;
          if (Array.isArray(scene.layers) && scene.layers.length > 0) return null;

          const entry = TEMPLATE_REGISTRY[scene.template];
          if (!entry || !entry.component) return null;

          const Component = entry.component;
          const startFrame = scene.startFrame ?? 0;
          const durationFrames = scene.durationFrames ?? 30;

          return (
            <Sequence
              key={`legacy-tpl-${sceneId}`}
              from={startFrame}
              durationInFrames={durationFrames}
            >
              <Component
                surface={scene.surface || {}}
                content={scene.content || {}}
                template_props={scene.template_props || {}}
              />
            </Sequence>
          );
        })}

        {/* ─── 3. Canonical Audio Subsystem (R07 Parity with Dynamic Ducking) ── */}
        {/* Voiceover Track */}
        {document.audio?.voiceover && (
          <Sequence
            from={document.audio.voiceover.startFrame ?? 0}
            durationInFrames={
              document.audio.voiceover.durationFrames ??
              (totalFrames - (document.audio.voiceover.startFrame ?? 0))
            }
          >
            <Audio
              src={resolveMediaSrc(document.audio.voiceover.asset_ref)}
              volume={
                document.audio.voiceover.mute
                  ? 0
                  : (document.audio.voiceover.volume ?? 1.0)
              }
            />
          </Sequence>
        )}

        {/* Background Music Track with Dynamic Ducking Evaluation */}
        {document.audio?.music && (
          <Sequence
            from={document.audio.music.startFrame ?? 0}
            durationInFrames={
              document.audio.music.durationFrames ??
              (totalFrames - (document.audio.music.startFrame ?? 0))
            }
          >
            <Audio
              src={resolveMediaSrc(document.audio.music.asset_ref)}
              volume={(f: number) => {
                const absFrame = (document.audio?.music?.startFrame ?? 0) + f;
                const evaluated = evaluateVideoAtFrame(document, absFrame);
                const musicTrack = evaluated.audio.tracks.find((t) => t.kind === "music");
                if (!musicTrack || musicTrack.muted || !musicTrack.active) return 0;
                return musicTrack.volume;
              }}
            />
          </Sequence>
        )}

        {/* Global SFX Tracks */}
        {document.audio?.global_sfx &&
          document.audio.global_sfx.map((sfx, idx) => (
            <Sequence
              key={`global-sfx-${idx}`}
              from={sfx.startFrame ?? 0}
              durationInFrames={sfx.durationFrames ?? 30}
            >
              <Audio
                src={resolveMediaSrc(sfx.asset_ref)}
                volume={sfx.mute ? 0 : (sfx.volume ?? 1.0)}
              />
            </Sequence>
          ))}

        {/* Scene-scoped audio layers */}
        {scenes.flatMap((scene) =>
          (scene.layers || [])
            .filter((l) => l.kind === "audio")
            .map((l) => {
              const start = l.time_range?.startFrame ?? scene.startFrame ?? 0;
              const dur = l.time_range?.durationFrames ?? scene.durationFrames ?? 30;
              return (
                <Sequence
                  key={`scene-audio-${l.layer_id}`}
                  from={start}
                  durationInFrames={dur}
                >
                  <Audio
                    src={resolveMediaSrc((l as any).asset_ref)}
                    volume={l.opacity <= 0 ? 0 : 1.0}
                  />
                </Sequence>
              );
            })
        )}
      </AbsoluteFill>
    </BrandProvider>
  );
};
