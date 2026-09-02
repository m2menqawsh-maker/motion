import React from 'react';
import { AbsoluteFill, Sequence, Audio, staticFile } from 'remotion';
import { Enter } from '@/engine/primitives/Enter';

export const Scene3: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: 'black', justifyContent: 'center', alignItems: 'center' }}>
      <Sequence from={10}>
         <Audio src={staticFile('media/sfx_swoosh.wav')} volume={0.8} />
      </Sequence>
      
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 20, fontFamily: 'Inter, sans-serif' }}>
        <Sequence from={5}>
          <Enter scaleFrom={0.5} duration={10}>
            <div style={{ fontSize: 60, fontWeight: 900, color: 'white', textShadow: '0 0 40px rgba(0,255,255,0.5)' }}>الذكاء الاصطناعي اليوم</div>
          </Enter>
        </Sequence>

        <Sequence from={30}>
          <Enter scaleFrom={0.5} duration={10}>
            <div style={{ fontSize: 50, fontWeight: 700, color: '#aaa' }}>بيحول أي فكرة</div>
          </Enter>
        </Sequence>

        <Sequence from={60}>
          <Enter scaleFrom={0.1} duration={15}>
            <div style={{ fontSize: 80, fontWeight: 900, color: '#00FFFF', textShadow: '0 0 60px rgba(0,255,255,1)' }}>
              لمشروع حقيقي!
            </div>
          </Enter>
        </Sequence>
      </div>
    </AbsoluteFill>
  );
};
