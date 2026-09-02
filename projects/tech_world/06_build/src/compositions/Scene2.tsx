import React from 'react';
import { AbsoluteFill, Sequence, Series, Audio, staticFile, interpolate, useCurrentFrame, useVideoConfig, spring, Img } from 'remotion';
import { Captions } from '../templates/elements/captions/captions/Captions';
import { SplitScreen } from '../templates/elements/ui/split-screen/SplitScreen';
import { Camera } from '../lib/onda/primitives/Camera';
import NotificationPop from '../templates/elements/ui/notification-pop';
import { loadFont } from "@remotion/google-fonts/Alexandria";
import timings from '../../../04_timings.json';

const { fontFamily } = loadFont();

// A generic Grid background
const GridBackground: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: '#050505' }}>
      <AbsoluteFill
        style={{
          opacity: 0.15,
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.2) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.2) 1px, transparent 1px)",
          backgroundSize: `40px 40px`,
          maskImage: "radial-gradient(circle at center, black, transparent 80%)",
        }}
      />
    </AbsoluteFill>
  );
};

export const Scene2: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps, width } = useVideoConfig();

  const sceneStartGlobal = 5.86;

  // Durations
  const shot1DurationFrames = Math.round((9.7 - 5.86) * fps); // 115 frames
  const shot2DurationFrames = Math.round((12.92 - 9.7) * fps); // 97 frames
  const shot3DurationFrames = Math.round((19.84 - 12.92) * fps); // 208 frames

  // All words for scene 2
  const segments = [timings.segments[1], timings.segments[2], timings.segments[3], timings.segments[4]];
  const allWords = segments.flatMap((s: any) => s.words).map((w: any) => ({
    text: w.word.trim(),
    startMs: w.start * 1000,
    endMs: w.end * 1000,
  }));

  const shot1Words = allWords.filter(w => w.startMs >= 5860 && w.startMs < 9700);
  const shot2Words = allWords.filter(w => w.startMs >= 9700 && w.startMs < 12920);
  const shot3Words = allWords.filter(w => w.startMs >= 12920);

  // Spotlight logic for Shot 1
  const spotlightRadius = interpolate(frame, [0, 45], [0, 60], { extrapolateRight: "clamp" });
  const questionMarkScale = spring({ fps, frame, config: { damping: 12 }, delay: 10 });

  // Letterbox logic for Shot 2
  // Shot 2 local frame starts at shot1DurationFrames
  const shot2LocalFrame = frame - shot1DurationFrames;
  const barHeight = interpolate(shot2LocalFrame, [0, 20], [50, 0], { extrapolateRight: "clamp", extrapolateLeft: "clamp" });

  // Floating logic for Shot 3
  const shot3LocalFrame = frame - (shot1DurationFrames + shot2DurationFrames);
  const floatY = Math.sin(shot3LocalFrame / 15) * 20;

  return (
    <AbsoluteFill style={{ backgroundColor: '#050505', color: 'white', fontFamily }}>

      {/* Scene Audio */}
      <Sequence from={shot1DurationFrames + shot2DurationFrames}>
        <Audio src={staticFile("media/sfx_sci_fi_motion_norm.mp3")} volume={0.8} />
      </Sequence>

      <Series>
        {/* Shot 1: The Question */}
        <Series.Sequence durationInFrames={shot1DurationFrames}>
          <GridBackground />
          <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center' }}>
            {/* Spotlight */}
            <div
              style={{
                position: 'absolute',
                inset: 0,
                background: `radial-gradient(circle at 50% 40%, rgba(79, 172, 254, 0.4) ${spotlightRadius}%, transparent ${spotlightRadius + 20}%)`,
                opacity: 0.8
              }}
            />
            {/* Giant Question Mark */}
            <h1
              style={{
                fontSize: 450,
                fontWeight: 900,
                margin: 0,
                background: 'linear-gradient(180deg, #4facfe 0%, #00f2fe 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                transform: `scale(${questionMarkScale})`,
                filter: 'drop-shadow(0px 0px 40px rgba(79,172,254,0.6))',
                lineHeight: 1
              }}
            >
              ?
            </h1>
          </AbsoluteFill>

          <AbsoluteFill style={{ justifyContent: 'flex-end', paddingBottom: 100 }}>
            <div style={{ direction: 'rtl', flexWrap: 'wrap', willChange: 'transform' }}>
              <Captions
                captions={shot1Words}
                delay={-(Math.round(sceneStartGlobal * fps))}
                color="#ffffff"
                accentColor="#4facfe"
                fontSize={65}
                fontFamily={fontFamily}
                fontWeight={800}
                align="center"
              />
            </div>
          </AbsoluteFill>
          {/* SFX */}
          <Audio src={staticFile("media/pixabay_audio_a_sfx_whoosh_01_norm.mp3")} volume={0.6} />
        </Series.Sequence>

        {/* Shot 2: The Shift */}
        <Series.Sequence durationInFrames={shot2DurationFrames}>
          <GridBackground />
          <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center' }}>
            <div style={{ direction: 'rtl', flexWrap: 'wrap', willChange: 'transform' }}>
              <Captions
                captions={shot2Words}
                delay={-(Math.round(sceneStartGlobal * fps) + shot1DurationFrames)}
                color="#ffffff"
                accentColor="#ff2a5f"
                fontSize={80}
                fontFamily={fontFamily}
                fontWeight={900}
                align="center"
              />
            </div>
          </AbsoluteFill>

          {/* Letterbox Bars */}
          <div style={{ position: 'absolute', top: 0, left: 0, right: 0, height: `${barHeight}%`, backgroundColor: 'black', zIndex: 10 }} />
          <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, height: `${barHeight}%`, backgroundColor: 'black', zIndex: 10 }} />

          {/* SFX */}
          <Audio src={staticFile("media/pixabay_audio_a_sfx_ui_pop_norm.mp3")} volume={0.8} />
        </Series.Sequence>

        {/* Shot 3: AI & No-Code Dynamic Camera Canvas */}
        <Series.Sequence durationInFrames={shot3DurationFrames}>
          <GridBackground />

          {(() => {
            const vw = 4000;
            const vh = 4000;

            const wordPositions = shot3Words.map((word, i) => {
              if (i === shot3Words.length - 1) {
                return { x: 600, y: 1100 };
              }
              const angle = i * 2.39996; // golden angle approx
              const radius = 300 + i * 200;
              return {
                x: vw / 2 + Math.cos(angle) * radius,
                y: vh / 2 + Math.sin(angle) * radius,
              };
            });

            const icons = [
              { src: 'chatgpt.svg', x: 1500, y: 1500, size: 200, rotate: -15 },
              { src: 'webflow.svg', x: 2500, y: 1600, size: 180, rotate: 10 },
              { src: 'python.svg', x: 1800, y: 2800, size: 150, rotate: -5 },
              { src: 'bot.svg', x: 2600, y: 2400, size: 220, rotate: 20 },
              { src: 'brain.svg', x: 1200, y: 2200, size: 190, rotate: -25 },
              { src: 'code.svg', x: 2800, y: 1200, size: 160, rotate: 15 },
            ];

            let camX = wordPositions[0]?.x ?? vw / 2;
            let camY = wordPositions[0]?.y ?? vh / 2;
            let camZoom = 1;

            const shot3StartGlobalMs = (sceneStartGlobal * 1000) + (shot1DurationFrames / fps * 1000) + (shot2DurationFrames / fps * 1000);

            for (let i = 1; i < shot3Words.length; i++) {
              const wordStartFrame = (shot3Words[i].startMs - shot3StartGlobalMs) / 1000 * fps;

              const transition = spring({
                frame: shot3LocalFrame - wordStartFrame,
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

            camX += Math.sin(shot3LocalFrame / 30) * 20;
            camY += Math.cos(shot3LocalFrame / 30) * 20;

            const lastWordStartFrame = (shot3Words[shot3Words.length - 1].startMs - shot3StartGlobalMs) / 1000 * fps;
            const isZoomOutPhase = shot3LocalFrame >= lastWordStartFrame;
            const zoomOutProgress = spring({
              frame: isZoomOutPhase ? shot3LocalFrame - lastWordStartFrame : 0,
              fps,
              config: { damping: 14, mass: 1, stiffness: 100 }
            });

            camX = interpolate(zoomOutProgress, [0, 1], [camX, vw / 2]);
            camY = interpolate(zoomOutProgress, [0, 1], [camY, vh / 2]);
            camZoom = interpolate(zoomOutProgress, [0, 1], [camZoom, 0.25]);

            return (
              <AbsoluteFill>
                <Camera focusX={camX} focusY={camY} zoom={camZoom} viewportWidth={width} viewportHeight={1920}>
                  <div style={{ position: 'absolute', width: vw, height: vh, left: 0, top: 0 }}>
                    {icons.map((icon, i) => (
                      <Img
                        key={i}
                        src={staticFile(`media/icons/${icon.src}`)}
                        style={{
                          position: 'absolute',
                          left: icon.x,
                          top: icon.y,
                          width: icon.size,
                          height: icon.size,
                          transform: `translate(-50%, -50%) rotate(${icon.rotate}deg)`,
                          opacity: 0.4,
                          filter: 'blur(4px)'
                        }}
                      />
                    ))}

                    {/* SVG Path tracing */}
                    <svg style={{ position: 'absolute', width: vw, height: vh, left: 0, top: 0, pointerEvents: 'none', zIndex: 0 }}>
                      <defs>
                        <filter id="neon-glow">
                          <feGaussianBlur stdDeviation="8" result="coloredBlur" />
                          <feMerge>
                            <feMergeNode in="coloredBlur" />
                            <feMergeNode in="SourceGraphic" />
                          </feMerge>
                        </filter>
                      </defs>
                      {shot3Words.map((word, i) => {
                        if (i === 0) return null;
                        const prevPos = wordPositions[i - 1];
                        const pos = wordPositions[i];

                        const wordStartFrame = (word.startMs - shot3StartGlobalMs) / 1000 * fps;
                        const transition = spring({
                          frame: shot3LocalFrame - wordStartFrame,
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
                            stroke="#00f2fe"
                            strokeWidth={15}
                            strokeLinecap="round"
                            strokeDasharray="30 30"
                            filter="url(#neon-glow)"
                            style={{ opacity: 0.6 }}
                          />
                        );
                      })}
                    </svg>

                    {shot3Words.map((word, i) => {
                      const wordStartFrame = (word.startMs - shot3StartGlobalMs) / 1000 * fps;
                      const wordPop = spring({
                        frame: shot3LocalFrame - wordStartFrame,
                        fps,
                        config: { damping: 12, mass: 0.5, stiffness: 200 }
                      });

                      const nextWordStartFrame = i < shot3Words.length - 1 ? (shot3Words[i + 1].startMs - shot3StartGlobalMs) / 1000 * fps : 99999;
                      const isCurrent = shot3LocalFrame >= wordStartFrame && shot3LocalFrame < nextWordStartFrame;

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
                              ? '0 0 40px #4facfe, 0 0 80px #00f2fe'
                              : '0 0 20px rgba(79, 172, 254, 0.2)',
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
            );
          })()}
        </Series.Sequence>
      </Series>
    </AbsoluteFill>
  );
};
