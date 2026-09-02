import React from 'react';
import { AbsoluteFill, Sequence, Series, staticFile } from 'remotion';
import { Captions } from '../templates/elements/captions/captions/Captions';
import { Highlight } from '../engine/primitives/Highlight';
import { DeviceMockupZoom } from '../remotion/scenes/device-mockup-zoom';
import { loadFont } from "@remotion/google-fonts/Alexandria";
import timings from '../../../04_timings.json';

const { fontFamily } = loadFont();

export const Scene1: React.FC = () => {
  const fps = 30;
  // total scene1 duration is 148 frames
  const shot1DurationFrames = 75; // ~2.5s
  const shot2DurationFrames = 148 - 75; // 73 frames

  // Segment 0
  const sceneWords = timings.segments[0].words.map((w: any) => ({
    text: w.word.trim(),
    startMs: w.start * 1000,
    endMs: w.end * 1000,
  }));

  // split words for shot1 and shot2
  const shot1Words = sceneWords.filter(w => w.startMs < 2510);
  const shot2Words = sceneWords.filter(w => w.startMs >= 2510);

  return (
    <AbsoluteFill style={{ backgroundColor: '#050505', color: 'white', fontFamily: 'Alexandria, sans-serif' }}>
      <Series>
        {/* Shot 1: Phone Mockup */}
        <Series.Sequence durationInFrames={shot1DurationFrames}>
          <AbsoluteFill>
            <DeviceMockupZoom device="phone">
              <AbsoluteFill style={{ backgroundColor: '#111', justifyContent: 'center', alignItems: 'center' }}>
                <h1 style={{ color: '#00f2fe', fontSize: 60 }}>AI MAGIC</h1>
              </AbsoluteFill>
            </DeviceMockupZoom>
          </AbsoluteFill>
          <AbsoluteFill style={{ justifyContent: 'flex-end', paddingBottom: 100 }}>
            <div style={{ direction: 'rtl', flexWrap: 'wrap', willChange: 'transform' }}>
              <Captions
                kind="captions"
                captions={shot1Words}
                delay={0}
                color="#ffffff"
                accentColor="#4facfe"
                fontSize={60}
                fontFamily={fontFamily}
                fontWeight={800}
                align="center"
              />
            </div>
          </AbsoluteFill>
        </Series.Sequence>

        {/* Shot 2: Deep Zoom / Highlight */}
        <Series.Sequence durationInFrames={shot2DurationFrames}>
          <AbsoluteFill style={{ backgroundColor: '#0a0a0a', justifyContent: 'center', alignItems: 'center' }}>
            <Highlight variant="glow" color="#4facfe" delay={10} duration={15} holdFrames={30}>
              <div style={{ padding: '20px 40px', backgroundColor: 'rgba(0,0,0,0.6)', borderRadius: 24, border: '1px solid rgba(255,255,255,0.1)' }}>
                <div style={{ direction: 'rtl', flexWrap: 'wrap', willChange: 'transform' }}>
                  <Captions
                    kind="captions"
                    captions={shot2Words}
                    delay={-(shot1DurationFrames)} 
                    color="#ffffff"
                    accentColor="#4facfe"
                    fontSize={70}
                    fontFamily={fontFamily}
                    fontWeight={800}
                    align="center"
                  />
                </div>
              </div>
            </Highlight>
          </AbsoluteFill>
        </Series.Sequence>
      </Series>
    </AbsoluteFill>
  );
};
