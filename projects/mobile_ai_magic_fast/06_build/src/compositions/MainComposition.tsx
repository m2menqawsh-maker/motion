import React from 'react';
import { AbsoluteFill, Series, Audio, staticFile, useVideoConfig } from 'remotion';
import { Scene1 } from './Scene1';
import { Scene2 } from './Scene2';
import { Scene3 } from './Scene3';
import { Scene4 } from './Scene4';
import { Scene5 } from './Scene5';

export const MainComposition: React.FC = () => {
  const { fps } = useVideoConfig();

  return (
    <AbsoluteFill style={{ backgroundColor: '#050505' }}>
      
      {/* Global Voiceover Track */}
      <Audio src={staticFile("media/الموبايل الي بايدك_norm.wav")} />
      
      <Series>
        <Series.Sequence durationInFrames={148}>
          <Scene1 />
        </Series.Sequence>
        
        <Series.Sequence durationInFrames={88}>
          <Scene2 />
        </Series.Sequence>

        <Series.Sequence durationInFrames={165}>
          <Scene3 />
        </Series.Sequence>

        <Series.Sequence durationInFrames={44}>
          <Scene4 />
        </Series.Sequence>

        <Series.Sequence durationInFrames={90}>
          <Scene5 />
        </Series.Sequence>
      </Series>
    </AbsoluteFill>
  );
};
