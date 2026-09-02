import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from 'remotion';
import { Captions } from '../templates/elements/captions/captions/Captions';
import { Camera } from '../lib/onda/primitives/Camera';
import { loadFont } from "@remotion/google-fonts/Alexandria";
import timings from '../../../04_timings.json';

const { fontFamily } = loadFont();

const GridBackground: React.FC = () => (
  <AbsoluteFill style={{ backgroundColor: '#050505' }}>
    <AbsoluteFill
      style={{
        opacity: 0.15,
        backgroundImage: "linear-gradient(rgba(255,255,255,0.2) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.2) 1px, transparent 1px)",
        backgroundSize: `40px 40px`,
        maskImage: "radial-gradient(circle at center, black, transparent 80%)",
      }}
    />
  </AbsoluteFill>
);

export const Scene3: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, width } = useVideoConfig();

  // Segment 2
  const sceneWords = timings.segments[2].words.map((w: any) => ({
    text: w.word.trim(),
    startMs: w.start * 1000,
    endMs: w.end * 1000,
  }));

  const sceneStartGlobalMs = 7.89 * 1000;

  const vw = 4000;
  const vh = 4000;

  const wordPositions = sceneWords.map((word: any, i: number) => {
    if (i === sceneWords.length - 1) {
      return { x: vw / 2, y: vh / 2 };
    }
    const angle = i * 2.39996;
    const radius = 300 + i * 150;
    return {
      x: vw / 2 + Math.cos(angle) * radius,
      y: vh / 2 + Math.sin(angle) * radius,
    };
  });

  let camX = wordPositions[0]?.x ?? vw / 2;
  let camY = wordPositions[0]?.y ?? vh / 2;
  let camZoom = 1;

  for (let i = 1; i < sceneWords.length; i++) {
    const wordStartFrame = (sceneWords[i].startMs - sceneStartGlobalMs) / 1000 * fps;

    const transition = spring({
      frame: frame - wordStartFrame,
      fps,
      config: { damping: 14, mass: 0.8, stiffness: 150 }
    });

    const dx = wordPositions[i].x - wordPositions[i - 1].x;
    const dy = wordPositions[i].y - wordPositions[i - 1].y;

    camX += dx * transition;
    camY += dy * transition;

    const zDip = Math.sin(transition * Math.PI) * 0.5;
    camZoom -= zDip;
  }

  const lastWordStartFrame = (sceneWords[sceneWords.length - 1].startMs - sceneStartGlobalMs) / 1000 * fps;
  const isZoomOutPhase = frame >= lastWordStartFrame;
  const zoomOutProgress = spring({
    frame: isZoomOutPhase ? frame - lastWordStartFrame : 0,
    fps,
    config: { damping: 14, mass: 1, stiffness: 100 }
  });

  camX = interpolate(zoomOutProgress, [0, 1], [camX, vw / 2]);
  camY = interpolate(zoomOutProgress, [0, 1], [camY, vh / 2]);
  camZoom = interpolate(zoomOutProgress, [0, 1], [camZoom, 0.4]);

  return (
    <AbsoluteFill style={{ backgroundColor: '#050505', color: 'white', fontFamily }}>
      <GridBackground />
      <AbsoluteFill>
        <Camera focusX={camX} focusY={camY} zoom={camZoom} viewportWidth={width} viewportHeight={1920}>
          <div style={{ position: 'absolute', width: vw, height: vh, left: 0, top: 0 }}>
            {/* SVG Path tracing */}
            <svg style={{ position: 'absolute', width: vw, height: vh, left: 0, top: 0, pointerEvents: 'none', zIndex: 0 }}>
              <defs>
                <filter id="neon-glow-ai">
                  <feGaussianBlur stdDeviation="8" result="coloredBlur" />
                  <feMerge>
                    <feMergeNode in="coloredBlur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
              </defs>
              {sceneWords.map((word: any, i: number) => {
                if (i === 0) return null;
                const prevPos = wordPositions[i - 1];
                const pos = wordPositions[i];

                const wordStartFrame = (word.startMs - sceneStartGlobalMs) / 1000 * fps;
                const transition = spring({
                  frame: frame - wordStartFrame,
                  fps,
                  config: { damping: 14, mass: 0.8, stiffness: 150 }
                });

                if (transition <= 0.01) return null;

                const currentX = prevPos.x + (pos.x - prevPos.x) * transition;
                const currentY = prevPos.y + (pos.y - prevPos.y) * transition;

                return (
                  <line
                    key={`path-${i}`}
                    x1={prevPos.x}
                    y1={prevPos.y}
                    x2={currentX}
                    y2={currentY}
                    stroke="#b300ff"
                    strokeWidth={15}
                    strokeLinecap="round"
                    strokeDasharray="30 30"
                    filter="url(#neon-glow-ai)"
                    style={{ opacity: 0.6 }}
                  />
                );
              })}
            </svg>

            {sceneWords.map((word: any, i: number) => {
              const wordStartFrame = (word.startMs - sceneStartGlobalMs) / 1000 * fps;
              const wordPop = spring({
                frame: frame - wordStartFrame,
                fps,
                config: { damping: 12, mass: 0.5, stiffness: 200 }
              });

              const nextWordStartFrame = i < sceneWords.length - 1 ? (sceneWords[i + 1].startMs - sceneStartGlobalMs) / 1000 * fps : 99999;
              const isCurrent = frame >= wordStartFrame && frame < nextWordStartFrame;

              return (
                <div
                  key={i}
                  style={{
                    position: 'absolute',
                    left: wordPositions[i].x,
                    top: wordPositions[i].y,
                    transform: `translate(-50%, -50%) scale(${wordPop})`,
                    opacity: wordPop,
                    color: '#ffffff',
                    fontSize: 180,
                    fontWeight: 900,
                    fontFamily,
                    whiteSpace: 'nowrap',
                    textShadow: isCurrent
                      ? '0 0 40px #b300ff, 0 0 80px #d870ff'
                      : '0 0 20px rgba(179, 0, 255, 0.2)',
                    direction: 'rtl'
                  }}
                >
                  {word.text}
                </div>
              );
            })}
          </div>
        </Camera>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
