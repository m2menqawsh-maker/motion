import React from 'react';
import { AbsoluteFill, useCurrentFrame, useVideoConfig, spring, interpolate } from 'remotion';
import { Captions } from '../templates/elements/captions/captions/Captions';
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

export const Scene2: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Segment 1
  const sceneWords = timings.segments[1].words.map((w: any) => ({
    text: w.word.trim(),
    startMs: w.start * 1000,
    endMs: w.end * 1000,
  }));

  const spotlightRadius = interpolate(frame, [0, 45], [0, 60], { extrapolateRight: "clamp" });
  const delayFrames = Math.round(4.97 * fps);

  return (
    <AbsoluteFill style={{ backgroundColor: '#050505', color: 'white', fontFamily }}>
      <GridBackground />
      <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center' }}>
        {/* Spotlight */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: `radial-gradient(circle at 50% 40%, rgba(255, 42, 95, 0.4) ${spotlightRadius}%, transparent ${spotlightRadius + 20}%)`,
            opacity: 0.8
          }}
        />
        <h1
          style={{
            fontSize: 250,
            fontWeight: 900,
            margin: 0,
            background: 'linear-gradient(180deg, #ff2a5f 0%, #ff7b93 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            filter: 'drop-shadow(0px 0px 40px rgba(255,42,95,0.6))',
            lineHeight: 1
          }}
        >
          CONSUMER
        </h1>
      </AbsoluteFill>

      <AbsoluteFill style={{ justifyContent: 'flex-end', paddingBottom: 100 }}>
        <div style={{ direction: 'rtl', flexWrap: 'wrap', willChange: 'transform' }}>
          <Captions
            kind="captions"
            captions={sceneWords}
            delay={-delayFrames}
            color="#ffffff"
            accentColor="#ff2a5f"
            fontSize={65}
            fontFamily={fontFamily}
            fontWeight={800}
            align="center"
          />
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
