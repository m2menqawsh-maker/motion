import React from 'react';
import { AbsoluteFill, Sequence, Audio, staticFile } from 'remotion';
import { Enter } from '@/engine/primitives/Enter';

export const Scene2: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: 'black', justifyContent: 'center', alignItems: 'center' }}>
      <Sequence from={1}>
         <Audio src={staticFile('media/sfx_whoosh.wav')} volume={0.6} />
      </Sequence>
      
      <div style={{ position: 'relative', width: 400, height: 600 }}>
        {/* Social Cards Stacking */}
        <Sequence from={5} durationInFrames={80}>
          <Enter scaleFrom={0.8} translateY={100} duration={15}>
            <div style={{ position: 'absolute', top: 50, left: 20, right: 20, height: 200, backgroundColor: '#222', borderRadius: 16, border: '1px solid #444', padding: 20, transform: 'rotate(-5deg)' }}>
              <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                <div style={{ width: 40, height: 40, borderRadius: '50%', backgroundColor: '#555' }} />
                <div style={{ flex: 1 }}>
                  <div style={{ height: 10, width: '60%', backgroundColor: '#555', borderRadius: 4, marginBottom: 5 }} />
                  <div style={{ height: 10, width: '40%', backgroundColor: '#444', borderRadius: 4 }} />
                </div>
              </div>
              <div style={{ marginTop: 20, height: 100, backgroundColor: '#333', borderRadius: 8 }} />
            </div>
          </Enter>
        </Sequence>

        <Sequence from={20} durationInFrames={65}>
          <Enter scaleFrom={0.8} translateY={100} duration={15}>
            <div style={{ position: 'absolute', top: 150, left: 20, right: 20, height: 200, backgroundColor: '#1a1a1a', borderRadius: 16, border: '1px solid #444', padding: 20, transform: 'rotate(3deg)' }}>
               <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                <div style={{ width: 40, height: 40, borderRadius: '50%', backgroundColor: '#555' }} />
                <div style={{ flex: 1 }}>
                  <div style={{ height: 10, width: '60%', backgroundColor: '#555', borderRadius: 4, marginBottom: 5 }} />
                  <div style={{ height: 10, width: '40%', backgroundColor: '#444', borderRadius: 4 }} />
                </div>
              </div>
              <div style={{ marginTop: 20, height: 100, backgroundColor: '#333', borderRadius: 8 }} />
            </div>
          </Enter>
        </Sequence>
        
        <Sequence from={35} durationInFrames={50}>
          <Enter scaleFrom={0.8} translateY={100} duration={15}>
            <div style={{ position: 'absolute', top: 250, left: 20, right: 20, height: 200, backgroundColor: '#111', borderRadius: 16, border: '1px solid #555', padding: 20, boxShadow: '0 10px 30px rgba(0,0,0,0.8)' }}>
               <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                <div style={{ width: 40, height: 40, borderRadius: '50%', backgroundColor: '#666' }} />
                <div style={{ flex: 1 }}>
                  <div style={{ height: 10, width: '60%', backgroundColor: '#666', borderRadius: 4, marginBottom: 5 }} />
                  <div style={{ height: 10, width: '40%', backgroundColor: '#555', borderRadius: 4 }} />
                </div>
              </div>
              <div style={{ marginTop: 20, height: 100, backgroundColor: '#444', borderRadius: 8 }} />
            </div>
          </Enter>
        </Sequence>
      </div>
    </AbsoluteFill>
  );
};
