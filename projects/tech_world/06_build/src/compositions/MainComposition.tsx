import React from 'react';
import { AbsoluteFill, Series, Audio, staticFile, useVideoConfig } from 'remotion';
import { Scene1 } from './Scene1';
import { Scene2 } from './Scene2';
import { Scene3 } from './Scene3';
import { Scene4 } from './Scene4';
import { Scene5 } from './Scene5';

// 176 frames for Scene1, 419 frames for Scene2. Total = 595.
export const MainComposition: React.FC = () => {
  const { fps } = useVideoConfig();

  return (
    <AbsoluteFill style={{ backgroundColor: '#050505' }}>
      
      {/* Global Voiceover Track */}
      <Audio src={staticFile("media/عالم التقنية_norm.wav")} />
      
      {/* Background Music (Optional, lowered volume) */}
      <Audio src={staticFile("media/tech_energetic_music_norm.mp3")} volume={0.1} />

      <Series>
        <Series.Sequence durationInFrames={176}>
          <Scene1 />
        </Series.Sequence>
        
        <Series.Sequence durationInFrames={419}>
          <Scene2 />
        </Series.Sequence>

        <Series.Sequence durationInFrames={155}>
          <Scene3 />
        </Series.Sequence>

        <Series.Sequence durationInFrames={132}>
          <Scene4 />
        </Series.Sequence>

        <Series.Sequence durationInFrames={138}>
          <Scene5 />
        </Series.Sequence>
      </Series>
    </AbsoluteFill>
  );
};
