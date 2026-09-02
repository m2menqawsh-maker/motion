import React from 'react';
import { AbsoluteFill, Sequence, Audio, staticFile } from 'remotion';
import { Enter } from '@/engine/primitives/Enter';
import { Pulse } from '@/engine/primitives/Pulse';

export const Scene4: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: 'black', justifyContent: 'center', alignItems: 'center', fontFamily: 'Inter, sans-serif' }}>
      
      <Sequence from={1}>
        <Enter translateY={50} duration={20}>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 40 }}>
            <div style={{ fontSize: 50, fontWeight: 900, color: 'white' }}>
              ابدأ ابني وتابعني لنكمل مع بعض
            </div>

            <Pulse count={Infinity} delay={0} intensity={1.05} period={30}>
              <div style={{ 
                backgroundColor: '#00FFFF', 
                color: 'black', 
                padding: '20px 60px', 
                borderRadius: 40, 
                fontSize: 30, 
                fontWeight: 'bold',
                boxShadow: '0 0 30px rgba(0,255,255,0.6)'
              }}>
                تابعني الآن
              </div>
            </Pulse>
          </div>
        </Enter>
      </Sequence>
      
    </AbsoluteFill>
  );
};
