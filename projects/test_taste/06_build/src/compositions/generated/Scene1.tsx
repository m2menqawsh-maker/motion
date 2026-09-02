// GENERATED — DO NOT EDIT
import React from 'react';
import { AbsoluteFill, Sequence, Audio, staticFile } from 'remotion';
import { TitleScene } from '@templates/TitleScene';
import { ZoomCarryBackground } from '@engine/transitions/ZoomCarryBackground';

export const Scene1: React.FC = () => {
  return (
    <AbsoluteFill>
      {/* Audio global واحد للـ VO */}
      <Audio src={staticFile("media/vo/test_vo.mp3")} />

      {/* خلفية مستمرة بـ zoom_carry */}
      <ZoomCarryBackground />

      {/* مكون المشهد الأساسي */}
      <Sequence from={0}>
        <TitleScene />
      </Sequence>

      {/* SFX Sequences */}
      
      {/* SFX 0 locked to word frame 0 */}
      <Sequence from={0}>
        <Audio src={staticFile("media/sfx/pop_01.mp3")} />
      </Sequence>
    </AbsoluteFill>
  );
};
