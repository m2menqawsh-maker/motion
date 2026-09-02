// GENERATED — DO NOT EDIT
import React from 'react';
import { AbsoluteFill, Sequence, Audio, staticFile } from 'remotion';
import { NeonCyberCard } from '@templates/NeonCyberCard';
import { ZoomCarryBackground } from '@engine/transitions/ZoomCarryBackground';

export const Scene3: React.FC = () => {
  return (
    <AbsoluteFill>
      {/* Audio global واحد للـ VO */}
      <Audio src={staticFile("media/vo/test_vo.mp3")} />

      {/* خلفية مستمرة بـ zoom_carry */}
      <ZoomCarryBackground />

      {/* مكون المشهد الأساسي */}
      <Sequence from={0}>
        <NeonCyberCard />
      </Sequence>

      {/* SFX Sequences */}
      
      {/* SFX 0 locked to word frame 184 */}
      <Sequence from={184}>
        <Audio src={staticFile("media/sfx/impact_01.mp3")} />
      </Sequence>
    </AbsoluteFill>
  );
};
