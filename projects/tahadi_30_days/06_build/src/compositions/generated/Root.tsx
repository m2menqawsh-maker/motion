import React from 'react';
import { Composition, AbsoluteFill, Audio, staticFile, Sequence, OffthreadVideo } from 'remotion';
import { Scene1 } from './Scene1';
import { Scene2 } from './Scene2';
import { Scene3 } from './Scene3';
import { Scene4 } from './Scene4';
import { Scene5 } from './Scene5';
import { Scene6 } from './Scene6';
import { Scene7 } from './Scene7';
import { Scene8 } from './Scene8';
import { Highlight } from '../../engine/primitives/Highlight';

export const MainComposition: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: '#0A0C14' }}>
      {/* Unified Ambient Continuous Background */}
      <AbsoluteFill style={{ backgroundColor: '#000000' }}>
        <Sequence from={0} durationInFrames={1560}>
          <OffthreadVideo 
            src={staticFile("media/bg_code.mp4")} 
            style={{ width: '100%', height: '100%', objectFit: 'cover', opacity: 0.65 }} 
          />
        </Sequence>
      </AbsoluteFill>

      {/* Main Audio & BGM */}
      <Audio src={staticFile("media/music_tech.wav")} volume={0.12} />
      <Audio src={staticFile("media/vo_main.wav")} volume={1} />

      {/* SFX Tracks for Scene 1 */}
      <Sequence from={0}><Audio src={staticFile("media/sfx_pop.mp3")} volume={0.6} /></Sequence>
      <Sequence from={24}><Audio src={staticFile("media/sfx_swoosh.mp3")} volume={0.5} /></Sequence>
      <Sequence from={80}><Audio src={staticFile("media/sfx_pop.mp3")} volume={0.6} /></Sequence>
      <Sequence from={124}><Audio src={staticFile("media/sfx_swoosh.mp3")} volume={0.5} /></Sequence>

      {/* Scenes Timeline */}
      <Sequence from={ 0 } durationInFrames={ 184 }><Scene1 /></Sequence>
      <Sequence from={ 184 } durationInFrames={ 193 }><Scene2 /></Sequence>
      <Sequence from={ 377 } durationInFrames={ 234 }><Scene3 /></Sequence>
      <Sequence from={ 611 } durationInFrames={ 289 }><Scene4 /></Sequence>
      <Sequence from={ 900 } durationInFrames={ 240 }><Scene5 /></Sequence>
      <Sequence from={ 1140 } durationInFrames={ 210 }><Scene6 /></Sequence>
      <Sequence from={ 1350 } durationInFrames={ 170 }><Scene7 /></Sequence>
    </AbsoluteFill>
  );
};
