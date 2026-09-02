import React from 'react';
import { Series } from 'remotion';
import { Scene1 } from './Scene1';
import { Scene2 } from './Scene2';
import { Scene3 } from './Scene3';
import { Scene4 } from './Scene4';

export const MainComposition: React.FC = () => {
  return (
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
      <Series.Sequence durationInFrames={119}>
        <Scene4 />
      </Series.Sequence>
    </Series>
  );
};
