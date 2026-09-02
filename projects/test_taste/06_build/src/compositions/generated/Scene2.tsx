// GENERATED — DO NOT EDIT
import React from 'react';
import { AbsoluteFill, Sequence, Audio, staticFile } from 'remotion';
import { HighlightCard } from '@templates/HighlightCard';
import { ZoomCarryBackground } from '@engine/transitions/ZoomCarryBackground';

export const Scene2: React.FC = () => {
  return (
    <AbsoluteFill>
      {/* Audio global واحد للـ VO */}
      <Audio src={staticFile("media/vo/test_vo.mp3")} />

      {/* خلفية مستمرة بـ zoom_carry */}
      <ZoomCarryBackground />

      {/* مكون المشهد الأساسي */}
      <Sequence from={0}>
        <HighlightCard />
      </Sequence>

      {/* SFX Sequences */}
      
      {/* SFX 0 locked to word frame 80 */}
      <Sequence from={80}>
        <Audio src={staticFile("media/sfx/whoosh_01.mp3")} />
      </Sequence>
    </AbsoluteFill>
  );
};
