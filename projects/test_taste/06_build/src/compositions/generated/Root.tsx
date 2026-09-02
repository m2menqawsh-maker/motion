// GENERATED — DO NOT EDIT
// Hash: 56830c19e3644a161582ff4afa45206d
import React from 'react';
import { Composition, AbsoluteFill, Audio, staticFile, Sequence, OffthreadVideo, interpolate, useCurrentFrame } from 'remotion';
import { Scene1 } from './Scene1';
import { Scene2 } from './Scene2';
import { Scene3 } from './Scene3';


export const MainComposition: React.FC = () => {
  const frame = useCurrentFrame();
  const bgZoom = interpolate(frame, [0, 296], [1, 1.2]); // continuity.background.zoom_carry

  return (
    <AbsoluteFill>
      <AbsoluteFill style={{ transform: `scale(${bgZoom})` }}>
        <OffthreadVideo src={staticFile(`media/bg_code_intra.mp4`)} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
      </AbsoluteFill>
      <Audio src={staticFile("media/tech_energetic_music.mp3")} volume={0.05} />
      <Audio src={staticFile(`media/تعلم_البرمجة_norm.wav`)} volume={1} />
      <Sequence from={ 23 }><Audio src={staticFile("media/whoosh.mp3")} volume={0.063} /></Sequence>
      <Sequence from={ 124 }><Audio src={staticFile("media/pop.mp3")} volume={0.063} /></Sequence>
      <Sequence from={ 184 }><Audio src={staticFile("media/digital.mp3")} volume={0.063} /></Sequence>

      <AbsoluteFill>
        <Sequence from={ 0 } durationInFrames={ 80 }><Scene1 /></Sequence>
        <Sequence from={ 80 } durationInFrames={ 104 }><Scene2 /></Sequence>
        <Sequence from={ 184 } durationInFrames={ 112 }><Scene3 /></Sequence>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
