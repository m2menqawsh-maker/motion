import React from 'react';
import { AbsoluteFill, useVideoConfig } from 'remotion';
import { Captions } from '../templates/elements/captions/captions/Captions';
import { loadFont } from "@remotion/google-fonts/Alexandria";
import timings from '../../../04_timings.json';

const { fontFamily } = loadFont();

export const Scene5: React.FC = () => {
  const { fps } = useVideoConfig();

  // Segment 4
  const sceneWords = timings.segments[4].words.map((w: any) => ({
    text: w.word.trim(),
    startMs: w.start * 1000,
    endMs: w.end * 1000,
  }));
  
  const delayFrames = Math.round(14.87 * fps);

  return (
    <AbsoluteFill style={{ backgroundColor: '#050505', color: 'white', fontFamily, justifyContent: 'center', alignItems: 'center' }}>
      
      {/* Profile Card / CTA */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 20, marginBottom: 60 }}>
         <img src="https://i.pravatar.cc/200" style={{ width: 150, height: 150, borderRadius: '50%', border: '4px solid #4facfe' }} />
         <div style={{ fontSize: 40, fontWeight: 'bold' }}>@tech_world</div>
         <div style={{ fontSize: 32, border: '2px solid white', borderRadius: 16, padding: '12px 40px', fontWeight: 'bold', backgroundColor: 'white', color: 'black' }}>
           Follow
         </div>
      </div>

      <AbsoluteFill style={{ justifyContent: 'flex-end', paddingBottom: 150 }}>
        <div style={{ direction: 'rtl', flexWrap: 'wrap', willChange: 'transform' }}>
          <Captions
            kind="captions"
            captions={sceneWords}
            delay={-delayFrames}
            color="#ffffff"
            accentColor="#4facfe"
            fontSize={70}
            fontFamily={fontFamily}
            fontWeight={800}
            align="center"
          />
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
