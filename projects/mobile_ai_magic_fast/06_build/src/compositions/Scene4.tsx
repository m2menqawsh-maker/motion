import React from 'react';
import { AbsoluteFill, useVideoConfig } from 'remotion';
import { Captions } from '../templates/elements/captions/captions/Captions';
import { Highlight } from '../engine/primitives/Highlight';
import { loadFont } from "@remotion/google-fonts/Alexandria";
import timings from '../../../04_timings.json';

const { fontFamily } = loadFont();

export const Scene4: React.FC = () => {
  const { fps } = useVideoConfig();

  // Segment 3
  const sceneWords = timings.segments[3].words.map((w: any) => ({
    text: w.word.trim(),
    startMs: w.start * 1000,
    endMs: w.end * 1000,
  }));
  
  const delayFrames = Math.round(13.39 * fps);

  return (
    <AbsoluteFill style={{ backgroundColor: '#050505', color: 'white', fontFamily, justifyContent: 'center', alignItems: 'center' }}>
      <Highlight variant="glow" color="#00f2fe" delay={10} duration={15} holdFrames={30}>
        <div style={{ padding: '40px 80px', backgroundColor: '#111', borderRadius: 32, border: '2px solid rgba(0, 242, 254, 0.3)' }}>
          <div style={{ direction: 'rtl', flexWrap: 'wrap', willChange: 'transform' }}>
            <Captions
              kind="captions"
              captions={sceneWords}
              delay={-delayFrames}
              color="#ffffff"
              accentColor="#00f2fe"
              fontSize={120}
              fontFamily={fontFamily}
              fontWeight={900}
              align="center"
            />
          </div>
        </div>
      </Highlight>
    </AbsoluteFill>
  );
};
